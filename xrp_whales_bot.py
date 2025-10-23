import json
import os
import asyncio
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import httpx

# --- Config ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WH_API_KEY = os.getenv("WH_API_KEY")  # Whale Alert API key
CHECK_INTERVAL = 60  # segundos
DATA_FILE = "whales.json"

# --- JSON Data ---
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"ballenas": [], "min_usd": 5000000, "last_tx": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- Telegram Handlers ---
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bienvenido al monitor de Ballenas XRP!")

async def add_ballena(update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /add <direccion>")
        return
    addr = context.args[0]
    data = load_data()
    if addr in data["ballenas"]:
        await update.message.reply_text("⚠️ Ballena ya registrada")
        return
    data["ballenas"].append(addr)
    save_data(data)
    await update.message.reply_text(f"✅ Ballena agregada: {addr}")

async def delete_ballena(update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /delete <direccion>")
        return
    addr = context.args[0]
    data = load_data()
    if addr not in data["ballenas"]:
        await update.message.reply_text("⚠️ Ballena no encontrada")
        return
    data["ballenas"].remove(addr)
    save_data(data)
    await update.message.reply_text(f"❌ Ballena eliminada: {addr}")

async def list_ballenas(update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["ballenas"]:
        await update.message.reply_text("No hay ballenas registradas")
        return
    texto = "📋 Ballenas:\n" + "\n".join(data["ballenas"])
    await update.message.reply_text(texto)

async def set_min(update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /setmin <usd>")
        return
    try:
        min_usd = int(context.args[0])
    except:
        await update.message.reply_text("Ingresa un número válido")
        return
    data = load_data()
    data["min_usd"] = min_usd
    save_data(data)
    await update.message.reply_text(f"✅ Monto mínimo actualizado: ${min_usd}")

# --- Función para obtener precio XRP USD de CoinGecko ---
async def get_xrp_price():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd")
        return resp.json()["ripple"]["usd"]

# --- Función para chequear Whale Alert ---
async def check_whale_alert(bot):
    while True:
        data = load_data()
        if not data["ballenas"]:
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        async with httpx.AsyncClient() as client:
            url = f"https://api.whale-alert.io/v1/transactions?api_key={WH_API_KEY}&min_value={data['min_usd']}&currency=xrp"
            resp = await client.get(url)
            result = resp.json()
            for tx in result.get("transactions", []):
                addr = tx.get("from")
                if addr not in data["ballenas"]:
                    continue

                tx_id = tx["hash"]
                if data["last_tx"].get(addr) == tx_id:
                    continue  # ya enviado
                data["last_tx"][addr] = tx_id
                save_data(data)

                # Emoji según tipo y dirección
                tipo = "💰" if tx["direction"]=="in" else "🛑"
                tipo += " ⬆️" if tx.get("long") else " ⬇️"

                xrp_usd = await get_xrp_price()
                amount_usd = round(tx["amount"] * xrp_usd,2)

                msg = f"{tipo} Ballena {addr}:\n{tx['amount']} XRP (~${amount_usd})\n{tx['hash']}"
                await bot.send_message(chat_id=CHAT_ID, text=msg)
        await asyncio.sleep(CHECK_INTERVAL)

# --- Main ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    await app.bot.set_my_commands([
        BotCommand("start", "Iniciar bot"),
        BotCommand("add", "Agregar ballena"),
        BotCommand("delete", "Eliminar ballena"),
        BotCommand("list", "Listar ballenas"),
        BotCommand("setmin", "Establecer mínimo de transacción"),
    ])

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_ballena))
    app.add_handler(CommandHandler("delete", delete_ballena))
    app.add_handler(CommandHandler("list", list_ballenas))
    app.add_handler(CommandHandler("setmin", set_min))

    # Ejecutar loop de Whale Alert
    asyncio.create_task(check_whale_alert(app.bot))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
