# Dockerfile para xrpwhales-bot
# Usamos Python 3.11 oficial
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos los requisitos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todos los archivos del proyecto
COPY . .

# Variables de entorno para Telegram (se configuran desde Render)
# Ejemplo: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID
ENV TELEGRAM_TOKEN=<pon_aqui_tu_token_si_quieres_test_local>
ENV TELEGRAM_CHAT_ID=<pon_aqui_tu_chat_id_si_quieres_test_local>

# Comando para iniciar el bot
CMD ["python", "xrp_whales_bot.py"]
