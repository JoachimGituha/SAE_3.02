import socket
import threading
import mariadb
import sys

# dictionnaire des adresses des routeurs
ROUTEURS = {}

#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs
#

ROUTEURS = {}

def recup_routeurs():
    conn = mariadb.connect(
        host="172.20.10.10",
        user="toto",
        password="toto",
        database="table_routage"
    )
    cur = conn.cursor()

    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM routeurs WHERE type='routeur'")
    rows = cur.fetchall()

    conn.close()

    ROUTEURS = {}
    for nom, ip, port, cle_publique, next_hop in rows:
        ROUTEURS[nom] = (ip, port, cle_publique, next_hop)
    
    print(ROUTEURS)

    return ROUTEURS

ROUTEURS = recup_routeurs()


   

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





def boucle_recevoir(ip, port):
    s = socket.socket()
    s.bind((ip, port))
    s.listen(1)

    print(f"[THREAD] Client en écoute sur {ip}:{port} ...")

    while True:
        conn, addr = s.accept()
        message = conn.recv(1024).decode()
        conn.close()

        print("\n Message reçu :", message)



def demander_chemin_au_master(nom):
    nb = input("Nombre de sauts voulus : ")
    
    s = socket.socket()
    s.connect(("172.20.10.10", 6000))  # IP et port du MASTER
    s.send(f"{nom} GET_PATH {nb}".encode())

    data = s.recv(1024).decode()
    s.close()

    # Transforme "R1,R2" en ["R1", "R2"]
    return data.split(",")

def construire_oignon(chemin, dest_client, message_final):
    msg = dest_client + "|" + message_final   # destination dynamique

    # remonte le chemin à l’envers
    for routeur in reversed(chemin):
        msg = routeur + "|" + msg

    return msg

def envoyer_message(ip, port, message):
    s = socket.socket()
    s.connect((ip, port))
    s.send(message.encode())
    s.close()


def mode_envoyer(nom):
    chemin = demander_chemin_au_master(nom)
    print("Chemin reçu :", chemin)

    dest = input("Envoyer à quel client ? (CLIENT1 / CLIENT2 / CLIENT3) : ")

    message = input("Message à envoyer : ")

    onion = construire_oignon(chemin, dest, message)
    print("Oignon construit :", onion)

    premier_routeur = chemin[0]
    ip, port, cle_publique, next_hop = ROUTEURS[premier_routeur]

    envoyer_message(ip, port, onion)


def client(nom, port):

    print(f"--- Démarrage du {nom} sur le port {port} ---")

    #Envoie dans le DB
    ip_locale = get_ip()
    envoie_donne_db(nom, ip_locale, port, "client")

    #Recupérer via DB les routeurs et leurs info
    global ROUTEURS
    ROUTEURS = recup_routeurs()


    print("1 = envoyer un message")
    t = threading.Thread(target=boucle_recevoir, args=("0.0.0.0", port), daemon=True)
    t.start()

    choix = input("Votre choix : ")

    if choix == "1":
        t2 = threading.Thread(target=mode_envoyer, args=(nom,))
        t2.start()

    else:
        print("Choix invalide.")



if __name__ == "__main__":
    # Vérification des arguments
    if len(sys.argv) != 3:
        print("Utilisation : python3 client.py <NOM_CLIENT> <PORT>")
        sys.exit(1)

    nom_client = sys.argv[1]
    port_client = int(sys.argv[2])

    client(nom_client, port_client)