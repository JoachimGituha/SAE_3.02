import socket
import threading

# dictionnaire des adresses des routeurs
ROUTEURS = {
    "R1": ("172.20.10.2", 5001),
    "R2": ("172.20.10.3", 5002),
    "R3": ("172.20.10.4", 5003)
}

CLIENT_IP = "0.0.0.0"
CLIENT_PORT = 6001    

def boucle_recevoir():
    s = socket.socket()
    s.bind((CLIENT_IP, CLIENT_PORT))
    s.listen(1)

    print(f"[THREAD] Client en écoute sur {CLIENT_IP}:{CLIENT_PORT} ...")

    while True:
        conn, addr = s.accept()
        message = conn.recv(1024).decode()
        conn.close()

        print("\n📩 Message reçu :", message)



def demander_chemin_au_master():
    nb = input("Nombre de sauts voulus : ")
    
    s = socket.socket()
    s.connect(("172.20.10.10", 6000))  # IP et port du MASTER
    s.send(f"GET_PATH {nb}".encode())

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


def mode_envoyer():
    chemin = demander_chemin_au_master()
    print("Chemin reçu :", chemin)

    dest = input("Envoyer à quel client ? (CLIENT1 / CLIENT2 / CLIENT3) : ")

    message = input("Message à envoyer : ")

    onion = construire_oignon(chemin, dest, message)
    print("Oignon construit :", onion)

    premier_routeur = chemin[0]
    ip, port = ROUTEURS[premier_routeur]

    envoyer_message(ip, port, onion)

def mode_recevoir():
    print(f"Client en écoute sur {CLIENT_IP}:{CLIENT_PORT} ...")

    s = socket.socket()
    s.bind((CLIENT_IP, CLIENT_PORT))
    s.listen(1)

    conn, addr = s.accept()
    data = conn.recv(1024).decode()
    conn.close()

    print("\n📩 Message reçu :", data)


def client():
    print("1 = envoyer un message")
    t = threading.Thread(target=boucle_recevoir, daemon=True)
    t.start()

    choix = input("Votre choix : ")

    if choix == "1":
        t2 = threading.Thread(target=mode_envoyer)
        t2.start()

    else:
        print("Choix invalide.")


if __name__ == "__main__":
    client()
