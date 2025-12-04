import socket
import threading
import mariadb
import sys



#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs / CLIENTS
#

ROUTEURS = {}
CLIENTS = {}


def recup_routeurs_client():
    global ROUTEURS,CLIENTS
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




def envoyer(ip, port, message):
    s = socket.socket()
    s.connect((ip, port))
    s.send(message.encode())
    s.close()


#   -   -   -   -   -   -   -   -   -   -
#   TRAITEMENT DES MESSAGES EN ENVOIE
#   -   -   -   -   -   -   -   -   -   -

def traitement_message(nom,message):

    print(f"{nom} a reçu :", message )

    # Découper NEXT|REST
    parts = message .split("|", 1) # permet de couper le message en 2 parties, exemple : ["R3", "R2|CLIENT2|HELLO"]
    next_hop = parts[0] # pour avoir l'information de ou envoyer le message (exemple : "R3")
    rest = parts[1]   # reste du message sous la forme "R2|CLIENT2|HELLO"

    # Si le prochain hop est un routeur
    if next_hop in ROUTEURS:
        nip, nport, cle_publique, next_hop_bdd = ROUTEURS[next_hop]
        envoyer(nip, nport, rest)
        print(f"{nom} → a transmis à {next_hop}")

    # Si le prochain hop est un client
    elif next_hop in CLIENTS:
        nip, nport, cle_publique, next_hop_bdd = CLIENTS[next_hop]
        envoyer(nip, nport, rest)
        print(f"{nom} → message final envoyé au client !")

    else:
        print(f"{nom} : Next hop inconnu :", next_hop)



#   -   -   -   -   -   -   -   -   -   -
#   TRAITEMENT DES MESSAGES EN RECEPTION
#   -   -   -   -   -   -   -   -   -   -
def traitement_reception(nom,ip,port):
    print(f"{nom} écoute sur {ip}:{port}")

    s = socket.socket()
    s.bind((ip, port))
    s.listen(5)


    while True:
        conn, addr = s.accept()
        message = conn.recv(1024).decode()
        conn.close()

        # chaque message reçu = NOUVEAU THREAD
        threading.Thread(target=traitement_message, args=(nom, message)).start()

def base_de_donne(nom, port):
    ip_locale = get_ip()
    envoie_donne_db(nom, ip_locale, port, "routeur")
    recup_routeurs_client()



#
# Définition principal 
#

def routeur(nom, port):
    base_de_donne(nom, port)
    t = threading.Thread(target=traitement_reception, args=(nom, "0.0.0.0", port))
    t.start()



if __name__ == "__main__":
    # Vérification des arguments
    if len(sys.argv) != 3:
        print("Utilisation : python3 routeur.py <NOM_ROUTEUR> <PORT>")
        sys.exit(1)

    nom_routeur = sys.argv[1]
    port_routeur = int(sys.argv[2])

    routeur(nom_routeur, port_routeur)