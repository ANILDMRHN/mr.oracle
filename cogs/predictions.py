import math

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import CURRENCY_NAME, CURRENCY_EMOJI


def build_prediction_embed(prediction) -> discord.Embed:
    total_a, total_b = db.get_pool_totals(prediction["id"])
    total = total_a + total_b

    if prediction["status"] == "open":
        color = discord.Color.blurple()
        status_text = "🟢 Tahminler açık!"
    elif prediction["status"] == "closed":
        color = discord.Color.orange()
        status_text = "🟡 Tahminler kapandı, sonuç bekleniyor..."
    else:
        color = discord.Color.green()
        kazanan = prediction["option_a"] if prediction["winner"] == "A" else prediction["option_b"]
        status_text = f"🏁 Sonuçlandı! Kazanan: **{kazanan}**"

    embed = discord.Embed(
        title=f"📊 Öngörü #{prediction['id']}",
        description=f"**{prediction['question']}**\n\n{status_text}",
        color=color,
    )

    embed.add_field(
        name=f"🟩 {prediction['option_a']}",
        value=f"Toplam: **{total_a} {CURRENCY_NAME}**",
        inline=True,
    )
    embed.add_field(
        name=f"🟥 {prediction['option_b']}",
        value=f"Toplam: **{total_b} {CURRENCY_NAME}**",
        inline=True,
    )
    embed.add_field(name="💰 Toplam Havuz", value=f"{total} {CURRENCY_NAME}", inline=False)
    embed.set_footer(text="Bahis yapmak için aşağıdaki butonlara tıkla")

    return embed


