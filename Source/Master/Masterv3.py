import socket
import random
import mariadb
from gui_master import *

#
# Déclaration pour l'interface graphique
#

dernier_reponse = None

#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs / CLIENTS
#

ROUTEURS = {}
CLIENTS = {}


def recup_routeurs_client():
    global ROUTEURS, CLIENTS  # créer une variable local
    conn = mariadb.connect(
        host="172.20.10.10",
        user="toto",
        password="toto",
        database="table_routage"
    )
    cur = conn.cursor()

    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM routeurs WHERE type='routeur'")
    rows_routeurs = cur.fetchall()


    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM routeurs WHERE type='client'")
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
        host="172.20.10.10",      # adresse du serveur MariaDB
        user="toto",
        password="toto",
        database="table_routage"
    )
    cur = conn.cursor()

    query = """
    INSERT INTO routeurs (nom, adresse_ip, port, type)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        adresse_ip = VALUES(adresse_ip),
        port = VALUES(port),
        type = VALUES(type)
    """

    cur.execute(query, (nom, ip, port, type_objet))
    conn.commit()
    conn.close()

ip_locale = get_ip()
envoie_donne_db("MASTER", ip_locale, 6000, "master")





def generer_chemin(ROUTEURS, nombre_sauts):
    return random.sample(list(ROUTEURS.keys()), nombre_sauts)





def master(gui):
    global dernier_reponse

    
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

        parts = data.split()

        nom_client = parts[0]        # exemple : "CLIENT1"
        nb_sauts = int(parts[-1])    # exmeple : 3


        liste_routeurs = list(ROUTEURS.keys()) #permet de transformer en vrai liste python

        if nb_sauts > len(liste_routeurs):
            nb_sauts = len(liste_routeurs)

        # On fabrique un chemin très simple ici :
        ### chemin random avec le nombre de  routeur
        
        # Tirage aléatoire AVEC mélange
        chemin = random.sample(liste_routeurs, nb_sauts)  # prends les NB_SAUTS premiers
        # Exemple : ["R1", "R2"]
            
        # transforme la liste en texte
        reponse = ",".join(chemin)

        
        info = f"{nom_client}:{reponse}"
        gui.signal_chemin.emit(info)


        conn.send(reponse.encode())
        print("Chemin envoyé :", reponse)

        conn.close()


