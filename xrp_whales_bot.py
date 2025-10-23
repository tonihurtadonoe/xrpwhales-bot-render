import json
import asyncio
import os
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

WHALES_FILE = "whales.json"

# --- Funciones de manejo del JSON ---
def load_whales():
    if not os.path.exists(WHALES_FILE):
        return []
    with open(WHALES_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- Comandos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Soy el bot de alertas de ballenas XRP 🐋\n"
        "Usa /add, /delete, /list y /setmin para configurar."
    )

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /add <address> <min_usd>")
        return
    address = context.args[0]
    try:
        min_usd = int(context.args[1])
    except ValueError:
        await update.message.reply_text("min_usd debe ser un número.")
        return

    whales = load_whales()
    # Evitar duplicados
    if any(w["address"] == address for w in whales):
        await update.message.reply_text("Esta ballena ya está registrada.")
        return

    whales.append({
        "address": address,
        "min_usd": min_usd,
        "chat_id": update.message.chat_id
    })
    save_whales(whales)
    await update.message.reply_text(f"Ballena {address} añadida con mínimo ${min_usd} 🐋")

async def delete_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Uso: /delete <address>")
        return
    address = context.args[0]
    whales = load_whales()
    new_whales = [w for w in whales if w["address"] != address]
    save_whales(new_whales)
    await update.message.reply_text(f"Ballena {address} eliminada 🗑️")

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whales = load_whales()
    if not whales:
        await update.message.reply_text("No hay ballenas registradas.")
        return
    text = "Ballenas registradas:\n"
    for w in whales:
        text += f"🐋 {w['address']} - Min USD: ${w['min_usd']}\n"
    await update.message.reply_text(text)

async def set_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /setmin <address> <min_usd>")
        return
    address = context.args[0]
    try:
        min_usd = int(context.args[1])
    except ValueError:
        await update.message.reply_text("min_usd debe ser un número.")
        return

    whales = load_whales()
    for w in whales:
        if w["address"] == address:
            w["min_usd"] = min_usd
            save_whales(whales)
            await update.message.reply_text(f"Nuevo mínimo para {address}: ${min_usd}")
            return
    await update.message.reply_text("Ballena no encontrada.")

# --- Función de alertas (ejemplo con emoji) ---
async def check_whale_alert():
    while True:
        whales = load_whales()
        for w in whales:
            # Aquí pondrías tu API/Coingecko o WebSocket
            # Simulación de alertas
            alert_amount = 6000000  # USD
            if alert_amount >= w["min_usd"]:
                # Emoji para compra/venta largo/corto de ejemplo
                msg = f"🚨 Ballena detectada {w['address']} - ${alert_amount}"
                bot = context.bot
                await bot.send_message(chat_id=w["chat_id"], text=msg)
        await asyncio.sleep(60)  # Revisa cada minuto

# --- Main ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("delete", delete_whale))
    app.add_handler(CommandHandler("list", list_whales))
    app.add_handler(CommandHandler("setmin", set_min))

    # Set commands con emojis
    await app.bot.set_my_commands([
        BotCommand("start", "Iniciar"),
        BotCommand("add", "Añadir ballena 🐋"),
        BotCommand("delete", "Eliminar ballena 🗑️"),
        BotCommand("list", "Listar ballenas 📜"),
        BotCommand("setmin", "Configurar mínimo 💰"),
    ])

    # Lanzar alerta en segundo plano
    asyncio.create_task(check_whale_alert())

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
