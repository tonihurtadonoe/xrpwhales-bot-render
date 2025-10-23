import os
import json
import logging
import asyncio
import requests
from datetime import datetime
from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.update import Update

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=os.getenv("LOG_LEVEL", "INFO")
)
logger = logging.getLogger(__name__)

# --- VARIABLES GLOBALES ---
TELEGRAM_TOKEN = os.getenv("TOKEN")  # Token del bot (desde Render)
AUTHORIZED_USER_ID = int(os.getenv("USER_ID", "278754715"))  # Tu user ID
DATA_FILE = "whales.json"
MIN_USD_THRESHOLD = 5_000_000  # Mínimo por defecto

# --- FUNCIONES DE UTILIDAD ---
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"transactions": []}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def format_transaction(tx):
    """Formato bonito del mensaje de transacción"""
    direction = "🟢 Compra (Long)" if tx.get("type") == "buy" else "🔴 Venta (Short)"
    return (
        f"{direction}\n"
        f"💰 **{tx['amount_usd']:,} USD**\n"
        f"📊 XRP: {tx['amount_xrp']:,}\n"
        f"🔗 Hash: [{tx['hash']}](https://xrpscan.com/tx/{tx['hash']})\n"
        f"🕒 {tx['timestamp']}"
    )

# --- COMANDOS DE TELEGRAM ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Bienvenido al bot XRP Whales.\n"
        "Te avisaré cuando haya movimientos grandes en la red XRP.\n"
        f"🔹 Límite actual: ${MIN_USD_THRESHOLD:,} USD"
    )

def set_threshold(update: Update, context: CallbackContext):
    """Permite cambiar el umbral desde Telegram"""
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return update.message.reply_text("🚫 No tienes permiso para usar este comando.")
    
    global MIN_USD_THRESHOLD
    try:
        value = float(context.args[0])
        MIN_USD_THRESHOLD = value
        update.message.reply_text(f"✅ Límite cambiado a ${MIN_USD_THRESHOLD:,} USD.")
    except (IndexError, ValueError):
        update.message.reply_text("Uso: /setlimit <monto_en_usd>")

def check_whales(bot: Bot):
    """Simula lectura de API de transacciones XRP y envía alertas"""
    data = load_data()
    last_tx = data["transactions"]

    # --- Ejemplo de simulación (puedes reemplazar con API real) ---
    simulated_tx = {
        "hash": f"TX-{datetime.utcnow().strftime('%H%M%S')}",
        "amount_usd": 5_500_000,
        "amount_xrp": 8_800_000,
        "type": "buy",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    if simulated_tx["amount_usd"] >= MIN_USD_THRESHOLD:
        message = format_transaction(simulated_tx)
        bot.send_message(
            chat_id=AUTHORIZED_USER_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        last_tx.append(simulated_tx)
        save_data(data)
        logger.info(f"Notificación enviada: {simulated_tx['hash']}")

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setlimit", set_threshold))

    updater.start_polling()
    logger.info("🤖 Bot iniciado correctamente (Python 3.13.4).")

    # Ciclo de comprobación cada 2 minutos
    while True:
        try:
            check_whales(bot)
            await asyncio.sleep(120)
        except Exception as e:
            logger.error(f"Error en ciclo principal: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
