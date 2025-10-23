import json
import requests
import threading
import websocket
import os
import logging
import time
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ===== CONFIGURACIÓN =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

TOKEN = os.environ.get("TOKEN")
USER_ID = 278754715  # Tu ID numérico de Telegram
WHALES_FILE = "whales.json"
CONFIG_FILE = "config.json"

if not TOKEN:
    logging.error("❌ TOKEN no definido en variables de entorno")
    exit()

# ===== LÍMITE DE ALERTA =====
USD_THRESHOLD = 5_000_000  # Límite por defecto en USD

# Cargar límite desde archivo si existe
try:
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        USD_THRESHOLD = data.get("USD_THRESHOLD", USD_THRESHOLD)
except FileNotFoundError:
    pass

# ===== FUNCIONES BASE =====
def load_whales():
    try:
        with open(WHALES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def send_alert(message: str):
    if USER_ID:
        await bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# ===== COMANDOS DEL BOT =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_alert("👋 Bot iniciado ✅")
    await update.message.reply_text(
        "👋 Bot activo. Usos:\n"
        "/add <wallet> <nombre>\n"
        "/del <wallet>\n"
        "/list\n"
        "/setlimit <USD>\n"
        f"Monitoreando transacciones grandes > ${USD_THRESHOLD:,}..."
    )

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whales = load_whales()
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /add <wallet> <nombre>")
        return
    address, name = context.args[0], " ".join(context.args[1:])
    whales.append({"address": address, "name": name})
    save_whales(whales)
    await update.message.reply_text(f"✅ Añadido {name} ({address})")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whales = load_whales()
    if not context.args:
        await update.message.reply_text("Uso: /del <wallet>")
        return
    address = context.args[0]
    whales = [w for w in whales if w["address"] != address]
    save_whales(whales)
    await update.message.reply_text(f"🗑️ Eliminado {address}")

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whales = load_whales()
    if not whales:
        await update.message.reply_text("No hay ballenas registradas.")
    else:
        text = "\n".join([f"• {w['name']}: `{w['address']}`" for w in whales])
        await update.message.reply_text(f"🐋 *Ballenas monitoreadas:*\n{text}", parse_mode=ParseMode.MARKDOWN)

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USD_THRESHOLD
    if not context.args:
        await update.message.reply_text(f"Uso: /setlimit <monto_en_USD>\nLímite actual: ${USD_THRESHOLD:,}")
        return
    try:
        USD_THRESHOLD = float(context.args[0])
        await update.message.reply_text(f"✅ Límite actualizado a ${USD_THRESHOLD:,}")
        # Guardar en archivo para persistencia
        with open(CONFIG_FILE, "w") as f:
            json.dump({"USD_THRESHOLD": USD_THRESHOLD}, f)
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Escribe un número.")

# ===== MONITOREO XRP =====
def on_message(ws, msg):
    data = json.loads(msg)
    if "transaction" in data and data["transaction"]["TransactionType"] == "Payment":
        amount_drops = int(data["transaction"].get("Amount", 0))
        amount_xrp = amount_drops / 1_000_000
        sender = data["transaction"]["Account"]
        receiver = data["transaction"]["Destination"]
        tx_hash = data["transaction"]["hash"]

        # Obtener precio XRP/USD
        try:
            r = requests.get("https://api.coincap.io/v2/assets/ripple")
            price = float(r.json()["data"]["priceUsd"])
        except:
            price = 0

        usd_value = amount_xrp * price
        if usd_value < USD_THRESHOLD:
            return  # Ignorar si no supera el límite

        whales = load_whales()
        for w in whales:
            if sender == w["address"] or receiver == w["address"]:
                direction = "💹 Largo" if receiver == w["address"] else "📉 Corto"
                message = (
                    f"🐋 *Movimiento detectado!*\n"
                    f"💸 {amount_xrp:.2f} XRP (~${usd_value:,.2f})\n"
                    f"🏦 {w['name']}\n"
                    f"🔗 [Ver en XRPSCAN](https://xrpscan.com/tx/{tx_hash})\n"
                    f"{direction}"
                )
                # asyncio.run(send_alert(message)) won't work here because websocket is sync
                # usamos threading
                threading.Thread(target=lambda: asyncio.run(send_alert(message)), daemon=True).start()

def start_websocket():
    ws = websocket.WebSocketApp("wss://s1.ripple.com", on_message=on_message)
    ws.run_forever()

# ===== INICIO BOT =====
import asyncio
bot = Bot(token=TOKEN)
app = ApplicationBuilder().token(TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_whale))
app.add_handler(CommandHandler("del", del_whale))
app.add_handler(CommandHandler("list", list_whales))
app.add_handler(CommandHandler("setlimit", set_limit))

# WebSocket en segundo plano
threading.Thread(target=start_websocket, daemon=True).start()

# ===== FLASK PORT FALSO PARA RENDER GRATIS =====
import flask
from threading import Thread
flask_app = flask.Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot XRP Whales corriendo ✅"

Thread(target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))).start()

# ===== RUN TELEGRAM BOT =====
logging.info("✅ Bot ejecutándose")
app.run_polling()
