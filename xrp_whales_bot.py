#!/usr/bin/env python3
# xrp_whales_bot.py
# Bot de Telegram que avisa movimientos grandes de ballenas XRP.
# Configura en Render las variables: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID.

import json
import requests
import threading
import websocket
import os
import time
import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

import os
print("TOKEN:", repr(os.environ.get("TOKEN")))

# ===== CONFIG =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
USER_ID = os.environ.get("TELEGRAM_CHAT_ID")  # tu chat id
WHALES_FILE = "whales.json"
CONFIG_FILE = "config.json"

if not TOKEN:
    logging.error("❌ TELEGRAM_TOKEN no encontrado en variables de entorno. Abortando.")
    raise SystemExit(1)

try:
    USER_ID = int(USER_ID)
except Exception:
    logging.warning("⚠️ TELEGRAM_CHAT_ID no es numérico. Se mantendrá como string.")

# ===== DEFAULTS =====
DEFAULT_USD_THRESHOLD = 5_000_000.0
USD_THRESHOLD = DEFAULT_USD_THRESHOLD
try:
    with open(CONFIG_FILE, "r") as f:
        conf = json.load(f)
        USD_THRESHOLD = float(conf.get("USD_THRESHOLD", USD_THRESHOLD))
except FileNotFoundError:
    pass

# ===== HELPERS =====
def load_whales():
    try:
        with open(WHALES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"USD_THRESHOLD": USD_THRESHOLD}, f, indent=2)

def authorized(update: Update):
    """Verifica si el usuario es el dueño del bot."""
    user_id = update.effective_user.id
    if str(user_id) != str(USER_ID):
        update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return False
    return True

def send_alert(message: str):
    try:
        updater.bot.send_message(
            chat_id=USER_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Error enviando mensaje: {e}")

# ===== BOT COMMANDS =====
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Bienvenido al bot XRP Whales.\n\n"
        "Comandos:\n"
        "/add <wallet> <nombre>\n"
        "/del <wallet>\n"
        "/list\n"
        "/setlimit <USD>\n\n"
        f"⚙️ Límite actual: ${USD_THRESHOLD:,.0f}"
    )

def add_whale(update: Update, context: CallbackContext):
    if not authorized(update):
        return
    if len(context.args) < 2:
        update.message.reply_text("Uso: /add <wallet> <nombre>")
        return
    whales = load_whales()
    address, name = context.args[0], " ".join(context.args[1:])
    if any(w["address"] == address for w in whales):
        update.message.reply_text("⚠️ Esa wallet ya está registrada.")
        return
    whales.append({"address": address, "name": name})
    save_whales(whales)
    update.message.reply_text(f"✅ Añadido {name} ({address})")

def del_whale(update: Update, context: CallbackContext):
    if not authorized(update):
        return
    if not context.args:
        update.message.reply_text("Uso: /del <wallet>")
        return
    address = context.args[0]
    whales = [w for w in load_whales() if w["address"] != address]
    save_whales(whales)
    update.message.reply_text(f"🗑️ Eliminada la wallet {address}")

def list_whales(update: Update, context: CallbackContext):
    whales = load_whales()
    if not whales:
        update.message.reply_text("No hay ballenas registradas.")
    else:
        msg = "\n".join([f"• {w['name']}: `{w['address']}`" for w in whales])
        update.message.reply_text(f"🐋 Ballenas monitoreadas:\n{msg}", parse_mode=ParseMode.MARKDOWN)

def set_limit(update: Update, context: CallbackContext):
    global USD_THRESHOLD
    if not authorized(update):
        return
    if not context.args:
        update.message.reply_text(f"Límite actual: ${USD_THRESHOLD:,.0f}\nUso: /setlimit <USD>")
        return
    try:
        USD_THRESHOLD = float(context.args[0])
        save_config()
        update.message.reply_text(f"✅ Nuevo límite: ${USD_THRESHOLD:,.0f}")
    except ValueError:
        update.message.reply_text("❌ Valor inválido.")

# ===== XRP API =====
def get_xrp_price_usd():
    try:
        res = requests.get("https://api.coincap.io/v2/assets/ripple", timeout=5)
        res.raise_for_status()
        return float(res.json()["data"]["priceUsd"])
    except Exception:
        return None

def on_message(ws, msg):
    try:
        data = json.loads(msg)
    except Exception:
        return

    tx = data.get("transaction") or data.get("tx") or {}
    if not tx or tx.get("TransactionType") != "Payment":
        return

    try:
        amount_drops = int(tx["Amount"])
        amount_xrp = amount_drops / 1_000_000
    except Exception:
        return

    price = get_xrp_price_usd()
    if not price:
        return
    usd_value = amount_xrp * price
    if usd_value < USD_THRESHOLD:
        return

    sender = tx.get("Account")
    receiver = tx.get("Destination")
    tx_hash = tx.get("hash")

    whales = load_whales()
    for w in whales:
        addr = w["address"]
        if sender == addr or receiver == addr:
            direction = "💹 *Compra / Largo*" if receiver == addr else "📉 *Venta / Corto*"
            msg = (
                f"🐋 *Movimiento detectado!*\n"
                f"💰 {amount_xrp:,.0f} XRP (~${usd_value:,.0f})\n"
                f"🏦 {w['name']}\n"
                f"{direction}\n"
                f"🔗 [Ver en XRPScan](https://xrpscan.com/tx/{tx_hash})"
            )
            send_alert(msg)

def start_websocket():
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://s1.ripple.com",
                on_message=lambda ws, m: on_message(ws, m),
                on_error=lambda ws, e: logging.error("WS error: %s", e),
                on_close=lambda ws: logging.warning("WS cerrado")
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            logging.error(f"WebSocket reiniciando: {e}")
            time.sleep(5)

# ===== TELEGRAM + FLASK =====
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("add", add_whale))
dp.add_handler(CommandHandler("del", del_whale))
dp.add_handler(CommandHandler("list", list_whales))
dp.add_handler(CommandHandler("setlimit", set_limit))

threading.Thread(target=start_websocket, daemon=True).start()

try:
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "✅ XRP Whales Bot activo"

    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()
except Exception:
    logging.warning("Flask no disponible (solo necesario en Render).")

if __name__ == "__main__":
    logging.info("Bot iniciado con límite: $%s", USD_THRESHOLD)
    updater.start_polling()
    updater.idle()

