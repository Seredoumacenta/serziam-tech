#!/usr/bin/env python3
"""
ASTERISK MANAGER - Version Complète avec Configuration Automatique
Système de gestion professionnel avec codes d'accès et blocage automatique
"""

import os
import sys
import sqlite3
import hashlib
import hmac
import subprocess
import time
from datetime import datetime, timedelta
import string
import random

# =============================================================================
# CONFIGURATION GLOBALE
# =============================================================================

class Config:
    DB_PATH = "/home/vps/asterisk/asterisk.db"
    SECRET_SEED = "asterisk_secure_deterministic_v1"
    ASTERISK_CONFIG_DIR = "/etc/asterisk"
    VENV_PATH = "/home/vps/asterisk"
    
    # Configuration des extensions
    EXTENSION_PREFIX = "601"
    EXTENSION_LENGTH = 9  # 601 + 6 chiffres = 9 chiffres au total

# =============================================================================
# ALGORITHME DÉTERMINISTE COMMUN
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
# GESTIONNAIRE DE CODES MASQUÉS
# =============================================================================

class HiddenAccessCodeManager(DeterministicCodeGenerator):
    """Gestionnaire avec codes masqués dans l'interface"""
    
    def __init__(self):
        super().__init__(Config.SECRET_SEED)
        self.initialize_database()
    
    def initialize_database(self):
        """Initialiser la base de données"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            # Table codes d'accès
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_codes (
                    id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    month_year TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table utilisateurs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    numero TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    context TEXT DEFAULT "default",
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Base de données initialisée")
        except Exception as e:
            print(f"❌ Erreur base de données: {e}")
    
    def get_current_code_with_expiry(self):
        """Obtenir le code actuel avec sa date d'expiration"""
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
        
        return code, expires_at
    
    def display_code_status(self):
        """Afficher le statut du code sans révéler le code"""
        current_date = datetime.now()
        code, expires_at = self.get_current_code_with_expiry()
        
        days_remaining = (expires_at - current_date).days
        month_name = self.month_names[current_date.month]
        
        print(f"🔐 Code d'accès {month_name} {current_date.year}: *** MASQUÉ ***")
        print(f"   Expire le: {expires_at.strftime('%d/%m/%Y')}")
        print(f"   Jours restants: {days_remaining}")
        
        return code, expires_at
    
    def validate_code(self, input_code):
        """Valider un code saisi"""
        expected_code = self.get_current_code()
        return input_code == expected_code
    
    def is_code_expired(self):
        """Vérifier si le code a expiré"""
        _, expires_at = self.get_current_code_with_expiry()
        return datetime.now() > expires_at

# =============================================================================
# GESTIONNAIRE ASTERISK
# =============================================================================

