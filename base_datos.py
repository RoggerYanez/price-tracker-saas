import sqlite3

def inicializar_bd():
    # Conecta (o crea) la base de datos local
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()

    # Crea una tabla para almacenar los registros de precios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            precio REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conexion.commit()
    conexion.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    inicializar_bd()