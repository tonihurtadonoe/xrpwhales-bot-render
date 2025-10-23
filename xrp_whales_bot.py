#!/usr/bin/env python3
# main.py - XRP Whales bot (mejorado)
import os
import json
import asyncio
from typing import List, Dict, Any, Optional

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

# ---------------- CONFIG INICIAL (ENV) ---------------- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("USER_ID")  # opcional fallback
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY", "").strip()
EXCHANGE_ADDRESSES = set(
    a.strip() for a in os.getenv("EXCHANGE_ADDRESSES", "").split(",") if a.strip()
)

# Umbral por defecto (USD)
DEFAULT_MIN_USD = float(os.getenv("MIN_USD_VALUE", "5000000"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # segundos
HISTORY_N = int(os.getenv("HISTORY_N", "6"))  # cuántas txs guardar por dirección

# Archivos de persistencia
TRACKED_FILE = os.getenv("TRACKED_FILE", "tracked_whales.json")
CHATS_FILE = os.getenv("CHATS_FILE", "active_chats.json")
HISTORY_FILE = os.getenv("HISTORY_FILE", "tx_history.json")
CONFIG_FILE = os.getenv("CONFIG_FILE", "bot_config.json")

# Endpoints
XRPL_TX_ENDPOINT = "https://data.ripple.com/v2/accounts/{account}/transactions?type=Payment&result=tesSUCCESS&limit=10"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd"
WHALE_ALERT_TX_ENDPOINT = "https://api.whale-alert.io/v1/transactions"

# Validaciones
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN no definido. Añádelo al .env o a las env vars de Render.")

# ---------------- Estado en disco/memoria ---------------- #
def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

tracked_whales: List[str] = _load_json(TRACKED_FILE, [])
active_chats: List[int] = _load_json(CHATS_FILE, [])
tx_history: Dict[str, List[str]] = _load_json(HISTORY_FILE, {})  # addr -> [last_tx_hashes..]
config: Dict[str, Any] = _load_json(CONFIG_FILE, {"min_usd": DEFAULT_MIN_USD})

# Asegurar estructura
if not isinstance(tracked_whales, list):
    tracked_whales = []
if not isinstance(active_chats, list):
    active_chats = []
if not isinstance(tx_history, dict):
    tx_history = {}
if "min_usd" not in config:
    config["min_usd"] = DEFAULT_MIN_USD

# ---------------- Helpers persistencia ---------------- #
def save_tracked():
    with open(TRACKED_FILE, "w", encoding="utf-8") as f:
        json.dump(tracked_whales, f, ensure_ascii=False, indent=2)

def save_chats():
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(active_chats, f, ensure_ascii=False, indent=2)

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(tx_history, f, ensure_ascii=False, indent=2)

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ---------------- API helpers (async) ---------------- #
async def fetch_xrp_price_usd() -> float:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(COINGECKO_URL)
            r.raise_for_status()
            data = r.json()
            return float(data.get("ripple", {}).get("usd", 0.0))
    except Exception as e:
        print(f"[CoinGecko error] {e}")
        return 0.0

async def fetch_account_transactions(account: str) -> List[Dict[str, Any]]:
    url = XRPL_TX_ENDPOINT.format(account=account)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            return data.get("transactions", [])
    except Exception as e:
        print(f"[XRPL API] error fetching {account}: {e}")
        return []

async def whale_alert_lookup(tx_hash: str) -> Optional[Dict[str, Any]]:
    if not WHALE_ALERT_API_KEY:
        return None
    try:
        params = {"api_key": WHALE_ALERT_API_KEY, "txn_hash": tx_hash}
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(WHALE_ALERT_TX_ENDPOINT, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f"[WhaleAlert lookup error] {e}")
        return None

# ---------------- Parsing y clasificación ---------------- #
def parse_amount_xrp(tx_item: Dict[str, Any]) -> float:
    """Devuelve cantidad en XRP (float) a partir de tx_item de data.ripple.com"""
    try:
        tx = tx_item.get("tx", {})
        amt = tx.get("Amount")
        if isinstance(amt, dict):
            # issued currency
            return float(amt.get("value", 0.0))
        # drops string/int -> convertir a XRP
        return float(amt) / 1_000_000.0
    except Exception:
        return 0.0

def classify_tx(tx_item: Dict[str, Any], tracked_addr: str, whale_info: Optional[Dict[str, Any]]) -> str:
    """Devuelve texto de clasificación (Compra/Venta/Largo/Corto/Transferencia)"""
    tx = tx_item.get("tx", {})
    src = tx.get("Account")
    dst = tx.get("Destination")

    # Intentar usar whale_info (Whale Alert) si está disponible
    if whale_info:
        try:
            # whale_info puede tener "transactions" list; intentar deducir owner_type
            for t in whale_info.get("transactions", []):
                from_addr = t.get("from", {}).get("address")
                to_addr = t.get("to", {}).get("address")
                from_owner = t.get("from", {}).get("owner_type")
                to_owner = t.get("to", {}).get("owner_type")
                if to_addr == tracked_addr and to_owner == "exchange":
                    return "Compra (exchange → whale)"
                if from_addr == tracked_addr and from_owner == "exchange":
                    return "Venta (whale → exchange)"
        except Exception:
            pass

    # Fallback: usar lista EXCHANGE_ADDRESSES
    if src and dst:
        if dst == tracked_addr and src in EXCHANGE_ADDRESSES:
            return "Compra (exchange → whale)"
        if src == tracked_addr and dst in EXCHANGE_ADDRESSES:
            return "Venta (whale → exchange)"

    # Simple: si tracked recibe -> compra/entrada, si tracked envía -> venta/salida
    if dst == tracked_addr:
        return "Compra / Entrada"
    if src == tracked_addr:
        return "Venta / Salida"
    return "Transferencia"

def short_tx_summary(tx_item: Dict[str, Any]) -> str:
    tx = tx_item.get("tx", {})
    h = tx.get("hash", "")
    a = parse_amount_xrp(tx_item)
    return f"{h} · {a:,.6f} XRP"

# ---------------- Telegram broadcast helper ---------------- #
async def broadcast(app, text: str):
    if active_chats:
        for chat in list(active_chats):
            try:
                await app.bot.send_message(chat_id=chat, text=text, parse_mode="Markdown")
            except Exception as e:
                print(f"[broadcast] error sending to {chat}: {e}")
    elif DEFAULT_CHAT_ID:
        try:
            await app.bot.send_message(chat_id=DEFAULT_CHAT_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"[broadcast default] {e}")
    else:
        print("[broadcast] no chat to send")

# ---------------- JOB: revisión periódica ---------------- #
async def check_whales_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    min_usd = float(config.get("min_usd", DEFAULT_MIN_USD))
    if not tracked_whales:
        return
    xrp_price = await fetch_xrp_price_usd()
    if xrp_price <= 0:
        print("[check] CoinGecko price error, skipping cycle.")
        return

    for addr in list(tracked_whales):
        try:
            txs = await fetch_account_transactions(addr)
            for tx_item in txs:
                tx = tx_item.get("tx", {})
                tx_hash = tx.get("hash")
                if not tx_hash:
                    continue

                # evitar duplicados por historial
                seen_list = tx_history.get(addr, [])
                if tx_hash in seen_list:
                    continue

                amount_xrp = parse_amount_xrp(tx_item)
                usd_val = amount_xrp * xrp_price
                if usd_val < min_usd:
                    continue

                # intentar lookup whale alert para clasificar mejor
                whale_info = await whale_alert_lookup(tx_hash) if WHALE_ALERT_API_KEY else None
                classification = classify_tx(tx_item, addr, whale_info)

                src = tx.get("Account", "unknown")
                dst = tx.get("Destination", "unknown")
                amount_str = f"{amount_xrp:,.6f}".rstrip("0").rstrip(".")
                msg = (
                    f"🐋 *XRP Whale Alert*\n"
                    f"🔎 *Tipo:* {classification}\n"
                    f"🏷 *Wallet monitoreada:* `{addr}`\n"
                    f"💰 *Cantidad:* {amount_str} XRP (~${usd_val:,.0f})\n"
                    f"📤 *De:* `{src}`\n"
                    f"📥 *A:* `{dst}`\n"
                    f"🔗 [Ver tx en XRPSCAN](https://xrpscan.com/tx/{tx_hash})"
                )

                await broadcast(app, msg)

                # actualizar historial (push al frente, mantener N)
                lst = tx_history.get(addr, [])
                lst.insert(0, tx_hash)
                tx_history[addr] = lst[:HISTORY_N]
                save_history()
        except Exception as e:
            print(f"[check_whales] error processing {addr}: {e}")

# ---------------- Telegram command handlers ---------------- #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    if chat not in active_chats:
        active_chats.append(chat)
        save_chats()
    await update.message.reply_text("✅ Bot activado. Este chat recibirá alertas. Usa /help para comandos.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/add <address> - Añadir dirección XRP a seguimiento\n"
        "/delete <address> - Eliminar dirección\n"
        "/list - Listar direcciones seguidas\n"
        "/status - Ver estado del bot\n"
        "/setmin <usd> - Cambiar umbral USD (ej: /setmin 3000000)\n"
        "/help - Mostrar este mensaje\n"
    )
    await update.message.reply_text(help_text)

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /add <direccion>")
        return
    addr = context.args[0]
    if addr in tracked_whales:
        await update.message.reply_text("➡️ Dirección ya en seguimiento.")
        return
    tracked_whales.append(addr)
    save_tracked()
    await update.message.reply_text(f"✅ Añadida: `{addr}`", parse_mode="Markdown")

async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /delete <direccion>")
        return
    addr = context.args[0]
    if addr in tracked_whales:
        tracked_whales.remove(addr)
        save_tracked()
        tx_history.pop(addr, None)
        save_history()
        await update.message.reply_text(f"🗑️ Eliminada: `{addr}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Dirección no encontrada.")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tracked_whales:
        await update.message.reply_text("No hay direcciones en seguimiento.")
        return
    msg = "📜 *Direcciones en seguimiento:*\n" + "\n".join(f"`{a}`" for a in tracked_whales)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    xrp_price = await fetch_xrp_price_usd()
    lines = [
        f"🔍 Tracking: {len(tracked_whales)} addresses",
        f"💱 Precio XRP (USD): ${xrp_price:,.4f}",
        f"💵 Umbral actual: ${config.get('min_usd', DEFAULT_MIN_USD):,.0f}",
        f"⏱ Poll interval: {POLL_INTERVAL}s",
        f"🧾 Historial por addr: {HISTORY_N} txs",
        f"🌐 Exchanges (fallback): {len(EXCHANGE_ADDRESSES)}"
    ]
    # añadir última tx por address
    for addr in tracked_whales:
        last = tx_history.get(addr, [])
        if last:
            lines.append(f"- `{addr}` last: {last[0]}")
        else:
            lines.append(f"- `{addr}` last: none")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_setmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /setmin <usd> (ej: /setmin 5000000)")
        return
    try:
        v = float(context.args[0])
        config["min_usd"] = v
        save_config()
        await update.message.reply_text(f"✅ Umbral actualizado a ${v:,.0f}")
    except Exception:
        await update.message.reply_text("Valor inválido. Usa número entero (ej: 5000000).")

# ---------------- Startup ---------------- #
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("setmin", cmd_setmin))

    # job periódica
    app.job_queue.run_repeating(check_whales_job, interval=POLL_INTERVAL, first=10)

    print("🚀 XRP Whale Bot mejorado iniciado.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
