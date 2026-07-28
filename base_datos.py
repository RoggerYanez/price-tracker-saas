import sqlite3

def inicializar_bd():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    
    # Tabla productos_configurados con la columna 'username'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos_configurados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            nombre TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, email, password, rol) VALUES (?, ?, ?, ?)", 
                       ('admin', 'admin@pricetracker.com', '12345', 'admin'))
        print("Administrador por defecto creado.")

    conexion.commit()
    conexion.close()
    print("Base de datos actualizada con productos por usuario.")

if __name__ == "__main__":
    inicializar_bd()