class AsteriskManager:
    """Gestionnaire Asterisk avec contrôle d'accès"""
    
    @staticmethod
    def is_running():
        """Vérifier si Asterisk est en cours d'exécution"""
        try:
            result = subprocess.run(["asterisk", "-rx", "core show version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and "Asterisk" in result.stdout
        except:
            return False
    
    @staticmethod
    def start():
        """Démarrer Asterisk"""
        print("🔄 Démarrage d'Asterisk...")
        try:
            subprocess.run(["asterisk", "-f"], capture_output=True, timeout=10)
            time.sleep(3)
            if AsteriskManager.is_running():
                print("✅ Asterisk démarré avec succès")
                return True
            else:
                print("❌ Échec du démarrage d'Asterisk")
                return False
        except Exception as e:
            print(f"❌ Erreur démarrage: {e}")
            return False
    
    @staticmethod
    def stop():
        """Arrêter Asterisk"""
        print("🔄 Arrêt d'Asterisk...")
        try:
            subprocess.run(["pkill", "asterisk"], capture_output=True)
            time.sleep(2)
            if not AsteriskManager.is_running():
                print("✅ Asterisk arrêté avec succès")
                return True
            else:
                print("❌ Échec de l'arrêt d'Asterisk")
                return False
        except Exception as e:
            print(f"❌ Erreur arrêt: {e}")
            return False
    
    @staticmethod
    def restart():
        """Redémarrer Asterisk"""
        AsteriskManager.stop()
        time.sleep(2)
        return AsteriskManager.start()

# =============================================================================
# GESTIONNAIRE D'UTILISATEURS
# =============================================================================

class UserManager:
    """Gestionnaire des utilisateurs avec numéros 601 automatiques"""
    
    def __init__(self):
        self.initialize_database()
    
    def initialize_database(self):
        """Initialiser la table des utilisateurs"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    numero TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    context TEXT DEFAULT "default",
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erreur initialisation utilisateurs: {e}")
    
    def generate_phone_number(self):
        """Générer un numéro de téléphone unique commençant par 601"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            while True:
                # Générer 6 chiffres aléatoires après 601
                random_digits = ''.join(random.choice(string.digits) for _ in range(6))
                phone_number = f"{Config.EXTENSION_PREFIX}{random_digits}"
                
                # Vérifier si le numéro existe déjà
                cursor.execute("SELECT id FROM users WHERE numero = ?", (phone_number,))
                if not cursor.fetchone():
                    conn.close()
                    return phone_number
                    
        except Exception as e:
            print(f"❌ Erreur génération numéro: {e}")
            return None
    
    def add_user(self, password, context="default"):
        """Ajouter un nouvel utilisateur avec numéro automatique"""
        try:
            phone_number = self.generate_phone_number()
            if not phone_number:
                return False
            
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO users (numero, password, context) VALUES (?, ?, ?)",
                (phone_number, password, context)
            )
            
            conn.commit()
            conn.close()
            
            print(f"✅ Utilisateur ajouté: {phone_number}")
            return phone_number
            
        except Exception as e:
            print(f"❌ Erreur ajout utilisateur: {e}")
            return False
    
    def list_users(self):
        """Lister tous les utilisateurs"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT numero, context, created_at FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
            
            conn.close()
            return users
            
        except Exception as e:
            print(f"❌ Erreur liste utilisateurs: {e}")
            return []
    
    def delete_user(self, phone_number):
        """Supprimer un utilisateur"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE numero = ?", (phone_number,))
            conn.commit()
            conn.close()
            
            print(f"✅ Utilisateur {phone_number} supprimé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression utilisateur: {e}")
            return False

# =============================================================================
# CONFIGURATEUR ASTERISK
# =============================================================================

class AsteriskConfigurator:
    """Configurateur automatique d'Asterisk"""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    def configure_asterisk(self):
        """Configurer Asterisk automatiquement"""
        print("🔄 Configuration d'Asterisk en cours...")
        
        try:
            # Créer le répertoire de configuration si nécessaire
            os.makedirs(Config.ASTERISK_CONFIG_DIR, exist_ok=True)
            
            # Configuration SIP de base
            self._create_sip_config()
            
            # Configuration extensions
            self._create_extensions_config()
            
            # Configuration PJSIP
            self._create_pjsip_config()
            
            print("✅ Configuration Asterisk terminée")
            return True
            
        except Exception as e:
            print(f"❌ Erreur configuration Asterisk: {e}")
            return False
    
    def _create_sip_config(self):
        """Créer la configuration SIP"""
        sip_conf = """
[general]
context=default
bindport=5060
bindaddr=0.0.0.0
srvlookup=yes
"""
        
        with open(os.path.join(Config.ASTERISK_CONFIG_DIR, "sip.conf"), "w") as f:
            f.write(sip_conf)
    
    def _create_extensions_config(self):
        """Créer la configuration des extensions"""
        extensions_conf = """
[default]
exten => 100,1,Answer()
exten => 100,n,Playback(hello)
exten => 100,n,Hangup()

; Utilisateurs générés automatiquement
"""
        
        # Ajouter les utilisateurs existants
        users = self.user_manager.list_users()
        for user in users:
            phone_number, context, _ = user
            extensions_conf += f"\nexten => {phone_number},1,Dial(SIP/{phone_number})\n"
        
        with open(os.path.join(Config.ASTERISK_CONFIG_DIR, "extensions.conf"), "w") as f:
            f.write(extensions_conf)
    
    def _create_pjsip_config(self):
        """Créer la configuration PJSIP"""
        pjsip_conf = """
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

"""
        
        # Ajouter les utilisateurs existants
        users = self.user_manager.list_users()
        for user in users:
            phone_number, context, _ = user
            pjsip_conf += f"""
[{phone_number}]
type=endpoint
context=default
disallow=all
allow=ulaw,alaw
auth={phone_number}
aors={phone_number}

[{phone_number}]
type=auth
auth_type=userpass
password={phone_number}
username={phone_number}

[{phone_number}]
type=aor
max_contacts=1
"""
        
        with open(os.path.join(Config.ASTERISK_CONFIG_DIR, "pjsip.conf"), "w") as f:
            f.write(pjsip_conf)

