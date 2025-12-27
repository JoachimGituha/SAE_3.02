2Alternant&1Timeout: NEFZI Mehdi LAUNAY Valentin GUTTER Joachim

# SAE_3.02 Conception d’une architecture distribuée avec routage en oignon

Description du projet

Ce projet consiste à concevoir un système de communication anonyme basé sur un ensemble de routeurs virtuels.
Chaque message envoyé par un client traverse plusieurs routeurs sélectionnés aléatoirement avant d’atteindre sa destination, afin d’assurer un anonymat similaire au réseau TOR.

Le projet se compose de :

Un Master : génère les chemins, centralise les données et propose une interface graphique.
Plusieurs routeurs virtuels (VM) : reçoivent, relaient ou transmettent les messages au prochain nœud.
Une base de données MariaDB : stocke les routeurs, leurs adresses IP, types, ports et next hop.

Fonctionnalités principales 
Master:
-Génération dynamique des chemins (aléatoires).
-Interface graphique PyQt5 :
-Affichage des routeurs enregistrés.
-Visualisation des chemins générés.
-Ajout d’un routeur via formulaire (avec liste déroulante des next hop).
-Logs d’activité.
-Enregistrement automatique du Master dans la base.
-Routeurs
-Réception de messages depuis le master ou un autre routeur.
-Transmission au prochain nœud (next hop).
-Écriture dans les logs en base.

Base de données MariaDB:
-Stockage des informations des routeurs.
-Gestion des chemins et des logs.
-Accès distant activé pour communication avec les VM.


Client → Master → R1 → R3 → R2 → Destinataire

Le Master interroge la base pour connaître :
-les routeurs disponibles
-leurs ports
 -leurs next hop

Technologies utilisées: 
-Python 3
-PyQt5 (interface graphique)
-MariaDB 10.x
-Sockets TCP/UDP
-Machines virtuelles Linux


Pour toute aide d'installation ou de configuration veuillez se référer aux documents d'installation se trouvant dans de dossier "Documentation".Vous y retrouverez aussi une vidéo de démonstration du fonctionnement de notre projet avec différentes exlications. 

Les codes source se situent dans le dossier Source et le dossier Gestion de Projet permet le suivi de notre projet.

Pour voir une vidéo démonstrative de notre projet, je vous invite à suivre ce lien YouTube : https://youtu.be/yynfDQ28M1M
