import random
import math
from sympy import isprime

def generer_cle_rsa():
    # Génération de nombres premiers entre 100 et 500 pour la démonstration
    # Pour plus de sécurité, on peut augmenter ces bornes
    primes = [i for i in range(100, 500) if isprime(i)]
    p = random.choice(primes)
    q = random.choice(primes)
    while q == p:
        q = random.choice(primes)
    
    n = p * q
    phi = (p - 1) * (q - 1)
    
    # Choix de l'exposant public e
    e = 65537
    if math.gcd(e, phi) != 1:
        e = 3
        while math.gcd(e, phi) != 1:
            e += 2
            
    # Calcul de l'exposant privé d (inverse modulaire)
    d = pow(e, -1, phi)
    return (e, n), (d, n)

def rsa_encrypt(message, pub_key):
    e, n = pub_key
    # Convertit chaque caractère en sa valeur Unicode, applique RSA, et joint par des virgules
    return ",".join([str(pow(ord(c), e, n)) for c in message])

def rsa_decrypt(cipher_text, priv_key):
    d, n = priv_key
    try:
        chars = cipher_text.split(",")
        return "".join([chr(pow(int(c), d, n)) for c in chars])
    except:
        return "[Erreur de déchiffrement]"
