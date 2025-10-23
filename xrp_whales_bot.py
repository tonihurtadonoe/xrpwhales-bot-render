import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
import requests
import asyncio

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Asegúrate de poner tu token aquí en Render
TRACKED_FILE = "tracked_whales.json"
CHECK_INTERVAL = 60  # Segundos entre comprobaciones

# --- HELPER: cargar whales ---
if os.path.exists(TRACKED_FILE):
    with open(TRACKED_FILE, "r") as f:
        tracked_whales = json.load(f)
else:
    tracked_whales = []

# --- HELPER: guardar whales ---
def save_whales():
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked_whales, f)

# --- COMANDOS ---

# /add <direccion>
async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /add <direccion>")
        return
    address = context.args[0]
    if address in tracked_whales:
        await update.message.reply_text("Esta dirección ya está en seguimiento.")
    else:
        tracked_whales.append(address)
        save_whales()
        await update.message.reply_text(f"Dirección {address} añadida.")

# /delete <direccion>
async def delete_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /delete <direccion>")
        return
    address = context.args[0]
    if address in tracked_whales:
        tracked_whales.remove(address)
        save_whales()
        await update.message.reply_text(f"Dirección {address} eliminada.")
    else:
        await update.message.reply_text("La dirección no está en seguimiento.")

# /list
async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tracked_whales:
        await update.message.reply_text("No hay direcciones en seguimiento.")
    else:
        message = "Direcciones en seguimiento:\n" + "\n".join(tracked_whales)
        await update.message.reply_text(message)

# /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tracking {len(tracked_whales)} whales.")

# --- FUNCION DE ALERTAS (simulada) ---
async def check_whales(context: CallbackContext):
    for address in tracked_whales:
        # Aquí iría la lógica real para comprobar transacciones en XRP
        # Ejemplo: response = requests.get(f"https://api.xrpscan.com/api/account/{address}/transactions")
        # Por ahora simulamos
        print(f"Comprobando {address}...")  

# --- CONFIG BOT ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Comandos
app.add_handler(CommandHandler("add", add_whale))
app.add_handler(CommandHandler("delete", delete_whale))
app.add_handler(CommandHandler("list", list_whales))
app.add_handler(CommandHandler("status", status))

# Tarea periódica de comprobación
async def periodic_check():
    while True:
        await check_whales(None)
        await asyncio.sleep(CHECK_INTERVAL)

app.job_queue.run_repeating(check_whales, interval=CHECK_INTERVAL, first=10)

# --- RUN ---
if __name__ == "__main__":
    print("Bot iniciado...")
    asyncio.get_event_loop().run_until_complete(app.run_polling())