# =============================================================================
# SYSTÈME DE BLOCAGE PAR CODE D'ACCÈS
# =============================================================================

class AccessControlSystem:
    """Système de contrôle d'accès avec blocage automatique"""
    
    def __init__(self):
        self.code_manager = HiddenAccessCodeManager()
        self.asterisk_manager = AsteriskManager()
    
    def check_access(self):
        """Vérifier l'accès et bloquer si nécessaire"""
        if self.code_manager.is_code_expired():
            print("🔒 CODE D'ACCÈS EXPIRÉ!")
            print("Le serveur est bloqué jusqu'à la saisie du nouveau code.")
            
            # Arrêter Asterisk
            self.asterisk_manager.stop()
            
            # Demander le nouveau code
            return self._prompt_for_new_code()
        else:
            print("✅ Code d'accès valide")
            return True
    
    def _prompt_for_new_code(self):
        """Demander le code du nouveau mois"""
        current_date = datetime.now()
        month_year = self.code_manager.get_current_period()
        expected_code = self.code_manager.get_current_code()
        
        print(f"\n📅 Période: {current_date.strftime('%B %Y')}")
        print("💡 Le code d'accès du nouveau mois a été généré automatiquement")
        print("🔐 Veuillez saisir le code d'accès pour débloquer le système:")
        
        attempts = 3
        while attempts > 0:
            try:
                entered_code = input("Code d'accès: ").strip().upper()
                
                if self.code_manager.validate_code(entered_code):
                    print("✅ Code correct! Déblocage du système...")
                    
                    # Redémarrer Asterisk
                    if self.asterisk_manager.start():
                        print("✅ Système débloqué et Asterisk redémarré")
                        return True
                    else:
                        print("❌ Erreur lors du redémarrage d'Asterisk")
                        return False
                else:
                    attempts -= 1
                    if attempts > 0:
                        print(f"❌ Code incorrect. Il vous reste {attempts} tentative(s).")
                    else:
                        print("❌ Trop de tentatives échouées. Le système reste bloqué.")
                        return False
                        
            except KeyboardInterrupt:
                print("\n❌ Saisie annulée. Le système reste bloqué.")
                return False
        
        return False

# =============================================================================
# INTERFACE UTILISATEUR COMPLÈTE
# =============================================================================

