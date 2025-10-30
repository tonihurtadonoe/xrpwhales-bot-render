import asyncio
import json
import requests
import os
import logging
import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from websockets import connect

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Forzamos la zona horaria de APScheduler a una válida de pytz
scheduler = AsyncIOScheduler(timezone=pytz.utc)

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
async def get_xrp_price_usd():
    try:
        async with asyncio.to_thread(requests.get, "https://api.coincap.io/v2/assets/ripple") as response:
            data = response.json()
            return float(data["data"]["priceUsd"])
    except:
        return None

async def handle_transaction(tx, app):
    if tx.get("TransactionType") != "Payment":
        return
    amount_xrp = int(tx["Amount"]) / 1_000_000
    price = await get_xrp_price_usd()
    if not price or amount_xrp * price < USD_THRESHOLD:
        return
    sender = tx.get("Account")
    receiver = tx.get("Destination")
    whales = load_whales()
    for w in whales:
        if sender == w["address"] or receiver == w["address"]:
            direction = "💹 Compra" if receiver == w["address"] else "📉 Venta"
            msg_text = f"{direction} {amount_xrp} XRP (~${amount_xrp*price:.0f})"
            await send_alert(app, msg_text)

async def xrp_ws_listener(app):
    url = "wss://s1.ripple.com"
    while True:
        try:
            async with connect(url) as websocket:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        tx = data.get("transaction") or {}
                        await handle_transaction(tx, app)
                    except:
                        continue
        except Exception as e:
            logging.warning(f"WebSocket error: {e}, reconectando en 5s...")
            await asyncio.sleep(5)

# FLASK
app_flask = Flask(__name__)
@app_flask.route("/")
def home():
    return "✅ Bot activo"

async def run_flask():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = [f"0.0.0.0:{int(os.environ.get('PORT', 10000))}"]
    await serve(app_flask, config)

# MAIN
async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # Inicia WebSocket y Flask en paralelo con asyncio
    await asyncio.gather(
        application.start(),
        application.updater.start_polling(),
        xrp_ws_listener(application),
        run_flask()
    )

if __name__ == "__main__":
    asyncio.run(main())

