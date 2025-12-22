import socket
import threading
import mariadb
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox, QComboBox
)
from PyQt5.QtCore import pyqtSignal, QObject
from rsa_tool import generer_cle_rsa, rsa_encrypt, rsa_decrypt

# CONFIGURATION UTILISATEUR
DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"

ROUTEURS = {}
CLIENTS = {}

def recup_routeurs(serveur_ip):
    conn = mariadb.connect(host=serveur_ip, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='routeur'")
    rows = cur.fetchall()
    conn.close()
    res = {}
    for nom, ip, port, cle_pub, nh in rows:
        res[nom] = (ip, port, cle_pub, nh)
    return res

def recup_client(serveur_ip):
    conn = mariadb.connect(host=serveur_ip, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nom, adresse_ip, port, cle_publique, next_hop FROM information WHERE type='client'")
    rows = cur.fetchall()
    conn.close()
    res = {}
    for nom, ip, port, cle_pub, nh in rows:
        res[nom] = (ip, port, cle_pub, nh)
    return res

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def envoie_donne_db(nom, ip, port, type_objet, serveur_ip, cle_pub):
    conn = mariadb.connect(host=serveur_ip, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cur = conn.cursor()
    query = """
    INSERT INTO information (nom, adresse_ip, port, type, cle_publique)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE adresse_ip = VALUES(adresse_ip), port = VALUES(port), cle_publique = VALUES(cle_publique)
    """
    cur.execute(query, (nom, ip, port, type_objet, cle_pub))
    conn.commit()
    conn.close()

class SignalBus(QObject):
    message_received = pyqtSignal(str)

class ClientGUI(QWidget):
    def __init__(self, nom, port):
        super().__init__()
        self.client_ip = get_ip()
        self.client_port = port
        self.client_name = nom 
        self.serveur_ip = "172.20.10.10"
        
        # RSA
        self.pub_key, self.priv_key = generer_cle_rsa()
        
        self.setWindowTitle(f"Client : {self.client_name}")
        self.setGeometry(300, 300, 450, 500)

        self.master_ip = "172.20.10.10"
        self.master_port = 6000
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Adresse du Master :"))
        self.input_master_ip = QLineEdit("172.20.10.10")
        layout.addWidget(self.input_master_ip)

        layout.addWidget(QLabel("Port du Master :"))
        self.input_master_port = QLineEdit("6000")
        layout.addWidget(self.input_master_port)

        btn_connect = QPushButton("Se connecter & Publier Clé RSA")
        btn_connect.clicked.connect(self.test_connect_master)
        layout.addWidget(btn_connect)

        self.label_status = QLabel("État : Déconnecté")
        layout.addWidget(self.label_status)

        self.bus = SignalBus()
        self.bus.message_received.connect(self.on_message_received)

        layout.addWidget(QLabel("Choisir le destinataire :"))
        self.combo_users = QComboBox()
        self.combo_users.addItem("Non connecté")
        layout.addWidget(self.combo_users)

        layout.addWidget(QLabel("Messages reçus (Déchiffrés) :"))
        self.text_recv = QTextEdit()
        self.text_recv.setReadOnly(True)
        layout.addWidget(self.text_recv)

        self.input_msg = QLineEdit()
        self.input_msg.setPlaceholderText("Entrez un message...")
        layout.addWidget(self.input_msg)

        layout.addWidget(QLabel("Nombre de sauts :"))
        self.combo_hops = QComboBox()
        self.combo_hops.addItems(["1", "2", "3"])
        layout.addWidget(self.combo_hops)

        btn_send = QPushButton("Envoyer Chiffré")
        btn_send.clicked.connect(self.send_message)
        layout.addWidget(btn_send)

        self.setLayout(layout)

    def test_connect_master(self):
        ip = self.input_master_ip.text().strip()
        port = int(self.input_master_port.text().strip())
        try:
            self.master_ip = ip
            self.master_port = port
            self.serveur_ip = ip
            
            pub_str = f"{self.pub_key[0]},{self.pub_key[1]}"
            envoie_donne_db(self.client_name, self.client_ip, self.client_port, "client", self.serveur_ip, pub_str)
            
            global ROUTEURS, CLIENTS
            ROUTEURS = recup_routeurs(self.serveur_ip)
            CLIENTS = recup_client(self.serveur_ip)

            self.combo_users.clear()
            self.combo_users.addItems([k for k in CLIENTS.keys() if k != self.client_name])
            self.label_status.setText("État : Connecté & Clé Publiée")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def send_message(self):
        msg = self.input_msg.text().strip()
        dest = self.combo_users.currentText()
        nb = self.combo_hops.currentText()
        if not msg or dest == "Non connecté": return

        threading.Thread(target=mode_envoyer, args=(self.client_name, dest, msg, nb, self.master_ip, self.master_port), daemon=True).start()
        self.input_msg.clear()

    def on_message_received(self, msg_chiffre):
        # Le client reçoit le message final et doit le déchiffrer avec sa clé privée
        decrypted = rsa_decrypt(msg_chiffre, self.priv_key)
        self.text_recv.append(f"Déchiffré : {decrypted}")

def boucle_recevoir(ip, port):
    s = socket.socket()
    s.bind((ip, port))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        message = conn.recv(4096).decode()
        conn.close()
        if "gui_instance" in globals():
            gui_instance.bus.message_received.emit(message)

def mode_envoyer(nom, dest, message, nb, master_ip, master_port):
    # Demander chemin
    s = socket.socket()
    s.connect((master_ip, master_port))
    s.send(f"{nom} GET_PATH {dest} {nb}".encode())
    chemin = s.recv(1024).decode().split(",")
    s.close()

    # Construire l'oignon RSA
    # 1. Chiffrement final pour le destinataire
    cle_dest_str = CLIENTS[dest][2]
    pub_dest = tuple(map(int, cle_dest_str.split(",")))
    oignon = rsa_encrypt(message, pub_dest)

    # 2. Encapsulation par couches routeurs (à l'envers)
    # Format de chaque couche : "DEST_SUIVANTE|DATA_CHIFFREE"
    current_dest = dest
    for r_nom in reversed(chemin):
        cle_r_str = ROUTEURS[r_nom][2]
        pub_r = tuple(map(int, cle_r_str.split(",")))
        
        payload = f"{current_dest}|{oignon}"
        oignon = rsa_encrypt(payload, pub_r)
        current_dest = r_nom

    # Envoyer au premier routeur
    premier = chemin[0]
    ip_r, port_r, _, _ = ROUTEURS[premier]
    s = socket.socket()
    s.connect((ip_r, port_r))
    # On envoie "NOM_DU_ROUTEUR|OIGNON" pour qu'il sache que c'est pour lui
    s.send(f"{premier}|{oignon}".encode())
    s.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 client.py <NOM> <PORT>")
        sys.exit(1)
    nom_client, port_client = sys.argv[1], int(sys.argv[2])
    threading.Thread(target=boucle_recevoir, args=("0.0.0.0", port_client), daemon=True).start()
    app = QApplication(sys.argv)
    gui_instance = ClientGUI(nom_client, port_client)
    gui_instance.show()
    sys.exit(app.exec_())
