import asyncio
import pytz
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    JobQueue,
)

# -------------------------
# CONFIGURACIÓN
# -------------------------
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
CHAT_ID = "TU_CHAT_ID_AQUI"  # chat donde se enviarán las alertas

# -------------------------
# FUNCIONES
# -------------------------

# Mensaje de bienvenida
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Bienvenido al bot de XRP Whales.\n"
        "Usa /help para ver los comandos disponibles."
    )

# Comandos de ayuda
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/start - Mensaje de bienvenida\n"
        "/help - Esta ayuda\n\n"
        "También puedo mostrar alertas de ballenas 💸⬆️🟢⬇️🔴"
    )

# Detecta palabras en mensajes y responde
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    reply = ""
    if "ballenas" in text:
        reply = "🐋 ¡Alerta de ballenas! Mantente atento 💸⬆️🟢⬇️🔴"
    if reply:
        await update.message.reply_text(reply)

# Alertas automáticas de ballenas
async def whale_alert(context: ContextTypes.DEFAULT_TYPE):
    alerts = [
        "Compra ⬆️🟢 detectada por una ballena",
        "Venta ⬇️🔴 detectada por una ballena",
        "Envío 💸 detectado por una ballena"
    ]
    alert = random.choice(alerts)
    await context.bot.send_message(chat_id=CHAT_ID, text=alert)

# -------------------------
# FUNCIÓN PRINCIPAL
# -------------------------
async def main():
    # Crear JobQueue con timezone compatible con pytz
    job_queue = JobQueue(timezone=pytz.UTC)
    job_queue.start()

    # Crear aplicación del bot
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(job_queue).build()

    # Agregar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Programar alertas cada 60 segundos (puedes ajustar)
    job_queue.run_repeating(whale_alert, interval=60, first=10, chat_id=CHAT_ID)

    # Iniciar el bot
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
