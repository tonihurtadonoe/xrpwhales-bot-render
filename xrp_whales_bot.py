import json
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
from datetime import datetime
import pytz

# -------------------------------
# Cargar configuración
# -------------------------------
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
BOT_SETTINGS = config.get("bot_settings", {})
WHALES = config.get("whales", [])

TIMEZONE_NAME = BOT_SETTINGS.get("timezone", "UTC")
TIMEZONE = pytz.timezone(TIMEZONE_NAME)
CHECK_INTERVAL = BOT_SETTINGS.get("check_interval_seconds", 60)
SYMBOLS = BOT_SETTINGS.get("symbols", ["XRPUSD"])

# Para evitar notificaciones duplicadas
notified_tx_ids = set()

# -------------------------------
# Funciones auxiliares
# -------------------------------
def save_config():
    global WHALES
    config["whales"] = WHALES
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

def format_whales():
    if not WHALES:
        return "No hay ballenas registradas."
    return "\n".join([f"{w['address']} → ${w['min_usd']}" for w in WHALES])

# -------------------------------
# Comandos del bot
# -------------------------------
async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_whales())
    if not context.application.chat_id:
        context.application.chat_id = update.effective_chat.id

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
    if not context.application.chat_id:
        context.application.chat_id = update.effective_chat.id

async def remove_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /remove_ballena <address>")
        return
    address = context.args[0]
    global WHALES
    WHALES = [w for w in WHALES if w["address"] != address]
    save_config()
    await update.message.reply_text(f"Ballena eliminada: {address}")
    if not context.application.chat_id:
        context.application.chat_id = update.effective_chat.id

# -------------------------------
# Función para revisar transacciones de ballenas
# -------------------------------
async def check_whales(app):
    if not app.chat_id:
        return  # No hay chat asignado aún

    for whale in WHALES:
        address = whale["address"]
        min_usd = whale["min_usd"]

        try:
            response = requests.get(
                f"https://data.ripple.com/v2/accounts/{address}/transactions?limit=5"
            )
            data = response.json()
        except Exception as e:
            print(f"Error consultando XRP Ledger: {e}")
            continue

        for tx in data.get("transactions", []):
            tx_id = tx.get("tx", {}).get("hash")
            if not tx_id or tx_id in notified_tx_ids:
                continue

            meta = tx.get("meta", {})
            tx_type = tx.get("tx", {}).get("TransactionType", "")
            amount = tx.get("tx", {}).get("Amount", 0)
            if isinstance(amount, dict):
                amount_val = float(amount.get("value", 0))
                currency = amount.get("currency", "")
            else:
                amount_val = float(amount) / 1_000_000
                currency = "XRP"

            if amount_val < min_usd:
                continue

            if tx_type == "Payment":
                direction = tx["tx"].get("Destination") == address
                emoji = "⬆️" if direction else "⬇️"
                action = "Compra" if direction else "Venta"
                text = f"{emoji} {action} de {amount_val} {currency} por {address}"
            elif tx_type in ["TrustSet", "OfferCreate", "OfferCancel"]:
                emoji = "💸"
                text = f"{emoji} Transacción de {address}: {tx_type} {amount_val} {currency}"
            else:
                continue

            await app.bot.send_message(chat_id=app.chat_id, text=text)
            notified_tx_ids.add(tx_id)

# -------------------------------
# Configuración y arranque del bot
# -------------------------------
async def main():
    # Crear la JobQueue explícitamente con timezone pytz
    job_queue = JobQueue(timezone=TIMEZONE)
    job_queue.start()

    # Crear el bot con la JobQueue
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(job_queue).build()

    # Handlers de comandos
    app.add_handler(CommandHandler("ballenas", list_whales))
    app.add_handler(CommandHandler("add_ballena", add_whale))
    app.add_handler(CommandHandler("remove_ballena", remove_whale))

    # Chat ID inicial
    app.chat_id = None

    # Añadir nuestro job de chequeo de ballenas
    app.job_queue.run_repeating(
        lambda ctx: asyncio.create_task(check_whales(app)),
        interval=CHECK_INTERVAL
    )

    print("Bot iniciado...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
