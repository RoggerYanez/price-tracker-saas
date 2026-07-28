import sqlite3

def forzar_precio_alto():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()

    # Actualizamos el precio del último registro a 55.00 para simular que antes era caro
    cursor.execute("""
        UPDATE historial_precios 
        SET precio = 55.00 
        WHERE id = (SELECT MAX(id) FROM historial_precios)
    """)

    conexion.commit()
    conexion.close()
    print("¡Listo! El último precio registrado ahora es 55.00 (simulando un precio alto).")

if __name__ == "__main__":
    forzar_precio_alto()