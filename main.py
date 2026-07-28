import os
import psycopg2
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="SaaS Monitoreo de Precios")
templates = Jinja2Templates(directory="templates")

def obtener_conexion():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(database_url)

class NuevoProducto(BaseModel):
    username: str
    nombre: str
    url: str

class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    email: str
    password: str

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/login")
def login(data: LoginData):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT rol, username FROM usuarios WHERE LOWER(username) = LOWER(%s) AND password = %s",
        (data.username.strip(), data.password)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()
    
    if not usuario:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    return {"mensaje": "Login exitoso", "rol": usuario[0], "username": usuario[1]}

@app.post("/api/register")
def register(data: RegisterData):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    user_limpio = data.username.strip()
    email_limpio = data.email.strip().lower()
    
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM usuarios WHERE LOWER(username) = LOWER(%s) OR LOWER(email) = %s",
            (user_limpio, email_limpio)
        )
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conexion.close()
            raise HTTPException(status_code=400, detail="El nombre de usuario o el correo ya están registrados")

        cursor.execute(
            "INSERT INTO usuarios (username, email, password, rol) VALUES (%s, %s, %s, %s)",
            (user_limpio, email_limpio, data.password, 'cliente')
        )
        conexion.commit()
    except psycopg2.IntegrityError:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=400, detail="Error al registrar los datos")
    
    cursor.close()
    conexion.close()
    return {"mensaje": "Registro exitoso"}

@app.get("/api/productos")
def listar_productos(username: str = Query(...), rol: str = Query(...)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    if rol == 'admin':
        cursor.execute("""
            SELECT hp.id, hp.producto, hp.precio, hp.fecha 
            FROM historial_precios hp
            JOIN (
                SELECT producto, MAX(id) as max_id 
                FROM historial_precios 
                GROUP BY producto
            ) latest ON hp.id = latest.max_id
        """)
    else:
        cursor.execute("""
            SELECT hp.id, hp.producto, hp.precio, hp.fecha 
            FROM historial_precios hp
            JOIN productos_configurados pc ON hp.producto = pc.nombre
            JOIN (
                SELECT producto, MAX(id) as max_id 
                FROM historial_precios 
                GROUP BY producto
            ) latest ON hp.id = latest.max_id
            WHERE pc.username = %s
        """, (username,))
        
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    
    return [{"id": f[0], "producto": f[1], "precio": f[2], "fecha": f[3]} for f in filas]

@app.post("/api/agregar-producto")
def agregar_producto(item: NuevoProducto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO productos_configurados (username, nombre, url) VALUES (%s, %s, %s)",
        (item.username, item.nombre, item.url)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"mensaje": "Producto registrado exitosamente"}