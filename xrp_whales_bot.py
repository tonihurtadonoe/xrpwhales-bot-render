import asyncio
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ===========================
# CONFIGURACIÓN INICIAL
# ===========================
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"  # Reemplaza con tu token
TIMEZONE = "America/New_York"     # Ajusta a tu zona horaria

# Datos de ejemplo de ballenas
ballenas = {
    "Whale1": {"nombre": "Alice", "limite": 100000},
    "Whale2": {"nombre": "Bob", "limite": 50000},
}

# ===========================
# HANDLERS DE MENSAJES
# ===========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Bienvenido al bot de XRP Whales! 😎\n"
        "Escribe 'ballenas' para ver la lista."
    )

async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ["hola", "hi"]:
        await update.message.reply_text("¡Hola! Bienvenido al bot de XRP Whales 😎")
    elif text == "ballenas":
        msg = "Lista de Ballenas:\n"
        for key, info in ballenas.items():
            msg += f"{key}: {info['nombre']}, Límite: {info['limite']}\n"
        await update.message.reply_text(msg)

# ===========================
# COMANDOS DE ADMINISTRACIÓN (solo tú)
# ===========================

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        limite = int(context.args[1])
        key = f"Whale{len(ballenas)+1}"
        ballenas[key] = {"nombre": nombre, "limite": limite}
        await update.message.reply_text(f"Ballena añadida: {key} -> {nombre}, Límite: {limite}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add <nombre> <limite>")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]
        if key in ballenas:
            del ballenas[key]
            await update.message.reply_text(f"Ballena {key} borrada.")
        else:
            await update.message.reply_text("No existe esa ballena.")
    except IndexError:
        await update.message.reply_text("Uso: /del <clave_ballena>")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]
        nuevo_limite = int(context.args[1])
        if key in ballenas:
            ballenas[key]["limite"] = nuevo_limite
            await update.message.reply_text(f"Límite de {key} actualizado a {nuevo_limite}")
        else:
            await update.message.reply_text("No existe esa ballena.")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /limit <clave_ballena> <nuevo_limite>")

# ===========================
# JOB DE ALERTAS (EJEMPLO)
# ===========================

async def alerta_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = "TU_CHAT_ID_DE_PRUEBA"
    await context.bot.send_message(chat_id=chat_id, text="🔔 Alerta de XRP Whales: revisa las ballenas!")

# ===========================
# MAIN
# ===========================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Configurar timezone con pytz para Render
    app.job_queue.scheduler.configure(timezone=pytz.timezone(TIMEZONE))

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("del", del_whale))
    app.add_handler(CommandHandler("limit", set_limit))

    # Job de alertas (cada 60 segundos, ejemplo)
    app.job_queue.run_repeating(alerta_job, interval=60, first=10)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
