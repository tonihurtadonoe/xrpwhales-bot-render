import os
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# ---------- VARIABLES DE ENTORNO ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_ENV = os.environ.get("CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en las variables de entorno.")
if not CHAT_ID_ENV:
    raise ValueError("Falta CHAT_ID en las variables de entorno.")

try:
    CHAT_ID = int(CHAT_ID_ENV)
except ValueError:
    raise ValueError("CHAT_ID debe ser un número entero.")

# ---------- EMOJIS FIJOS ----------
EMOJI_COMPRA = "⬆️🟢"
EMOJI_VENTA = "⬇️🔴"
EMOJI_ENVIO = "💸"

# ---------- FUNCIONES DEL BOT ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_lang = update.effective_user.language_code
    greeting = "Hola" if user_lang and user_lang.startswith("es") else "Hi"
    await update.message.reply_text(f"{greeting}, {update.effective_user.first_name}! Bot activo ✅")

async def enviar_compra(context: ContextTypes.DEFAULT_TYPE):
    bot: Bot = context.bot
    await bot.send_message(chat_id=CHAT_ID, text=f"{EMOJI_COMPRA} Nueva compra detectada!")

async def enviar_venta(context: ContextTypes.DEFAULT_TYPE):
    bot: Bot = context.bot
    await bot.send_message(chat_id=CHAT_ID, text=f"{EMOJI_VENTA} Nueva venta detectada!")

async def enviar_envio(context: ContextTypes.DEFAULT_TYPE, wallet: str, amount: float):
    bot: Bot = context.bot
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"{EMOJI_ENVIO} Envío de {amount} a wallet {wallet}"
    )

# ---------- COMANDOS MANUALES ----------
async def compra_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{EMOJI_COMPRA} Compra manual activada")
    await enviar_compra(context)

async def venta_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{EMOJI_VENTA} Venta manual activada")
    await enviar_venta(context)

# ---------- MAIN ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("compra", compra_manual))
    app.add_handler(CommandHandler("venta", venta_manual))
    
    # JobQueue
    job_queue: JobQueue = app.job_queue
    
    # EJEMPLO: jobs periódicos cada 60s (puedes cambiar)
    job_queue.run_repeating(enviar_compra, interval=60, first=5)
    job_queue.run_repeating(enviar_venta, interval=60, first=10)
    
    print("Bot corriendo...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
