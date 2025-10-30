import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# ⚙ Configuración
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
CHECK_INTERVAL = 60  # en segundos
TIMEZONE = "America/New_York"

# Lista de ballenas (ejemplo)
whales = []

# Funciones de comandos
async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not whales:
        await update.message.reply_text("🐋 No hay ballenas registradas.")
    else:
        msg = "🐳 Lista de ballenas:\n" + "\n".join(f"• {w}" for w in whales)
        await update.message.reply_text(msg)

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        whale = " ".join(context.args)
        whales.append(whale)
        await update.message.reply_text(f"✅ Ballena agregada: {whale}")
    else:
        await update.message.reply_text("⚠️ Usa /add_ballena <nombre>")

async def remove_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        whale = " ".join(context.args)
        if whale in whales:
            whales.remove(whale)
            await update.message.reply_text(f"🗑️ Ballena removida: {whale}")
        else:
            await update.message.reply_text(f"❌ Ballena no encontrada: {whale}")
    else:
        await update.message.reply_text("⚠️ Usa /remove_whale <nombre>")

# Función de chequeo periódico (simulación)
async def check_whales(app):
    if whales:
        for whale in whales:
            # Aquí pondrías la lógica real de monitoreo
            print(f"👀 Revisando ballena: {whale}")
            # Opcional: enviar mensaje a Telegram
            # await app.bot.send_message(chat_id=app.chat_id, text=f"🐋 Ballena activa: {whale}")

# Main
async def main():
    # Crear bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.chat_id = None  # opcional, si quieres enviar mensajes automáticos a un chat específico

    # Agregar handlers
    app.add_handler(CommandHandler("ballenas", list_whales))
    app.add_handler(CommandHandler("add_ballena", add_whale))
    app.add_handler(CommandHandler("remove_whale", remove_whale))

    # Scheduler externo con pytz
    scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
    scheduler.add_job(lambda: asyncio.create_task(check_whales(app)), "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    print("🤖 Bot iniciado...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
