# Imagen base ligera de Python
FROM python:3.11-slim

# Establecer directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos necesarios
COPY requirements.txt ./

# Instalar dependencias
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY . .

# Establecer variable de entorno para Flask
ENV PORT=10000

# Exponer el puerto que Render usará
EXPOSE 10000

# Comando de inicio (ajústalo si tu archivo principal tiene otro nombre)
CMD ["python", "xrp_whales_bot.py"]

