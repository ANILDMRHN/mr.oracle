import discord
from discord.ext import commands, tasks

import database as db
from config import (
    VOICE_POINTS_PER_INTERVAL,
    VOICE_INTERVAL_MINUTES,
    REQUIRE_MULTIPLE_USERS,
    CURRENCY_NAME,
)


class VoiceTracker(commands.Cog):
    """Sesli kanalda bulunan kullanıcılara periyodik olarak puan verir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.point_loop.change_interval(minutes=VOICE_INTERVAL_MINUTES)
        self.point_loop.start()

    def cog_unload(self):
        self.point_loop.cancel()

    @tasks.loop(minutes=VOICE_INTERVAL_MINUTES)
    async def point_loop(self):
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                # AFK kanalını sayma
                if guild.afk_channel and voice_channel.id == guild.afk_channel.id:
                    continue

                members = [m for m in voice_channel.members if not m.bot]

                if REQUIRE_MULTIPLE_USERS and len(members) < 2:
                    continue

                for member in members:
                    # Kendi mikrofonunu kapatıp sağırsa (deafened) ve
                    # ayrıca AFK işaretliyse puan verme
                    voice_state = member.voice
                    if voice_state and voice_state.afk:
                        continue

                    db.change_balance(guild.id, member.id, VOICE_POINTS_PER_INTERVAL)

    @point_loop.before_loop
    async def before_point_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Şu an basit zaman aralıklı sistem kullanıyoruz, bu listener
        # ileride detaylı süre takibi eklemek istersen kullanılabilir.
        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceTracker(bot))
