import socket
import threading
import mariadb
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox, QComboBox
)
from PyQt5.QtCore import pyqtSignal, QObject



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
#
#
# Back - END 
#
#
#


# dictionnaire des adresses des routeurs
ROUTEURS = {}

#
# RECUPERATION DES INFOS POUR LES ROUTEURS DE LA DB + Dictionnaire des routeurs
#

ROUTEURS = {}

def recup_routeurs(serveur_ip):
    conn = mariadb.connect(
        host=serveur_ip,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor()

    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM information WHERE type='routeur'")
    rows = cur.fetchall()

    conn.close()

    ROUTEURS = {}
    for nom, ip, port, cle_publique, next_hop in rows:
        ROUTEURS[nom] = (ip, port, cle_publique, next_hop)
    
    print(ROUTEURS)

    return ROUTEURS



# Recuperer les clients 

def recup_client(serveur_ip):
    conn = mariadb.connect(
        host=serveur_ip,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor()

    cur.execute("SELECT nom, adresse_ip, port, cle_publique ,next_hop FROM information WHERE type='client'")
    rows = cur.fetchall()

    conn.close()

    CLIENT = {}
    for nom, ip, port, cle_publique, next_hop in rows:
        CLIENT[nom] = (ip, port, cle_publique, next_hop)
    
    print(CLIENT)

    return CLIENT


   

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



def envoie_donne_db(nom, ip, port, type_objet, serveur_ip):
    conn = mariadb.connect(
        host=serveur_ip,      # adresse du serveur MariaDB
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

        # ENVOI AU GUI
        if "gui_instance" in globals():
            gui_instance.bus.message_received.emit(message)


def demander_chemin_au_master(nom, dest, nb, master_ip, master_port):
    s = socket.socket()
    s.connect((master_ip, master_port))
    s.send(f"{nom} GET_PATH {dest} {nb}".encode())

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



def mode_envoyer(nom, dest=None, message=None, nb=None, master_ip=None, master_port=None):
    
    # Mode GUI → paramètres fournis
    if dest is not None and message is not None and nb is not None:
        chemin = demander_chemin_au_master(nom, dest, nb, master_ip, master_port)


    print("Chemin reçu :", chemin)

    onion = construire_oignon(chemin, dest, message)
    print("Oignon construit :", onion)

    premier_routeur = chemin[0]
    ip, port, cle_publique, next_hop = ROUTEURS[premier_routeur]
    envoyer_message(ip, port, onion)



def client(nom, port):

    print(f"--- Démarrage du {nom} sur le port {port} ---")

    ip_locale = get_ip()




    t = threading.Thread(target=boucle_recevoir, args=("0.0.0.0", port), daemon=True)
    t.start()




#
# 
# 
# FRONT - END 
#
#
#



# -------------------------
# Thread communicant → UI
# -------------------------
class SignalBus(QObject):
    message_received = pyqtSignal(str)


# -------------------------
# Interface Client
# -------------------------
class ClientGUI(QWidget):

    def __init__(self, nom, port):
        super().__init__()

        self.client_ip = get_ip()
        self.client_port = port  # venant du back-end
        self.client_name = nom 
        self.serveur_ip = "172.20.10.10"

        self.setWindowTitle(f"Client : {self.client_name}")
        self.setGeometry(300, 300, 450, 450)

        

        self.master_ip = "0.0.0.0"
        self.master_port = 6000
        layout = QVBoxLayout()
        # -------------------------
        # Connexion au Master
        # -------------------------
        layout.addWidget(QLabel("Adresse du Master :"))

        self.input_master_ip = QLineEdit()
        self.input_master_ip.setPlaceholderText("Ex : 172.20.10.10")
        self.input_master_ip.setText("172.20.10.10")
        layout.addWidget(self.input_master_ip)

        layout.addWidget(QLabel("Port du Master :"))

        self.input_master_port = QLineEdit()
        self.input_master_port.setPlaceholderText("Ex : 6000")
        self.input_master_port.setText("6000")
        layout.addWidget(self.input_master_port)

        btn_connect = QPushButton("Se connecter au Master (Rechargement de la DB)")
        btn_connect.clicked.connect(self.test_connect_master)
        
        layout.addWidget(btn_connect)

        self.label_status = QLabel("État : Déconnecté")
        layout.addWidget(self.label_status)


        # Signaux
        self.bus = SignalBus()
        self.bus.message_received.connect(self.on_message_received)

        

        # Infos réseau
        layout.addWidget(QLabel(f"IP Client : {self.client_ip}"))
        layout.addWidget(QLabel(f"Port : {self.client_port}"))
        layout.addWidget(QLabel(f"Master : {self.master_ip}:{self.master_port}"))

        # -------------------------
        # Menu déroulant depuis MariaDB
        # -------------------------
        layout.addWidget(QLabel("Choisir le destinataire :"))

        self.combo_users = QComboBox()
        self.combo_users.addItem("Chargement...")

        self.combo_users = QComboBox()
        self.combo_users.addItem("Non connecté")
        layout.addWidget(self.combo_users)


        layout.addWidget(self.combo_users)

        # -------------------------
        # Messages reçus
        # -------------------------
        layout.addWidget(QLabel("Messages reçus :"))

        self.text_recv = QTextEdit()
        self.text_recv.setReadOnly(True)
        layout.addWidget(self.text_recv)

        # Zone pour envoyer un message
        self.input_msg = QLineEdit()
        self.input_msg.setPlaceholderText("Entrez un message...")
        layout.addWidget(self.input_msg)

        btn_send = QPushButton("Envoyer")
        btn_send.clicked.connect(self.send_message)
        layout.addWidget(btn_send)

        self.setLayout(layout)

        # Case Nombre de saut 
        layout.addWidget(QLabel("Nombre de sauts :"))

        self.combo_hops = QComboBox()
        self.combo_hops.addItems(["1", "2", "3", "4", "5"])
        layout.addWidget(self.combo_hops)


    #
    # Test connexion master
    #

    def test_connect_master(self):
        ip = self.input_master_ip.text().strip()
        port = int(self.input_master_port.text().strip())

        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect((ip, port))
            s.close()

            self.label_status.setText("État : Connecté")
            self.master_ip = ip
            self.master_port = port
            self.serveur_ip = ip

            envoie_donne_db(self.client_name,self.client_ip,self.client_port,"client",self.serveur_ip)
            # Recharge la DB lors de la connexion au master
            global ROUTEURS, CLIENT
            ROUTEURS = recup_routeurs(self.serveur_ip)
            CLIENT = recup_client(self.serveur_ip)

            #Recharge pour la liste des clients 

            self.combo_users.clear()
            if CLIENT:
                self.combo_users.addItems(CLIENT.keys())
            else:
                self.combo_users.addItem("Aucun utilisateur")

        except Exception as e:
            self.label_status.setText("État : Impossible de se connecter")
            QMessageBox.critical(self, "Connexion impossible", str(e))


    # -------------------------
    # Envoi d'un message au Master
    # -------------------------
    def send_message(self):
        msg = self.input_msg.text().strip()
        if not msg:
            return

        dest = self.combo_users.currentText()
        nb = self.combo_hops.currentText()

        # On appelle DIRECTEMENT le backend !
        threading.Thread(target=mode_envoyer,args=(self.client_name,),kwargs={"dest": dest,"message": msg,"nb": nb,"master_ip": self.master_ip,"master_port": self.master_port},daemon=True).start()

        self.input_msg.clear()


    # -------------------------
    # Mise à jour UI depuis un message reçu
    # -------------------------
    def on_message_received(self, msg):
        self.text_recv.append(msg)


# -------------------------
# Lancement Client
# -------------------------
def run_client_gui():
    app = QApplication(sys.argv)
    global gui_instance
    gui_instance = ClientGUI(nom_client, port_client)
    gui_instance.show()
    sys.exit(app.exec_())











#
#
#
# MAIN
#
#
#


if __name__ == "__main__":


    #
    # Back-end
    #

    # Vérification des arguments
    if len(sys.argv) != 3:
        print("Utilisation : python3 client.py <NOM_CLIENT> <PORT>")
        sys.exit(1)

    nom_client = sys.argv[1]
    port_client = int(sys.argv[2])

    # Lancer le backend dans un thread
    threading.Thread(target=client, args=(nom_client, port_client), daemon=True).start()

    #
    # Front-end
    #

    run_client_gui()