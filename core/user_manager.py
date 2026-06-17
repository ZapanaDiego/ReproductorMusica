import os
import json
import time

DATABASE_DIR = os.path.join(os.path.dirname(__file__), "database")
DB_FILE = os.path.join(DATABASE_DIR, "users_db.json")

def _clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def _create_database():
    _clear_screen()
    print("=================================================")
    print("    INICIALIZACIÓN DEL SISTEMA MULTIUSUARIO      ")
    print("=================================================")
    
    while True:
        try:
            num_users = int(input("\nIngrese cantidad de usuarios a registrar (Mín: 1, Máx: 5): "))
            if 1 <= num_users <= 5:
                break
            print("❌ Error: La cantidad debe estar entre 1 y 5.")
        except ValueError:
            print("❌ Error: Por favor, ingrese un número válido.")
            
    users = []
    for i in range(1, num_users + 1):
        while True:
            name = input(f"Nombre del Usuario {i}: ").strip()
            if name:
                users.append({
                    "id": i,
                    "name": name,
                    "liked_tracks": [],
                    "liked_albums": {}
                })
                break
            print("❌ Error: El nombre no puede estar vacío.")
            
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)
        
    db_data = {"users": users}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=4)
        
    print("\n✅ Base de datos de usuarios creada exitosamente.")
    time.sleep(1)
    return db_data

def bootstrap_system() -> dict:
    """
    Punto de entrada CLI pre-Textual.
    Se encarga de arrancar, crear si no existe y seleccionar un usuario activo.
    Retorna el diccionario de datos del usuario seleccionado.
    """
    if not os.path.exists(DB_FILE):
        db_data = _create_database()
    else:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        except Exception as e:
            print(f"❌ Error crítico leyendo la base de datos de usuarios: {e}")
            print("Recreando base de datos...")
            time.sleep(2)
            db_data = _create_database()
            
    users = db_data.get("users", [])
    if not users:
        print("❌ Error: Base de datos vacía.")
        db_data = _create_database()
        users = db_data.get("users", [])
        
    if len(users) == 1:
        return users[0]
        
    # Menú de selección interactiva (Neo-Terminal)
    while True:
        _clear_screen()
        print("╔═══════════════════════════════════════════════╗")
        print("║          SELECCIÓN DE PERFIL ACTIVO           ║")
        print("╚═══════════════════════════════════════════════╝\n")
        
        for u in users:
            print(f"  [{u['id']}] \033[96m{u['name']}\033[0m")
            
        print("\n-------------------------------------------------")
        choice = input("Seleccione el ID de su perfil: ").strip()
        
        try:
            choice_id = int(choice)
            for u in users:
                if u["id"] == choice_id:
                    print(f"\n⚡ Iniciando sesión como \033[92m{u['name']}\033[0m ...")
                    time.sleep(0.5)
                    return u
            print("❌ ID no encontrado. Intente de nuevo.")
            time.sleep(1)
        except ValueError:
            print("❌ Opción inválida. Ingrese un número.")
            time.sleep(1)
