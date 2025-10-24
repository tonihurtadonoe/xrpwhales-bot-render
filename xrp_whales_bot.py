import json
import os
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Cargar variables de entorno
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY")
MIN_USD = int(os.getenv("MIN_USD", 5000000))
WHALES_FILE = "whales.json"
LAST_TX_FILE = "last_tx.json"

# Cargar whales.json
def load_whales():
    if not os.path.exists(WHALES_FILE):
        with open(WHALES_FILE, "w") as f:
            json.dump([], f)
    with open(WHALES_FILE, "r") as f:
        return json.load(f)

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Cargar últimas transacciones
def load_last_tx():
    if not os.path.exists(LAST_TX_FILE):
        with open(LAST_TX_FILE, "w") as f:
            json.dump({}, f)
    with open(LAST_TX_FILE, "r") as f:
        return json.load(f)

def save_last_tx(data):
    with open(LAST_TX_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Bot commands
async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usa /add <direccion> [min_usd]")
        return
    address = context.args[0]
    min_usd = int(context.args[1]) if len(context.args) > 1 else MIN_USD
    whales = load_whales()
    if any(w["address"] == address for w in whales):
        await update.message.reply_text("Ballena ya registrada.")
        return
    whales.append({"address": address, "min_usd": min_usd})
    save_whales(whales)
    await update.message.reply_text(f"Ballena {address} añadida con mínimo ${min_usd}")

async def delete_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usa /delete <direccion>")
        return
    address = context.args[0]
    whales = load_whales()
    whales = [w for w in whales if w["address"] != address]
    save_whales(whales)
    await update.message.reply_text(f"Ballena {address} eliminada.")

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whales = load_whales()
    if not whales:
        await update.message.reply_text("No hay ballenas registradas.")
        return
    msg = "📋 Ballenas registradas:\n"
    for w in whales:
        msg += f"- {w['address']} (min USD: {w.get('min_usd', MIN_USD)})\n"
    await update.message.reply_text(msg)

async def set_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MIN_USD
    if len(context.args) < 1:
        await update.message.reply_text(f"Uso: /setmin <usd>\nActual: {MIN_USD}")
        return
    MIN_USD = int(context.args[0])
    await update.message.reply_text(f"Mínimo USD actualizado a {MIN_USD}")

# Función principal para revisar Whale Alert
async def check_whale_alert(app):
    last_tx = load_last_tx()
    whales = load_whales()
    if not whales:
        return

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.whale-alert.io/v1/transactions",
            params={"api_key": WHALE_ALERT_API_KEY, "min_value": MIN_USD, "currency": "XRP"}
        )
        data = resp.json().get("transactions", [])

        for tx in data:
            addr = tx.get("from")
            value = tx.get("amount_usd", 0)
            tx_id = tx.get("transaction_hash")

            # Revisar si la ballena está registrada
            whale = next((w for w in whales if w["address"] == addr), None)
            if not whale:
                continue

            # Evitar duplicados
            if last_tx.get(addr) == tx_id:
                continue
            last_tx[addr] = tx_id
            save_last_tx(last_tx)

            # Determinar tipo y emoji
            action = "Compra" if tx.get("to") else "Venta"
            emoji = "🟢💰" if action == "Compra" else "🔴💸"
            msg = f"{emoji} {action} de ${int(value):,} por {addr}\nTx: {tx_id}"
            await app.bot.send_message(chat_id=update_chat_id, text=msg)

# Loop principal
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("delete", delete_whale))
    app.add_handler(CommandHandler("list", list_whales))
    app.add_handler(CommandHandler("setmin", set_min))

    # Revisar cada 60s
    async def job():
        while True:
            try:
                await check_whale_alert(app)
            except Exception as e:
                print("Error check_whale_alert:", e)
            await asyncio.sleep(60)

    asyncio.create_task(job())
    await app.run_polling()

if __name__ == "__main__":
    # Reemplaza con tu chat_id de Telegram para enviar alertas
    update_chat_id = "TU_CHAT_ID_AQUI"
    asyncio.run(main())