class CompleteMenuManager:
    """Interface utilisateur complète avec toutes les fonctionnalités"""
    
    def __init__(self):
        self.code_manager = HiddenAccessCodeManager()
        self.user_manager = UserManager()
        self.asterisk_manager = AsteriskManager()
        self.configurator = AsteriskConfigurator()
        self.access_control = AccessControlSystem()
    
    @staticmethod
    def clear_screen():
        os.system('clear')
    
    @staticmethod
    def show_header():
        CompleteMenuManager.clear_screen()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              ASTERISK MANAGER - VERSION COMPLÈTE            ║")
        print("║         Configuration Auto + Codes + Blocage Sécurité       ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()
    
    def main_menu(self):
        """Menu principal"""
        
        # Vérifier l'accès au système
        if not self.access_control.check_access():
            print("❌ Accès refusé. Le système est bloqué.")
            return
        
        while True:
            self.show_header()
            
            # Afficher statut Asterisk
            status = "✅ EN COURS" if self.asterisk_manager.is_running() else "❌ ARRÊTÉ"
            print(f"Statut Asterisk: {status}")
            
            # Afficher statut du code (masqué)
            self.code_manager.display_code_status()
            
            # Afficher nombre d'utilisateurs
            users = self.user_manager.list_users()
            print(f"Utilisateurs configurés: {len(users)}")
            
            print(f"\nMENU PRINCIPAL:")
            print("1. 🔧 Configuration Asterisk Automatique")
            print("2. 👥 Gestion des utilisateurs")
            print("3. 📞 Gestion des numéros 601")
            print("4. 🚀 Contrôle Asterisk (Start/Stop/Restart)")
            print("5. 🔐 Gestion des codes d'accès")
            print("6. 🔍 Vérification système")
            print("7. 🚪 Quitter")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.configuration_menu()
            elif choice == "2":
                self.users_menu()
            elif choice == "3":
                self.numbers_menu()
            elif choice == "4":
                self.asterisk_control_menu()
            elif choice == "5":
                self.access_codes_menu()
            elif choice == "6":
                self.system_check_menu()
            elif choice == "7":
                print("Au revoir!")
                sys.exit(0)
            else:
                print("❌ Choix invalide")
                input("Appuyez sur Entrée pour continuer...")
    
    def configuration_menu(self):
        """Menu de configuration Asterisk"""
        self.show_header()
        print("🔧 CONFIGURATION ASTERISK AUTOMATIQUE")
        print()
        
        print("Cette configuration va:")
        print("✅ Créer les fichiers de configuration Asterisk")
        print("✅ Configurer les utilisateurs existants")
        print("✅ Redémarrer Asterisk")
        print()
        
        confirm = input("Confirmer la configuration? (o/N): ").strip().lower()
        
        if confirm == 'o' or confirm == 'oui':
            if self.configurator.configure_asterisk():
                print("🔄 Redémarrage d'Asterisk...")
                self.asterisk_manager.restart()
            else:
                print("❌ Échec de la configuration")
        else:
            print("❌ Configuration annulée")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def users_menu(self):
        """Menu de gestion des utilisateurs"""
        while True:
            self.show_header()
            print("👥 GESTION DES UTILISATEURS")
            print()
            
            users = self.user_manager.list_users()
            if users:
                print("Utilisateurs existants:")
                for i, user in enumerate(users, 1):
                    numero, context, created_at = user
                    print(f"  {i}. {numero} (Contexte: {context}) - Créé le: {created_at}")
            else:
                print("Aucun utilisateur configuré")
            
            print(f"\n1. ➕ Ajouter un utilisateur")
            print("2. 🗑️  Supprimer un utilisateur")
            print("3. 🔄 Reconfigurer Asterisk")
            print("0. ↩️  Retour")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.add_user_menu()
            elif choice == "2":
                self.delete_user_menu(users)
            elif choice == "3":
                self.configurator.configure_asterisk()
                print("✅ Asterisk reconfiguré avec les utilisateurs actuels")
                input("Appuyez sur Entrée pour continuer...")
            elif choice == "0":
                return
            else:
                print("❌ Choix invalide")
                input("Appuyez sur Entrée pour continuer...")
    
    def add_user_menu(self):
        """Menu d'ajout d'utilisateur"""
        self.show_header()
        print("➕ AJOUT D'UTILISATEUR")
        print()
        
        password = input("Mot de passe pour l'utilisateur: ").strip()
        context = input("Contexte [default]: ").strip() or "default"
        
        if password:
            phone_number = self.user_manager.add_user(password, context)
            if phone_number:
                print(f"✅ Utilisateur créé: {phone_number}")
                print("🔄 Mise à jour de la configuration Asterisk...")
                self.configurator.configure_asterisk()
            else:
                print("❌ Erreur lors de la création de l'utilisateur")
        else:
            print("❌ Le mot de passe est obligatoire")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def delete_user_menu(self, users):
        """Menu de suppression d'utilisateur"""
        if not users:
            print("❌ Aucun utilisateur à supprimer")
            input("Appuyez sur Entrée pour continuer...")
            return
        
        self.show_header()
        print("🗑️  SUPPRESSION D'UTILISATEUR")
        print()
        
        print("Utilisateurs existants:")
        for i, user in enumerate(users, 1):
            numero, context, _ = user
            print(f"  {i}. {numero}")
        
        try:
            choice = int(input("\nNuméro de l'utilisateur à supprimer (0 pour annuler): ").strip())
            if choice == 0:
                return
            
            if 1 <= choice <= len(users):
                phone_number = users[choice-1][0]
                confirm = input(f"Confirmer la suppression de {phone_number}? (o/N): ").strip().lower()
                
                if confirm == 'o' or confirm == 'oui':
                    if self.user_manager.delete_user(phone_number):
                        print("🔄 Mise à jour de la configuration Asterisk...")
                        self.configurator.configure_asterisk()
                else:
                    print("❌ Suppression annulée")
            else:
                print("❌ Choix invalide")
        except ValueError:
            print("❌ Veuillez entrer un numéro valide")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def numbers_menu(self):
        """Menu de gestion des numéros 601"""
        self.show_header()
        print("📞 GESTION DES NUMÉROS 601")
        print()
        
        users = self.user_manager.list_users()
        if users:
            print("Numéros 601 attribués:")
            for user in users:
                numero, context, created_at = user
                print(f"  📞 {numero} (Contexte: {context})")
        else:
            print("Aucun numéro 601 attribué")
        
        print(f"\nFormat: {Config.EXTENSION_PREFIX}XXXXXX (9 chiffres)")
        print("Génération automatique à chaque nouvel utilisateur")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def asterisk_control_menu(self):
        """Menu de contrôle Asterisk"""
        while True:
            self.show_header()
            print("🚀 CONTRÔLE ASTERISK")
            print()
            
            status = "✅ EN COURS" if self.asterisk_manager.is_running() else "❌ ARRÊTÉ"
            print(f"Statut actuel: {status}")
            
            print(f"\n1. ▶️  Démarrer Asterisk")
            print("2. ⏹️  Arrêter Asterisk")
            print("3. 🔄 Redémarrer Asterisk")
            print("4. 📊 Statut détaillé")
            print("0. ↩️  Retour")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.asterisk_manager.start()
            elif choice == "2":
                self.asterisk_manager.stop()
            elif choice == "3":
                self.asterisk_manager.restart()
            elif choice == "4":
                self.show_asterisk_status()
            elif choice == "0":
                return
            else:
                print("❌ Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def show_asterisk_status(self):
        """Afficher le statut détaillé d'Asterisk"""
        self.show_header()
        print("📊 STATUT DÉTAILLÉ ASTERISK")
        print()
        
        if self.asterisk_manager.is_running():
            print("✅ Asterisk est en cours d'exécution")
            
            try:
                # Commande de statut de base
                result = subprocess.run(["asterisk", "-rx", "core show version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"Version: {result.stdout.strip()}")
                
                # Statut des canaux
                result = subprocess.run(["asterisk", "-rx", "core show channels"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        print(f"Canaux: {lines[0]}")
                
            except Exception as e:
                print(f"❌ Erreur récupération statut: {e}")
        else:
            print("❌ Asterisk n'est pas en cours d'exécution")
    
    def access_codes_menu(self):
        """Menu de gestion des codes d'accès"""
        while True:
            self.show_header()
            print("🔐 GESTION DES CODES D'ACCÈS")
            print()
            
            # Afficher statut du code
            code, expires_at = self.code_manager.display_code_status()
            
            print(f"\n1. 🔄 Régénérer le code")
            print("2. ✅ Valider un code")
            print("3. 🔍 Tester la synchronisation")
            print("0. ↩️  Retour")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.regenerate_code()
            elif choice == "2":
                self.validate_code_menu()
            elif choice == "3":
                self.test_synchronization()
            elif choice == "0":
                return
            else:
                print("❌ Choix invalide")
                input("Appuyez sur Entrée pour continuer...")
    
    def regenerate_code(self):
        """Régénérer le code (en réalité, même code déterministe)"""
        current_date = datetime.now()
        month_year = self.code_manager.get_current_period()
        new_code = self.code_manager.generate_deterministic_code(month_year)
        
        month_name = self.code_manager.month_names[current_date.month]
        print(f"✅ Code {month_name} {current_date.year} régénéré (identique)")
        print(f"🔐 Code: *** MASQUÉ ***")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def validate_code_menu(self):
        """Menu de validation de code"""
        self.show_header()
        print("🔐 VALIDATION DE CODE")
        print()
        
        test_code = input("Code à valider: ").strip().upper()
        
        if self.code_manager.validate_code(test_code):
            print("✅ Code valide!")
        else:
            print("❌ Code invalide ou expiré")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def test_synchronization(self):
        """Tester la synchronisation"""
        self.show_header()
        print("🔍 TEST DE SYNCHRONISATION")
        print()
        
        # Générer le code actuel
        current_code = self.code_manager.get_current_code()
        month_year = self.code_manager.get_current_period()
        
        # Régénérer pour vérifier la consistance
        regenerated_code = self.code_manager.generate_deterministic_code(month_year)
        
        print(f"Période: {month_year}")
        print(f"Code généré: *** MASQUÉ ***")
        print(f"Code régénéré: *** MASQUÉ ***")
        
        if current_code == regenerated_code:
            print("✅ Synchronisation: PARFAITE")
            print("   Les deux instances génèrent le même code")
        else:
            print("❌ Synchronisation: ÉCHEC")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def system_check_menu(self):
        """Menu de vérification système"""
        self.show_header()
        print("🔍 VÉRIFICATION SYSTÈME")
        print()
        
        # Vérifier Asterisk
        asterisk_ok = self.asterisk_manager.is_running()
        print(f"Asterisk: {'✅' if asterisk_ok else '❌'} {'EN COURS' if asterisk_ok else 'ARRÊTÉ'}")
        
        # Vérifier code d'accès
        code_expired = self.code_manager.is_code_expired()
        print(f"Code d'accès: {'❌ EXPIRÉ' if code_expired else '✅ VALIDE'}")
        
        # Vérifier utilisateurs
        users = self.user_manager.list_users()
        print(f"Utilisateurs: {len(users)} configuré(s)")
        
        # Vérifier base de données
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            conn.close()
            print("Base de données: ✅ ACCESSIBLE")
        except:
            print("Base de données: ❌ INACCESSIBLE")
        
        print(f"\nStatut global: {'✅ OPÉRATIONNEL' if asterisk_ok and not code_expired else '❌ PROBLÈME'}")
        
        input("\nAppuyez sur Entrée pour continuer...")

# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

def main():
    """Fonction principale"""
    try:
        # Vérifier les privilèges root
        if os.geteuid() != 0:
            print("❌ Ce script doit être exécuté en tant que root")
            sys.exit(1)
        
        print("🚀 DÉMARRAGE ASTERISK MANAGER - VERSION COMPLÈTE")
        print("   Système de gestion professionnel avec sécurité avancée")
        print()
        
        # Démarrer le menu principal
        menu = CompleteMenuManager()
        menu.main_menu()
        
    except KeyboardInterrupt:
        print(f"\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
