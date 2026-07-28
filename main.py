import os
import csv
import io
import psycopg2
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager

def inicializar_bd():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")

    conexion = psycopg2.connect(database_url)
    cursor = conexion.cursor()
    
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
            url TEXT NOT NULL,
            categoria TEXT DEFAULT 'General',
            precio_objetivo REAL DEFAULT 0.0,
            estado TEXT DEFAULT 'activo'
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
        cursor.execute(
            "INSERT INTO usuarios (username, email, password, rol) VALUES (%s, %s, %s, %s)",
            ('admin', 'admin@pricetracker.com', '12345', 'admin')
        )
        print("Administrador por defecto creado.")

    conexion.commit()
    cursor.close()
    conexion.close()
    print("Base de datos PostgreSQL inicializada con éxito para Fase 2.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        inicializar_bd()
    except Exception as e:
        print(f"Error crítico al inicializar la base de datos: {e}")
    yield

app = FastAPI(title="SaaS Monitoreo de Precios - Fase 2", lifespan=lifespan)
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
    categoria: str = "General"
    precio_objetivo: float = 0.0

class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    email: str
    password: str

class EstadoProducto(BaseModel):
    estado: str

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
            SELECT pc.id, pc.nombre, hp.precio, hp.fecha, pc.categoria, pc.precio_objetivo, pc.estado, pc.username
            FROM productos_configurados pc
            LEFT JOIN LATERAL (
                SELECT precio, fecha FROM historial_precios 
                WHERE producto = pc.nombre 
                ORDER BY id DESC LIMIT 1
            ) hp ON true
        """)
    else:
        cursor.execute("""
            SELECT pc.id, pc.nombre, hp.precio, hp.fecha, pc.categoria, pc.precio_objetivo, pc.estado, pc.username
            FROM productos_configurados pc
            LEFT JOIN LATERAL (
                SELECT precio, fecha FROM historial_precios 
                WHERE producto = pc.nombre 
                ORDER BY id DESC LIMIT 1
            ) hp ON true
            WHERE pc.username = %s
        """, (username,))
        
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    
    resultados = []
    for f in filas:
        resultados.append({
            "id": f[0],
            "producto": f[1],
            "precio": f[2] if f[2] is not None else 0.0,
            "fecha": f[3] if f[3] is not None else "Sin registros",
            "categoria": f[4],
            "precio_objetivo": f[5],
            "estado": f[6],
            "username": f[7]
        })
    return resultados

@app.post("/api/agregar-producto")
def agregar_producto(item: NuevoProducto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO productos_configurados (username, nombre, url, categoria, precio_objetivo, estado) VALUES (%s, %s, %s, %s, %s, 'activo')",
        (item.username, item.nombre, item.url, item.categoria, item.precio_objetivo)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"mensaje": "Producto registrado exitosamente"}

@app.patch("/api/productos/{producto_id}/estado")
def cambiar_estado_producto(producto_id: int, data: EstadoProducto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE productos_configurados SET estado = %s WHERE id = %s",
        (data.estado, producto_id)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"mensaje": f"Estado actualizado a {data.estado}"}

@app.delete("/api/productos/{producto_id}")
def eliminar_producto(producto_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM productos_configurados WHERE id = %s", (producto_id,))
    prod = cursor.fetchone()
    if prod:
        nombre_prod = prod[0]
        cursor.execute("DELETE FROM productos_configurados WHERE id = %s", (producto_id,))
        cursor.execute("DELETE FROM historial_precios WHERE producto = %s", (nombre_prod,))
        conexion.commit()
    cursor.close()
    conexion.close()
    return {"mensaje": "Producto eliminado exitosamente"}

@app.get("/api/historial/{nombre_producto}")
def obtener_historial_producto(nombre_producto: str):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT precio, fecha FROM historial_precios WHERE producto = %s ORDER BY id ASC",
        (nombre_producto,)
    )
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [{"precio": f[0], "fecha": f[1]} for f in filas]

@app.get("/api/exportar-csv")
def exportar_csv(username: str = Query(...), rol: str = Query(...)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    if rol == 'admin':
        cursor.execute("SELECT producto, precio, fecha FROM historial_precios ORDER BY id DESC")
    else:
        cursor.execute("""
            SELECT hp.producto, hp.precio, hp.fecha 
            FROM historial_precios hp
            JOIN productos_configurados pc ON hp.producto = pc.nombre
            WHERE pc.username = %s
            ORDER BY hp.id DESC
        """, (username,))
        
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Producto", "Precio", "Fecha"])
    for fila in filas:
        writer.writerow(fila)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historial_precios.csv"}
    )