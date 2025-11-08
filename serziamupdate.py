# =============================================================================
# INSTALLATEUR AUTOMATIQUE SYSTÈME
# =============================================================================

class SystemInstaller:
    """Installateur automatique pour Ubuntu/Debian"""
    
    @staticmethod
    def check_and_install_packages():
        """Vérifier et installer les paquets nécessaires"""
        print("🔍 Vérification des paquets système...")
        
        required_packages = {
            'asterisk': 'Asterisk PBX',
            'iptables': 'Système de firewall',
            'ufw': 'Firewall simplifié',
            'sqlite3': 'Base de données SQLite',
            'python3-pip': 'Gestionnaire de paquets Python'
        }
        
        missing_packages = []
        
        for package, description in required_packages.items():
            try:
                # Vérifier si le paquet est installé
                result = subprocess.run(
                    ['dpkg', '-l', package], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    missing_packages.append((package, description))
                else:
                    print(f"✅ {package} ({description}) - Installé")
            except Exception as e:
                print(f"❌ Erreur vérification {package}: {e}")
        
        if missing_packages:
            print(f"\n📦 Installation de {len(missing_packages)} paquet(s) manquant(s)...")
            SystemInstaller.install_packages(missing_packages)
        else:
            print("✅ Tous les paquets nécessaires sont installés")
    
    @staticmethod
    def install_packages(missing_packages):
        """Installer les paquets manquants"""
        try:
            # Mettre à jour les dépôts
            print("🔄 Mise à jour des dépôts...")
            subprocess.run(['apt', 'update'], check=True)
            
            # Installer les paquets
            packages_to_install = [pkg[0] for pkg in missing_packages]
            print(f"📦 Installation: {', '.join(packages_to_install)}")
            
            subprocess.run(
                ['apt', 'install', '-y'] + packages_to_install,
                check=True
            )
            
            print("✅ Tous les paquets installés avec succès")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'installation: {e}")
            print("💡 Essayez: sudo apt update && sudo apt install asterisk iptables ufw sqlite3 python3-pip")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return False
        
        return True
    
    @staticmethod
    def configure_firewall():
        """Configurer le firewall pour Asterisk"""
        print("🔥 Configuration du firewall...")
        
        # Ports Asterisk à ouvrir
        asterisk_ports = [
            '5060/tcp',  # SIP TCP
            '5060/udp',  # SIP UDP
            '5061/tcp',  # SIP TLS
            '5061/udp',  # SIP UDP
            '10000:20000/udp',  # RTP
            '5038/tcp',  # AMI
            '8088/tcp',  # HTTP
            '8089/tcp'   # HTTPS
        ]
        
        try:
            # Réinitialiser UFW
            subprocess.run(['ufw', '--force', 'reset'], check=True)
            
            # Politique par défaut
            subprocess.run(['ufw', 'default', 'deny', 'incoming'], check=True)
            subprocess.run(['ufw', 'default', 'allow', 'outgoing'], check=True)
            
            # Ouvrir les ports Asterisk
            for port in asterisk_ports:
                subprocess.run(['ufw', 'allow', port], check=True)
                print(f"✅ Port {port} ouvert")
            
            # Activer UFW
            subprocess.run(['ufw', '--force', 'enable'], check=True)
            
            # Configurer iptables pour la persistance
            subprocess.run(['iptables-save'], check=True)
            
            print("✅ Firewall configuré avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur configuration firewall: {e}")
            print("💡 Configuration manuelle requise")
            return False
    
    @staticmethod
    def setup_asterisk():
        """Configuration de base d'Asterisk"""
        print("📞 Configuration d'Asterisk...")
        
        try:
            # Créer les répertoires nécessaires
            directories = [
                '/etc/asterisk',
                '/var/log/asterisk', 
                '/var/run/asterisk',
                '/var/spool/asterisk',
                '/var/lib/asterisk'
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                subprocess.run(['chown', 'asterisk:asterisk', directory], check=True)
            
            # Configuration minimale d'Asterisk
            basic_config = """
[directories]
astetcdir => /etc/asterisk
astmoddir => /usr/lib/asterisk/modules
astvarlibdir => /var/lib/asterisk
astdbdir => /var/lib/asterisk
astkeydir => /var/lib/asterisk
astdatadir => /var/lib/asterisk
astagidir => /var/lib/asterisk/agi-bin
astspooldir => /var/spool/asterisk
astrundir => /var/run/asterisk
astlogdir => /var/log/asterisk

[options]
verbose = 3
debug = 0
maxfiles = 100000
"""
            
            with open('/etc/asterisk/asterisk.conf', 'w') as f:
                f.write(basic_config)
            
            # Redémarrer Asterisk
            subprocess.run(['systemctl', 'restart', 'asterisk'], check=True)
            subprocess.run(['systemctl', 'enable', 'asterisk'], check=True)
            
            print("✅ Asterisk configuré avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur configuration Asterisk: {e}")
            return False
    
    @staticmethod
    def initialize_database():
        """Initialiser la base de données si elle n'existe pas"""
        print("🗄️  Initialisation de la base de données...")
        
        try:
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
            
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
            
            # Table statut système
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_status (
                    id INTEGER PRIMARY KEY,
                    asterisk_running INTEGER DEFAULT 0,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insérer l'état initial
            cursor.execute('INSERT OR IGNORE INTO system_status (id, asterisk_running) VALUES (1, 0)')
            
            conn.commit()
            conn.close()
            
            # Appliquer les permissions
            subprocess.run(['chmod', '755', os.path.dirname(Config.DB_PATH)], check=True)
            subprocess.run(['chmod', '644', Config.DB_PATH], check=True)
            
            print("✅ Base de données initialisée avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur initialisation base de données: {e}")
            return False
    
    @staticmethod
    def full_system_install():
        """Installation complète du système"""
        print("🚀 INSTALLATION AUTOMATIQUE DU SYSTÈME")
        print("=" * 50)
        
        steps = [
            ("Vérification des paquets", SystemInstaller.check_and_install_packages),
            ("Configuration du firewall", SystemInstaller.configure_firewall),
            ("Configuration d'Asterisk", SystemInstaller.setup_asterisk),
            ("Initialisation base de données", SystemInstaller.initialize_database)
        ]
        
        for step_name, step_function in steps:
            print(f"\n📋 {step_name}...")
            if step_function():
                print(f"✅ {step_name} - TERMINÉ")
            else:
                print(f"❌ {step_name} - ÉCHEC")
                return False
            
            time.sleep(1)
        
        print("\n🎉 INSTALLATION TERMINÉE AVEC SUCCÈS!")
        print("Le système est maintenant prêt à être utilisé.")
        return True

# =============================================================================
# VÉRIFICATEUR SYSTÈME
# =============================================================================

class SystemChecker:
    """Vérificateur de l'état du système"""
    
    @staticmethod
    def check_system_requirements():
        """Vérifier les prérequis système"""
        print("🔍 Diagnostic du système...")
        
        checks = [
            ("Système Ubuntu/Debian", SystemChecker._check_ubuntu),
            ("Privilèges root", SystemChecker._check_root),
            ("Connectivité Internet", SystemChecker._check_internet),
            ("Base de données", SystemChecker._check_database),
            ("Service Asterisk", SystemChecker._check_asterisk_service)
        ]
        
        all_ok = True
        
        for check_name, check_function in checks:
            if check_function():
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_ok = False
        
        return all_ok
    
    @staticmethod
    def _check_ubuntu():
        """Vérifier si le système est Ubuntu/Debian"""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                return 'ubuntu' in content or 'debian' in content
        except:
            return False
    
    @staticmethod
    def _check_root():
        """Vérifier les privilèges root"""
        return os.geteuid() == 0
    
    @staticmethod
    def _check_internet():
        """Vérifier la connectivité Internet"""
        try:
            subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                         capture_output=True, timeout=5)
            return True
        except:
            return False
    
    @staticmethod
    def _check_database():
        """Vérifier l'accès à la base de données"""
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            conn.close()
            return True
        except:
            return False
    
    @staticmethod
    def _check_asterisk_service():
        """Vérifier le service Asterisk"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'asterisk'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

# =============================================================================
# MODIFICATIONS DU POINT D'ENTRÉE PRINCIPAL
# =============================================================================

def main():
    """Fonction principale avec installation automatique"""
    try:
        # Afficher le header
        print("🚀 ASTERISK MANAGER - INSTALLATION AUTOMATIQUE")
        print("   Système professionnel de gestion Asterisk")
        print("=" * 60)
        
        # Vérifier les prérequis système
        if not SystemChecker.check_system_requirements():
            print("\n❌ Prérequis système non satisfaits.")
            print("🔧 Lancement de l'installation automatique...")
            
            if not SystemInstaller.full_system_install():
                print("❌ Échec de l'installation automatique")
                print("💡 Solutions manuelles:")
                print("   1. sudo apt update && sudo apt install asterisk iptables ufw sqlite3")
                print("   2. Configurer le firewall: sudo ufw allow 5060,5061,10000:20000/udp")
                print("   3. Redémarrer: sudo systemctl restart asterisk")
                sys.exit(1)
        
        # Vérifier les privilèges root
        if os.geteuid() != 0:
            print("❌ Ce script doit être exécuté en tant que root")
            print("💡 Utilisez: sudo python3 script_complet.py")
            sys.exit(1)
        
        print("\n✅ Système prêt!")
        print("📞 Démarrage du gestionnaire Asterisk...")
        
        # Démarrer le menu principal
        menu = CompleteMenuManager()
        menu.main_menu()
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# =============================================================================
# AJOUT AU MENU PRINCIPAL
# =============================================================================

# Ajouter cette option dans le menu principal de la classe CompleteMenuManager
def main_menu(self):
    """Menu principal avec option d'installation"""
    
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
        print("7. ⚙️  Installation/Réparation système")  # NOUVELLE OPTION
        print("8. 🚪 Quitter")
        
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
        elif choice == "7":  # NOUVELLE OPTION
            self.system_install_menu()
        elif choice == "8":
            print("Au revoir!")
            sys.exit(0)
        else:
            print("❌ Choix invalide")
            input("Appuyez sur Entrée pour continuer...")

# Ajouter cette nouvelle méthode à la classe CompleteMenuManager
def system_install_menu(self):
    """Menu d'installation et réparation du système"""
    self.show_header()
    print("⚙️  INSTALLATION ET RÉPARATION SYSTÈME")
    print()
    
    print("Options disponibles:")
    print("1. 🔍 Vérifier l'état du système")
    print("2. 📦 Installer les paquets manquants")
    print("3. 🔥 Configurer le firewall")
    print("4. 📞 Configurer Asterisk")
    print("5. 🗄️  Réinitialiser la base de données")
    print("6. 🚀 Installation complète automatique")
    print("0. ↩️  Retour")
    
    choice = input("\nVotre choix: ").strip()
    
    if choice == "1":
        SystemChecker.check_system_requirements()
    elif choice == "2":
        SystemInstaller.check_and_install_packages()
    elif choice == "3":
        SystemInstaller.configure_firewall()
    elif choice == "4":
        SystemInstaller.setup_asterisk()
    elif choice == "5":
        SystemInstaller.initialize_database()
    elif choice == "6":
        SystemInstaller.full_system_install()
    elif choice == "0":
        return
    else:
        print("❌ Choix invalide")
    
    input("\nAppuyez sur Entrée pour continuer...")
