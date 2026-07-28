import sqlite3

def inicializar_bd():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()
    
    # Tabla para el historial de precios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    
    # Tabla para las URLs dinámicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos_configurados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            url TEXT
        )
    """)
    
    # NUEVA TABLA: Usuarios y roles (admin o cliente)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    
    # Insertar usuarios por defecto si no existen
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                       ('admin', '12345', 'admin'))
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                       ('cliente1', '12345', 'cliente'))
        print("Usuarios de prueba creados: admin / cliente1 (Contraseña: 12345)")

    conexion.commit()
    conexion.close()
    print("Base de datos inicializada correctamente con seguridad.")

if __name__ == "__main__":
    inicializar_bd()