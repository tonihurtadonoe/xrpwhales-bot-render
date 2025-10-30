# Usamos Python 3.12 oficial (compatible con python-telegram-bot 13.15)
FROM python:3.12-slim

# Directorio de trabajo
WORKDIR /app

# Copiamos y instalamos requisitos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el proyecto
COPY . .

# Variables de entorno (pueden ser sobreescritas en Render)
ENV TOKEN=""

# Comando para iniciar el bot
CMD ["python", "xrp_whales_bot.py"]
