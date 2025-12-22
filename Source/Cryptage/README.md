Guide d'utilisation rapide
Installation des dépendances : pip install mariadb sympy PyQt5

Base de données : Assurez-vous que votre table information possède une colonne cle_publique TEXT.

Lancement :

Lancer le Master (main.py).

Lancer plusieurs routeurs : python3 router.py R1 5001, python3 router.py R2 5002.

Lancer deux clients : python3 client.py Alice 7001 et python3 client.py Bob 7002.

Envoi :

Dans le client Alice, cliquer sur "Se connecter" (cela publie sa clé RSA dans la DB).

Sélectionner "Bob" dans la liste, écrire un message et envoyer.

Le message traversera les routeurs (chiffré pour chacun) et Bob recevra une chaîne de chiffres qu'il déchiffrera automatiquement.
