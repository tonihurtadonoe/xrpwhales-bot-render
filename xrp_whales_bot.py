# xrp_whales_bot.py
# Bot de Telegram para alertas de movimientos grandes de XRP (ballenas)
# Compatible con python-telegram-bot v20 y Python 3.13+

import asyncio
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
import httpx
import os

# --- CONFIGURACIÓN ---
TOKEN = "7750255822:AAG1tElixPESOV4ZHtwufvdzcvNzbEhUOHM"
CHAT_ID = 278754715
MIN_AMOUNT_USD = 5_000_000  # Alerta a partir de 5 millones
CHECK_INTERVAL = 30  # segundos entre revisiones

# --- API simulada para movimientos de ballenas ---
# En producción, reemplaza esta función con la API real que uses
async def fetch_whale_transactions():
    """
    Simula la obtención de movimientos grandes de XRP.
    Devuelve lista de dicts con:
    {'type': 'buy'/'sell', 'amount_usd': float, 'tx_hash': str}
    """
    # Ejemplo simulado
    return [
        {"type": "buy", "amount_usd": 7000000, "tx_hash": "0xabc123"},
        {"type": "sell", "amount_usd": 6000000, "tx_hash": "0xdef456"},
    ]

# --- FUNCIONES DEL BOT ---
async def start(update, context):
    await update.message.reply_text(
        "Hola! Soy tu bot de alertas de XRP Whales.\n"
        "Te avisaré cuando una ballena compre o venda más de $5M."
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/start - iniciar bot\n"
        "/help - mostrar ayuda\n"
        "/check - revisar movimientos ahora"
    )

async def check_command(update, context):
    await update.message.reply_text("Revisando movimientos de ballenas...")
    await check_whales(context.bot)

# --- LÓGICA DE ALERTAS ---
async def check_whales(bot: Bot):
    transactions = await fetch_whale_transactions()
    for tx in transactions:
        if tx["amount_usd"] >= MIN_AMOUNT_USD:
            type_str = "COMPRA EN LARGO" if tx["type"] == "buy" else "VENTA CORTA"
            msg = (
                f"💰 ALERTA BALLENA 💰\n"
                f"Tipo: {type_str}\n"
                f"Monto: ${tx['amount_usd']:,}\n"
                f"Tx: {tx['tx_hash']}"
            )
            await bot.send_message(chat_id=CHAT_ID, text=msg)

# --- TAREA PERIÓDICA ---
async def periodic_whale_check(app):
    while True:
        try:
            await check_whales(app.bot)
        except Exception as e:
            print("Error revisando ballenas:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# --- MAIN ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("check", check_command))

    # Iniciar tarea periódica
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(check_whales(app.bot)),
                                interval=CHECK_INTERVAL,
                                first=5)

    print("Bot iniciado...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
