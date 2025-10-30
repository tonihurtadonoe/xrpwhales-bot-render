import asyncio
from pytz import timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "TU_TOKEN_AQUI"

# --- Datos de ejemplo para ballenas ---
ballenas = {
    "Whale1": {"nombre": "Alice", "limite": 100000},
    "Whale2": {"nombre": "Bob", "limite": 50000},
}

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saludo al usuario."""
    await update.message.reply_text("¡Bienvenido al bot de XRP Whales! 😎\nEscribe 'ballenas' para ver la lista de ballenas.")

async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responder a mensajes de texto normales."""
    text = update.message.text.lower()
    if text in ["hola", "hi"]:
        await update.message.reply_text("¡Hola! Bienvenido al bot de XRP Whales 😎")
    elif text == "ballenas":
        msg = "Lista de Ballenas:\n"
        for key, info in ballenas.items():
            msg += f"{key}: {info['nombre']}, Límite: {info['limite']}\n"
        await update.message.reply_text(msg)

# --- Comandos para modificar ballenas ---

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Añadir una ballena: /add nombre limite"""
    try:
        nombre = context.args[0]
        limite = int(context.args[1])
        key = f"Whale{len(ballenas)+1}"
        ballenas[key] = {"nombre": nombre, "limite": limite}
        await update.message.reply_text(f"Ballena añadida: {key} -> {nombre}, Límite: {limite}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add <nombre> <limite>")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borrar ballena: /del Whale1"""
    try:
        key = context.args[0]
        if key in ballenas:
            del ballenas[key]
            await update.message.reply_text(f"Ballena {key} borrada.")
        else:
            await update.message.reply_text("No existe esa ballena.")
    except IndexError:
        await update.message.reply_text("Uso: /del <clave_ballena>")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Modificar límite: /limit Whale1 200000"""
    try:
        key = context.args[0]
        nuevo_limite = int(context.args[1])
        if key in ballenas:
            ballenas[key]["limite"] = nuevo_limite
            await update.message.reply_text(f"Límite de {key} actualizado a {nuevo_limite}")
        else:
            await update.message.reply_text("No existe esa ballena.")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /limit <clave_ballena> <nuevo_limite>")

# --- Main ---

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.job_queue.scheduler.timezone = timezone("America/New_York")

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.add_handler(CommandHandler("add", add_whale))
    app.add_handler(CommandHandler("del", del_whale))
    app.add_handler(CommandHandler("limit", set_limit))

    # Aquí irían tus jobs automáticos de alertas, si los tienes
    # Ejemplo: app.job_queue.run_repeating(job_func, interval=60, first=0)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
