# Dockerfile para xrpwhales-bot
FROM python:3.11-slim

WORKDIR /app

# Copiamos requisitos e instalamos
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiamos todos los archivos del proyecto
COPY . .

# Variables de entorno para Telegram (configurables desde Render)
ENV TELEGRAM_TOKEN=<pon_aqui_tu_token_si_quieres_test_local>
ENV TELEGRAM_CHAT_ID=<pon_aqui_tu_chat_id_si_quieres_test_local>

# Puerto Flask
ENV PORT=10000

# Comando para iniciar el bot
CMD ["python", "xrp_whales_bot.py"]
