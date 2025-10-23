import os
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# Carga variables de entorno
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # Chat donde mandarás alertas
XRPL_API = os.getenv("XRPL_API")  # Endpoint de tu API para whales

if not BOT_TOKEN or not CHAT_ID or not XRPL_API:
    raise ValueError("BOT_TOKEN, CHAT_ID y XRPL_API deben estar definidos.")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado ✅ listo para alertas de whales XRP.")

# Comando /status (opcional)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot corriendo y conectado a XRP API.")

# Función para revisar whales
async def check_whales(context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(XRPL_API)
            data = response.json()
            
            # Ejemplo: lógica de detección de whales
            whales = data.get("whales", [])
            for whale in whales:
                amount = whale.get("amount")
                address = whale.get("address")
                tx_hash = whale.get("tx_hash")
                if amount >= 100000:  # mínimo para alertar
                    message = f"🚨 Whale XRP detectada!\nMonto: {amount}\nDirección: {address}\nTX: {tx_hash}"
                    await context.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print("Error en check_whales:", e)

# Función principal
async def main():
    # Crea la aplicación
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    # JobQueue para revisar whales cada minuto
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(check_whales, interval=60, first=5)  # cada 60s

    print("Bot corriendo...")
    await app.run_polling()

# Ejecuta el bot
if __name__ == "__main__":
    asyncio.run(main())