class BetModal(discord.ui.Modal):
    def __init__(self, prediction_id: int, option: str, option_label: str, cog: "Predictions"):
        super().__init__(title=f"{option_label} için bahis")
        self.prediction_id = prediction_id
        self.option = option
        self.cog = cog

        self.amount_input = discord.ui.TextInput(
            label=f"Kaç {CURRENCY_NAME} puan tahmin yapmak istiyorsun?",
            placeholder="Örn: 50",
            required=True,
            max_length=10,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
        except ValueError:
            await interaction.response.send_message("Lütfen geçerli bir sayı gir.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("Tahmin miktarı pozitif olmalı.", ephemeral=True)
            return

        prediction = db.get_prediction(self.prediction_id)
        if not prediction or prediction["status"] != "open":
            await interaction.response.send_message("Bu öngörü artık tahmine açık değil.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        user_id = interaction.user.id
        balance = db.get_balance(guild_id, user_id)

        existing_bet = db.get_user_bet(self.prediction_id, user_id)
        if existing_bet and existing_bet["option"] != self.option:
            secenek_adi = prediction["option_a"] if existing_bet["option"] == "A" else prediction["option_b"]
            await interaction.response.send_message(
                f"❌ Bu öngörüde zaten **{secenek_adi}** seçeneğine bahis yaptın. "
                f"Aynı öngörüde farklı seçeneklere tahmin yapamazsın.",
                ephemeral=True,
            )
            return

        if amount > balance:
            await interaction.response.send_message(
                f"❌ Yeterli bakiyen yok. Bakiyen: **{balance} {CURRENCY_NAME}**",
                ephemeral=True,
            )
            return

        db.change_balance(guild_id, user_id, -amount)
        db.add_bet(self.prediction_id, user_id, self.option, amount)

        secenek_adi = prediction["option_a"] if self.option == "A" else prediction["option_b"]
        await interaction.response.send_message(
            f"✅ **{amount} {CURRENCY_NAME}** ile **{secenek_adi}** seçeneğine tahmin yaptın!",
            ephemeral=True,
        )

        await self.cog.refresh_prediction_message(interaction.guild, self.prediction_id)


class BetButton(discord.ui.Button):
    def __init__(self, prediction_id: int, option: str, option_label: str, cog: "Predictions"):
        style = discord.ButtonStyle.success if option == "A" else discord.ButtonStyle.danger
        super().__init__(
            label=f"{option_label}",
            style=style,
            custom_id=f"prediction_bet_{option}_{prediction_id}",
        )
        self.prediction_id = prediction_id
        self.option = option
        self.option_label = option_label
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        prediction = db.get_prediction(self.prediction_id)
        if not prediction or prediction["status"] != "open":
            await interaction.response.send_message("Bu öngörü artık tahmine açık değil.", ephemeral=True)
            return

        await interaction.response.send_modal(
            BetModal(self.prediction_id, self.option, self.option_label, self.cog)
        )


class PredictionView(discord.ui.View):
    def __init__(self, prediction_id: int, option_a: str, option_b: str, cog: "Predictions"):
        super().__init__(timeout=None)
        self.add_item(BetButton(prediction_id, "A", option_a, cog))
        self.add_item(BetButton(prediction_id, "B", option_b, cog))


class Predictions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Bot yeniden başladığında açık öngörülerin butonlarını yeniden bağla
        for guild in self.bot.guilds:
            for prediction in db.get_open_predictions(guild.id):
                if prediction["message_id"]:
                    view = PredictionView(prediction["id"], prediction["option_a"], prediction["option_b"], self)
                    self.bot.add_view(view, message_id=prediction["message_id"])

    async def refresh_prediction_message(self, guild: discord.Guild, prediction_id: int):
        prediction = db.get_prediction(prediction_id)
        if not prediction or not prediction["channel_id"] or not prediction["message_id"]:
            return

        channel = guild.get_channel(prediction["channel_id"])
        if channel is None:
            return

        try:
            message = await channel.fetch_message(prediction["message_id"])
        except discord.NotFound:
            return

        embed = build_prediction_embed(prediction)

        if prediction["status"] == "open":
            view = PredictionView(prediction_id, prediction["option_a"], prediction["option_b"], self)
        else:
            view = None

        await message.edit(embed=embed, view=view)

    @app_commands.command(name="tahmin-olustur", description="[Admin] Yeni bir öngörü/tahmin başlatır")
    @app_commands.describe(
        soru="Öngörü sorusu (Örn: 'Oyunu 1 saatte biter mi?')",
        secenek_a="1. seçenek (Örn: 'Biter')",
        secenek_b="2. seçenek (Örn: 'Bitmez')",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def tahmin_olustur(self, interaction: discord.Interaction, soru: str, secenek_a: str, secenek_b: str):
        prediction_id = db.create_prediction(interaction.guild_id, soru, secenek_a, secenek_b, interaction.user.id)
        prediction = db.get_prediction(prediction_id)

        embed = build_prediction_embed(prediction)
        view = PredictionView(prediction_id, secenek_a, secenek_b, self)

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        db.set_prediction_message(prediction_id, message.channel.id, message.id)

    @app_commands.command(name="tahmin-listele", description="Sunucudaki açık öngörüleri listeler")
    async def tahmin_listele(self, interaction: discord.Interaction):
        predictions = db.get_open_predictions(interaction.guild_id)

        if not predictions:
            await interaction.response.send_message("Şu anda açık bir öngörü yok.")
            return

        lines = []
        for p in predictions:
            total_a, total_b = db.get_pool_totals(p["id"])
            lines.append(
                f"**#{p['id']}** — {p['question']}\n"
                f"   🟩 {p['option_a']}: {total_a} {CURRENCY_NAME}  |  "
                f"🟥 {p['option_b']}: {total_b} {CURRENCY_NAME}"
            )

        embed = discord.Embed(
            title="📋 Açık Öngörüler",
            description="\n\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tahmin-bitir", description="[Admin] Bir öngörüyü sonuçlandırır ve ödülleri dağıtır")
    @app_commands.describe(
        tahmin_id="Sonuçlandırılacak öngörünün ID'si (/tahmin-listele ile görebilirsin)",
        kazanan="Kazanan seçenek",
    )
    @app_commands.choices(kazanan=[
        app_commands.Choice(name="Seçenek A", value="A"),
        app_commands.Choice(name="Seçenek B", value="B"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def tahmin_bitir(self, interaction: discord.Interaction, tahmin_id: int, kazanan: app_commands.Choice[str]):
        prediction = db.get_prediction(tahmin_id)

        if not prediction or prediction["guild_id"] != interaction.guild_id:
            await interaction.response.send_message("Bu ID'ye sahip bir öngörü bulunamadı.", ephemeral=True)
            return

        if prediction["status"] == "resolved":
            await interaction.response.send_message("Bu öngörü zaten sonuçlandırılmış.", ephemeral=True)
            return

        winner_option = kazanan.value
        bets = db.get_bets(tahmin_id)
        total_a, total_b = db.get_pool_totals(tahmin_id)
        total_pool = total_a + total_b
        winning_pool = total_a if winner_option == "A" else total_b

        sonuc_satirlari = []

        if winning_pool == 0:
            # Kazanan tarafa kimse bahis yapmadıysa, herkese parası geri verilir
            for bet in bets:
                db.change_balance(interaction.guild_id, bet["user_id"], bet["amount"])
            sonuc_satirlari.append("Kazanan seçeneğe kimse bahis yapmadığı için tüm bahisler iade edildi.")
        else:
            for bet in bets:
                if bet["option"] == winner_option:
                    payout = math.floor(bet["amount"] * (total_pool / winning_pool))
                    db.change_balance(interaction.guild_id, bet["user_id"], payout)
                    sonuc_satirlari.append(
                        f"<@{bet['user_id']}>: {bet['amount']} → **{payout} {CURRENCY_NAME}** kazandı"
                    )

        db.set_prediction_winner(tahmin_id, winner_option)
        await self.refresh_prediction_message(interaction.guild, tahmin_id)

        kazanan_adi = prediction["option_a"] if winner_option == "A" else prediction["option_b"]
        sonuc_metni = "\n".join(sonuc_satirlari) if sonuc_satirlari else "Bu öngörüye kimse bahis yapmadı."

        embed = discord.Embed(
            title=f"🏁 Öngörü #{tahmin_id} Sonuçlandı",
            description=f"**Kazanan:** {kazanan_adi}\n\n{sonuc_metni}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tahmin-iptal", description="[Admin] Bir öngörüyü iptal eder ve tüm tahminleri iade eder")
    @app_commands.describe(tahmin_id="İptal edilecek öngörünün ID'si")
    @app_commands.checks.has_permissions(administrator=True)
    async def tahmin_iptal(self, interaction: discord.Interaction, tahmin_id: int):
        prediction = db.get_prediction(tahmin_id)

        if not prediction or prediction["guild_id"] != interaction.guild_id:
            await interaction.response.send_message("Bu ID'ye sahip bir öngörü bulunamadı.", ephemeral=True)
            return

        if prediction["status"] != "open":
            await interaction.response.send_message("Bu öngörü artık açık değil.", ephemeral=True)
            return

        bets = db.get_bets(tahmin_id)
        for bet in bets:
            db.change_balance(interaction.guild_id, bet["user_id"], bet["amount"])

        db.close_prediction(tahmin_id)
        await self.refresh_prediction_message(interaction.guild, tahmin_id)

        await interaction.response.send_message(
            f"✅ Öngörü #{tahmin_id} iptal edildi ve tüm puanlar iade edildi."
        )

    @tahmin_olustur.error
    @tahmin_bitir.error
    @tahmin_iptal.error
    async def admin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Bu komutu kullanmak için yönetici (administrator) yetkisine sahip olmalısın.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Predictions(bot))
