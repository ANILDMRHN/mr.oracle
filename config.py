import os
from dotenv import load_dotenv

load_dotenv()

# Discord bot token'ı .env dosyasından okunur
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Yeni kullanıcıya verilecek başlangıç puanı
STARTING_BALANCE = 100

# Sesli kanalda geçirilen süreye göre verilecek puan ayarları
VOICE_POINTS_PER_INTERVAL = 1     # Her aralıkta verilecek puan
VOICE_INTERVAL_MINUTES = 5        # Aralık süresi (dakika)

# True ise, AFK kanalındaki ve kendi kendine (tek kişi) sesli kanalda
# olan kullanıcılar puan alamaz
REQUIRE_MULTIPLE_USERS = True

# Para biriminin adı (mesajlarda gösterilecek)
CURRENCY_NAME = "puan"
CURRENCY_EMOJI = "🪙"
