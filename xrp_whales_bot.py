import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ------------------------------
# Configuración
# ------------------------------
BOT_TOKEN = "TU_TOKEN_DE_TELEGRAM"
CHANNEL_ID = "@TU_CANAL_O_GRUPO"  # o ID numérico del grupo
ADMIN_IDS = [123456789]  # tu ID de Telegram para comandos privados

# Lista simulada de alertas
whale_alerts = [
    {"nombre": "Whale1", "tipo": "compra_largo", "cantidad": 500000},
    {"nombre": "Whale2", "tipo": "compra_corto", "cantidad": 300000},
    {"nombre": "Whale3", "tipo": "venta", "cantidad": 200000},
]

# Mapeo de emojis
emoji_map = {
    "compra_largo": "⬆️",
    "compra_corto": "⬇️",
    "venta": "💸"
}

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# Handlers
# ------------------------------
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    if "hola" in user_text:
        await update.message.reply_text(
            "¡Hola! 👋\nPara ver las ballenas activas escribe: ballenas"
        )

async def show_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🐋 Alertas de Ballenas XRP 🐋\n\n"
    for alert in whale_alerts:
        emoji = emoji_map.get(alert["tipo"], "")
        text += f"{emoji} {alert['nombre']} - ${alert['cantidad']:,}\n"
    await update.message.reply_text(text)

# Comandos solo para admins
async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        nombre, tipo, cantidad = context.args
        cantidad = int(cantidad)
        whale_alerts.append({"nombre": nombre, "tipo": tipo, "cantidad": cantidad})
        await update.message.reply_text(f"✅ Alerta añadida: {nombre} {tipo} ${cantidad}")
    except Exception as e:
        await update.message.reply_text("❌ Uso: /add nombre tipo cantidad")

async def del_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        nombre = context.args[0]
        global whale_alerts
        whale_alerts = [w for w in whale_alerts if w["nombre"] != nombre]
        await update.message.reply_text(f"🗑️ Alerta eliminada: {nombre}")
    except Exception as e:
        await update.message.reply_text("❌ Uso: /dell nombre")

async def limit_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        limite = int(context.args[0])
        global whale_alerts
        whale_alerts = whale_alerts[:limite]
        await update.message.reply_text(f"⚡ Limite de alertas establecido en {limite}")
    except Exception as e:
        await update.message.reply_text("❌ Uso: /limit numero")

# ------------------------------
# Main
# ------------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Mensajes normales
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), welcome))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^ballenas$"), show_whales))

    # Comandos admin
    app.add_handler(CommandHandler("add", add_alert))
    app.add_handler(CommandHandler("dell", del_alert))
    app.add_handler(CommandHandler("limit", limit_alert))

    # Inicia bot
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
