from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3

app = FastAPI(title="SaaS Monitoreo de Precios")

# Configurar la carpeta donde estará la interfaz visual
templates = Jinja2Templates(directory="templates")

def obtener_conexion():
    return sqlite3.connect("monitoreo.db")

# Ruta principal que muestra la página web (Corregida para versiones recientes)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

# API para que el Frontend obtenga la lista de productos y sus últimos precios
@app.get("/api/productos")
def listar_productos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("""
        SELECT hp.id, hp.producto, hp.precio, hp.fecha 
        FROM historial_precios hp
        JOIN (
            SELECT producto, MAX(id) as max_id 
            FROM historial_precios 
            GROUP BY producto
        ) latest ON hp.id = latest.max_id
    """)
    filas = cursor.fetchall()
    conexion.close()
    
    productos = []
    for fila in filas:
        productos.append({
            "id": fila[0],
            "producto": fila[1],
            "precio": fila[2],
            "fecha": fila[3]
        })
    return productos

# API para ver el historial de precios de un producto específico
@app.get("/api/historial/{nombre_producto}")
def ver_historial(nombre_producto: str):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT precio, fecha FROM historial_precios 
        WHERE producto = ? ORDER BY fecha ASC
    """, (nombre_producto,))
    filas = cursor.fetchall()
    conexion.close()
    
    historial = [{"precio": f[0], "fecha": f[1]} for f in filas]
    return historial