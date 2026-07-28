from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="SaaS Monitoreo de Precios")
templates = Jinja2Templates(directory="templates")

def obtener_conexion():
    return sqlite3.connect("monitoreo.db")

class NuevoProducto(BaseModel):
    nombre: str
    url: str

class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    password: str

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

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

# NUEVO: Endpoint para registrarse como cliente nuevo
@app.post("/api/register")
def register(data: RegisterData):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        # Por seguridad, el rol se define siempre como 'cliente' por defecto
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                       (data.username, data.password, 'cliente'))
        conexion.commit()
    except sqlite3.IntegrityError:
        conexion.close()
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
    
    conexion.close()
    return {"mensaje": "Registro exitoso"}

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
    
    return [{"id": f[0], "producto": f[1], "precio": f[2], "fecha": f[3]} for f in filas]

@app.post("/api/agregar-producto")
def agregar_producto(item: NuevoProducto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO productos_configurados (nombre, url) VALUES (?, ?)", (item.nombre, item.url))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Producto registrado exitosamente"}