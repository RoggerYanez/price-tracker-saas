import os
import psycopg2
from playwright.sync_api import sync_playwright
from datetime import datetime

def ejecutar_scraping():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("La variable de entorno DATABASE_URL no está configurada.")
        return

    conexion = psycopg2.connect(database_url)
    cursor = conexion.cursor()
    
    # Solo rastrear productos activos
    cursor.execute("SELECT nombre, url FROM productos_configurados WHERE estado = 'activo'")
    productos = cursor.fetchall()
    cursor.close()
    conexion.close()

    if not productos:
        print("No hay productos activos para rastrear en la base de datos.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for nombre, url in productos:
            try:
                print(f"Rastreando producto: {nombre} -> {url}")
                page.goto(url)
                
                # Selector de ejemplo (ajustar según la página web)
                precio_texto = page.locator(".price_color").inner_text()
                precio_limpio = float(precio_texto.replace("S/", "").replace("£", "").replace("$", "").strip())
                
                conexion = psycopg2.connect(database_url)
                cursor = conexion.cursor()
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO historial_precios (producto, precio, fecha) VALUES (%s, %s, %s)",
                    (nombre, precio_limpio, fecha_actual)
                )
                conexion.commit()
                cursor.close()
                conexion.close()
                print(f"Precio guardado con éxito para: {nombre}")
                
            except Exception as e:
                print(f"Error al rastrear {nombre} en la URL {url}: {e}")

        browser.close()

if __name__ == "__main__":
    ejecutar_scraping()