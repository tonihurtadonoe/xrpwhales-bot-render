import json
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

# Cargar configuración
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
bot_settings = config.get("bot_settings", {})
TIMEZONE = pytz.timezone(bot_settings.get("timezone", "UTC"))
CHECK_INTERVAL = bot_settings.get("check_interval_seconds", 60)

# Configurar logging
log_level = getattr(logging, bot_settings.get("log_level", "INFO"))
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Lista de whales
whales = config.get("whales", [])

# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola! 👋 Soy tu bot de XRP Whales. Usa /help para ver los comandos disponibles.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/add <address> <min_usd> - Añadir una ballena\n"
        "/remove <address> - Borrar una ballena\n"
        "/ballenas - Listar todas las ballenas\n"
        "El bot enviará notificaciones con estos emotis:\n"
        "⬆️ Compra\n"
        "⬇️ Venta\n"
        "💸 Transferencia"
    )

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        address = context.args[0]
        min_usd = float(context.args[1])
        whales.append({"address": address, "min_usd": min_usd})
        await update.message.reply_text(f"Ballena añadida: {address} con mínimo ${min_usd}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add <address> <min_usd>")

async def remove_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        address = context.args[0]
        global whales
        whales = [w for w in whales if w["address"] != address]
        await update.message.reply_text(f"Ballena eliminada: {address}")
    except IndexError:
        await update.message.reply_text("Uso: /remove <address>")

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not whales:
        await update.message.reply_text("No hay ballenas registradas.")
        return
    msg = "Ballenas actuales:\n"
    for w in whales:
        msg += f"- {w['address']} mínimo ${w['min_usd']}\n"
    await update.message.reply_text(msg)

# Función simulada para detectar movimientos de whales (placeholder)
async def check_whales():
    # Aquí pondrías tu lógica real para chequear la blockchain
    for whale in whales:
        # Ejemplo de notificación simulada
        print(f"Detectada actividad de {whale['address']}: ⬆️ Compra, ⬇️ Venta, 💸 Transferencia")

async def main():
    # Crear aplicación de Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Agregar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("remove", remove_whale))
    app.add_handler(CommandHandler("ballenas", list_whales))

    # Scheduler para chequeos periódicos
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(check_whales, IntervalTrigger(seconds=CHECK_INTERVAL))
    scheduler.start()

    # Ejecutar bot
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
