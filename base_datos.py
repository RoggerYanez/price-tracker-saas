import os
import psycopg2

def inicializar_bd():
    # Obtener la URL de la base de datos desde las variables de entorno de Railway
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")

    # Conectar a PostgreSQL usando la URL de Railway
    conexion = psycopg2.connect(database_url)
    cursor = conexion.cursor()
    
    # En PostgreSQL se usa SERIAL PRIMARY KEY en lugar de AUTOINCREMENT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_precios (
            id SERIAL PRIMARY KEY,
            producto TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos_configurados (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            nombre TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        # En PostgreSQL los placeholders para parámetros son %s en lugar de ?
        cursor.execute("INSERT INTO usuarios (username, email, password, rol) VALUES (%s, %s, %s, %s)", 
                       ('admin', 'admin@pricetracker.com', '12345', 'admin'))
        print("Administrador por defecto creado.")

    conexion.commit()
    cursor.close()
    conexion.close()
    print("Base de datos PostgreSQL inicializada con éxito.")

if __name__ == "__main__":
    inicializar_bd()