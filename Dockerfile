FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema operativo para que Playwright (Chromium) pueda correr en Linux
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar las librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar el navegador Chromium optimizado para Playwright en la nube
RUN playwright install chromium

# Copiar todo el código de tu proyecto al contenedor
COPY . .

# Comando dinámico para iniciar FastAPI usando el puerto que asigne Railway
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"