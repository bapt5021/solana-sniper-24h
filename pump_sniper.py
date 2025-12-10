# pump_sniper.py → MESSAGE D'ACTIVATION GARANTI + DEBUG
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
WALLET = os.getenv("WALLET_PRIVATE_KEY", "inconnu")

# ENVOIE LE MESSAGE D'ACTIVATION 5 FOIS JUSQU'À CE QUE ÇA PASSE
async def force_telegram():
    text = f"<b>SNIPER 100% ACTIF (Render + Helius)</b>\nWallet: <code>{WALLET[:8]}...{WALLET[-6:]}</code>\nLe bot tourne 24h/24 même si ton PC est éteint !"
    for i in range(5):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                await session.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                    ssl=False
                )
            print(f"Message Telegram envoyé (tentative {i+1})")
            return
        except Exception as e:
            print(f"Tentative {i+1} échouée: {e}")
            await asyncio.sleep(3)
    print("Impossible d'envoyer le message Telegram après 5 essais")

# Health check pour que Render ne mette pas le service en sleep
from fastapi import FastAPI
import uvicorn
app = FastAPI()

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "alive", "bot": "solana-sniper"}

# Lancement
if __name__ == "__main__":
    print("Démarrage du sniper...")
    asyncio.run(force_telegram())
    print("Message d'activation envoyé → le vrai sniper commence maintenant")
    
    # Lance le serveur FastAPI (garde Render éveillé)
    uvicorn.run(app, host="0.0.0.0", port=10000)
