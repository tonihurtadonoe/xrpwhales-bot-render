import os
import time
import threading
import requests
from dotenv import load_dotenv
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# ---------------- Configuración inicial ---------------- #
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = os.getenv("USER_ID")
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY") or "TU_API_KEY_DE_WHALE_ALERT"

MIN_USD_VALUE = 5_000_000  # Filtrar transacciones >= 5M USD
POLL_INTERVAL = 60         # Segundos entre consultas a la API

bot = Bot(token=BOT_TOKEN)
seen_tx_hashes = set()

# ---------------- Función para obtener transacciones ---------------- #
def fetch_whale_alert_transactions():
    """
    Obtiene transacciones grandes de Whale Alert para XRP >= MIN_USD_VALUE
    """
    url = "https://api.whale-alert.io/v1/transactions"
    params = {
        "api_key": WHALE_ALERT_API_KEY,
        "min_value": MIN_USD_VALUE,
        "currency": "xrp"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        transactions = []
        for tx in data.get("transactions", []):
            tx_hash = tx.get("hash")
            if not tx_hash or tx_hash in seen_tx_hashes:
                continue

            seen_tx_hashes.add(tx_hash)
            from_owner = tx.get("from", {}).get("owner", "desconocido")
            to_owner = tx.get("to", {}).get("owner", "desconocido")
            amount_usd = tx.get("amount_usd", 0)
            tx_type = "🔵 Envío a exchange (posible venta)" if tx.get("to", {}).get("owner_type") == "exchange" else "🟢 Retiro de exchange (posible compra)"

            transactions.append({
                "type": tx_type,
                "amount_usd": amount_usd,
                "hash": tx_hash,
                "from": from_owner,
                "to": to_owner
            })

        return transactions

    except Exception as e:
        print(f"[ERROR] fetch_whale_alert_transactions: {e}")
        return []

# ---------------- Función para enviar alertas ---------------- #
async def send_telegram_alert(tx):
    message = (
        f"{tx['type']}\n"
        f"💰 *Monto:* ${tx['amount_usd']:,.0f}\n"
        f"📤 De: {tx['from']}\n"
        f"📥 A: {tx['to']}\n"
        f"[Ver transacción](https://xrpscan.com/tx/{tx['hash']})"
    )

    try:
        await bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)
        print(f"[OK] Alerta enviada: {tx['hash']}")
    except Exception as e:
        print(f"[ERROR] send_telegram_alert: {e}")

# ---------------- Job periódico ---------------- #
async def check_whales(context: ContextTypes.DEFAULT_TYPE):
    transactions = fetch_whale_alert_transactions()
    for tx in transactions:
        await send_telegram_alert(tx)

# ---------------- Comando /start ---------------- #
async def start(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🚀 Bot de alertas XRP activo.\nRecibirás notificaciones de movimientos > $5M USD."
    )

# ---------------- Flask (mantener vivo el bot) ---------------- #
app = Flask(__name__)

@app.route("/")
@app.route("/status")
def status():
    return {"status": "✅ Bot activo", "checked": time.ctime()}

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

# ---------------- Iniciar el bot ---------------- #
def start_bot():
    print("Iniciando bot XRP Whales...")

    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comando /start
    app_telegram.add_handler(CommandHandler("start", start))

    # Job periódico
    job_queue = app_telegram.job_queue
    job_queue.run_repeating(check_whales, interval=POLL_INTERVAL, first=5)

    print("✅ Bot iniciado correctamente.")
    app_telegram.run_polling()

if __name__ == "__main__":
    # Iniciar Flask en un hilo separado
    threading.Thread(target=run_flask).start()

    # Iniciar el bot
    start_bot()
