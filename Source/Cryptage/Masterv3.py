import socket
import random
import mariadb
from rsa_tool import rsa_encrypt # Optionnel si le master doit notifier

DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

MASTER_IP = get_ip()

def recup_routeurs_client():
    conn = mariadb.connect(host=MASTER_IP, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='routeur'")
    rows_r = cur.fetchall()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='client'")
    rows_c = cur.fetchall()
    conn.close()
    
    r_dict = {nom: (ip, port, cp, nh) for nom, ip, port, cp, nh in rows_r}
    c_dict = {nom: (ip, port, cp, nh) for nom, ip, port, cp, nh in rows_c}
    return r_dict, c_dict

def master(gui):
    server = socket.socket()
    server.bind(("0.0.0.0", 6000))
    server.listen(5)
    print("MASTER prêt...")

    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode()
        if not data: continue
        
        parts = data.split()
        if "GET_PATH" in parts:
            nom_src = parts[0]
            nom_dest = parts[2]
            nb_sauts = int(parts[3])
            
            # (Ici insérer votre algorithme de génération de chemin existant)
            # Pour l'exemple, on simule un chemin :
            r_dict, c_dict = recup_routeurs_client()
            chemin = random.sample(list(r_dict.keys()), min(nb_sauts, len(r_dict)))
            
            reponse = ",".join(chemin)
            conn.send(reponse.encode())
        conn.close()
