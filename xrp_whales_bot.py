import os
import json
import requests
import threading
import websocket
import time
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging

logging.basicConfig(level=logging.INFO)

# ===== TOKEN DESDE VARIABLE DE ENTORNO =====
TOKEN = os.environ.get("TOKEN")
CHAT_ID = None  # Se detectará automáticamente al primer uso
WHALES_FILE = "whales.json"

# ===== VERIFICAR TOKEN =====
if not TOKEN:
    print("❌ ERROR: No se encontró el TOKEN en las variables de entorno.")
    exit()
else:
    print("🔑 TOKEN recibido correctamente")

# ===== FUNCIONES BASE =====
def load_whales():
    try:
        with open(WHALES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_whales(data):
    with open(WHALES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def send_alert(message: str):
    if CHAT_ID:
        updater.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# ===== BOT COMMANDS =====
def start(update: Update, context: CallbackContext):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    update.message.reply_text(
        "👋 Bot activo. Usos
