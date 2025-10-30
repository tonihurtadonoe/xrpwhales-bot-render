import asyncio
import logging
import pytz
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    JobQueue
)

# ------------------------------
# CONFIGURACIÓN (PON TUS DATOS AQUÍ)
# ------------------------------
BOT_TOKEN = "TU_BOT_TOKEN"
CHANNEL_ID = "@tu_canal_o_id"
WHALE_ALERT_API_KEY = "TU_API_KEY_DE_WHALE_ALERTS"

# ------------------------------
# CONFIGURACIÓN DE LOGS
# ------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# FUNCIONES DEL BOT
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Bot XRP Whales activo!")

async def check_whales(context: ContextTypes.DEFAULT_TYPE):
    """
    Función que consulta la API de Whale Alerts y envía alertas al canal.
    """
    url = f"https://api.whale-alert.io/v1/transactions?api_key={WHALE_ALERT_API_KEY}&currency=xrp&min_value=100000"
    try:
        response = requests.get(url)
        data = response.json()
        if "transactions" in data:
            for tx in data["transactions"]:
                msg = (
                    f"💰 Whale Alert XRP:\n"
                    f"De: {tx['from']['owner']}\n"
                    f"Para: {tx['to']['owner']}\n"
                    f"Monto: {tx['amount']} XRP\n"
                    f"Hash: {tx['hash']}"
                )
                await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
    except Exception as e:
        logger.error(f"Error al consultar Whale Alerts: {e}")

# ------------------------------
# MAIN
# ------------------------------
async def main():
    # Crear aplicación del bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Forzar que todos los schedulers usen pytz
    application.job_queue.scheduler.configure(timezone=pytz.UTC)

    # Comandos
    application.add_handler(CommandHandler("start", start))

    # Job para revisar Whale Alerts cada 60 segundos
    application.job_queue.run_repeating(check_whales, interval=60, first=0)

    # Iniciar bot
    logger.info("Starting XRP Whale Bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
