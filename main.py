from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="SaaS Monitoreo de Precios con Seguridad")
templates = Jinja2Templates(directory="templates")

def obtener_conexion():
    return sqlite3.connect("monitoreo.db")

class NuevoProducto(BaseModel):
    nombre: str
    url: str

class LoginData(BaseModel):
    username: str
    password: str

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

# NUEVO: Endpoint para autenticar usuarios y retornar su rol
@app.post("/api/login")
def login(data: LoginData):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT rol FROM usuarios WHERE username = ? AND password = ?", (data.username, data.password))
    usuario = cursor.fetchone()
    conexion.close()
    
    if not usuario:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    return {"mensaje": "Login exitoso", "rol": usuario[0], "username": data.username}

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
    
    productos = [{"id": f[0], "producto": f[1], "precio": f[2], "fecha": f[3]} for f in filas]
    return productos

@app.post("/api/agregar-producto")
def agregar_producto(item: NuevoProducto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO productos_configurados (nombre, url) VALUES (?, ?)", (item.nombre, item.url))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Producto y URL registrados exitosamente"}