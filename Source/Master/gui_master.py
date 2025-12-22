import sys, os
import socket
import mariadb
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QTabWidget, QLineEdit, QMessageBox, QFormLayout, QComboBox
from PyQt5.QtCore import pyqtSignal


#
# CONFIGURATION UTILISATEUR
# 

  
DB_NAME = "Basededonnee"
DB_USER = "toto"
DB_PASSWORD = "toto"









#
# !!! NE PAS TOUCHER !!!
#






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
        self.setGeometry(500, 500, 650, 650)

        self.routeurs = {}
        self.clients = {}
        self.dernier_reponse = None
        self.routeurs_liste = []
        self.clients_liste = []



        self.master_ip = get_ip()
        self.master_port = 6000

        # Onglets
        tabs = QTabWidget()
        tabs.addTab(self.moniteur(), "Onglet 1")
        tabs.addTab(self.ajouter_routeur_client(), "Ajouter un routeur ou un client")
        tabs.addTab(self.topologie(), "Topologie Réseau")
        tabs.addTab(self.commandes_routeurs(), "Commandes Routeurs")


        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

        self.routeurs_db = {}
        self.load_routeurs()
        self.afficher_topologie()

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
        btn_refresh.clicked.connect(self.refresh_all)
        layout.addWidget(btn_refresh)

        page.setLayout(layout)
        return page

    # Onglet d'ajout routeur
    def ajouter_routeur_client(self):
        page = QWidget()
        form = QFormLayout()

        self.input_nom = QLineEdit()
        self.input_port = QLineEdit()

        # *** CHANGEMENT ICI : liste déroulante au lieu d'un QLineEdit ***
        self.combo_type = QComboBox()
        self.combo_type.addItems(["routeur", "client"])

        form.addRow("Type :", self.combo_type)

        self.combo_next_hop = QComboBox()
        self.combo_next_hop.addItem("Aucun")

        self.update_next_hop_list()  # charge les routeurs depuis la BDD

        form.addRow("Nom :", self.input_nom)
        form.addRow("Port :", self.input_port)
        form.addRow("Next hop :", self.combo_next_hop)

        self.direction = QLineEdit()
        self.direction.setPlaceholderText("/home/toto/Documents")
        self.direction.setText("/home/toto/Documents")

        form.addRow("Dossier scripts :", self.direction)


        btn_add = QPushButton("Ajouter")
        btn_add.clicked.connect(self.add_routeur_client)
        form.addRow(btn_add)

        page.setLayout(form)
        return page

    # Actualisation liste déroulante
    def update_next_hop_list(self):
        try:
            conn = mariadb.connect(
                host=self.master_ip,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()
            cur.execute("SELECT nom FROM information")
            noms = cur.fetchall()
            conn.close()

            for n in noms:
                self.combo_next_hop.addItem(n[0])

        except:
            self.combo_next_hop.addItem("Erreur DB")


   

    # Insert DB
    def add_routeur_client(self):

        nom = self.input_nom.text().strip()
        port = self.input_port.text().strip()
        type_objet = self.combo_type.currentText()

        if not nom or not port.isdigit():
            QMessageBox.warning(self, "Erreur", "Nom ou port invalide")
            return

        directory = self.direction.text().strip()

        directory = self.direction.text().strip()

        if not directory:
            QMessageBox.warning(self, "Erreur", "Dossier scripts requis")
            return

        t = threading.Thread(
            target=self.lancer_terminal,
            args=(directory, type_objet, nom, port),
            daemon=True
        )
        t.start()

        if type_objet == "routeur":
            cmd = f"cd {directory} && python3 router.py {nom} {port} "
        else:
            cmd = f"cd {directory} && python3 client.py {nom} {port} "


        self.text_logs.append(f"Lancement {type_objet.upper()} : {cmd}")

        # reset champs
        self.input_nom.clear()
        self.input_port.clear()
        self.combo_type.setCurrentIndex(0)


    #Pour refresh les routeurs et les clients
    def load_routeurs(self):
        self.routeurs_liste = []
        self.clients_liste = []

        try:
            conn = mariadb.connect(
                host=self.master_ip,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()
            cur.execute("SELECT nom, adresse_ip, port, type, next_hop FROM information")
            routeurs = cur.fetchall()
            conn.close()

            self.text_routeurs.clear()
            for r in routeurs:
                self.text_routeurs.append(f"{r[0]} - {r[1]}:{r[2]} - {r[3]} -> {r[4]}")
                if r[3] == "routeur":          # type = routeur
                    self.routeurs_liste.append(r[0])
                elif r[3] == "client":
                    self.clients_liste.append(r[0])
            
            return routeurs

            if self.dernier_reponse is not None:
                self.text_chemin.setText(self.dernier_reponse)

            else:
                self.text_chemin.setText("Aucun chemin généré pour l’instant")

        except Exception as e:
            self.text_logs.append("DB erreur : " + str(e))
    




    #
    #Permet de refaire une demande pour relaod routeur/client Backend + front end
    #

    def refresh_all(self):
        # 1. reload backend (DB → ROUTEURS / CLIENTS)
        if hasattr(self, "reload_backend"):
            self.reload_backend()

        # 2. refresh affichage
        self.load_routeurs()
        self.refresh_routeurs_topo()

        self.text_logs.append("Actualisation complète effectuée")



    #
    # Permet de lancer les équipements via le cmd
    #
    def lancer_equipement(self, cmd):
        os.system(cmd)



    #
    # Lancement du terminal pour le lancement des équipements 
    #
    def lancer_terminal(self, directory, type_objet, nom, port):
        if sys.platform.startswith("win"):
            # WINDOWS
            if type_objet == "routeur":
                cmd = f'cmd /k "cd /d {directory} && python routerv7.py {nom} {port}"'
            else:
                cmd = f'cmd /k "cd /d {directory} && python clientv7.py {nom} {port}"'

        else:
            # LINUX
            if type_objet == "routeur":
                cmd = f'xterm -hold -e "cd {directory} && python3 routerv7.py {nom} {port}"'
            else:
                cmd = f'xterm -hold -e "cd {directory} && python3 clientv7.py {nom} {port}"'

        # AFFICHAGE DU CMD (debug / traçabilité)
        self.text_logs.append(f"CMD lancé : {cmd}")

        os.system(cmd)



    #
    # CREATION DE l'ONGLET POUR LA TOPO RESEAU
    #

    def topologie(self):
        page = QWidget()
        layout = QFormLayout()

        self.combo_routeur = QComboBox()

        self.combo_next_hop_1 = QComboBox()
        self.combo_next_hop_2 = QComboBox()
        self.combo_next_hop_3 = QComboBox()

        self.refresh_routeurs_topo()

        layout.addRow("Équipement :", self.combo_routeur)
        layout.addRow("Next hop 1 :", self.combo_next_hop_1)
        layout.addRow("Next hop 2 :", self.combo_next_hop_2)
        layout.addRow("Next hop 3 :", self.combo_next_hop_3)

        btn_apply = QPushButton("Appliquer les next hop")
        btn_apply.clicked.connect(self.verif_next_hop)
        layout.addRow(btn_apply)

        btn_delete = QPushButton("Supprimer l’équipement")
        btn_delete.clicked.connect(self.supprimer_equipement)
        layout.addRow(btn_delete)


        self.text_topologie = QTextEdit()
        self.text_topologie.setReadOnly(True)
        layout.addRow(QLabel("Vue topologique :"))
        layout.addRow(self.text_topologie)


        page.setLayout(layout)
        return page



    def refresh_routeurs_topo(self):
        self.combo_routeur.clear()
        self.combo_next_hop_1.clear()
        self.combo_next_hop_2.clear()
        self.combo_next_hop_3.clear()

        self.combo_routeur.addItem("Choisir un Equipement")

        for combo in (
            self.combo_next_hop_1,
            self.combo_next_hop_2,
            self.combo_next_hop_3
        ):
            combo.addItem("Aucun")

        # 🔹 Routeurs
        for r in self.routeurs_liste:
            self.combo_routeur.addItem(r)
            for combo in (
                self.combo_next_hop_1,
                self.combo_next_hop_2,
                self.combo_next_hop_3
            ):
                combo.addItem(r)

        # 🔹 Clients
        for c in self.clients_liste:
            self.combo_routeur.addItem(c)
            for combo in (
                self.combo_next_hop_1,
                self.combo_next_hop_2,
                self.combo_next_hop_3
            ):
                combo.addItem(c)





    #
    # Vérification des données + envoie dans la DB pour l'info next hop
    #
    def verif_next_hop(self):
        routeur = self.combo_routeur.currentText()

        hops = []

        #Détéction d'erreur pour assignation de routeur en temps que next hop
        for combo in (self.combo_next_hop_1,self.combo_next_hop_2,self.combo_next_hop_3):
            if combo.currentText() == routeur:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "L'équipement ne peut pas être son propre next hop"
                )
                return

        for combo in (self.combo_next_hop_1,self.combo_next_hop_2,self.combo_next_hop_3):
            val = combo.currentText()
            if val != "Aucun" and val not in hops:
                hops.append(val)


        next_hop_str = ",".join(hops) if hops else None


        if routeur == "Choisir un routeur":
            QMessageBox.warning(self, "Erreur", "Choisissez un équipement.")
            return

        
        #Assemblage avec une , pour -> [R1, R2]
        next_hop_str = ",".join(hops) if hops else None

        try:
            conn = mariadb.connect(
                host=self.master_ip,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()

            # MAJ du routeur sélectionné 
            cur.execute(
                "UPDATE information SET next_hop = %s WHERE nom = %s",
                (next_hop_str, routeur)
            )

            # MAJ AUTOMATIQUE DES ROUTEURS CHOISIS
            for nh in hops:
                cur.execute("SELECT next_hop FROM information WHERE nom=%s",(nh,))
                row = cur.fetchone()

                if row and row[0]:
                    nh_list = row[0].split(",")
                else:
                    nh_list = []

                if routeur not in nh_list:
                    nh_list.append(routeur)

                new_nh = ",".join(nh_list)
                cur.execute(
                    "UPDATE information SET next_hop=%s WHERE nom=%s",
                    (new_nh, nh)
                )
            conn.commit()
            conn.close()

            QMessageBox.information(
                self,
                "OK",
                f"Next hop de {routeur} mis à jour"
            )
            # Synchronisation DB -> backend -> GUi     
            self.refresh_routeurs_topo() # met à jour les listes déroulantes
            self.load_routeurs()         # met à jour l’affichage texte
            self.afficher_topologie()

        except Exception as e:
            QMessageBox.critical(self, "Erreur DB", str(e))

    #
    # Definition pour supprimer les equipements dans topologie réseau 
    #

    def supprimer_equipement(self):
        equipement = self.combo_routeur.currentText()

        if equipement in ("Choisir un Equipement", "", None):
            #Message d'erruer en cas de non choix de l'équipement
            QMessageBox.warning(self,"Erreur","Veuillez sélectionner un équipement à supprimer")
            return

        # Messga de confirmation utilisateur
        rep = QMessageBox.question(self,"Confirmation",f"Voulez-vous vraiment supprimer '{equipement}' ?",QMessageBox.Yes | QMessageBox.No)

        if rep != QMessageBox.Yes:
            return

        try:
            conn = mariadb.connect(
                host=self.master_ip,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()

            #Supprimer l’équipement / requet sql
            cur.execute(
                "DELETE FROM information WHERE nom = %s",
                (equipement,)
            )

            #Nettoyer les next_hop des autres équipements
            cur.execute("SELECT nom, next_hop FROM information")
            rows = cur.fetchall()

            for nom, next_hop in rows:
                if next_hop:
                    hops = next_hop.split(",")
                    if equipement in hops:
                        hops.remove(equipement)
                        new_nh = ",".join(hops) if hops else None
                        cur.execute(
                            "UPDATE information SET next_hop=%s WHERE nom=%s",
                            (new_nh, nom)
                        )

            conn.commit()
            conn.close()

            #Message de suppression
            QMessageBox.information(self,"Supprimé",f"Équipement '{equipement}' supprimé")

            # 🔄 Refresh complet
            self.load_routeurs()
            self.refresh_routeurs_topo()
            self.afficher_topologie()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur DB",
                str(e)
            )



    



    #
    # Afficher la topologie
    #
    def afficher_topologie(self):
        self.text_topologie.clear()

        try:
            conn = mariadb.connect(
                host=self.master_ip,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()
            cur.execute("SELECT nom, next_hop FROM information")
            rows = cur.fetchall()
            conn.close()

            for nom, next_hop in rows:
                if next_hop:
                    self.text_topologie.append(f"{nom} → {next_hop}")
                else:
                    self.text_topologie.append(f"{nom} → (aucun)")

        except Exception as e:
            self.text_topologie.append("Erreur DB : " + str(e))




    #
    #
    # ONGLET COMMANDES ROUTEURS 
    #
    #

    def commandes_routeurs(self):
        page = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Commandes globales envoyées aux routeurs")
        layout.addWidget(label)

        btn_reload = QPushButton("Recharger la DB des routeurs")
        btn_reload.clicked.connect(self.envoyer_reload_db)
        layout.addWidget(btn_reload)

        self.page_commandes_logs = QTextEdit()
        self.page_commandes_logs.setReadOnly(True)
        layout.addWidget(self.page_commandes_logs)

        page.setLayout(layout)
        return page
    

    def envoyer_reload_db(self):
        try:
            self.envoyer_rechargement_db_routeurs()
            self.page_commandes_logs.append("Commande 'rechargement_db' envoyée à tous les routeurs")
        except Exception as e:
            self.page_commandes_logs.append(f"Erreur lors de l'envoi : {e}")


    def envoyer_rechargement_db_routeurs(self):
        routeurs = self.load_routeurs()

        for nom, ip, port, type_objet, next_hop in routeurs:
            if type_objet != "routeur":
                continue

            try:
                s = socket.socket()
                s.connect((ip, port))
                s.send("rechargement_db".encode())
                s.close()
            except:
                pass


def run_master_gui():
    app = QApplication(sys.argv)
    gui = MasterGUI()
    gui.show()
    sys.exit(app.exec_())
