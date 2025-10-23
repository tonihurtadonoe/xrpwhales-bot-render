import os
import requests
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# ---------------- Configuración ---------------- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = os.getenv("USER_ID")  # Tu chat_id de Telegram

# Lista de APIs públicas de XRPSCAN (puedes añadir más backups)
XRPSCAN_APIS = [
    "https://api.xrpscan.com/api/v1",
    # "https://backup.xrpscan.com/api/v1",  # ejemplo de backup
]

# Filtrar transacciones grandes
MIN_USD_VALUE = 5_000_000
POLL_INTERVAL = 60  # segundos entre consultas

# Guardar transacciones ya enviadas para evitar duplicados
seen_tx_hashes = set()


# ---------------- Funciones ---------------- #
def fetch_xrpscan_transactions(account="rEXAMPLE"):
    """
    Intenta obtener datos de XRPSCAN desde varias APIs hasta que una funcione.
    Hace failover automático si alguna API falla.
    """
    for api in XRPSCAN_APIS:
        try:
            url = f"{api}/account/{account}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            transactions = data.get("transactions", [])
            new_tx = []
            for tx in transactions:
                tx_hash = tx.get("hash")
                if tx_hash in seen_tx_hashes:
                    continue

                # Suponemos que la API devuelve "amount_usd" o "amount" en USD
                amount_usd = float(tx.get("amount_usd", tx.get("amount", 0)))
                if amount_usd < MIN_USD_VALUE:
                    continue

                seen_tx_hashes.add(tx_hash)
                new_tx.append({
                    "hash": tx_hash,
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "amount": amount_usd,
                })
            return new_tx
        except Exception as e:
            print(f"❌ Error con {api}: {e}, intentando siguiente API...")
    return []  # Ninguna API funcionó


async def send_telegram_alert(app, tx):
    """
    Envía la alerta de Telegram
    """
    message = (
        f"💰 *Transacción detectada!*\n"
        f"Monto: {tx['amount']}\n"
        f"De: {tx['from']}\n"
        f"A: {tx['to']}\n"
        f"[Ver transacción](https://xrpscan.com/tx/{tx['hash']})"
    )
    await app.bot.send_message(chat_id=USER_ID, text=message, parse_mode="Markdown")


async def check_whales(context: ContextTypes.DEFAULT_TYPE):
    """
    Función periódica para chequear transacciones grandes
    """
    app = context.application
    transactions = fetch_xrpscan_transactions()
    for tx in transactions:
        await send_telegram_alert(app, tx)


# ---------------- Comandos de Telegram ---------------- #
async def start(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Bot XRP Whales activo. Recibirás alertas de transacciones >= {MIN_USD_VALUE} USD."
    )


# ---------------- Inicialización ---------------- #
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comando /start
    app.add_handler(CommandHandler("start", start))

    # Job periódico
    app.job_queue.run_repeating(check_whales, interval=POLL_INTERVAL, first=0)

    print("Bot XRP Whales iniciado...")
    app.run_polling()
