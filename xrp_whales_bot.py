import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

# Cargar configuración
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
BOT_SETTINGS = config.get("bot_settings", {})
WHALES = config.get("whales", [])

TIMEZONE = pytz.timezone(BOT_SETTINGS.get("timezone", "UTC"))
CHECK_INTERVAL = BOT_SETTINGS.get("check_interval_seconds", 60)
SYMBOLS = BOT_SETTINGS.get("symbols", ["XRPUSD"])

# Funciones auxiliares
def save_config():
    global WHALES
    config["whales"] = WHALES
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

def format_whales():
    if not WHALES:
        return "No hay ballenas registradas."
    return "\n".join([f"{w['address']} → ${w['min_usd']}" for w in WHALES])

# Comandos del bot
async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_whales())

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Uso: /add_ballena <address> <min_usd>")
        return
    address, min_usd = context.args
    try:
        min_usd = float(min_usd)
    except ValueError:
        await update.message.reply_text("min_usd debe ser un número.")
        return
    WHALES.append({"address": address, "min_usd": min_usd})
    save_config()
    await update.message.reply_text(f"Ballena añadida: {address} → ${min_usd}")

async def remove_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /remove_ballena <address>")
        return
    address = context.args[0]
    global WHALES
    WHALES = [w for w in WHALES if w["address"] != address]
    save_config()
    await update.message.reply_text(f"Ballena eliminada: {address}")

# Función principal para revisar ballenas (simulada)
async def check_whales(app):
    for whale in WHALES:
        # Aquí podrías conectar a API real para detectar transacciones
        # Ejemplo simulado de notificación
        await app.bot.send_message(
            chat_id=app.chat_id, 
            text=f"Ballena {whale['address']} ha realizado una acción: ⬆️ Compra simulada de ${whale['min_usd']}"
        )

# Configuración del bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("ballenas", list_whales))
    app.add_handler(CommandHandler("add_ballena", add_whale))
    app.add_handler(CommandHandler("remove_ballena", remove_whale))

    # Chat_id donde enviar notificaciones automáticas
    # Para pruebas, se puede asignar manualmente el primer chat que envíe un comando
    app.chat_id = None

    # Scheduler para revisiones periódicas
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: check_whales(app), "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    print("Bot iniciado...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
