import asyncio
import logging

import discord
from discord.ext import commands

import database as db
from config import DISCORD_TOKEN

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

EXTENSIONS = [
    "cogs.economy",
    "cogs.predictions",
    "cogs.voice_tracker",
]


@bot.event
async def on_ready():
    print(f"✅ Giriş yapıldı: {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"Slash komutları senkronize edilirken hata oluştu: {e}")


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN bulunamadı. Lütfen .env dosyasına DISCORD_TOKEN=... şeklinde ekleyin."
        )

    db.init_db()

    async with bot:
        for ext in EXTENSIONS:
            await bot.load_extension(ext)
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
