import asyncio
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# ----------------------------
# CONFIG
BOT_TOKEN = "TU_BOT_TOKEN"
CHANNEL_ID = "@tu_canal"  # tu canal o grupo
WHALE_ALERT_API_KEY = "TU_API_KEY"  # clave de la API real
# ----------------------------

ballenas_seguidas = {
    "Whale1": 500000,
    "Whale2": 300000,
    "Whale3": 1000000
}

alert_limit = 5
alert_count = 0

# ----------------------------
# FUNCIONES DE ALERTA
async def enviar_alerta(context: ContextTypes.DEFAULT_TYPE, tipo: str, nombre: str, cantidad: float):
    emoji = {"largo": "⬆️", "corto": "⬇️", "venta": "💸"}.get(tipo, "")
    mensaje = f"{emoji} {nombre} - ${cantidad:,.2f}"
    await context.bot.send_message(chat_id=CHANNEL_ID, text=mensaje)

def obtener_alertas_reales():
    headers = {"Authorization": f"Bearer {WHALE_ALERT_API_KEY}"}
    try:
        response = requests.get("https://api.xrpwhales.com/alerts", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener alertas: {e}")
        return []

async def revisar_alertas(context: ContextTypes.DEFAULT_TYPE):
    global alert_count
    if alert_count >= alert_limit:
        return

    alertas = obtener_alertas_reales()
    for alerta in alertas:
        nombre = alerta.get("name")
        cantidad = alerta.get("amount")
        tipo = alerta.get("type")
        if nombre in ballenas_seguidas:
            await enviar_alerta(context, tipo, nombre, cantidad)
            alert_count += 1
            if alert_count >= alert_limit:
                break

# ----------------------------
# COMANDOS DE ADMIN
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        cantidad = float(context.args[1])
        ballenas_seguidas[nombre] = cantidad
        await update.message.reply_text(f"✅ Ballena {nombre} agregada con ${cantidad:,.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add <nombre> <cantidad>")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nombre = context.args[0]
        if nombre in ballenas_seguidas:
            del ballenas_seguidas[nombre]
            await update.message.reply_text(f"❌ Ballena {nombre} eliminada")
        else:
            await update.message.reply_text(f"No existe la ballena {nombre}")
    except IndexError:
        await update.message.reply_text("Uso: /del <nombre>")

async def list_ballenas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ballenas_seguidas:
        lista = "\n".join([f"{nombre} - ${cantidad:,.2f}" for nombre, cantidad in ballenas_seguidas.items()])
        await update.message.reply_text(f"Ballenas seguidas:\n{lista}")
    else:
        await update.message.reply_text("No hay ballenas en seguimiento.")

async def limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alert_limit
    try:
        alert_limit = int(context.args[0])
        await update.message.reply_text(f"✅ Límite de alertas establecido a {alert_limit}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /limit <numero>")

# ----------------------------
# MENSAJES DE TEXTO
async def mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()
    if "hola" in texto:
        await update.message.reply_text(
            "¡Hola! 👋\nPara ver las ballenas que seguimos, escribe: ballenas"
        )
    elif "ballenas" in texto:
        if ballenas_seguidas:
            lista = "\n".join([f"{nombre} - ${cantidad:,.2f}" for nombre, cantidad in ballenas_seguidas.items()])
            await update.message.reply_text(f"Ballenas seguidas:\n{lista}")
        else:
            await update.message.reply_text("No hay ballenas en seguimiento.")

# ----------------------------
# FUNCION PRINCIPAL
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de comandos
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("del", delete))
    app.add_handler(CommandHandler("list", list_ballenas))
    app.add_handler(CommandHandler("limit", limit))

    # Handler de mensajes de texto
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensajes))

    # Programar revisión de alertas cada 30 segundos con pytz.UTC
    scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    scheduler.add_job(lambda: asyncio.create_task(revisar_alertas(app.bot)), 'interval', seconds=30)
    scheduler.start()

    print("Bot activo con alertas reales...")
    await app.run_polling()

# ----------------------------
if __name__ == "__main__":
    asyncio.run(main())
