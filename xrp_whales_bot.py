import asyncio
import json
import requests
import websocket
import os
import logging
import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# =============================
# CONFIGURACIÓN INICIAL
# =============================
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

# Umbral por defecto en USD
USD_THRESHOLD = 5_000_000.0
try:
    with open(CONFIG_FILE, "r") as f:
        USD_THRESHOLD = float(json.load(f).get("USD_THRESHOLD", USD_THRESHOLD))
except:
    pass


# =============================
# FUNCIONES AUXILIARES
# =============================

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
    """Envía alerta al canal o usuario configurado."""
    try:
        await app.bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Error enviando mensaje: {e}")


# =============================
# COMANDOS DE TELEGRAM
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot activo.\nUmbral: ${USD_THRESHOLD:,.0f}")


# =============================
# API Y PROCESAMIENTO XRP
# =============================

def get_xrp_price_usd():
    try:
        r = requests.get("https://api.coincap.io/v2/assets/ripple", timeout=5)
        return float(r.json()["data"]["priceUsd"])
    except Exception as e:
        logging.warning(f"Error obteniendo precio XRP: {e}")
        return None


def on_message(ws, msg, app):
    """Procesa mensajes recibidos del WebSocket de Ripple."""
    try:
        data = json.loads(msg)
        tx = data.get("transaction") or {}
        if tx.get("TransactionType") != "Payment":
            return

        amount_xrp = int(tx["Amount"]) / 1_000_000
        price = get_xrp_price_usd()
        if not price or amount_xrp * price < USD_THRESHOLD:
            return

        sender = tx.get("Account")
        receiver = tx.get("Destination")
        whales = load_whales()

        for w in whales:
            if sender == w["address"] or receiver == w["address"]:
                direction = "💹 *Compra*" if receiver == w["address"] else "📉 *Venta*"
                msg_text = (
                    f"{direction}\n"
                    f"{amount_xrp:,.0f} XRP (~${amount_xrp * price:,.0f})\n"
                    f"Tx: `{tx.get('hash')}`"
                )
                asyncio.create_task(send_alert(app, msg_text))
    except Exception as e:
        logging.error(f"Error en on_message: {e}")


def start_ws(app):
    """Mantiene conexión persistente al WebSocket de Ripple."""
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://s1.ripple.com",
                on_message=lambda ws, msg: on_message(ws, msg, app),
            )
            ws.run_forever()
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
        finally:
            asyncio.sleep(5)


# =============================
# FLASK SERVER (Mantener vivo en Render)
# =============================

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ XRP Whales Bot activo"


# =============================
# MAIN
# =============================

async def main():
    """Punto de entrada principal asincrónico."""

    # Crear app de Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Registrar comandos
    application.add_handler(CommandHandler("start", start))

    # Iniciar WebSocket en hilo separado
    Thread(target=lambda: start_ws(application), daemon=True).start()

    # Iniciar Flask en hilo separado
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app_flask.run(host="0.0.0.0", port=port), daemon=True).start()

    # Iniciar el bot
    await application.initialize()
    await application.start()
    logging.info("🚀 XRP Whales Bot iniciado correctamente.")
    await application.updater.start_polling()
    await application.updater.idle()


if __name__ == "__main__":
    asyncio.run(main())
