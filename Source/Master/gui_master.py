import sys
import socket
import mariadb
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QTabWidget, QLineEdit, QMessageBox, QFormLayout, QComboBox
from PyQt5.QtCore import pyqtSignal
from Masterv3 import *


#Pour la récup de son @IP
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

#Interface Graphique
class MasterGUI(QWidget):
    signal_chemin = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interface Graphique Master")
        self.setGeometry(200, 200, 450, 550)

        self.master_ip = get_ip()
        self.master_port = 6000

        # Onglets
        tabs = QTabWidget()
        tabs.addTab(self.moniteur(), "Onglet 1")
        tabs.addTab(self.ajouter_routeur(), "Ajouter un routeur")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

        self.routeurs_db = {}
        self.load_routeurs()

        #Pour chemin générer 
        self.signal_chemin.connect(self.ajouter_chemin)

        #Pour le compteur pour chemin générer 
        self.compteur_chemins = 0



    def ajouter_chemin(self, chemin):
        self.compteur_chemins += 1   # 

        # Transformer "R1,R2,R3" en "R1 -> R2 -> R3"
        chemin_formate = " -> ".join(chemin.split(","))

        # Ligne finale : "1. R1 -> R2 -> R3"
        ligne = f"{self.compteur_chemins}. {chemin_formate}"

        self.text_chemin.append(ligne)




    # Onglet de base
    def moniteur(self):
        page = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"IP Master : {self.master_ip}"))
        layout.addWidget(QLabel(f"Port : {self.master_port}"))

        self.text_routeurs = QTextEdit()
        self.text_routeurs.setReadOnly(True)
        layout.addWidget(QLabel("Routeurs :"))
        layout.addWidget(self.text_routeurs)

        self.text_chemin = QTextEdit()
        self.text_chemin.setReadOnly(True)
        layout.addWidget(QLabel("Chemin généré :"))
        layout.addWidget(self.text_chemin)

        self.text_logs = QTextEdit()
        self.text_logs.setReadOnly(True)
        layout.addWidget(QLabel("Logs :"))
        layout.addWidget(self.text_logs)

        btn_refresh = QPushButton("Actualiser")
        btn_refresh.clicked.connect(self.load_routeurs)
        layout.addWidget(btn_refresh)

        page.setLayout(layout)
        return page

    # Onglet d'ajout routeur
    def ajouter_routeur(self):
        page = QWidget()
        form = QFormLayout()

        self.input_nom = QLineEdit()
        self.input_port = QLineEdit()

        # *** CHANGEMENT ICI : liste déroulante au lieu d'un QLineEdit ***
        self.combo_next_hop = QComboBox()
        self.combo_next_hop.addItem("Aucun")  # par défaut
        self.update_next_hop_list()  # charge les routeurs depuis la BDD

        form.addRow("Nom :", self.input_nom)
        form.addRow("Port :", self.input_port)
        form.addRow("Next hop :", self.combo_next_hop)

        btn_add = QPushButton("Ajouter")
        btn_add.clicked.connect(self.add_routeur)
        form.addRow(btn_add)

        page.setLayout(form)
        return page

    # Actualisation liste déroulante
    def update_next_hop_list(self):
        try:
            conn = mariadb.connect(
                host="172.20.10.10",
                user="toto",
                password="toto",
                database="table_routage"
            )
            cur = conn.cursor()
            cur.execute("SELECT nom FROM routeurs")
            noms = cur.fetchall()
            conn.close()

            for n in noms:
                self.combo_next_hop.addItem(n[0])

        except:
            self.combo_next_hop.addItem("Erreur DB")

    # Insert DB
    def add_routeur(self):
        nom = self.input_nom.text()
        port = self.input_port.text()
        next_hop = self.combo_next_hop.currentText()

        if next_hop == "Aucun":
            next_hop = None

        if not nom or not port.isdigit():
            QMessageBox.warning(self, "Erreur", "Vérifiez le nom et le port.")
            return

        try:
            conn = mariadb.connect(
                host="172.20.10.10",
                user="toto",
                password="toto",
                database="table_routage"
            )
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO routeurs (nom, port, next_hop)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE port = VALUES(port), next_hop = VALUES(next_hop)
            """, (nom, int(port), next_hop))
            conn.commit()
            conn.close()

            QMessageBox.information(self, "OK", f"Routeur '{nom}' ajouté.")
            self.input_nom.clear()
            self.input_port.clear()
            self.combo_next_hop.setCurrentIndex(0)
            self.load_routeurs()
        #Sinon
        except Exception as e:
            QMessageBox.critical(self, "Erreur DB", str(e))

    #Pour refresh les routeurs
    def load_routeurs(self):
        try:
            conn = mariadb.connect(
                host="172.20.10.10",
                user="toto",
                password="toto",
                database="table_routage"
            )
            cur = conn.cursor()
            cur.execute("SELECT nom, adresse_ip, port, type, next_hop FROM routeurs")
            routeurs = cur.fetchall()
            conn.close()

            self.text_routeurs.clear()
            for r in routeurs:
                self.text_routeurs.append(f"{r[0]} - {r[1]}:{r[2]} - {r[3]} -> {r[4]}")
            self.text_logs.append("Routeurs actualisés")

            if dernier_reponse is not None:
                self.text_chemin.setText(dernier_reponse)
            else:
                self.text_chemin.setText("Aucun chemin généré pour l’instant")

        except Exception as e:
            self.text_logs.append("DB erreur : " + str(e))

def run_master_gui():
    app = QApplication(sys.argv)
    gui = MasterGUI()
    gui.show()
    sys.exit(app.exec_())
