import os
import csv
import io
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg2
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

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
    print("Base de datos PostgreSQL inicializada con éxito.")

# ==========================================
# FUNCIÓN DE SCRAPING UNIVERSAL INTELIGENTE
# ==========================================
def extraer_precio_universal(url: str) -> float:
    """Función universal que intenta extraer el precio de cualquier tienda online real (electrodomésticos, libros, videojuegos, etc.)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            return 0.0
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # ESTRATEGIA 1: Buscar en datos estructurados (JSON-LD / Schema.org)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0]
                if isinstance(data, dict):
                    if data.get('@type') == 'Product' and 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, list):
                            precio = offers[0].get('price') or offers[0].get('highPrice')
                        elif isinstance(offers, dict):
                            precio = offers.get('price')
                        if precio:
                            return float(str(precio).replace(",", ""))
            except Exception:
                pass

        # ESTRATEGIA 2: Probar selectores CSS comunes en tiendas de e-commerce globales y locales
        selectores_comunes = [
            "[itemprop='price']",
            ".price",
            "#price",
            ".precio",
            ".current-price",
            ".product-price",
            ".andes-money-amount__fraction", # Muy utilizado en MercadoLibre y plataformas de LATAM
            ".price_color"
        ]
        
        for sel in selectores_comunes:
            elemento = soup.select_one(sel)
            if elemento:
                texto = elemento.text.strip().replace(",", "")
                match = re.search(r"[\d\.]+", texto)
                if match:
                    try:
                        val = float(match.group())
                        if val > 0:
                            return val
                    except ValueError:
                        continue

    except Exception as e:
        print(f"Error haciendo scraping universal para {url}: {e}")
    
    return 0.0

# ==========================================
# CONFIGURACIÓN DEL PLANIFICADOR AUTOMÁTICO
# ==========================================
scheduler = BackgroundScheduler()

def tarea_scraping_automatico():
    """Tarea periódica que recorre todos los productos activos y actualiza su precio."""
    print("Iniciando tarea automática de rastreo de precios en segundo plano...")
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return
        
        conexion = psycopg2.connect(database_url)
        cursor = conexion.cursor()
        
        cursor.execute("SELECT id, nombre, url FROM productos_configurados WHERE estado = 'activo'")
        productos = cursor.fetchall()
        
        for prod in productos:
            prod_id, nombre, url = prod
            precio_encontrado = extraer_precio_universal(url)
            
            fecha_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO historial_precios (producto, precio, fecha) VALUES (%s, %s, %s)",
                (nombre, precio_encontrado, fecha_actual)
            )
            
        conexion.commit()
        cursor.close()
        conexion.close()
        print("Tarea automática de precios finalizada con éxito.")
    except Exception as e:
        print(f"Error crítico en APScheduler: {e}")

scheduler.add_job(tarea_scraping_automatico, 'interval', minutes=2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        inicializar_bd()
        scheduler.start()
        print("APScheduler iniciado correctamente.")
    except Exception as e:
        print(f"Error crítico al iniciar servicios: {e}")
    yield
    scheduler.shutdown()
    print("APScheduler detenido.")

app = FastAPI(title="SaaS Monitoreo de Precios - Automatizado", lifespan=lifespan)
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

class RolData(BaseModel):
    rol: str

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
    
    # 1. Verificar el rol y restricciones de planes (cliente: 2, estandar: 15, pro/admin: ilimitado)
    cursor.execute("SELECT rol FROM usuarios WHERE username = %s", (item.username,))
    res_usuario = cursor.fetchone()
    
    if not res_usuario:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    rol_usuario = res_usuario[0]

    if rol_usuario == 'cliente':
        cursor.execute("SELECT COUNT(*) FROM productos_configurados WHERE username = %s", (item.username,))
        total_prods = cursor.fetchone()[0]
        
        if total_prods >= 2:
            cursor.close()
            conexion.close()
            raise HTTPException(
                status_code=403, 
                detail="LÍMITE_GRATIS_ALCANZADO"
            )
    elif rol_usuario == 'estandar':
        cursor.execute("SELECT COUNT(*) FROM productos_configurados WHERE username = %s", (item.username,))
        total_prods = cursor.fetchone()[0]
        
        if total_prods >= 15:
            cursor.close()
            conexion.close()
            raise HTTPException(
                status_code=403, 
                detail="LÍMITE_ESTANDAR_ALCANZADO"
            )

    # 2. Insertar el producto si pasa la validación
    cursor.execute(
        "INSERT INTO productos_configurados (username, nombre, url, categoria, precio_objetivo, estado) VALUES (%s, %s, %s, %s, %s, 'activo')",
        (item.username, item.nombre, item.url, item.categoria, item.precio_objetivo)
    )
    conexion.commit()

    # Extracción automática y universal del precio inicial
    precio_encontrado = extraer_precio_universal(item.url)

    fecha_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO historial_precios (producto, precio, fecha) VALUES (%s, %s, %s)",
        (item.nombre, precio_encontrado, fecha_actual)
    )
    conexion.commit()

    cursor.close()
    conexion.close()
    return {"mensaje": "Producto registrado y rastreado exitosamente"}

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
def obtener_historial_producto(nombre_producto: str, rol: str = Query('cliente')):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Validar permisos: solo 'estandar' y 'pro' (o admin) pueden ver el historial detallado de 5 registros
    if rol == 'cliente':
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=403, detail="El plan gratuito no incluye historial de precios detallado.")

    cursor.execute(
        "SELECT precio, fecha FROM historial_precios WHERE producto = %s ORDER BY id DESC LIMIT 5",
        (nombre_producto,)
    )
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [{"precio": f[0], "fecha": f[1]} for f in filas]

# ==========================================
# ENDPOINTS DE ADMINISTRACIÓN
# ==========================================

def logica_admin_data():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id, username, email, rol FROM usuarios WHERE LOWER(rol) != 'admin'")
    usuarios_db = cursor.fetchall()
    
    clientes = []
    total_productos = 0
    total_alertas = 0
    ganancias_totales = 0.0
    
    for u in usuarios_db:
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN hp.precio IS NOT NULL AND pc.precio_objetivo > 0 AND hp.precio <= pc.precio_objetivo THEN 1 ELSE 0 END) 
            FROM productos_configurados pc
            LEFT JOIN LATERAL (
                SELECT precio FROM historial_precios WHERE producto = pc.nombre ORDER BY id DESC LIMIT 1
            ) hp ON true
            WHERE pc.username = %s
        """, (u[1],))
        res_prod = cursor.fetchone()
        prod_count = res_prod[0] or 0
        alertas_count = res_prod[1] or 0
        
        total_productos += prod_count
        total_alertas += alertas_count
        
        # Calcular ingresos acumulados según el rol del usuario (estandar = S/ 14.90, pro = S/ 29.90)
        rol_usuario = u[3]
        if rol_usuario == 'estandar':
            ganancias_totales += 14.90
        elif rol_usuario == 'pro':
            ganancias_totales += 29.90
        
        clientes.append({
            "id": u[0],
            "username": u[1],
            "email": u[2],
            "rol": rol_usuario,
            "productos_count": prod_count,
            "productos_registrados": prod_count
        })
    
    cursor.close()
    conexion.close()
    
    return {
        "ganancias_totales": ganancias_totales,
        "ganancias": ganancias_totales,
        "total_clientes": len(clientes),
        "total_usuarios": len(clientes),
        "total_productos": total_productos,
        "total_alertas": total_alertas,
        "clientes": clientes,
        "usuarios": clientes
    }

