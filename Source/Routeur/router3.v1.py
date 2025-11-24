import socket
import threading

# dictionnaire : routeurs
ROUTEURS = {
    "R1": ("172.20.10.2", 5001),
    "R2": ("172.20.10.3", 5002),
    "R3": ("172.20.10.4", 5003)
}

# dictionnaire : clients
CLIENTS = {
    "CLIENT1": ("172.20.10.7", 6002),
    "CLIENT2": ("172.20.10.8", 6001)
}

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
        nip, nport = ROUTEURS[next_hop]
        envoyer(nip, nport, rest)
        print(f"{nom} → a transmis à {next_hop}")

    # Si le prochain hop est un client
    elif next_hop in CLIENTS:
        nip, nport = CLIENTS[next_hop]
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

def routeur(nom, ip, port):
    t = threading.Thread(target=traitement_reception, args=(nom, ip, port))
    t.start()


if __name__ == "__main__":
    routeur("R3", "172.20.10.4", 5003)
