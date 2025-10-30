# Usamos Python 3.11 oficial
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "xrp_whales_bot.py"]
