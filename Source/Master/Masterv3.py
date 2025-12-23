import socket
import random
import mariadb
from gui_master import *



#
# CONFIGURATION UTILISATEUR
# 
   
DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"









#
# !!! NE PAS TOUCHER !!!
#








#
# Déclaration pour l'interface graphique
#

dernier_reponse = None

#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs / CLIENTS
#

ROUTEURS = {}
CLIENTS = {}

#
# IP + Port pour les envoies DB
#

MASTER_IP = get_ip()
MASTER_PORT = 6000


def recup_routeurs_client():
    global ROUTEURS, CLIENTS  # créer une variable local
    conn = mariadb.connect(
        host=MASTER_IP,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor()

    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM information WHERE type='routeur'")
    rows_routeurs = cur.fetchall()


    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM information WHERE type='client'")
    rows_clients = cur.fetchall()

    conn.close()

    ROUTEURS = {}
    for nom, ip, port, cle_publique, next_hop in rows_routeurs:
        ROUTEURS[nom] = (ip, port, cle_publique, next_hop)
    
    print(ROUTEURS)

    CLIENTS = {}
    for nom, ip, port, cle_publique, next_hop in rows_clients:
        CLIENTS[nom] = (ip, port, cle_publique, next_hop)
    
    print(CLIENTS)

    return ROUTEURS,CLIENTS



#
# RECUPERATION @IP POUR L'ENVOIE VERS LA DB
#

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # création d'un socket UDP vide
    s.connect(("8.8.8.8", 80)) # Créer une connexion vers google pour savoir quelle @ip on utilise sans envoyer de packet
    ip = s.getsockname()[0] #getsockname() -> envoie ('172.20.10.5', 54321) et avec [0] on récuper juste l'@ip
    s.close()
    return ip


#
# Envoies des données à la DB sur le master
#

def envoie_donne_db(nom, ip, port, type_objet):
    conn = mariadb.connect(
        host=MASTER_IP,      # adresse du serveur MariaDB
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor()

    query = """
    INSERT INTO information (nom, adresse_ip, port, type)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        adresse_ip = VALUES(adresse_ip),
        port = VALUES(port),
        type = VALUES(type)
    """

    cur.execute(query, (nom, ip, port, type_objet))
    conn.commit()
    conn.close()




#
# Définition principal / Qui permet la génération de chemnin 
#

def master(gui):
    global dernier_reponse

    #
    # Initialisation du serveur en mode écoute
    #
    host = "0.0.0.0"
    port = 6000  # Port du master

    server = socket.socket()
    server.bind((host, port))
    server.listen(5)

    print("MASTER en écoute sur le port 6000...")

    while True:
        conn, addr = server.accept()
        print("Client connecté :", addr)

        data = conn.recv(1024).decode()
        print("Reçu du client :", data)

        if not data:
            print("Connexion acceptée (aucune requête)")
            conn.close()
            continue

        parts = data.split()

        if len(parts) < 4:
            print("Requête invalide :", data)
            conn.close()
            continue

        nom_client  = parts[0] # exemple : "CLIENT1"
        client_dest = parts[2] # exemple : "CLIENT2"
        nb_sauts    = int(parts[3]) # exmeple : 3 

        #En cas de chemin client vers client donc client interconncter
        if nb_sauts == 1:
            nh_src = CLIENTS[nom_client][3]
            if nh_src and client_dest in nh_src.split(","):

                # Chemin logique vide (aucun routeur)
                chemin = []

                reponse = ""  # aucun routeur traversé
                info = f"{nom_client}:DIRECT"

                gui.dernier_reponse = "DIRECT"
                gui.signal_chemin.emit(info)

                conn.send("DIRECT".encode())
                conn.close()
                continue


        if client_dest not in CLIENTS:
            print("Client destination inconnu :", client_dest)
            conn.close()
            continue

        nh_dest = CLIENTS[client_dest][3]



        #
        # Génération du chemin en respectant les next hop et la topologie !!!!!!!
        #
        MAX_TRY = 500
        chemins_valides = []

        for _ in range(MAX_TRY):
            chemin = []

            # next hop du client source -> routeurs uniquement
            nh_src = CLIENTS[nom_client][3]
            if not nh_src:
                continue

            candidats_src = [
                r for r in nh_src.split(",")
                if r in ROUTEURS
            ]

            if not candidats_src:
                continue

            courant = random.choice(candidats_src)
            chemin.append(courant)

            # construction du chemin
            while len(chemin) < nb_sauts:
                nh = ROUTEURS[courant][3]
                if not nh:
                    break

                candidats = [
                    r for r in nh.split(",")
                    if r in ROUTEURS
                ]


                if not candidats:
                    break

                courant = random.choice(candidats)
                chemin.append(courant)

            # longueur exacte
            if len(chemin) != nb_sauts:
                continue

            # vérification finale vers client destination
            nh_dest = CLIENTS[client_dest][3]
            if nh_dest:
                dest_ok = nh_dest.split(",")
                if chemin[-1] in dest_ok:
                    chemins_valides.append(tuple(chemin))

        # aucun chemin valide
        if not chemins_valides:
            conn.send("NO_PATH".encode())
            conn.close()
            continue

        # dédoublonnage + hasard réel
        chemins_uniques = list(set(chemins_valides))
        chemin = list(random.choice(chemins_uniques))




        # transforme la liste en texte
        reponse = ",".join(chemin)

        info = f"{nom_client}:{reponse}"
        gui.dernier_reponse = reponse
        gui.signal_chemin.emit(info)

        conn.send(reponse.encode())
        print("Chemin envoyé :", reponse)

        conn.close()



