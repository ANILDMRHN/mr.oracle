import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import CURRENCY_NAME, CURRENCY_EMOJI


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bakiye", description="Kendi veya başka birinin puan bakiyesini gösterir")
    @app_commands.describe(kullanici="Bakiyesi gösterilecek kullanıcı (boş bırakılırsa kendin)")
    async def bakiye(self, interaction: discord.Interaction, kullanici: discord.Member = None):
        hedef = kullanici or interaction.user
        bakiye = db.get_balance(interaction.guild_id, hedef.id)

        embed = discord.Embed(
            title="Bakiye",
            description=f"{hedef.mention} → **{bakiye} {CURRENCY_NAME}** {CURRENCY_EMOJI}",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="liderlik", description="En çok puana sahip kullanıcıları gösterir")
    async def liderlik(self, interaction: discord.Interaction):
        rows = db.get_leaderboard(interaction.guild_id, limit=10)

        if not rows:
            await interaction.response.send_message("Henüz kimsenin puanı yok.")
            return

        lines = []
        for i, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            isim = member.display_name if member else f"Kullanıcı ({row['user_id']})"
            lines.append(f"**{i}.** {isim} — {row['balance']} {CURRENCY_NAME}")

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} Liderlik Tablosu",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="puan-ver", description="[Admin] Bir kullanıcıya puan ekler")
    @app_commands.describe(kullanici="Puan eklenecek kullanıcı", miktar="Eklenecek puan miktarı")
    @app_commands.checks.has_permissions(administrator=True)
    async def puan_ver(self, interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
        if miktar <= 0:
            await interaction.response.send_message("Miktar pozitif bir sayı olmalı.", ephemeral=True)
            return

        yeni_bakiye = db.change_balance(interaction.guild_id, kullanici.id, miktar)
        await interaction.response.send_message(
            f"✅ {kullanici.mention} kullanıcısına **{miktar} {CURRENCY_NAME}** eklendi. "
            f"Yeni bakiye: **{yeni_bakiye} {CURRENCY_NAME}**"
        )

    @app_commands.command(name="puan-al", description="[Admin] Bir kullanıcıdan puan alır")
    @app_commands.describe(kullanici="Puanı azaltılacak kullanıcı", miktar="Azaltılacak puan miktarı")
    @app_commands.checks.has_permissions(administrator=True)
    async def puan_al(self, interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
        if miktar <= 0:
            await interaction.response.send_message("Miktar pozitif bir sayı olmalı.", ephemeral=True)
            return

        yeni_bakiye = db.change_balance(interaction.guild_id, kullanici.id, -miktar)
        await interaction.response.send_message(
            f"✅ {kullanici.mention} kullanıcısından **{miktar} {CURRENCY_NAME}** alındı. "
            f"Yeni bakiye: **{yeni_bakiye} {CURRENCY_NAME}**"
        )

    @puan_ver.error
    @puan_al.error
    async def admin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Bu komutu kullanmak için yönetici (administrator) yetkisine sahip olmalısın.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
