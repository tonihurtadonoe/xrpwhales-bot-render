import os
import json
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Archivo para guardar las ballenas
BALLENAS_FILE = "ballenas.json"

# Cargar ballenas desde JSON
if os.path.exists(BALLENAS_FILE):
    with open(BALLENAS_FILE, "r") as f:
        ballenas = json.load(f)
else:
    ballenas = {}

# Guardar ballenas en JSON
def save_ballenas():
    with open(BALLENAS_FILE, "w") as f:
        json.dump(ballenas, f, indent=2)

# Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bienvenido al bot de XRP Whales!\n"
        "Usa /add, /delete o /list para gestionar ballenas."
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /add <direccion>")
        return
    addr = context.args[0]
    if addr in ballenas:
        await update.message.reply_text("⚠️ Ballena ya registrada.")
    else:
        ballenas[addr] = []
        save_ballenas()
        await update.message.reply_text(f"✅ Ballena {addr} agregada.")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /delete <direccion>")
        return
    addr = context.args[0]
    if addr in ballenas:
        del ballenas[addr]
        save_ballenas()
        await update.message.reply_text(f"❌ Ballena {addr} eliminada.")
    else:
        await update.message.reply_text("⚠️ Ballena no encontrada.")

async def list_ballenas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ballenas:
        await update.message.reply_text("No hay ballenas registradas.")
        return
    msg = "🐋 Ballenas registradas:\n"
    for addr in ballenas.keys():
        msg += f"- {addr}\n"
    await update.message.reply_text(msg)

# Inicializar bot
app = Application.builder().token(BOT_TOKEN).build()

# Registrar comandos
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(CommandHandler("list", list_ballenas))

# Registrar comandos visibles en Telegram
app.bot.set_my_commands([
    BotCommand("start", "Inicia el bot"),
    BotCommand("add", "Agrega una ballena"),
    BotCommand("delete", "Elimina una ballena"),
    BotCommand("list", "Lista ballenas registradas")
])

# Ejecutar bot
if __name__ == "__main__":
    print("🤖 Bot iniciado...")
    app.run_polling()
