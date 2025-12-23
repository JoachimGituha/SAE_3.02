import socket
import threading
import mariadb
import sys
from rsa_tool import generer_cle_rsa, rsa_decrypt

#
# CONFIGURATION UTILISATEUR
# 

DB_HOST = "172.20.10.10"     
DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"









#
# !!! NE PAS TOUCHER !!!
#




print("CMD de lancement :", " ".join(sys.argv))



#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs / CLIENTS
#

ROUTEURS = {}
CLIENTS = {}

CLE_PRIVEE = None
CLE_PUBLIQUE = None


def recup_routeurs_client():
    global ROUTEURS,CLIENTS
    try:
        conn = mariadb.connect(
            host=DB_HOST,
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
    except Exception as e:
        print("[ERREUR DB] Impossible de charger routeurs/clients")




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

def envoie_donne_db(nom, ip, port, type_objet, cle_pub):
    try:
        conn = mariadb.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cur = conn.cursor()
    

        query = """
        INSERT INTO information (nom, adresse_ip, port, type, cle_publique)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            adresse_ip = VALUES(adresse_ip),
            port = VALUES(port),
            type = VALUES(type),
            cle_publique = VALUES(cle_publique)
        """

        cur.execute(query, (nom, ip, port, type_objet, cle_pub))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERREUR DB] Impossible d'enregistrer {nom}")



def envoyer(ip, port, message):
    s = socket.socket()
    s.connect((ip, port))
    s.send(message.encode())
    s.close()


#  
#   TRAITEMENT DES MESSAGES EN ENVOIE
#   

def traitement_message(nom,message):

    print(f"{nom} a reçu :", message)

    # Découper NOM_ROUTEUR|OIGNON_CHIFFRE
    parts = message.split("|", 1)  
    # permet de couper le message en 2 parties, exemple :
    # ["R2", "938472,384723,...."]

    if len(parts) != 2:
        print(f"{nom} : message invalide")
        return

    oignon_chiffre = parts[1]  # oignon chiffré qui est destiné à CE routeur

    # Déchiffrement de LA couche du routeur avec sa clé privée
    couche_dechiffree = rsa_decrypt(oignon_chiffre, CLE_PRIVEE)
    print(f"{nom} a déchiffré :", couche_dechiffree)

    # Découper NEXT|REST après déchiffrement
    parts = couche_dechiffree.split("|", 1)
    # permet de couper le message en 2 parties, exemple :
    # ["R3", "R2|CLIENT2|HELLO"]

    if len(parts) != 2:
        print(f"{nom} : couche invalide après déchiffrement")
        return

    next_hop = parts[0]  # pour avoir l'information de où envoyer le message (exemple : "R3")
    rest = parts[1]      # reste du message sous la forme "R2|CLIENT2|HELLO" (encore chiffré)

    # Si le prochain hop est un routeur
    if next_hop in ROUTEURS:
        nip, nport, cle_publique, next_hop_bdd = ROUTEURS[next_hop]
        envoyer(nip, nport, f"{next_hop}|{rest}")
        print(f"{nom} → a transmis à {next_hop}")

    # Si le prochain hop est un client
    elif next_hop in CLIENTS:
        nip, nport, cle_publique, next_hop_bdd = CLIENTS[next_hop]
        envoyer(nip, nport, rest)
        # le client recevra encore le message chiffré avec SA clé publique
        print(f"{nom} → message final envoyé au client !")

    else:
        print(f"{nom} : Next hop inconnu :", next_hop)



#   
#   TRAITEMENT DES MESSAGES EN RECEPTION
#   

#Pour le décodage des messages sans crash car message trop long 
def recv_all(conn):
    data = b""
    while True:
        part = conn.recv(8192)
        if not part:
            break
        data += part
    return data


def traitement_reception(nom,ip,port):
    global ROUTEURS, CLIENTS

    print(f"{nom} écoute sur {ip}:{port}")

    s = socket.socket()
    s.bind((ip, port))
    s.listen(5)


    while True:
        conn, addr = s.accept()
        message = recv_all(conn).decode()

        conn.close()

        print(f"[{nom}] Message reçu :", message)
        
        
        if message == "rechargement_db":
            print(f"[{nom}] Rechargement DB demandé par le Master")
            ROUTEURS, CLIENTS = recup_routeurs_client()
            print(f"[{nom}] DB rechargée")
            continue

        # chaque message reçu = NOUVEAU THREAD
        threading.Thread(target=traitement_message, args=(nom, message)).start()



def base_de_donne(nom, port):
    global CLE_PUBLIQUE, CLE_PRIVEE

    ip_locale = get_ip()

    # Génération RSA du routeur
    CLE_PUBLIQUE, CLE_PRIVEE = generer_cle_rsa()
    pub_str = f"{CLE_PUBLIQUE[0]},{CLE_PUBLIQUE[1]}"

    # Publier routeur + clé publique
    envoie_donne_db(nom, ip_locale, port, "routeur", pub_str)

    # Charger la DB
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