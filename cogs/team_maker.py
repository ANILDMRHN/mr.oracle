"""
cogs/team_maker.py
──────────────────
Strikers Club için karma takım kurma modülü.

Akış:
  1. /takim-kur komutuyla liderler (isteğe bağlı), oyuncular ve
     isteğe bağlı takım isimleri girilir.
  2. Bot oyuncuları (+ liderleri) karıştırır, ikiye böler.
  3. Lider varsa liderler kendi takımlarına sabitlenir; geri kalan
     oyuncular eşit (±1) dağıtılır.
  4. Sonuç güzel bir embed ile kanala gönderilir.
"""

import random

import discord
from discord import app_commands
from discord.ext import commands


def _split_teams(
    leader_a: discord.Member | None,
    leader_b: discord.Member | None,
    players: list[discord.Member],
) -> tuple[list[discord.Member], list[discord.Member]]:
    """
    Oyuncuları iki eşit takıma böler.
    Liderler kendi takımlarına sabitlenir ve pool'a dahil edilmez.
    """
    pool = [p for p in players if p not in (leader_a, leader_b)]
    random.shuffle(pool)

    # Lider sayısını hesaba katarak eşit bölme
    # Takım A'ya gidecek oyuncu sayısı
    total = len(pool) + (1 if leader_a else 0) + (1 if leader_b else 0)
    # Pool'dan A'ya kaç kişi gidecek?
    a_count = (total // 2) - (1 if leader_a else 0)
    a_count = max(0, a_count)

    team_a = ([leader_a] if leader_a else []) + pool[:a_count]
    team_b = ([leader_b] if leader_b else []) + pool[a_count:]

    return team_a, team_b


def _build_embed(
    team_a: list[discord.Member],
    team_b: list[discord.Member],
    name_a: str,
    name_b: str,
    leader_a: discord.Member | None,
    leader_b: discord.Member | None,
) -> discord.Embed:
    embed = discord.Embed(
        title="⚽ Strikers Club — Takımlar Hazır!",
        color=discord.Color.orange(),
    )

    def fmt_player(m: discord.Member, leader: discord.Member | None) -> str:
        return f"👑 {m.mention}" if m == leader else f"• {m.mention}"

    a_lines = "\n".join(fmt_player(m, leader_a) for m in team_a) or "_(boş)_"
    b_lines = "\n".join(fmt_player(m, leader_b) for m in team_b) or "_(boş)_"

    embed.add_field(
        name=f"🔵 {name_a}  ({len(team_a)} oyuncu)",
        value=a_lines,
        inline=True,
    )
    embed.add_field(
        name=f"🔴 {name_b}  ({len(team_b)} oyuncu)",
        value=b_lines,
        inline=True,
    )

    embed.set_footer(text="İyi oyunlar! ⚽")
    return embed


class TeamMaker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="takim-kur",
        description="Oyuncuları rastgele iki takıma böler (Strikers Club)",
    )
    @app_commands.describe(
        oyuncular="Takımlara dahil edilecek oyuncular (boşlukla ayırarak etiketle, ör: @Ali @Veli @Kemal)",
        lider_a="A takımının lideri (isteğe bağlı)",
        lider_b="B takımının lideri (isteğe bağlı)",
        takim_adi_a="A takımının adı (isteğe bağlı, varsayılan: Takım A)",
        takim_adi_b="B takımının adı (isteğe bağlı, varsayılan: Takım B)",
    )
    async def takim_kur(
        self,
        interaction: discord.Interaction,
        oyuncular: str,
        lider_a: discord.Member = None,
        lider_b: discord.Member = None,
        takim_adi_a: str = "Takım A",
        takim_adi_b: str = "Takım B",
    ):
        await interaction.response.defer()

        # Oyuncular parametresini mention ID'lerine dönüştür
        # Discord slash command mention dizesi: <@123456789>
        import re
        mention_ids = re.findall(r"<@!?(\d+)>", oyuncular)

        if not mention_ids:
            await interaction.followup.send(
                "❌ Hiç oyuncu etiketlemedin. Oyuncuları `@kullanici` şeklinde yaz.",
                ephemeral=True,
            )
            return

        # Member objelerine çevir (bulunamayanları atla)
        members: list[discord.Member] = []
        for uid in mention_ids:
            member = interaction.guild.get_member(int(uid))
            if member and not member.bot:
                if member not in members:
                    members.append(member)

        # Liderleri de listeye ekle (henüz yoklarsa)
        for leader in (lider_a, lider_b):
            if leader and not leader.bot and leader not in members:
                members.append(leader)

        if len(members) < 2:
            await interaction.followup.send(
                "❌ En az 2 oyuncu gerekli.",
                ephemeral=True,
            )
            return

        # Lider validasyonu
        if lider_a and lider_b and lider_a == lider_b:
            await interaction.followup.send(
                "❌ Her iki takımın lideri aynı kişi olamaz.",
                ephemeral=True,
            )
            return

        team_a, team_b = _split_teams(lider_a, lider_b, members)
        embed = _build_embed(team_a, team_b, takim_adi_a, takim_adi_b, lider_a, lider_b)

        # Yeniden karıştır butonu
        view = RemixView(
            original_interaction=interaction,
            members=members,
            lider_a=lider_a,
            lider_b=lider_b,
            takim_adi_a=takim_adi_a,
            takim_adi_b=takim_adi_b,
        )

        await interaction.followup.send(embed=embed, view=view)


class RemixView(discord.ui.View):
    """Takımları yeniden karıştırma butonu."""

    def __init__(
        self,
        original_interaction: discord.Interaction,
        members: list[discord.Member],
        lider_a: discord.Member | None,
        lider_b: discord.Member | None,
        takim_adi_a: str,
        takim_adi_b: str,
    ):
        super().__init__(timeout=300)  # 5 dakika sonra buton pasifleşir
        self.original_interaction = original_interaction
        self.members = members
        self.lider_a = lider_a
        self.lider_b = lider_b
        self.takim_adi_a = takim_adi_a
        self.takim_adi_b = takim_adi_b

    @discord.ui.button(label="🔀 Yeniden Karıştır", style=discord.ButtonStyle.secondary)
    async def remix(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Sadece komutu çalıştıran veya adminler kullanabilsin
        is_admin = interaction.user.guild_permissions.administrator
        is_requester = interaction.user == self.original_interaction.user

        if not (is_admin or is_requester):
            await interaction.response.send_message(
                "❌ Yalnızca komutu başlatan kişi veya adminler yeniden karıştırabilir.",
                ephemeral=True,
            )
            return

        team_a, team_b = _split_teams(self.lider_a, self.lider_b, self.members)
        embed = _build_embed(
            team_a, team_b,
            self.takim_adi_a, self.takim_adi_b,
            self.lider_a, self.lider_b,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Timeout olunca butonu devre dışı bırak
        for item in self.children:
            item.disabled = True
        try:
            await self.original_interaction.edit_original_response(view=self)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamMaker(bot))
