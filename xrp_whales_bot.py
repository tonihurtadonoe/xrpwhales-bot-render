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
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

TOKEN = os.environ.get("TOKEN")
USER_ID = int(os.environ.get("USER_ID", "0"))  # Tu ID numérico de Telegram

if not TOKEN:
    logging.error("❌ TOKEN no definido en variables de entorno")
    exit()

if USER_ID == 0:
    logging.error("❌ USER_ID no definido en variables de entorno")
    exit()

WHALES_FILE = "whales.json"

# Asegurarse de que exista whales.json
if not os.path.exists(WHALES_FILE):
    with open(WHALES_FILE, "w") as f:
        json.dump([], f)

# ===== FUNCIONES BASE =====
def load_whales():
    try:
        with open(WHALES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error cargando whales.json: {e}")
        return []

def save_whales(data):
    try:
        with open(WHALES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error guardando whales.json: {e}")

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
        "Monitoreando transacciones grandes..."
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

# ===== MONITOREO XRP =====
def on_message(ws, msg):
    data = json.loads(msg)
    if "transaction" in data and data["transaction"]["TransactionType"] == "Payment":
        amount = int(data["transaction"].get("Amount", 0))
        sender = data["transaction"]["Account"]
        receiver = data["transaction"]["Destination"]
        tx_hash = data["transaction"]["hash"]

        if amount > 5_000_000_000:  # 5000 XRP en drops
            whales = load_whales()
            for w in whales:
                if sender == w["address"] or receiver == w["address"]:
                    direction = "💹 Largo" if receiver == w["address"] else "📉 Corto"
                    message = (
                        f"🐋 *Movimiento detectado!*\n"
                        f"💸 {amount/1_000_000:.2f} XRP\n"
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
