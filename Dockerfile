# Dockerfile optimizado para xrpwhales-bot (async + websockets)
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos los requisitos y los instalamos
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiamos todos los archivos del proyecto
COPY . .

# Variables de entorno para Telegram (configuradas desde Render)
# Ejemplo local:
# ENV TELEGRAM_TOKEN=<tu_token_local>
# ENV TELEGRAM_CHAT_ID=<tu_chat_id_local>

# Puerto para Flask (Render define el puerto vía ENV PORT)
ENV PORT=10000

# Comando para iniciar el bot
CMD ["python", "xrp_whales_bot.py"]
