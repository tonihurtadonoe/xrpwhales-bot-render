import os
import asyncio
import datetime
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configuración desde variables de entorno de Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))

# ========================
# Comandos del bot
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ¡Bienvenido al bot de XRP Whales!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Usa /start para comenzar, y espera alertas de ballenas XRP.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ No entiendo ese comando.")

# ========================
# Jobs programados
# ========================
async def daily_alert(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text="💸 ¡Recordatorio diario de XRP Whales!")

# ========================
# Función principal
# ========================
async def main():
    # Crear aplicación
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Obtener JobQueue de la app (no pasar timezone aquí)
    job_queue = app.job_queue

    # Configurar zona horaria para jobs
    tz = pytz.timezone("America/New_York")

    # Agregar job diario a las 10:00 AM hora NY
    job_queue.run_daily(
        daily_alert,
        time=datetime.time(hour=10, minute=0, tzinfo=tz)
    )

    # Iniciar bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# ========================
# Ejecutar bot
# ========================
if __name__ == "__main__":
    asyncio.run(main())
