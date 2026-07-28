import sqlite3
from playwright.sync_api import sync_playwright
from datetime import datetime

def ejecutar_scraping():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()
    
    # Consultar todas las URLs configuradas por los clientes
    cursor.execute("SELECT nombre, url FROM productos_configurados")
    productos = cursor.fetchall()
    conexion.close()

    if not productos:
        print("No hay productos configurados para rastrear en la base de datos.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for nombre, url in productos:
            try:
                print(f"Rastreando producto: {nombre} -> {url}")
                page.goto(url)
                
                # NOTA: Ajusta el selector CSS según la página web que tus clientes deseen rastrear
                # Este selector '.price_color' es un ejemplo de prueba (puedes adaptarlo o hacerlo genérico)
                precio_texto = page.locator(".price_color").inner_text()
                
                # Limpiar el texto del precio para convertirlo a número decimal
                precio_limpio = float(precio_texto.replace("S/", "").replace("£", "").replace("$", "").strip())
                
                # Guardar el nuevo precio obtenido en el historial
                conexion = sqlite3.connect("monitoreo.db")
                cursor = conexion.cursor()
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO historial_precios (producto, precio, fecha) VALUES (?, ?, ?)",
                    (nombre, precio_limpio, fecha_actual)
                )
                conexion.commit()
                conexion.close()
                print(f"Precio guardado con éxito para: {nombre}")
                
            except Exception as e:
                print(f"Error al rastrear {nombre} en la URL {url}: {e}")

        browser.close()

if __name__ == "__main__":
    ejecutar_scraping()