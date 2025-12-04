from Masterv3 import *
from gui_master import *
import threading

if __name__ == "__main__":
    ROUTEURS_CLIENTS = recup_routeurs_client()
    app = QApplication([])

    # 1. Création du GUI
    gui = MasterGUI()
    gui.show()

    # 2. Lancer le backend Master AVEC gui
    t = threading.Thread(target=master, args=(gui,), daemon=True)
    t.start()

    # 3. Lancer la boucle Qt
    app.exec_()