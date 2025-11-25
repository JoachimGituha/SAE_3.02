import sys
import socket
import threading
import json
import base64
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLineEdit, 
                             QLabel, QComboBox, QFileDialog, QMessageBox, QTabWidget)
from PyQt5.QtCore import pyqtSignal, QObject

# Chiffrement XOR simple
class SimpleEncryption:
    @staticmethod
    def encrypt(message, key):
        encrypted = []
        for i, char in enumerate(message):
            key_char = key[i % len(key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            encrypted.append(encrypted_char)
        return ''.join(encrypted)
    
    @staticmethod
    def decrypt(encrypted_message, key):
        return SimpleEncryption.encrypt(encrypted_message, key)

# Routeur
class Router:
    def __init__(self, router_id, key):
        self.router_id = router_id
        self.key = key
    
    def process_message(self, message):
        decrypted = SimpleEncryption.decrypt(message, self.key)
        encrypted = SimpleEncryption.encrypt(decrypted, self.key)
        return encrypted

# Serveur
class MasterServer:
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}
        self.running = False
        
        self.routers = [
            Router("R1", "cle_router_1"),
            Router("R2", "cle_router_2"),
            Router("R3", "cle_router_3")
        ]
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        print(f"[SERVEUR] Demarrage sur {self.host}:{self.port}")
        
        accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
        accept_thread.start()
    
    def _accept_clients(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket,), 
                    daemon=True
                )
                client_thread.start()
            except:
                break
    
    def _handle_client(self, client_socket):
        client_name = None
        
        try:
            data = client_socket.recv(4096).decode('utf-8')
            message = json.loads(data)
            
            if message['type'] == 'connect':
                client_name = message['name']
                self.clients[client_name] = client_socket
                print(f"[SERVEUR] Client connecte: {client_name}")
                self._send_client_list()
                
                while self.running:
                    data = client_socket.recv(8192)
                    if not data:
                        break
                    
                    message = json.loads(data.decode('utf-8'))
                    self._route_message(message)
        
        except Exception as e:
            print(f"[SERVEUR] Erreur: {e}")
        
        finally:
            if client_name and client_name in self.clients:
                del self.clients[client_name]
                print(f"[SERVEUR] Client deconnecte: {client_name}")
                self._send_client_list()
            
            try:
                client_socket.close()
            except:
                pass
    
    def _route_message(self, message):
        sender = message['sender']
        recipient = message['recipient']
        msg_type = message['type']
        content = message['content']
        
        route_path = []
        encrypted_content = content
        
        for router in self.routers:
            encrypted_content = router.process_message(encrypted_content)
            route_path.append(router.router_id)
        
        route_string = ' -> '.join(route_path)
        
        final_message = {
            'type': msg_type,
            'sender': sender,
            'content': content,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        if msg_type == 'file':
            final_message['filename'] = message['filename']
            final_message['filedata'] = message['filedata']
        
        if recipient in self.clients:
            try:
                self.clients[recipient].send(
                    json.dumps(final_message).encode('utf-8')
                )
            except:
                pass
        
        route_message = {
            'type': 'route',
            'path': route_string,
            'recipient': recipient
        }
        
        if sender in self.clients:
            try:
                self.clients[sender].send(
                    json.dumps(route_message).encode('utf-8')
                )
            except:
                pass
    
    def _send_client_list(self):
        client_list = list(self.clients.keys())
        message = {
            'type': 'client_list',
            'clients': client_list
        }
        
        message_json = json.dumps(message)
        
        for client_socket in self.clients.values():
            try:
                client_socket.send(message_json.encode('utf-8'))
            except:
                pass
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

# Signaux
class ClientSignals(QObject):
    message_received = pyqtSignal(str, str, str)
    route_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    clients_updated = pyqtSignal(list)

# Interface Client
class ChatClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client_name = None
        self.client_socket = None
        self.connected = False
        self.signals = ClientSignals()
        
        self.init_interface()
        self.connect_signals()
    
    def init_interface(self):
        self.setWindowTitle("Client de Messagerie")
        self.setGeometry(100, 100, 800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Connexion
        connect_layout = QHBoxLayout()
        
        connect_layout.addWidget(QLabel("Serveur:"))
        self.host_input = QLineEdit("localhost")
        connect_layout.addWidget(self.host_input)
        
        connect_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("5555")
        connect_layout.addWidget(self.port_input)
        
        connect_layout.addWidget(QLabel("Nom:"))
        self.name_input = QLineEdit()
        connect_layout.addWidget(self.name_input)
        
        self.connect_button = QPushButton("Connecter")
        self.connect_button.clicked.connect(self.toggle_connection)
        connect_layout.addWidget(self.connect_button)
        
        main_layout.addLayout(connect_layout)
        
        # Onglets
        tabs = QTabWidget()
        
        # Messages
        messages_tab = QWidget()
        msg_layout = QVBoxLayout(messages_tab)
        
        self.messages_display = QTextEdit()
        self.messages_display.setReadOnly(True)
        msg_layout.addWidget(self.messages_display)
        
        send_layout = QHBoxLayout()
        
        send_layout.addWidget(QLabel("Destinataire:"))
        self.recipient_combo = QComboBox()
        send_layout.addWidget(self.recipient_combo)
        
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_text_message)
        send_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_text_message)
        self.send_button.setEnabled(False)
        send_layout.addWidget(self.send_button)
        
        self.file_button = QPushButton("Fichier")
        self.file_button.clicked.connect(self.send_file)
        self.file_button.setEnabled(False)
        send_layout.addWidget(self.file_button)
        
        msg_layout.addLayout(send_layout)
        tabs.addTab(messages_tab, "Messages")
        
        # Routage
        route_tab = QWidget()
        route_layout = QVBoxLayout(route_tab)
        
        self.route_display = QTextEdit()
        self.route_display.setReadOnly(True)
        route_layout.addWidget(self.route_display)
        
        tabs.addTab(route_tab, "Routage")
        
        main_layout.addWidget(tabs)
        
        # Statut
        self.status_label = QLabel("Deconnecte")
        main_layout.addWidget(self.status_label)
    
    def connect_signals(self):
        self.signals.message_received.connect(self.display_message)
        self.signals.route_received.connect(self.display_route)
        self.signals.status_changed.connect(self.update_status)
        self.signals.clients_updated.connect(self.update_clients)
    
    def toggle_connection(self):
        if not self.connected:
            self.connect_to_server()
        else:
            self.disconnect_from_server()
    
    def connect_to_server(self):
        host = self.host_input.text()
        port = int(self.port_input.text())
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Erreur", "Entrez un nom")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.client_name = name
            
            connect_msg = {
                'type': 'connect',
                'name': self.client_name
            }
            self.client_socket.send(json.dumps(connect_msg).encode('utf-8'))
            
            self.connected = True
            self.connect_button.setText("Deconnecter")
            self.send_button.setEnabled(True)
            self.file_button.setEnabled(True)
            self.signals.status_changed.emit(f"Connecte: {self.client_name}")
            
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Connexion impossible: {e}")
    
    def disconnect_from_server(self):
        self.connected = False
        if self.client_socket:
            self.client_socket.close()
        
        self.connect_button.setText("Connecter")
        self.send_button.setEnabled(False)
        self.file_button.setEnabled(False)
        self.signals.status_changed.emit("Deconnecte")
    
    def receive_messages(self):
        while self.connected:
            try:
                data = self.client_socket.recv(8192)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                msg_type = message['type']
                
                if msg_type == 'message':
                    self.signals.message_received.emit(
                        message['sender'],
                        message['content'],
                        message['timestamp']
                    )
                
                elif msg_type == 'file':
                    self.handle_file_received(message)
                
                elif msg_type == 'route':
                    route_info = f"[{datetime.now().strftime('%H:%M:%S')}] -> {message['recipient']}: {message['path']}\n"
                    self.signals.route_received.emit(route_info)
                
                elif msg_type == 'client_list':
                    self.signals.clients_updated.emit(message['clients'])
            
            except:
                break
        
        if self.connected:
            self.disconnect_from_server()
    
    def send_text_message(self):
        recipient = self.recipient_combo.currentText()
        content = self.message_input.text().strip()
        
        if not recipient or not content:
            return
        
        message = {
            'type': 'message',
            'sender': self.client_name,
            'recipient': recipient,
            'content': content
        }
        
        try:
            self.client_socket.send(json.dumps(message).encode('utf-8'))
            self.message_input.clear()
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.display_message(f"Moi -> {recipient}", content, timestamp)
        
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Envoi echoue: {e}")
    
    def send_file(self):
        recipient = self.recipient_combo.currentText()
        
        if not recipient:
            return
        
        filepath, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
        if not filepath:
            return
        
        try:
            with open(filepath, 'rb') as f:
                file_content = f.read()
                file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            filename = os.path.basename(filepath)
            
            message = {
                'type': 'file',
                'sender': self.client_name,
                'recipient': recipient,
                'filename': filename,
                'filedata': file_base64,
                'content': f"Fichier: {filename}"
            }
            
            self.client_socket.send(json.dumps(message).encode('utf-8'))
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.display_message(f"Moi -> {recipient}", f"Fichier envoye: {filename}", timestamp)
        
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Envoi fichier echoue: {e}")
    
    def handle_file_received(self, message):
        filename = message['filename']
        file_base64 = message['filedata']
        sender = message['sender']
        timestamp = message['timestamp']
        
        self.display_message(sender, f"Fichier: {filename}", timestamp)
        
        reply = QMessageBox.question(
            self, 
            "Fichier recu", 
            f"Fichier recu de {sender}: {filename}\nSauvegarder ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            save_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", filename)
            if save_path:
                file_content = base64.b64decode(file_base64)
                with open(save_path, 'wb') as f:
                    f.write(file_content)
                QMessageBox.information(self, "Succes", "Fichier sauvegarde")
    
    def display_message(self, sender, content, timestamp):
        self.messages_display.append(f"[{timestamp}] {sender}: {content}")
    
    def display_route(self, route_text):
        self.route_display.append(route_text)
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def update_clients(self, clients):
        current = self.recipient_combo.currentText()
        self.recipient_combo.clear()
        
        for client in clients:
            if client != self.client_name:
                self.recipient_combo.addItem(client)
        
        if current in clients:
            index = self.recipient_combo.findText(current)
            if index >= 0:
                self.recipient_combo.setCurrentIndex(index)

def main():
    server = MasterServer()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    app = QApplication(sys.argv)
    client = ChatClient()
    client.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()