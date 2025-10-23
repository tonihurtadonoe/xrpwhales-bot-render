# xrp_whales_bot.py
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Cargar variables de entorno
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN no está definido en el archivo .env")

# Función de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Bot de XRP Whales iniciado!")

# Aquí puedes agregar más funciones de comandos o jobs

# Crear la aplicación
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Agregar handlers
app.add_handler(CommandHandler("start", start))

# Función principal
if __name__ == "__main__":
    print("Bot iniciado, escuchando...")
    app.run_polling()
