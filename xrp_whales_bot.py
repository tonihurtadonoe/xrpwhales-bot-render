import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

# ======== VARIABLES DE ENTORNO ========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
OWNER_ID = int(os.environ.get("OWNER_ID"))

EMOJI_BUY = os.environ.get("EMOJI_BUY", "🐋⬆️🟢")
EMOJI_SELL = os.environ.get("EMOJI_SELL", "🐋⬇️🔴")
EMOJI_SEND = os.environ.get("EMOJI_SEND", "🐋💸")

WELCOME_ES = "🐋 ¡Hola! Bienvenido al bot de XRP Whales."
WELCOME_EN = "🐋 Hi! Welcome to the XRP Whales bot."

# ======== CONFIGURACIÓN EN MEMORIA ========
# Inicializamos whales y min_trans desde variables de entorno si existen
whales = {}
MIN_TRANS = float(os.environ.get("MIN_TRANS", 1000))

# ======== FUNCIONES PARA SIMULAR "PERSISTENCIA" ========
def save_whales():
    """Simula guardar whales en variable de entorno (en memoria)"""
    os.environ["WHALES"] = str(whales)

def load_whales():
    """Carga whales desde variable de entorno (si existe)"""
    global whales
    env_whales = os.environ.get("WHALES")
    if env_whales:
        try:
            # Convierte string de dict a dict
            whales = eval(env_whales)
        except Exception:
            whales = {}

# ======== COMANDOS ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_lang = update.effective_user.language_code
    if user_lang and user_lang.startswith("es"):
        await update.message.reply_text(WELCOME_ES)
    else:
        await update.message.reply_text(WELCOME_EN)

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not whales:
        await update.message.reply_text("No hay ballenas registradas 🐋.")
        return
    text = "🐋 Lista de ballenas:\n"
    for name, addr in whales.items():
        text += f"{name}: {addr}\n"
    await update.message.reply_text(text)

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("No tienes permisos para añadir ballenas 🐋.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /addwhale <nombre> <direccion>")
        return
    name, address = context.args[0], context.args[1]
    whales[name] = address
    save_whales()
    await update.message.reply_text(f"Ballena añadida: {name} 🐋")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("No tienes permisos para borrar ballenas 🐋.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Uso: /delwhale <nombre>")
        return
    name = context.args[0]
    if name in whales:
        del whales[name]
        save_whales()
        await update.message.reply_text(f"Ballena eliminada: {name} 🐋")
    else:
        await update.message.reply_text(f"No existe la ballena: {name} 🐋")

async def set_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MIN_TRANS
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("No tienes permisos para cambiar el límite 🐋.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Uso: /setmin <cantidad>")
        return
    try:
        MIN_TRANS = float(context.args[0])
        os.environ["MIN_TRANS"] = str(MIN_TRANS)
        await update.message.reply_text(f"Límite mínimo actualizado a {MIN_TRANS} 🐋")
    except ValueError:
        await update.message.reply_text("Cantidad inválida 🐋.")

# ======== NOTIFICACIONES DE TRADING ========
async def trade_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=(
            f"{EMOJI_BUY} Nueva compra detectada!\n"
            f"{EMOJI_SELL} Nueva venta detectada!\n"
            f"{EMOJI_SEND} Envío a otro wallet!"
        )
    )

# ======== MAIN ========
async def main():
    # Cargamos whales desde memoria
    load_whales()

    # Construimos la app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Forzamos JobQueue con pytz para evitar errores en Render
    app.job_queue.scheduler = AsyncIOScheduler(timezone=timezone("America/New_York"))

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ballenas", list_whales))
    app.add_handler(CommandHandler("addwhale", add_whale))
    app.add_handler(CommandHandler("delwhale", del_whale))
    app.add_handler(CommandHandler("setmin", set_min))
    app.add_handler(CommandHandler("trade", trade_notification))

    # Ejecutamos polling
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
