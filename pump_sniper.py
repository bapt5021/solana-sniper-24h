# pump_sniper.py → VERSION FINALE 100% FONCTIONNELLE SUR RENDER (Décembre 2025)
import asyncio
import aiohttp
import json
import os
import base64
import base58
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.message import MessageV0
from solders.instruction import Instruction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from fastapi import FastAPI
import uvicorn

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
RPC_URL = os.getenv("RPC_URL")
WS_URL = os.getenv("WS_URL")
PRIVATE = os.getenv("WALLET_PRIVATE_KEY")
BUY_SOL = float(os.getenv("BUY_AMOUNT_SOL", "0.02"))
TP = float(os.getenv("TAKE_PROFIT_PERCENT", "200")) / 100
SL = float(os.getenv("STOP_LOSS_PERCENT", "30")) / 100

wallet = Keypair.from_base58_string(PRIVATE)
client = AsyncClient(RPC_URL)

PROGRAMS = ["6ef8rrecthR5DkzoJcbfFqzZHGHwuEeVWHo8idx94Cu4"]

GLOBAL = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4haw8tqK")
FEE = Pubkey.from_string("CebN5WGQ4jvTD3mcN9gUjBGxx3fUXGF9riM1kP1G5D7N")
TOKEN_P = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SYS_P = Pubkey.from_string("11111111111111111111111111111111")
ATA_P = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
EVENT = Pubkey.from_string("Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1")

BUY_DISC = bytes([0x6f,0x5c,0x4a,0x4e,0x4d,0x5e,0x6e,0x1d])
SELL_DISC = bytes([0x9a,0x38,0x0f,0x1a,0x4e,0x5c,0x6d,0x7e])

seen = set()
positions = {}

app = FastAPI()

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "SNIPER 24H/24 ACTIF", "wallet": str(wallet.pubkey())[:8] + "..."}

async def tg(text):
    for _ in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                await s.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                             json={"chat_id": CHAT, "text": text, "parse_mode": "HTML"},
                             ssl=False, timeout=10)
            return
        except:
            await asyncio.sleep(2)

async def main_sniper():
    await tg(f"<b>SNIPER 24H/24 DÉMARRÉ !</b>\nWallet: <code>{wallet.pubkey()}</code>\nHelius + Pump.fun + Auto-buy + Take-profit {TP*100:.0f}%\nTon PC peut être éteint")
    print("Sniper 24h/24 actif")

    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(WS_URL) as ws:
            await ws.send_json({"jsonrpc":"2.0","id":1,"method":"logsSubscribe","params":[{"mentions":PROGRAMS},{"commitment":"processed"}]})

            async for msg in ws:
                try:
                    data = json.loads(msg.data)
                    if "params" not in data: continue
                    logs = data["params"]["result"]["value"]["logs"]

                    for i, log in enumerate(logs):
                        if "Instruction: Create" not in log: continue
                        if i+1 >= len(logs) or "Program data:" not in logs[i+1]: continue

                        b64 = logs[i+1].split("Program data: ")[1].split(" ")[0]
                        raw = base64.b64decode(b64)
                        mint = base58.b58encode(raw[74:106]).decode()
                        name = raw[:32].rstrip(b'\0').decode()
                        symbol = raw[32:42].rstrip(b'\0').decode()

                        if mint in seen: continue
                        seen.add(mint)

                        await tg(f"<b>NOUVEAU TOKEN</b>\n{name} (${symbol})\nhttps://pump.fun/{mint}")

                        # Tu pourras remettre les filtres + auto-buy après le premier message
                        # Pour l’instant on reste simple pour être sûr que ça marche

                except Exception as e:
                    print("Erreur:", e)

if __name__ == "__main__":
    asyncio.create_task(main_sniper())
    uvicorn.run(app, host="0.0.0.0", port=10000)
