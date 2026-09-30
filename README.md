# Logitech G300s Gesture Remapper

G300s'in ekstra butonlarını macOS Magic Mouse gesturelarına veya Windows sanal masaüstü kısayollarına firmware seviyesinde atar. Ayarlar mouse flash'a yazılır — her bilgisayarda, yazılım kurmadan çalışır.

## Gereksinimler

- **Linux makine** (Ubuntu/Debian) — ratslap sadece Linux'ta çalışır
- G300s USB ile Linux makineye takılı olmalı
- İnternet (ilk kurulumda ratslap indirilir)

Script bağımlılıkları (`libusb`, `build-essential`, `git`, `ratslap`) otomatik kurar.

## Kullanım

```bash
# Script'i Linux makineye kopyala, G300s'i tak, çalıştır:
./remap.sh mac        # macOS profili
./remap.sh windows    # Windows profili
./remap.sh show       # Mevcut ayarları göster
./remap.sh reset      # Fabrika ayarlarına dön
```

## Web Arayüzü (önerilen)

```bash
./g300s_web.py --open      # http://127.0.0.1:8300
```

Tarayıcıdan üç profili (Turkuaz=F3, Kırmızı=F4, Mavi=F5) okur ve düzenler: buton atamaları, DPI seviyeleri (tüm profillerde eşitleme), polling, LED rengi. macOS / Linux / Windows hazır ayarları vardır.

- Mouse'a yazmadan önce değişiklik özeti gösterilir, her yazmadan önce `backups/` altına yedek alınır, yazılan değerler geri okunarak doğrulanır.
- Sadece `127.0.0.1` dinler; yazma istekleri oturum token'ı ister.
- **Canlı test**: "▶ Canlı test" ile mouse'a basınca haritada butonlar yanar (G4-G9 makroları, sol/sağ/orta tık, tekerlek, hareket). Mouse'un hangi modda (renk) olduğunu da gösterir. Makrolar test sırasında OS'a iletilmez (isteğe bağlı). G8 ve DPI tuşları bilgisayara olay göndermediği için görünmez. Test mouse'un gerçek ayarını (taslağı değil) esas alır.
  - Gereksinim (bir kez): `/etc/udev/rules.d/99-g300s-input.rules` — `SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c246", GROUP="plugdev", MODE="0660"`
- Sol/sağ/orta tık ve G8 (mod değiştirme) arayüzden değiştirilemez.
- Tek başına modifier (ör. sadece `Super_L`) atanamaz; ratslap bunu `Super_L+Super_L` diye saklıyor.
- Gereksinim: `bin/ratslap` (veya `/tmp/ratslap/ratslap`) ve udev kuralı — `./remap.sh show` ilk çalıştırmada kurar.

Önerilen düzen: F3/turkuaz = macOS, F4/kırmızı = Linux, F5/mavi = Windows. Bilgisayar değiştirirken G8 ile ilgili renge geç.

## Buton Düzeni

```
  G5 (sol-üst)        G7 (sağ-üst)
  G4 (sol-alt)        G6 (sağ-alt)
             G9 (alt-orta)

  G8 = Profil değiştirme (dokunma)
  Sol/Sağ/Orta tık = Normal
```

## Profiller

### macOS

| Buton | Kısayol | Aksiyon |
|-------|---------|---------|
| G4 (sol-alt) | Ctrl+Up | Mission Control |
| G5 (sol-üst) | Ctrl+Left | Sol masaüstüne geç |
| G6 (sağ-alt) | Ctrl+Down | App Exposé |
| G7 (sağ-üst) | Ctrl+Right | Sağ masaüstüne geç |
| G9 (alt-orta) | Cmd+[ | Sayfa geri |

> macOS'ta bu kısayollar varsayılan olarak aktif.
> Değiştirdiysen: System Settings → Keyboard → Keyboard Shortcuts → Mission Control

### Windows

| Buton | Kısayol | Aksiyon |
|-------|---------|---------|
| G4 (sol-alt) | Win+Tab | Task View |
| G5 (sol-üst) | Win+Ctrl+Left | Sol masaüstüne geç |
| G6 (sağ-alt) | Win+D | Masaüstünü göster |
| G7 (sağ-üst) | Win+Ctrl+Right | Sağ masaüstüne geç |
| G9 (alt-orta) | Alt+Left | Sayfa geri |

## Nasıl Çalışıyor

G300s'in 3 profili (F3/F4/F5) var, her birinde 9 buton atanabilir. Buton atamaları mouse'un flash belleğinde saklanır. Bu script [ratslap](https://github.com/krayon/ratslap) aracılığıyla USB HID feature report göndererek bu flash'ı yeniden yazar.

### Teknik Detaylar

1. **Protokol**: G300s özel bir HID protokolü kullanır (HID++ 1.0/2.0 DEĞİL). USB Interface 1 üzerinden 35-byte feature report (ID: 0xF3/F4/F5) ile profil okuma/yazma yapılır.

2. **Neden Linux gerekiyor**: macOS'ta kernel HID driver (`AppleUserUSBHostHIDDevice`) cihazı exclusive modda tutar ve USB control transfer ile yazma yapmaya izin vermez. Linux'ta `libusb_detach_kernel_driver` ile driver ayrılabilir.

3. **35-byte profil yapısı**:
   ```
   [0]     Report ID (0xF3/F4/F5)
   [1]     LED rengi (R=bit2, G=bit1, B=bit0)
   [2]     Polling rate (0=125Hz, 1=250Hz, 2=500Hz, 3=1000Hz)
   [3-6]   DPI seviyeleri (4 x 1 byte)
   [7]     DPI shift
   [8-34]  9 buton x 3 byte [kod, modifier, tuş]
   ```

4. **Buton kodları**:
   - `0x01`-`0x09`: Mouse button 1-9
   - `0x0A`: DPI Up, `0x0B`: DPI Down, `0x0C`: DPI Cycle
   - `0x0D`: Profile/Mode Cycle
   - `0x00`: Klavye macro (modifier + tuş)

5. **Kalıcılık**: Ayarlar mouse flash'a yazılır. Bilgisayar değişse, OS değişse bile korunur. `./remap.sh reset` ile fabrika ayarlarına dönülebilir.

### ratslap Kurulumu (Manuel)

Eğer script otomatik kuramıyorsa:

```bash
sudo apt install libusb-1.0-0-dev git build-essential
cd /tmp && git clone https://github.com/krayon/ratslap.git && cd ratslap && make

# USB izni (bir kez):
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="046d", ATTR{idProduct}=="c246", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-g300s.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### ratslap Komut Referansı

```bash
# Profil göster
./ratslap --print F3

# Tek buton değiştir
./ratslap --modify F3 --G4 LeftCtrl+Up

# Desteklenen tuşları listele
./ratslap --listkeys

# Profil seç (mouse LED rengi değişir)
./ratslap --select F3
```
