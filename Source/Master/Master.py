import socket
import random

routeurs = {
    "R1": ("172.20.10.2", 5001),
    "R2": ("172.20.10.3", 5002),
    "R3": ("172.20.10.4", 5003)
}

def generer_chemin(routeurs, nombre_sauts):
    return random.sample(list(routeurs.keys()), nombre_sauts)





def master():
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

        nb_sauts = int(data.split(" ")[1])


        liste_routeurs = list(routeurs.keys()) #permet de transformer en vrai liste python

        if nb_sauts > len(liste_routeurs):
            nb_sauts = len(liste_routeurs)

        # On fabrique un chemin très simple ici :
        ### chemin random avec le nombre de  routeur
        
        # Tirage aléatoire AVEC mélange
        chemin = random.sample(liste_routeurs, nb_sauts)  # prends les NB_SAUTS premiers
        # Exemple : ["R1", "R2"]
            
        # transforme la liste en texte
        reponse = ",".join(chemin)

        conn.send(reponse.encode())
        print("Chemin envoyé :", reponse)

        conn.close()

if __name__ == "__main__":
    master()