import sys
import socket
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QObject

# -------------------------
# Récupération de l'IP locale
# -------------------------
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "0.0.0.0"
    s.close()
    return ip


# -------------------------
# Thread communicant → UI
# -------------------------
class SignalBus(QObject):
    message_received = pyqtSignal(str)


# -------------------------
# Interface Client
# -------------------------
class ClientGUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interface Client")
        self.setGeometry(300, 300, 450, 350)

        self.client_ip = get_ip()
        self.client_port = 5000
        self.master_ip = "127.0.0.1"
        self.master_port = 6000

        # Signaux
        self.bus = SignalBus()
        self.bus.message_received.connect(self.on_message_received)

        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"IP Client : {self.client_ip}"))
        layout.addWidget(QLabel(f"Port : {self.client_port}"))
        layout.addWidget(QLabel(f"Master : {self.master_ip}:{self.master_port}"))
        layout.addWidget(QLabel("Messages reçus :"))

        # Zone messages reçus
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

        # Lancement du serveur d'écoute du client
        self.start_listener()

    # -------------------------
    # Envoi d'un message au Master
    # -------------------------
    def send_message(self):
        msg = self.input_msg.text().strip()
        if not msg:
            return

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.master_ip, self.master_port))
            s.sendall(msg.encode())
            s.close()

            self.input_msg.clear()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # -------------------------
    # Thread d'écoute
    # -------------------------
    def start_listener(self):
        thread = threading.Thread(target=self.listen_thread, daemon=True)
        thread.start()

    def listen_thread(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.client_ip, self.client_port))
        s.listen(5)

        while True:
            conn, addr = s.accept()
            data = conn.recv(1024).decode()
            conn.close()

            if data:
                self.bus.message_received.emit(data)

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
    gui = ClientGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_client_gui()
