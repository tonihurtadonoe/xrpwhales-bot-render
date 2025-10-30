import os
import asyncio
import logging
import requests
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# -----------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@xrpwhales")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))  # segundos

API_URL = "https://api.whale-alert.io/v1/transactions"
API_KEY = os.getenv("WHALE_ALERT_API_KEY")

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# FLASK APP (para mantener Render activo)
# -----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ XRP Whales Bot is running on Render!"

# -----------------------------
# FUNCIÓN PARA OBTENER TRANSACCIONES
# -----------------------------
last_seen_tx = set()

def fetch_whale_transactions():
    try:
        response = requests.get(
            API_URL,
            params={"api_key": API_KEY, "currency": "xrp", "min_value": 500000},
            timeout=10
        )
        data = response.json()
        transactions = data.get("transactions", [])
        logger.info(f"Fetched {len(transactions)} transactions.")
        return transactions
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return []

# -----------------------------
# PROCESAMIENTO DE TRANSACCIONES
# -----------------------------
def parse_transaction(tx):
    tx_id = tx.get("hash")
    amount = tx.get("amount")
    sender = tx.get("from", {}).get("owner_type", "unknown")
    receiver = tx.get("to", {}).get("owner_type", "unknown")
    timestamp = tx.get("timestamp")

    direction = "🟢 Buy (to exchange)" if receiver == "exchange" else "🔴 Sell (from exchange)"
    message = (
        f"🐋 <b>Whale Alert - XRP</b>\n"
        f"{direction}\n"
        f"💰 Amount: {amount:,.0f} XRP\n"
        f"📤 From: {sender}\n"
        f"📥 To: {receiver}\n"
        f"⏰ Timestamp: {timestamp}\n"
        f"#XRP #WhaleAlert"
    )

    return tx_id, message

# -----------------------------
# ENVÍO DE ALERTAS A TELEGRAM
# -----------------------------
async def send_whale_alert(context: ContextTypes.DEFAULT_TYPE):
    transactions = fetch_whale_transactions()
    global last_seen_tx

    for tx in transactions:
        tx_id, message = parse_transaction(tx)
        if tx_id not in last_seen_tx:
            last_seen_tx.add(tx_id)
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="HTML"
            )

# -----------------------------
# COMANDOS DE TELEGRAM
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🐋 XRP Whale Bot is active!")

# -----------------------------
# MAIN ASYNC
# -----------------------------
async def main():
    logger.info("Starting XRP Whale Bot...")

    # Forzamos el uso de pytz para evitar el error del timezone
    scheduler = AsyncIOScheduler(timezone=pytz.UTC)

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .job_queue(scheduler)
        .build()
    )

    # Comando /start
    application.add_handler(CommandHandler("start", start))

    # Tarea repetitiva
    job_queue = application.job_queue
    job_queue.run_repeating(send_whale_alert, interval=CHECK_INTERVAL, first=10)

    # Iniciar el bot
    await application.initialize()
    await application.start()
    logger.info("✅ XRP Whale Bot is running.")
    await application.updater.start_polling()
    await application.run_polling()

# -----------------------------
# EJECUCIÓN PRINCIPAL
# -----------------------------
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))).start()

    asyncio.run(main())
