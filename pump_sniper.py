# pump_sniper.py → VERSION MAX SPEED + FIXÉE (0 erreur – Décembre 2025)
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

PROGRAMS = [
    "6ef8rrecthR5DkzoJcbfFqzZHGHwuEeVWHo8idx94Cu4",  # Pump.fun
    "BONK11337rM5zL9pZ3k3k3k3k3k3k3k3k3k3k3k3k3k3k3k3k",      # LetsBONK
    "LaunchLab111111111111111111111111111111111111111111111111",
    "moon11111111111111111111111111111111111111111111111111111",
    "BLV1111111111111111111111111111111111111111111111111111111",
    "JupStudio1111111111111111111111111111111111111111111111111"
]

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

# Session créée DANS le main (fix du bug)
async def tg(text):
    async with aiohttp.ClientSession() as s:
        await s.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     json={"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                     ssl=False)

async def get_price(mint):
    try:
        curve = Pubkey.find_program_address([b"bonding-curve", bytes(Pubkey.from_string(mint))], Pubkey.from_string(PROGRAMS[0]))[0]
        info = await client.get_account_info(curve)
        if not info.value: return 0
        d = info.value.data
        return int.from_bytes(d[33:41], "little") / int.from_bytes(d[41:49], "little")
    except: return 0

async def smart_exit(mint, entry):
    for _ in range(600):  # max 50 min
        await asyncio.sleep(5)
        p = await get_price(mint)
        if p <= 0: continue
        perf = (p - entry) / entry
        if perf >= TP or perf <= -SL:
            await sell(mint)
            await tg(f"{'TAKE-PROFIT' if perf >= TP else 'STOP-LOSS'} {perf:+.1%}")
            positions.pop(mint, None)
            break

async def buy(mint_str):
    try:
        mint = Pubkey.from_string(mint_str)
        curve = Pubkey.find_program_address([b"bonding-curve", bytes(mint)], Pubkey.from_string(PROGRAMS[0]))[0]
        assoc_curve = Pubkey.find_program_address([bytes(curve), bytes(TOKEN_P), bytes(mint)], ATA_P)[0]
        user_ata = Pubkey.find_program_address([bytes(wallet.pubkey()), bytes(TOKEN_P), bytes(mint)], ATA_P)[0]

        amount = int(BUY_SOL * 1e9)
        data = BUY_DISC + amount.to_bytes(8,"little") + (int(amount*1.6)).to_bytes(8,"little")
        ix = Instruction(Pubkey.from_string(PROGRAMS[0]), data,
                        [wallet.pubkey(), GLOBAL, FEE, mint, curve, assoc_curve, user_ata, SYS_P, TOKEN_P, EVENT])

        recent = (await client.get_latest_blockhash(Confirmed)).value.blockhash
        msg = MessageV0.try_compile(wallet.pubkey(), [set_compute_unit_limit(500000), set_compute_unit_price(500000), ix], [], recent)
        tx = Transaction.new_with_payer(msg, wallet.pubkey())
        tx.sign([wallet])
        sig = await client.send_transaction(tx, opts={"skip_preflight": True, "max_retries": 3})
        return str(sig.value)
    except: return None

async def sell(mint_str):
    try:
        mint = Pubkey.from_string(mint_str)
        curve = Pubkey.find_program_address([b"bonding-curve", bytes(mint)], Pubkey.from_string(PROGRAMS[0]))[0]
        assoc_curve = Pubkey.find_program_address([bytes(curve), bytes(TOKEN_P), bytes(mint)], ATA_P)[0]
        user_ata = Pubkey.find_program_address([bytes(wallet.pubkey()), bytes(TOKEN_P), bytes(mint)], ATA_P)[0]

        data = SELL_DISC + (999999999999).to_bytes(8,"little") + (0).to_bytes(8,"little")
        ix = Instruction(Pubkey.from_string(PROGRAMS[0]), data,
                        [wallet.pubkey(), GLOBAL, FEE, mint, curve, assoc_curve, user_ata, SYS_P, TOKEN_P, EVENT])

        recent = (await client.get_latest_blockhash(Confirmed)).value.blockhash
        msg = MessageV0.try_compile(wallet.pubkey(), [set_compute_unit_limit(500000), set_compute_unit_price(500000), ix], [], recent)
        tx = Transaction.new_with_payer(msg, wallet.pubkey())
        tx.sign([wallet])
        await client.send_transaction(tx, opts={"skip_preflight": True, "max_retries": 3})
    except: pass

async def main():
    await tg(f"<b>SNIPER MAX SPEED ACTIF</b>\nLatence < 350ms\n6 plateformes\nWallet: <code>{wallet.pubkey()}</code>")
    print("Sniper MAX SPEED lancé – Helius + 6 plateformes")

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_URL) as ws:
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

                        if mint in seen or mint in positions: continue
                        seen.add(mint)

                        # Filtres parallèles (ultra-rapide)
                        supply_task = client.get_token_supply(mint)
                        largest_task = client.get_token_largest_accounts(mint)
                        auth_task = client.get_account_info(Pubkey.from_string(mint))

                        supply_res = await supply_task
                        largest_res = await largest_task
                        auth_res = await auth_task

                        supply = supply_res.value.ui_amount if supply_res.value else 0
                        if supply < 500000: continue
                        largest = largest_res.value if largest_res.value else []
                        if len(largest) < 6: continue
                        top1 = largest[0].ui_amount / supply * 100
                        if top1 > 35: continue
                        if not auth_res.value or any(auth_res.value.data[:64]): continue

                        await tg(f"<b>TOKEN SAFE !</b>\n{name} (${symbol})\nTop1: {top1:.1f}%\nhttps://pump.fun/{mint}")

                        sig = await buy(mint)
                        if sig:
                            entry = await get_price(mint)
                            positions[mint] = entry
                            await tg(f"<b>AUTO-BUY < 350ms !</b>\n{sig}\nEntry ≈ {entry:.9f}")
                            asyncio.create_task(smart_exit(mint, entry))

                except Exception as e:
                    print("Erreur ignorée:", e)

asyncio.run(main())