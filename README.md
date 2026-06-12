# Discord Öngörü & Sesli Puan Botu

Bu bot iki özellik sunar:

1. **Öngörü (bahis) sistemi** – Kick'teki "prediction" sistemine benzer şekilde,
   bir soru için iki seçenek açılır, sunucu üyeleri kendi puanlarından bahis yapar,
   sonuç açıklandığında kazananlara puanlar oranlı şekilde dağıtılır.
2. **Sesli kanal puanı** – Sesli kanalda vakit geçiren üyeler belirli aralıklarla
   otomatik puan kazanır. Bu puanlar öngörü sisteminde bahis olarak kullanılır.

Ayrıca admin yetkisi olanlar `/puan-ver` ve `/puan-al` komutlarıyla puanları
elle düzenleyebilir.

---

## 1. Discord Bot Oluşturma

1. https://discord.com/developers/applications adresine git, **New Application**
   ile yeni bir uygulama oluştur.
2. Sol menüden **Bot** sekmesine geç, **Add Bot** ile bot kullanıcısı oluştur.
3. **Privileged Gateway Intents** kısmında şunları **açık (ON)** yap:
   - `SERVER MEMBERS INTENT`
   - `MESSAGE CONTENT INTENT`
4. **Reset Token** ile bir token al ve kopyala (bu token'ı kimseyle paylaşma!).
5. Sol menüden **OAuth2 > URL Generator**'a git:
   - Scopes: `bot` ve `applications.commands` seç.
   - Bot Permissions: en azından `Send Messages`, `Embed Links`,
     `Read Message History`, `View Channels`, `Use Slash Commands` seç.
   - Oluşan linki tarayıcıda açıp botu kendi sunucuna ekle.

---

## 2. Projeyi Çalıştırma

```bash
# 1) Bağımlılıkları yükle
pip install -r requirements.txt

# 2) .env dosyasını oluştur
cp .env.example .env
# .env dosyasını aç ve DISCORD_TOKEN=... satırına kendi token'ını yapıştır

# 3) Botu başlat
python main.py
```

Bot açıldığında konsolda "✅ Giriş yapıldı" ve "🔄 ... slash komut senkronize edildi"
yazısını görmelisin. Discord'da `/` yazınca komutlar görünecek (yeni eklenen
slash komutların sunucuda görünmesi bazen birkaç dakika sürebilir).

---

## 3. Komutlar

| Komut | Açıklama | Yetki |
|---|---|---|
| `/bakiye [kullanici]` | Kendi veya başkasının puanını gösterir | Herkes |
| `/liderlik` | En çok puana sahip 10 kişiyi gösterir | Herkes |
| `/puan-ver kullanici miktar` | Kullanıcıya puan ekler | Admin |
| `/puan-al kullanici miktar` | Kullanıcıdan puan alır | Admin |
| `/tahmin-olustur soru secenek_a secenek_b` | Yeni öngörü/bahis başlatır | Admin |
| `/tahmin-listele` | Açık öngörüleri listeler | Herkes |
| `/tahmin-bitir tahmin_id kazanan` | Öngörüyü sonuçlandırır, ödülleri dağıtır | Admin |
| `/tahmin-iptal tahmin_id` | Öngörüyü iptal eder, bahisleri iade eder | Admin |

### Örnek kullanım senaryosu

1. Admin: `/tahmin-olustur soru:"Oyunu 1 saatte biter mi?" secenek_a:"Biter" secenek_b:"Bitmez"`
2. Bot, iki butonlu bir mesaj gönderir. Üyeler butona basıp açılan pencereye
   bahis miktarını yazar.
3. Yayın/oyun bitince admin: `/tahmin-bitir tahmin_id:3 kazanan:"Seçenek A"`
4. Bot, kazanan tarafa bahis yapan herkese, toplam havuzu kendi bahisleri
   oranında dağıtır ve sonucu mesaja yazar.

---

## 4. Ayarları Değiştirme (`config.py`)

- `STARTING_BALANCE`: Yeni kullanıcıların başlangıç puanı (varsayılan 100).
- `VOICE_POINTS_PER_INTERVAL`: Her aralıkta verilecek puan (varsayılan 1).
- `VOICE_INTERVAL_MINUTES`: Puan verme aralığı, dakika (varsayılan 5).
  Örneğin "her 10 dakikada 2 puan" istiyorsan `VOICE_INTERVAL_MINUTES = 10` ve
  `VOICE_POINTS_PER_INTERVAL = 2` yapabilirsin.
- `REQUIRE_MULTIPLE_USERS`: `True` ise, sesli kanalda en az 2 kişi (bot hariç)
  olmadan puan verilmez. Tek başına kanalda oturup puan toplamayı engeller.
- `CURRENCY_NAME`, `CURRENCY_EMOJI`: Puan biriminin adı ve emojisi.

---

## 5. Botu 7/24 Çalışır Tutma (Hosting Önerileri)

Test ederken kendi bilgisayarında çalıştırman yeterli, ama bilgisayarı
kapattığında bot da kapanır. Sürekli açık olması için seçenekler:

- **Eski bir bilgisayar / Raspberry Pi**: Evde sürekli açık bir cihaz varsa,
  ek maliyet olmadan en pratik çözüm. `python main.py`'ı arka planda
  çalıştırmak için `screen`, `tmux` veya `systemd` servisi kullanılabilir.
- **Ücretsiz/uygun VPS**: Oracle Cloud'un ücretsiz katmanı (Always Free) küçük
  bir sunucu için yeterli; Hetzner gibi sağlayıcılarda da çok ucuz (aylık
  birkaç euro) VPS'ler bulunur. SQLite tabanlı bu bot çok az kaynak gerektirir.
- **Railway / Render gibi PaaS servisleri**: Kod deposunu (GitHub) bağlayıp
  birkaç tıkla deploy edebilirsin; küçük botlar için ücretsiz kotaları
  genellikle yeterlidir, ama saatlik/aylık limitlere dikkat etmek gerekir.

Hangi seçeneği seçersen seç, `.env` dosyasındaki token'ı sunucuya da
taşımalısın ve `data.db` dosyası (puanları/bahisleri tutan veritabanı)
bot ile aynı klasörde kalmalı — bu dosyayı silersen tüm puanlar sıfırlanır,
yedeklemek istersen ara sıra kopyalayabilirsin.
