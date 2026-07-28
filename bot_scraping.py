import sqlite3
from datetime import datetime
import time
from playwright.sync_api import sync_playwright
import schedule

def asegurar_tabla():
    conexion = sqlite3.connect("monitoreo.db")
    cursor = conexion.cursor()
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

def extraer_y_guardar():
    asegurar_tabla()
    url = "https://www.buscalibre.pe/libro-moonwalk-a-memoir/9780307716989/p/2754152"

    print(f"\n--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Revisando producto en Buscalibre ---")
    
    try:
        with sync_playwright() as p:
            # Puedes poner headless=True una vez que verifiques que funciona
            browser = p.chromium.launch(headless=False)
            page = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ).new_page()
            
            page.goto(url, timeout=60000)
            
            # Esperamos a que cargue al menos el título
            page.wait_for_selector(".tituloProducto", timeout=15000)
            nombre_producto = page.locator("p.tituloProducto").inner_text().strip()

            # Verificamos si el producto está SIN STOCK antes de buscar el precio
            sin_stock = page.locator("text=Sin Stock").count() > 0
            
            if sin_stock:
                print(f"Producto: {nombre_producto}")
                print("⚠️ El producto se encuentra actualmente SIN STOCK. No hay precio disponible para registrar.")
                browser.close()
                return

            # Si hay stock, buscamos el precio
            page.wait_for_selector("strong.precio", timeout=5000)
            precio_texto = page.locator("strong.precio").inner_text().strip()
            
            time.sleep(2)
            browser.close()

        # Limpiar el formato de moneda peruana
        precio_limpio = float(
            precio_texto.replace("S/", "")
                        .replace("S/.", "")
                        .replace(",", ".")
                        .strip()
        )

        conexion = sqlite3.connect("monitoreo.db")
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT precio FROM historial_precios 
            WHERE producto = ? 
            ORDER BY id DESC LIMIT 1
        """, (nombre_producto,))
        ultimo_registro = cursor.fetchone()

        print(f"Producto: {nombre_producto}")
        
        if ultimo_registro:
            precio_anterior = ultimo_registro[0]
            print(f"Precio anterior: S/ {precio_anterior:.2f} | Precio actual: S/ {precio_limpio:.2f}")
            
            if precio_limpio < precio_anterior:
                diferencia = precio_anterior - precio_limpio
                print(f"🔥 ¡ALERTA! El precio BAJÓ. ¡Ahorro de S/ {diferencia:.2f}! 🔥")
            elif precio_limpio > precio_anterior:
                diferencia = precio_limpio - precio_anterior
                print(f"📈 El precio SUBIÓ S/ {diferencia:.2f} respecto a la última revisión.")
            else:
                print(f"➖ El precio se mantiene estable sin cambios.")
        else:
            print(f"Primer registro histórico guardado para: {nombre_producto} (S/ {precio_limpio:.2f})")

        cursor.execute("""
            INSERT INTO historial_precios (producto, precio)
            VALUES (?, ?)
        """, (nombre_producto, precio_limpio))
        
        conexion.commit()
        conexion.close()

    except Exception as e:
        print(f"Ocurrió un error durante el proceso con Playwright: {e}")

schedule.every(1).minutes.do(extraer_y_guardar)

if __name__ == "__main__":
    print("--- BOT COMERCIAL CON VALIDACIÓN DE STOCK ACTIVADO ---")
    print("El bot analizará los cambios automáticamente cada minuto. (Presiona Ctrl+C para detener).")
    
    extraer_y_guardar()

    while True:
        schedule.run_pending()
        time.sleep(1)