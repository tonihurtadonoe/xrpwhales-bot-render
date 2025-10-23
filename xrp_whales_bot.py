import os
import time
import requests
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dotenv import load_dotenv

# ---------------- Cargar variables de entorno ---------------- #
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = os.getenv("USER_ID")
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY")  # opcional
XRPSCAN_API_KEY = os.getenv("XRPSCAN_API_KEY")  # opcional

MIN_USD_VALUE = 5_000_000  # Filtrar transacciones >= 5M USD
POLL_INTERVAL = 60  # Segundos entre consultas a la API

# Inicializar bot
bot = Bot(token=BOT_TOKEN)

# Guardar transacciones ya enviadas para evitar duplicados
seen_tx_hashes = set()


# ---------------- Funciones ---------------- #
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
            tx_hash = tx["hash"]
            if tx_hash in seen_tx_hashes:
                continue
            seen_tx_hashes.add(tx_hash)

            # Determinar tipo de transacción
            tx_type = (
                "📈 Ingreso a exchange (posible venta)"
                if tx["to"]["owner_type"] == "exchange"
                else "📤 Salida de exchange (posible compra)"
            )

            amount_usd = tx["amount_usd"]
            transactions.append({
                "type": tx_type,
                "amount_usd": amount_usd,
                "hash": tx_hash,
                "from": tx["from"]["owner"],
                "to": tx["to"]["owner"]
            })
        return transactions
    except Exception as e:
        print(f"❌ Error al obtener transacciones: {e}")
        return []


async def send_telegram_alert(tx):
    """
    Envía la alerta a Telegram
    """
    try:
        message = (
            f"🐋 *{tx['type']} detectada!*\n"
            f"Monto: ${tx['amount_usd']:,}\n"
            f"De: {tx['from']}\n"
            f"A: {tx['to']}\n"
            f"[🔗 Ver en XRPScan](https://xrpscan.com/tx/{tx['hash']})"
        )
        await bot.send_message(chat_id=USER_ID, text=message, parse_mode=ParseMode.MARKDOWN)
        print(f"✅ Alerta enviada: {tx['hash']}")
    except Exception as e:
        print(f"⚠️ Error al enviar mensaje Telegram: {e}")


async def check_whales(context: ContextTypes.DEFAULT_TYPE):
    """
    Función periódica para revisar transacciones grandes
    """
    transactions = fetch_whale_alert_transactions()
    for tx in transactions:
        await send_telegram_alert(tx)


# ---------------- Comando /start ---------------- #
async def start(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Bot XRP Whales activo. Recibirás alertas de transacciones >= 5M USD."
    )


# ---------------- Inicialización ---------------- #
if __name__ == "__main__":
    print("🚀 Iniciando bot XRP Whales...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comando /start
    app.add_handler(CommandHandler("start", start))

    # Tarea periódica
    job_queue = app.job_queue
    job_queue.run_repeating(check_whales, interval=POLL_INTERVAL, first=5)

    print("🤖 Bot ejecutándose. Esperando transacciones...")
    app.run_polling()
