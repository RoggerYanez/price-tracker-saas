import sqlite3

def inicializar_bd():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()
    
    # Tabla para guardar el historial de precios extraídos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    
    # Tabla para guardar los productos y URLs dinámicas de los clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos_configurados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            url TEXT
        )
    """)
    
    conexion.commit()
    conexion.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    inicializar_bd()