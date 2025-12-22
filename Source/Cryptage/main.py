from Masterv3 import *
from gui_master import *
import threading

if __name__ == "__main__":
    MASTER_IP = get_ip()
    # Initialisation DB Master
    # envoie_donne_db("MASTER", MASTER_IP, 6000, "master", "") 

    app = QApplication([])
    gui = MasterGUI()
    
    # On lance le serveur master en arrière-plan
    t = threading.Thread(target=master, args=(gui,), daemon=True)
    t.start()
    
    gui.show()
    app.exec_()
