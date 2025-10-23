import json
import requests
import threading
import websocket
import os
import time
import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

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

def send_alert(message: str):
    if USER_ID:
        updater.bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# ===== COMANDOS DEL BOT =====
def start(update: Update, context: CallbackContext):
    send_alert("👋 Bot iniciado ✅")
    update.message.reply_text(
        "👋 Bot activo. Usos:\n"
        "/add <wallet> <nombre>\n"
        "/del <wallet>\n"
        "/list\n"
        "/setlimit <USD>\n"
        f"Monitoreando transacciones grandes > ${USD_THRESHOLD:,.0f}..."
    )

def add_whale(update: Update, context: CallbackContext):
    whales = load_whales()
    if len(context.args) < 2:
        update.message.reply_text("Uso: /add <wallet> <nombre>")
        return
    address, name = context.args[0], " ".join(context.args[1:])
    whales.append({"address": address, "name": name})
    save_whales(whales)
    update.message.reply_text(f"✅ Añadido {name} ({address})")

def del_whale(update: Update, context: CallbackContext):
    whales = load_whales()
    if not context.args:
        update.message.reply_text("Uso: /del <wallet>")
        return
    address = context.args[0]
    whales = [w for w in whales if w["address"] != address]
    save_whales(whales)
    update.message.reply_text(f"🗑️ Eliminado {address}")

def list_whales(update: Update, context: CallbackContext):
    whales = load_whales()
    if not whales:
        update.message.reply_text("No hay ballenas registradas.")
    else:
        text = "\n".join([f"• {w['name']}: `{w['address']}`" for w in whales])
        update.message.reply_text(f"🐋 *Ballenas monitoreadas:*\n{text}", parse_mode=ParseMode.MARKDOWN)

# ===== COMANDO PARA CAMBIAR LÍMITE =====
def set_limit(update: Update, context: CallbackContext):
    global USD_THRESHOLD
    if not context.args:
        update.message.reply_text(f"Uso: /setlimit <monto_en_USD>\nLímite actual: ${USD_THRESHOLD:,.0f}")
        return
    try:
        USD_THRESHOLD = float(context.args[0])
        update.message.reply_text(f"✅ Límite actualizado a ${USD_THRESHOLD:,.0f}")
        # Guardar en archivo para persistencia
        with open(CONFIG_FILE, "w") as f:
            json.dump({"USD_THRESHOLD": USD_THRESHOLD}, f)
    except ValueError:
        update.message.reply_text("❌ Valor inválido. Escribe un número.")

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
                    f"💸 {amount_xrp:,.2f} XRP (~${usd_value:,.2f})\n"
                    f"🏦 {w['name']}\n"
                    f"🔗 [Ver en XRPSCAN](https://xrpscan.com/tx/{tx_hash})\n"
                    f"{direction}"
                )
                send_alert(message)

def start_websocket():
    ws = websocket.WebSocketApp("wss://s1.ripple.com", on_message=on_message)
    ws.run_forever()

# ===== INICIO BOT =====
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("add", add_whale))
dp.add_handler(CommandHandler("del", del_whale))
dp.add_handler(CommandHandler("list", list_whales))
dp.add_handler(CommandHandler("setlimit", set_limit))

# Inicia WebSocket en segundo plano
threading.Thread(target=start_websocket, daemon=True).start()

# ===== FLASK PORT FALSO PARA RENDER GRATIS =====
import flask
from threading import Thread
app = flask.Flask(__name__)

@app.route("/")
def home():
    return "Bot XRP Whales corriendo ✅"

Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))).start()

# Inicia bot de Telegram
updater.start_polling()
logging.info("✅ Bot ejecutándose")
updater.idle()
