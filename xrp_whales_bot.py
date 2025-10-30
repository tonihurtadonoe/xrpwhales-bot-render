import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    JobQueue
)

# ---------- VARIABLES DE ENTORNO ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en variables de entorno")
CHAT_ID = int(CHAT_ID)

# ---------- CONFIGURACIONES ----------
MIN_TRANSACTION = 100  # valor mínimo por defecto
WALLETS = {}  # dict wallet: nombre

# ---------- FUNCIONES ADMIN ----------
async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        await update.message.reply_text("❌ No tienes permiso para añadir ballenas.")
        return
    try:
        wallet, name = context.args[0], context.args[1]
    except IndexError:
        await update.message.reply_text("⚠️ Usa: /add WALLET NOMBRE")
        return
    if wallet not in WALLETS:
        WALLETS[wallet] = name
        await update.message.reply_text(f"✅ Wallet añadida: {wallet} ({name})")
    else:
        await update.message.reply_text("⚠️ Wallet ya estaba añadida.")

async def del_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID:
        await update.message.reply_text("❌ No tienes permiso para borrar ballenas.")
        return
    try:
        wallet = context.args[0]
    except IndexError:
        await update.message.reply_text("⚠️ Usa: /dell WALLET")
        return
    if wallet in WALLETS:
        name = WALLETS.pop(wallet)
        await update.message.reply_text(f"🗑️ Wallet borrada: {wallet} ({name})")
    else:
        await update.message.reply_text("⚠️ Wallet no encontrada.")

async def set_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MIN_TRANSACTION
    if update.effective_user.id != CHAT_ID:
        await update.message.reply_text("❌ No tienes permiso para cambiar el límite.")
        return
    try:
        value = float(context.args[0])
        MIN_TRANSACTION = value
        await update.message.reply_text(f"✅ Límite mínimo actualizado a {MIN_TRANSACTION}")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Debes escribir un número válido.")

# ---------- FUNCIONES NORMALES ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    greeting = "Hola" if lang.startswith("es") else "Hi"
    await update.message.reply_text(f"{greeting} 🐋! Soy tu bot de alertas XRP. Usa /ballenas para ver todas las ballenas vigiladas.")

async def show_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WALLETS:
        await update.message.reply_text("No hay ballenas añadidas.")
        return
    msg = "🐋 Lista de ballenas vigiladas:\n"
    for w, n in WALLETS.items():
        msg += f"- {w} ({n})\n"
    await update.message.reply_text(msg)

# ---------- ALERTAS ----------
async def alert_buy(wallet, amount, context: ContextTypes.DEFAULT_TYPE):
    if amount >= MIN_TRANSACTION:
        await context.bot.send_message(
            CHAT_ID, f"⬆️🟢 Compra detectada!\nWallet: {wallet} ({WALLETS.get(wallet,'')})\nMonto: {amount}"
        )

async def alert_sell(wallet, amount, context: ContextTypes.DEFAULT_TYPE):
    if amount >= MIN_TRANSACTION:
        await context.bot.send_message(
            CHAT_ID, f"⬇️🔴 Venta detectada!\nWallet: {wallet} ({WALLETS.get(wallet,'')})\nMonto: {amount}"
        )

async def alert_transfer(wallet, amount, context: ContextTypes.DEFAULT_TYPE):
    if amount >= MIN_TRANSACTION:
        await context.bot.send_message(
            CHAT_ID, f"💸 Transferencia detectada!\nWallet: {wallet} ({WALLETS.get(wallet,'')})\nMonto: {amount}"
        )

# ---------- JOB EJEMPLO (MONITOREO XRP) ----------
async def check_wallets(context: ContextTypes.DEFAULT_TYPE):
    # Aquí va tu lógica real de monitor XRP
    for wallet in WALLETS:
        # Simulación de alertas
        await alert_buy(wallet, 150, context)
        await alert_sell(wallet, 200, context)
        await alert_transfer(wallet, 120, context)

# ---------- MAIN ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos de administración (solo tú)
    app.add_handler(CommandHandler("add", add_wallet))
    app.add_handler(CommandHandler("dell", del_wallet))
    app.add_handler(CommandHandler("min", set_min))

    # Comandos normales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ballenas", show_wallets))

    # JobQueue sin timezone
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(check_wallets, interval=60, first=5)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
