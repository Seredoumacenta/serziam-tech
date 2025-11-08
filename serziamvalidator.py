#!/usr/bin/env python3
"""
ASTERISK MANAGER - Version Codes Visibles  
Algorithme déterministe de génération de codes
"""

import os
import sys
import sqlite3
import hashlib
import hmac
from datetime import datetime, timedelta
import string

# =============================================================================
# CONFIGURATION GLOBALE
# =============================================================================

class Config:
    DB_PATH = "/home/vps/asterisk/asterisk.db"
    SECRET_SEED = "asterisk_secure_deterministic_v1"

# =============================================================================
# ALGORITHME DÉTERMINISTE COMMUN (IDENTIQUE AU SCRIPT 1)
# =============================================================================

class DeterministicCodeGenerator:
    """Générateur déterministe de codes - VERSION SYNCHRONISÉE"""
    
    def __init__(self, secret_seed=Config.SECRET_SEED):
        self.secret_seed = secret_seed
        self.month_names = {
            1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
            5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août", 
            9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
        }
    
    def get_current_period(self):
        """Obtenir la période courante (mois-année)"""
        current_date = datetime.now()
        return f"{current_date.month:02d}-{current_date.year}"
    
    def generate_deterministic_code(self, month_year=None, length=8):
        """Génère un code déterministe basé sur le mois/année et la graine secrète"""
        if month_year is None:
            month_year = self.get_current_period()
        
        # Créer une clé HMAC basée sur la graine secrète
        hmac_obj = hmac.new(
            self.secret_seed.encode('utf-8'),
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
    
    def get_current_code(self):
        """Obtenir le code du mois courant - Version déterministe"""
        month_year = self.get_current_period()
        return self.generate_deterministic_code(month_year)

# =============================================================================
# GESTIONNAIRE DE CODES VISIBLES
# =============================================================================

class VisibleAccessCodeManager(DeterministicCodeGenerator):
    """Gestionnaire avec codes affichés dans l'interface"""
    
    def __init__(self):
        super().__init__(Config.SECRET_SEED)
    
    def display_code_status(self):
        """Afficher le statut du code en révélant le code"""
        current_date = datetime.now()
        month_year = self.get_current_period()
        code = self.get_current_code()
        
        # Calculer l'expiration (fin du mois)
        if current_date.month == 12:
            next_month = datetime(current_date.year + 1, 1, 1)
        else:
            next_month = datetime(current_date.year, current_date.month + 1, 1)
        
        expires_at = next_month - timedelta(days=1)
        expires_at = expires_at.replace(hour=23, minute=59, second=59)
        
        days_remaining = (expires_at - current_date).days
        month_name = self.month_names[current_date.month]
        
        print(f"🔐 Code d'accès {month_name} {current_date.year}: {code}")
        print(f"   Expire le: {expires_at.strftime('%d/%m/%Y')}")
        print(f"   Jours restants: {days_remaining}")
        
        return code, expires_at
    
    def validate_code(self, input_code):
        """Valider un code saisi"""
        expected_code = self.get_current_code()
        return input_code == expected_code

# =============================================================================
# INTERFACE UTILISATEUR - VERSION VISIBLE
# =============================================================================

class VisibleMenuManager:
    """Interface avec codes affichés"""
    
    @staticmethod
    def clear_screen():
        os.system('clear')
    
    @staticmethod
    def show_header():
        VisibleMenuManager.clear_screen()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              ASTERISK MANAGER - CODES VISIBLES              ║")
        print("║             Algorithme déterministe synchronisé             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()
    
    def main_menu(self):
        code_manager = VisibleAccessCodeManager()
        
        while True:
            self.show_header()
            
            # Afficher statut du code (visible)
            code, expires_at = code_manager.display_code_status()
            
            print(f"\nMENU PRINCIPAL:")
            print("1. 🔄 Régénérer le code")
            print("2. ✅ Valider un code")
            print("3. 🔍 Tester la synchronisation")
            print("4. 🚪 Quitter")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.regenerate_code(code_manager)
            elif choice == "2":
                self.validate_code_menu(code_manager)
            elif choice == "3":
                self.test_synchronization(code_manager)
            elif choice == "4":
                print("Au revoir!")
                sys.exit(0)
            else:
                print("❌ Choix invalide")
                input("Appuyez sur Entrée pour continuer...")
    
    def regenerate_code(self, code_manager):
        """Régénérer le code (en réalité, même code déterministe)"""
        current_date = datetime.now()
        month_year = code_manager.get_current_period()
        new_code = code_manager.generate_deterministic_code(month_year)
        
        month_name = code_manager.month_names[current_date.month]
        print(f"✅ Code {month_name} {current_date.year} régénéré")
        print(f"🔐 Nouveau code: {new_code}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def validate_code_menu(self, code_manager):
        """Menu de validation de code"""
        self.show_header()
        print("🔐 VALIDATION DE CODE")
        print(f"Code actuel: {code_manager.get_current_code()}")
        print()
        
        test_code = input("Code à valider: ").strip().upper()
        
        if code_manager.validate_code(test_code):
            print("✅ Code valide!")
        else:
            print("❌ Code invalide ou expiré")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def test_synchronization(self, code_manager):
        """Tester la synchronisation"""
        self.show_header()
        print("🔍 TEST DE SYNCHRONISATION")
        print()
        
        # Générer le code actuel
        current_code = code_manager.get_current_code()
        month_year = code_manager.get_current_period()
        
        # Régénérer pour vérifier la consistance
        regenerated_code = code_manager.generate_deterministic_code(month_year)
        
        print(f"Période: {month_year}")
        print(f"Code généré: {current_code}")
        print(f"Code régénéré: {regenerated_code}")
        
        if current_code == regenerated_code:
            print("✅ Synchronisation: PARFAITE")
            print("   Les deux instances génèrent le même code")
        else:
            print("❌ Synchronisation: ÉCHEC")
            print(f"   Différence: {current_code} vs {regenerated_code}")
        
        # Tester avec une autre instance
        test_manager = VisibleAccessCodeManager()
        test_code = test_manager.get_current_code()
        print(f"Code autre instance: {test_code}")
        
        if current_code == test_code:
            print("✅ Synchronisation inter-instances: PARFAITE")
        else:
            print("❌ Synchronisation inter-instances: ÉCHEC")
        
        input("\nAppuyez sur Entrée pour continuer...")

# =============================================================================
# FONCTIONS DE TEST
# =============================================================================

def compare_scripts():
    """Comparer les codes générés par les deux scripts"""
    print("🔍 COMPARAISON DES DEUX SCRIPTS")
    print()
    
    # Importer les deux gestionnaires
    from hidden_script import HiddenAccessCodeManager as HiddenManager
    from visible_script import VisibleAccessCodeManager as VisibleManager
    
    hidden_manager = HiddenManager()
    visible_manager = VisibleManager()
    
    hidden_code = hidden_manager.get_current_code()
    visible_code = visible_manager.get_current_code()
    
    print(f"Script 1 (masqué): {hidden_code}")
    print(f"Script 2 (visible): {visible_code}")
    
    if hidden_code == visible_code:
        print("✅ LES DEUX SCRIPTS GÉNÈRENT LE MÊME CODE!")
    else:
        print("❌ LES CODES SONT DIFFÉRENTS!")
    
    return hidden_code == visible_code

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    """Fonction principale"""
    try:
        # Vérifier les privilèges root
        if os.geteuid() != 0:
            print("❌ Ce script doit être exécuté en tant que root")
            sys.exit(1)
        
        print("🚀 Démarrage ASTERISK MANAGER - Version Codes Visibles")
        print("   Algorithme déterministe activé")
        print()
        
        # Initialisation
        code_manager = VisibleAccessCodeManager()
        current_code = code_manager.get_current_code()
        month_year = code_manager.get_current_period()
        
        print(f"✅ Code pour {month_year}: {current_code}")
        print("🔐 Le code est visible dans l'interface")
        print()
        
        # Démarrer le menu
        menu = VisibleMenuManager()
        menu.main_menu()
        
    except KeyboardInterrupt:
        print(f"\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