@app.get("/api/admin/data")
@app.get("/api/admin/stats")
@app.get("/api/admin/clientes")
def get_admin_data():
    return logica_admin_data()

@app.patch("/api/admin/usuarios/{usuario_id}/rol")
def cambiar_rol_usuario(usuario_id: int, data: RolData):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE usuarios SET rol = %s WHERE id = %s",
        (data.rol, usuario_id)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"mensaje": f"Rol actualizado a {data.rol}"}

@app.delete("/api/admin/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT username FROM usuarios WHERE id = %s", (cliente_id,))
    user = cursor.fetchone()
    if user:
        username = user[0]
        cursor.execute("SELECT nombre FROM productos_configurados WHERE username = %s", (username,))
        productos = cursor.fetchall()
        for p in productos:
            cursor.execute("DELETE FROM historial_precios WHERE producto = %s", (p[0],))
            
        cursor.execute("DELETE FROM productos_configurados WHERE username = %s", (username,))
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (cliente_id,))
        conexion.commit()
        
    cursor.close()
    conexion.close()
    return {"message": "Cliente eliminado correctamente"}

@app.get("/api/exportar-csv")
def exportar_csv(username: str = Query(...), rol: str = Query(...)):
    # Restricción: Solo los usuarios con rol 'pro' (o admin) pueden exportar a CSV
    if rol != 'pro' and rol != 'admin':
        raise HTTPException(status_code=403, detail="La exportación a CSV es un beneficio exclusivo del plan Pro.")

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