import json
import os
import asyncio
import requests
from datetime import datetime
from telegram import Bot

# Configuración desde .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID", 0))
bot = Bot(token=BOT_TOKEN)

# Archivos JSON
WHALES_FILE = "whales.json"
LAST_TX_FILE = "last_tx.json"

# Cargar whales.json
if not os.path.exists(WHALES_FILE):
    with open(WHALES_FILE, "w") as f:
        json.dump([], f)

with open(WHALES_FILE, "r") as f:
    whales = json.load(f)  # Lista de ballenas

# Cargar last_tx.json
if not os.path.exists(LAST_TX_FILE):
    with open(LAST_TX_FILE, "w") as f:
        json.dump({}, f)

with open(LAST_TX_FILE, "r") as f:
    last_tx = json.load(f)


def get_xrp_usd():
    """Consulta el precio de XRP en USD desde Coingecko"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd")
        return r.json()["ripple"]["usd"]
    except Exception:
        return 0


async def check_whale_alert():
    """Revisar Whale Alert y mandar notificaciones con emojis"""
    url = "https://api.whale-alert.io/v1/transactions?api_key=YOUR_WHALE_ALERT_API_KEY&currency=xrp&min_value=100000"
    try:
        response = requests.get(url).json()
    except Exception as e:
        print("Error Whale Alert:", e)
        return

    transactions = response.get("transactions", [])

    xrp_usd = get_xrp_usd()

    for tx in transactions:
        tx_id = tx.get("id")
        if tx_id in last_tx:
            continue  # Ya notificado

        from_addr = tx.get("from")
        to_addr = tx.get("to")
        amount_xrp = tx.get("amount", 0)
        amount_usd = amount_xrp * xrp_usd

        # Determinar tipo de operación
        emoji = "💰" if tx.get("type") == "transfer" else "🔄"
        direction = "📈 LARGO" if to_addr in [w.get("address") for w in whales] else "📉 CORTO"

        # Comprobar si la dirección está en whales.json
        for whale in whales:
            if from_addr == whale.get("address") or to_addr == whale.get("address"):
                min_usd = whale.get("min_usd", 0)
                if amount_usd >= min_usd:
                    message = (
                        f"{emoji} *Ballena detectada*\n"
                        f"{direction}\n"
                        f"De: `{from_addr}`\n"
                        f"A: `{to_addr}`\n"
                        f"Monto: {amount_xrp:,.2f} XRP ≈ ${amount_usd:,.2f}\n"
                        f"Fecha: {datetime.fromtimestamp(tx.get('timestamp'))}"
                    )
                    try:
                        bot.send_message(chat_id=USER_ID, text=message, parse_mode="Markdown")
                    except Exception as e:
                        print("Error Telegram:", e)

        # Guardar última transacción
        last_tx[tx_id] = tx.get("timestamp")

    # Guardar last_tx.json
    with open(LAST_TX_FILE, "w") as f:
        json.dump(last_tx, f, indent=2)


async def main():
    while True:
        await check_whale_alert()
        await asyncio.sleep(60)  # Revisa cada minuto


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
