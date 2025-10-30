import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# ================= CONFIG =================
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
TIMEZONE = pytz.timezone("America/New_York")  # <- Ajusta a tu zona horaria
# =========================================

# Lista de ballenas de ejemplo
whales = [
    {"name": "Whale1", "wallet": "rXXX...1", "limit": 1000},
    {"name": "Whale2", "wallet": "rXXX...2", "limit": 500},
]

# Comandos solo para el administrador
ADMIN_ID = 123456789  # <- Tu ID de Telegram

# ================= FUNCIONES =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Bienvenido al bot de XRP Whales.\n"
        "Escribe 'ballenas' para ver la lista de ballenas."
    )

async def show_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🐋 Lista de Ballenas:\n"
    for whale in whales:
        msg += f"{whale['name']}: {whale['wallet']} - Límite: {whale['limit']}\n"
    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ["hola", "hi"]:
        await start(update, context)
    elif text == "ballenas":
        await show_whales(update, context)

# ================= COMANDOS ADMIN =================
async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        name, wallet, limit = context.args
        whales.append({"name": name, "wallet": wallet, "limit": int(limit)})
        await update.message.reply_text(f"✅ Ballena {name} añadida correctamente.")
    except:
        await update.message.reply_text("❌ Uso: /add <nombre> <wallet> <límite>")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        name = context.args[0]
        global whales
        whales = [w for w in whales if w['name'] != name]
        await update.message.reply_text(f"✅ Ballena {name} eliminada correctamente.")
    except:
        await update.message.reply_text("❌ Uso: /del <nombre>")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        name, new_limit = context.args
        for w in whales:
            if w['name'] == name:
                w['limit'] = int(new_limit)
                await update.message.reply_text(f"✅ Límite de {name} actualizado a {new_limit}.")
                return
        await update.message.reply_text("❌ Ballena no encontrada.")
    except:
        await update.message.reply_text("❌ Uso: /limit <nombre> <nuevo_limite>")

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Scheduler con timezone correcto
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.start()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("del", del_whale))
    app.add_handler(CommandHandler("limit", set_limit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
