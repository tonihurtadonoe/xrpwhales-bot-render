import asyncio
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- CONFIGURACIÓN ---
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
whales = {}  # Diccionario de ballenas {nombre: limite_transaccion}

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! 🤖 Bienvenido al bot de seguimiento de XRP Whales.\n"
        "Escribe 'ballenas' para ver la lista de todas las ballenas."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if text in ["hola", "hi"]:
        await update.message.reply_text(
            "¡Hola! 🤖 Bienvenido al bot de seguimiento de XRP Whales.\n"
            "Escribe 'ballenas' para ver la lista de todas las ballenas."
        )
    elif text == "ballenas":
        if whales:
            message = "Lista de ballenas:\n"
            for nombre, limite in whales.items():
                message += f"- {nombre}: límite de {limite} XRP\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("No hay ballenas registradas aún.")
    else:
        await update.message.reply_text("Comando no reconocido. Usa 'hola' o 'ballenas'.")

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        limite = float(context.args[1])
        whales[nombre] = limite
        await update.message.reply_text(f"✅ Ballena '{nombre}' añadida con límite {limite} XRP.")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add <nombre> <límite>")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        if nombre in whales:
            del whales[nombre]
            await update.message.reply_text(f"❌ Ballena '{nombre}' eliminada.")
        else:
            await update.message.reply_text("La ballena no existe.")
    except IndexError:
        await update.message.reply_text("Uso: /del <nombre>")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        limite = float(context.args[1])
        if nombre in whales:
            whales[nombre] = limite
            await update.message.reply_text(f"⚡ Límite de '{nombre}' actualizado a {limite} XRP.")
        else:
            await update.message.reply_text("La ballena no existe.")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /limit <nombre> <nuevo_limite>")

# --- MAIN ---

async def main():
    # Crear scheduler con pytz
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/New_York"))
    scheduler.start()

    # Crear JobQueue con ese scheduler
    job_queue = JobQueue()
    job_queue.scheduler = scheduler
    job_queue.start()

    # Crear aplicación pasando nuestro JobQueue
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(job_queue).build()

    # Añadir handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("del", del_whale))
    app.add_handler(CommandHandler("limit", set_limit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Ejecutar bot
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
