import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# ----------------------
# CONFIGURACIÓN DEL BOT
# ----------------------
BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
OWNER_ID = 123456789  # Tu ID de Telegram para /add /del /limit

# Lista de ballenas de ejemplo
ballenas = [
    {"nombre": "Whale1", "ultimo_mov": "Compra ⬆️🟢 5000 XRP"},
    {"nombre": "Whale2", "ultimo_mov": "Venta ⬇️🔴 2000 XRP"},
    {"nombre": "Whale3", "ultimo_mov": "Envio 💸 1000 XRP"},
]

# ----------------------
# HANDLERS
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Bienvenido al bot de alertas de ballenas XRP!\n"
        'Escribe "ballenas" para ver la lista completa de ballenas y sus movimientos.'
    )

async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if text in ["hola", "hi"]:
        await start(update, context)
    
    elif text == "ballenas":
        msg = "🐋 Lista de Ballenas:\n\n"
        for whale in ballenas:
            msg += f"{whale['nombre']}: {whale['ultimo_mov']}\n"
        await update.message.reply_text(msg)
    
    # Puedes añadir más respuestas aquí si quieres

# Comandos privados solo para ti
async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    try:
        nombre = context.args[0]
        mov = " ".join(context.args[1:])
        ballenas.append({"nombre": nombre, "ultimo_mov": mov})
        await update.message.reply_text(f"Ballena {nombre} añadida ✅")
    except Exception:
        await update.message.reply_text("Uso: /add <nombre> <movimiento>")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    try:
        nombre = context.args[0]
        global ballenas
        ballenas = [w for w in ballenas if w['nombre'] != nombre]
        await update.message.reply_text(f"Ballena {nombre} eliminada ✅")
    except Exception:
        await update.message.reply_text("Uso: /del <nombre>")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    try:
        limit = float(context.args[0])
        # Aquí guardas tu límite
        await update.message.reply_text(f"Límite actualizado a {limit} XRP ✅")
    except Exception:
        await update.message.reply_text("Uso: /limit <valor>")

# ----------------------
# MAIN
# ----------------------
async def main():
    # Scheduler con pytz para evitar errores de timezone
    scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    scheduler.start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("del", del_whale))
    app.add_handler(CommandHandler("limit", set_limit))
    
    # Start polling
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
