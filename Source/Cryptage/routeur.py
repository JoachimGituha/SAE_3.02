import socket
import threading
import mariadb
import sys
from rsa_tool import generer_cle_rsa, rsa_decrypt, rsa_encrypt

DB_HOST = "172.20.10.10"     
DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"

ROUTEURS = {}
CLIENTS = {}
CLE_PRIVEE = None
CLE_PUBLIQUE = None

def recup_routeurs_client():
    global ROUTEURS, CLIENTS
    conn = mariadb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='routeur'")
    rows_r = cur.fetchall()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='client'")
    rows_c = cur.fetchall()
    conn.close()
    ROUTEURS = {nom: (ip, port, cp, nh) for nom, ip, port, cp, nh in rows_r}
    CLIENTS = {nom: (ip, port, cp, nh) for nom, ip, port, cp, nh in rows_c}

def envoie_donne_db(nom, ip, port, type_objet, cle_pub):
    conn = mariadb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    query = """
    INSERT INTO information (nom, adresse_ip, port, type, cle_publique)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE adresse_ip = VALUES(adresse_ip), port = VALUES(port), cle_publique = VALUES(cle_publique)
    """
    cur.execute(query, (nom, ip, port, type_objet, cle_pub))
    conn.commit()
    conn.close()

def traitement_message(nom_moi, message_full):
    # Format reçu : "NOM_MOI|OIGNON_CHIFFRE"
    try:
        parts = message_full.split("|", 1)
        oignon_chiffre = parts[1]
        
        # Déchiffrement de la couche
        dechiffre = rsa_decrypt(oignon_chiffre, CLE_PRIVEE)
        
        # Format déchiffré : "SUIVANT|RESTE_OIGNON"
        p_next = dechiffre.split("|", 1)
        suivant = p_next[0]
        reste = p_next[1]
        
        if suivant in ROUTEURS:
            ip, port, _, _ = ROUTEURS[suivant]
            print(f"Transmis au routeur {suivant}")
            s = socket.socket()
            s.connect((ip, port))
            s.send(f"{suivant}|{reste}".encode())
            s.close()
        elif suivant in CLIENTS:
            ip, port, _, _ = CLIENTS[suivant]
            print(f"Transmis au client final {suivant}")
            s = socket.socket()
            s.connect((ip, port))
            s.send(reste.encode()) # Le client reçoit le message encore chiffré sous sa propre clé
            s.close()
    except Exception as e:
        print(f"Erreur traitement : {e}")

def ecoute(nom, port):
    s = socket.socket()
    s.bind(("0.0.0.0", port))
    s.listen(5)
    print(f"Routeur {nom} prêt sur {port}")
    while True:
        conn, addr = s.accept()
        msg = conn.recv(8192).decode()
        conn.close()
        threading.Thread(target=traitement_message, args=(nom, msg)).start()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    nom_r, port_r = sys.argv[1], int(sys.argv[2])
    
    CLE_PUBLIQUE, CLE_PRIVEE = generer_cle_rsa()
    pub_str = f"{CLE_PUBLIQUE[0]},{CLE_PUBLIQUE[1]}"
    
    envoie_donne_db(nom_r, "127.0.0.1", port_r, "routeur", pub_str) # Remplacer par get_ip() en réel
    recup_routeurs_client()
    ecoute(nom_r, port_r)
