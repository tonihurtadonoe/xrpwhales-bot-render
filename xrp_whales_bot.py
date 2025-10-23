import json
import requests
import threading
import websocket
import os
import time
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# ===== VARIABLES =====
TOKEN = os.environ.get("TOKEN")
AUTHORIZED_USER = "@ToniHurtadoNoe"  # Solo este usuario puede usar comandos
CHAT_ID = None  # Se detectará al primer uso
WHALES_FILE = "whales.json"
MEMORY_FILE = "memory.json"

if not TOKEN:
    logging.error("❌ ERROR: No se encontró el TOKEN en las variables de entorno.")
    exit()
else:
    logging.info("🔑 TOKEN recibido correctamente")

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

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def send_alert(message: str):
    if CHAT_ID:
        updater.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)

def authorized(update: Update):
    """Verifica que el usuario sea el autorizado"""
    user = update.message.from_user.username
    return user == AUTHORIZED_USER.strip("@")

# ===== BOT COMMANDS =====
def start(update: Update, context: CallbackContext):
    global CHAT_ID
    if not authorized(update):
        return
    CHAT_ID = update.message.chat_id
    update.message.reply_text(
        "👋 Bot activo. Usos:\n"
        "/add <wallet> <nombre>\n"
        "/del <wallet>\n"
        "/list\n"
        "Iniciando monitoreo de transacciones grandes..."
    )

def add_whale(update: Update, context: CallbackContext):
    if not authorized(update):
        return
    whales = load_whales()
    if len(context.args) < 2:
        update.message.reply_text("Uso: /add <wallet> <nombre>")
        return
    address, name = context.args[0], " ".join(context.args[1:])
    whales.append({"address": address, "name": name})
    save_whales(whales)
    update.message.reply_text(f"✅ Añadido {name} ({address})")

def del_whale(update: Update, context: CallbackContext):
    if not authorized(update):
        return
    whales = load_whales()
    if not context.args:
        update.message.reply_text("Uso: /del <wallet>")
        return
    address = context.args[0]
    whales = [w for w in whales if w["address"] != address]
    save_whales(whales)
    update.message.reply_text(f"🗑️ Eliminado {address}")

def list_whales(update: Update, context: CallbackContext):
    if not authorized(update):
        return
    whales = load_whales()
    if not whales:
        update.message.reply_text("No hay ballenas registradas.")
    else:
        text = "\n".join([f"• {w['name']}: `{w['address']}`" for w in whales])
        update.message.reply_text(f"🐋 *Ballenas monitoreadas:*\n{text}", parse_mode=ParseMode.MARKDOWN)

# ===== MONITOREO DE XRP Y MODO PRO =====
def on_message(ws, msg):
    data = json.loads(msg)
    if "transaction" not in data or data["transaction"]["TransactionType"] != "Payment":
        return

    transaction = data["transaction"]
    amount_drops = int(transaction.get("Amount", 0))
    amount_xrp = amount_drops / 1_000_000
    sender = transaction["Account"]
    receiver = transaction["Destination"]
    tx_hash = transaction["hash"]

    whales = load_whales()
    memory = load_memory()

    for w in whales:
        if sender == w["address"] or receiver == w["address"]:
            # Determinar cambio en balance para long/short
            asset = "XRP"
            prev_balance = memory.get(w["address"], {}).get(asset, 0)
            change = amount_xrp if receiver == w["address"] else -amount_xrp
            new_balance = prev_balance + change
            direction = "📈 LONG" if change > 0 else "📉 SHORT"

            # Actualizar memoria
            if w["address"] not in memory:
                memory[w["address"]] = {}
            memory[w["address"]][asset] = new_balance
            memory[w["address"]]["last_tx"] = tx_hash
            save_memory(memory)

            # Enviar alerta
            message = (
                f"🐋 *Movimiento detectado!*\n"
                f"💸 {abs(change):.2f} {asset}\n"
                f"{direction}\n"
                f"🏦 {w['name']}\n"
                f"🔗 [Ver en XRPSCAN](https://xrpscan.com/tx/{tx_hash})"
            )
            send_alert(message)

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

# Iniciar WebSocket en segundo plano
threading.Thread(target=start_websocket, daemon=True).start()

# Iniciar bot de Telegram
updater.start_polling()
logging.info("✅ Bot ejecutándose...")

# Mantener bot activo
updater.idle()
