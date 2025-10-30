import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Cargar config.json
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config.get("bot_token")
whales = config.get("whales", [])

# Función para guardar whales en config.json
def save_whales():
    config["whales"] = whales
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola! Soy tu bot de seguimiento de whales XRP. Escribe /help para ver comandos.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = (
        "Comandos disponibles:\n"
        "/ballenas - Listar todas las whales\n"
        "/add_whale <address> <min_usd> - Añadir una whale\n"
        "/del_whale <address> - Borrar una whale\n"
        "Responde 'hola' o 'hi' para un saludo!"
    )
    await update.message.reply_text(commands)

async def list_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not whales:
        await update.message.reply_text("No hay whales registradas.")
        return
    message = "Lista de whales:\n"
    for w in whales:
        message += f"- {w['address']} (mínimo USD {w['min_usd']})\n"
    await update.message.reply_text(message)

async def add_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        address = context.args[0]
        min_usd = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /add_whale <address> <min_usd>")
        return

    # Verificar si ya existe
    for w in whales:
        if w["address"] == address:
            await update.message.reply_text("La whale ya está registrada.")
            return

    whales.append({"address": address, "min_usd": min_usd})
    save_whales()
    await update.message.reply_text(f"Whale {address} añadida con mínimo USD {min_usd}.")

async def del_whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        address = context.args[0]
    except IndexError:
        await update.message.reply_text("Uso: /del_whale <address>")
        return

    for w in whales:
        if w["address"] == address:
            whales.remove(w)
            save_whales()
            await update.message.reply_text(f"Whale {address} eliminada.")
            return
    await update.message.reply_text("No se encontró la whale.")

# Mensajes generales
async def respond_greetings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ["hola", "hi"]:
        await update.message.reply_text("¡Hola! 👋")

# Función para reportar acción de whales
async def report_action(address, action, usd_amount, context: ContextTypes.DEFAULT_TYPE):
    emoji = ""
    if action.lower() == "compra":
        emoji = "⬆️"
    elif action.lower() == "venta":
        emoji = "⬇️"
    elif action.lower() == "transferencia":
        emoji = "💸"

    message = f"{emoji} Whale {address} realizó {action} de ${usd_amount}"
    # Para testing local, imprime. Cambiar a context.bot.send_message si quieres enviar al chat
    print(message)

# Main
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ballenas", list_whales))
    app.add_handler(CommandHandler("add_whale", add_whale))
    app.add_handler(CommandHandler("del_whale", del_whale))

    # Mensajes generales
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond_greetings))

    print("Bot corriendo...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
