from Masterv3 import *
from gui_master import *
import threading

if __name__ == "__main__":

    #Envoie des données dans la DB
    MASTER_IP = get_ip()
    envoie_donne_db("MASTER", MASTER_IP, 6000, "master")    

    ROUTEURS_CLIENTS = recup_routeurs_client()
    app = QApplication([])

    # 1. Création du GUI
    gui = MasterGUI()

    #Varaible à récuperer pour le GUI
    gui.routeurs = ROUTEURS
    gui.clients = CLIENTS
    gui.reload_backend = recup_routeurs_client
    gui.refresh_routeurs_topo()
    gui.show()

    # 2. Lancer le backend Master AVEC gui
    t = threading.Thread(target=master, args=(gui,), daemon=True)
    t.start()

    # 3. Lancer la boucle Qt
    app.exec_()