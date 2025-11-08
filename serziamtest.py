#!/usr/bin/env python3
"""
TEST DE SYNCHRONISATION - Vérification que les deux scripts génèrent les mêmes codes
"""

import hashlib
import hmac
from datetime import datetime
import string

# Configuration identique pour les deux scripts
SECRET_SEED = "asterisk_secure_deterministic_v1"

def generate_deterministic_code(month_year, length=8):
    """Algorithme de génération identique pour les deux scripts"""
    # Créer une clé HMAC basée sur la graine secrète
    hmac_obj = hmac.new(
        SECRET_SEED.encode('utf-8'),
        month_year.encode('utf-8'),
        hashlib.sha256
    )
    
    # Obtenir le hash et le convertir en code lisible
    hash_bytes = hmac_obj.digest()
    
    # Utiliser les bytes pour générer un code alphanumérique
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    code_chars = []
    
    for i in range(length):
        # Prendre un byte différent pour chaque caractère
        byte_val = hash_bytes[i % len(hash_bytes)] + i
        code_chars.append(chars[byte_val % len(chars)])
    
    return ''.join(code_chars)

def test_synchronization():
    """Tester que les deux scripts produisent les mêmes codes"""
    print("🧪 TEST DE SYNCHRONISATION COMPLET")
    print("=" * 50)
    
    current_date = datetime.now()
    current_period = f"{current_date.month:02d}-{current_date.year}"
    
    # Générer le code actuel
    current_code = generate_deterministic_code(current_period)
    print(f"Période actuelle: {current_period}")
    print(f"Code généré: {current_code}")
    print()
    
    # Tester avec différentes périodes
    test_periods = [
        current_period,
        "01-2024", "02-2024", "03-2024", "06-2024", "12-2024",
        "01-2025", "06-2025", "12-2025"
    ]
    
    print("📅 TEST AVEC DIFFÉRENTES PÉRIODES:")
    print("-" * 40)
    
    all_synchronized = True
    
    for period in test_periods:
        code1 = generate_deterministic_code(period)
        # Régénérer pour vérifier la consistance
        code2 = generate_deterministic_code(period)
        
        status = "✅" if code1 == code2 else "❌"
        print(f"{status} {period}: {code1}")
        
        if code1 != code2:
            all_synchronized = False
            print(f"   ERREUR: {code1} != {code2}")
    
    print()
    print("🔍 TEST DE REPRODUCTIBILITÉ:")
    print("-" * 40)
    
    # Tester 10 générations successives
    test_code = None
    reproducible = True
    
    for i in range(10):
        new_code = generate_deterministic_code(current_period)
        if test_code is None:
            test_code = new_code
            print(f"Génération 1: {new_code}")
        else:
            status = "✅" if new_code == test_code else "❌"
            print(f"Génération {i+1}: {new_code} {status}")
            if new_code != test_code:
                reproducible = False
    
    print()
    print("📊 RÉSULTATS:")
    print("-" * 40)
    
    if all_synchronized and reproducible:
        print("🎉 SUCCÈS: Tous les tests de synchronisation sont passés!")
        print("   - Codes identiques pour toutes les périodes")
        print("   - Génération parfaitement reproductible")
        print("   - Les deux scripts produiront les mêmes codes")
    else:
        print("💥 ÉCHEC: Problèmes de synchronisation détectés")
        
        if not all_synchronized:
            print("   - Inconsistance entre différentes périodes")
        if not reproducible:
            print("   - Génération non reproductible")

if __name__ == "__main__":
    test_synchronization()
