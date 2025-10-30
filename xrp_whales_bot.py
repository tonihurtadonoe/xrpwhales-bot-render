import asyncio
import json
import requests
import threading
import websocket
import os
import time
import logging
import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# CONFIG
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
USER_ID = os.environ.get("TELEGRAM_CHAT_ID")
WHALES_FILE = "whales.json"
CONFIG_FILE = "config.json"

if not TOKEN:
    raise SystemExit("❌ TELEGRAM_TOKEN no encontrado.")

try:
    USER_ID = int(USER_ID)
except Exception:
    USER_ID = str(USER_ID)

USD_THRESHOLD = 5_000_000.0
try:
    with open(CONFIG_FILE, "r") as f:
        USD_THRESHOLD = float(json.load(f).get("USD_THRESHOLD", USD_THRESHOLD))
except:
    pass

def load_whales():
    try:
        with open(WHALES_FILE) as f:
            return json.load(f)
    except:
        return []

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"USD_THRESHOLD": USD_THRESHOLD}, f, indent=2)

def authorized(update: Update):
    return str(update.effective_user.id) == str(USER_ID)

async def send_alert(app, message: str):
    await app.bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# COMANDOS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Bot activo. Límite: ${USD_THRESHOLD:,.0f}")

# XRP API
def get_xrp_price_usd():
    try:
        return float(requests.get("https://api.coincap.io/v2/assets/ripple").json()["data"]["priceUsd"])
    except:
        return None

def on_message(ws, msg, app):
    try:
        data = json.loads(msg)
        tx = data.get("transaction") or {}
        if tx.get("TransactionType") != "Payment":
            return
        amount_xrp = int(tx["Amount"])/1_000_000
        price = get_xrp_price_usd()
        if not price or amount_xrp*price < USD_THRESHOLD:
            return
        sender = tx.get("Account")
        receiver = tx.get("Destination")
        tx_hash = tx.get("hash")
        whales = load_whales()
        for w in whales:
            if sender == w["address"] or receiver == w["address"]:
                direction = "💹 Compra" if receiver==w["address"] else "📉 Venta"
                msg = f"{direction} {amount_xrp} XRP (~${amount_xrp*price:.0f})"
                asyncio.create_task(send_alert(app, msg))
    except:
        return

def start_ws(app):
    while True:
        ws = websocket.WebSocketApp("wss://s1.ripple.com", on_message=lambda ws,msg: on_message(ws,msg,app))
        ws.run_forever()
        time.sleep(5)

# FLASK
app_flask = Flask(__name__)
@app_flask.route("/")
def home():
    return "✅ Bot activo"

# MAIN
async def main():
    # Creamos un scheduler con pytz
    scheduler = AsyncIOScheduler(timezone=pytz.utc)

    # Creamos la app de Telegram
    application = ApplicationBuilder().token(TOKEN).build()
    application.job_queue.scheduler = scheduler

    # Comandos
    application.add_handler(CommandHandler("start", start))

    # Iniciamos websocket en hilo aparte
    threading.Thread(target=lambda: start_ws(application), daemon=True).start()

    # Iniciamos Flask en hilo aparte
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=port), daemon=True).start()

    # Arrancamos scheduler
    scheduler.start()

    # Arrancamos bot
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())

