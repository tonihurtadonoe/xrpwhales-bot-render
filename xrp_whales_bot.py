import json
import requests
import threading
import websocket
import os
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# ===== TOKEN DESDE VARIABLE DE ENTORNO =====
TOKEN = os.environ.get("TOKEN")
CHAT_ID = None  # Se detectará automáticamente al primer uso
WHALES_FILE = "whales.json"

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

def send_alert(context: CallbackContext, message: str):
    if CHAT_ID:
        context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# ===== BOT COMMANDS =====
def start(update: Update, context: CallbackContext):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    update.message.reply_text(
        "👋 Bot activo. Usos:\n"
        "/add <wallet> <nombre>\n"
        "/del <wallet>\n"
        "/list\n"
        "Iniciando monitoreo de transacciones grandes..."
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

# ===== MONITOREO DE XRP =====
def on_message(ws, msg):
    data = json.loads(msg)
    if "transaction" in data and data["transaction"]["TransactionType"] == "Payment":
        amount = int(data["transaction"].get("Amount", 0))
        if amount > 5_000_000_000:  # más de 5M XRP
            sender = data["transaction"]["Account"]
            receiver = data["transaction"]["Destination"]
            tx_hash = data["transaction"]["hash"]
            whales = load_whales()

            for w in whales:
                if sender == w["address"] or receiver == w["address"]:
                    message = (
                        f"🐋 *Movimiento detectado!*\n"
                        f"💸 {amount/1_000_000:.2f} XRP\n"
                        f"🏦 {w['name']}\n"
                        f"🔗 [Ver en XRPSCAN](https://xrpscan.com/tx/{tx_hash})"
                    )
                    if updater:
                        send_alert(updater.job_queue, message)

def start_websocket():
    ws = websocket.WebSocketApp("wss://s1.ripple.com", on_message=on_message)
    ws.run_forever()

# ===== MAIN =====
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("add", add_whale))
dp.add_handler(CommandHandler("del", del_whale))
dp.add_handler(CommandHandler("list", list_whales))

threading.Thread(target=start_websocket, daemon=True).start()

updater.start_polling()
print("✅ Bot ejecutándose...")

import time
try:
    while True:
        print("💤 Manteniendo conexión activa...")
        time.sleep(60)
except KeyboardInterrupt:
    print("🛑 Bot detenido manualmente")

updater.idle()
