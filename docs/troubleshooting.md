# Troubleshooting

## ratslap "Failed to find Logitech G300s"

**Sebep**: USB izin sorunu.

```bash
# Kontrol:
ls -la /dev/bus/usb/001/  # G300s'in device node'unu bul, perms kontrol et

# Çözüm — udev rule:
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="046d", ATTR{idProduct}=="c246", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-g300s.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# Mouse'u çıkar-tak
```

Alternatif: `sudo ./ratslap ...`

## ratslap "Invalid key" hatası

ratslap'ın kabul ettiği isimler `--listkeys` ile listelenir:

```bash
./ratslap --listkeys
```

Yaygın hatalar:
- `Mouse6` ❌ → `Button6` ✅
- `Ctrl` ❌ → `LeftCtrl` ✅
- `Win` ❌ → `Super_L` ✅
- `Alt` ❌ → `LeftAlt` ✅
- Combo ayracı `+` (boşluk yok): `LeftCtrl+Up` ✅

## macOS'ta butonlar algılanmıyor

### Keyboard macro olarak atanmış butonlar
Firmware'de `0x00` (keyboard macro) koduyla atanmış butonlar `kCGEventOtherMouseDown` yerine `kCGEventKeyDown` olarak gelir. `detect_buttons.py` ile keyboard event modunda dinle.

### DPI/ModeSwitch butonları
`0x0C` (DPI Cycle), `0x0D` (Mode Switch) firmware içinde kalır, OS'e event göndermez. Bu butonları kullanmak istiyorsan ratslap ile mouse button veya keyboard macro olarak yeniden ata.

### Accessibility izni
CGEventTap kullanmak için:
System Settings → Privacy & Security → Accessibility → Terminal (veya Python) ekle.

## macOS'ta gesture kısayolları çalışmıyor

macOS'ta Mission Control vb. kısayollar değiştirilmiş olabilir. Kontrol:

System Settings → Keyboard → Keyboard Shortcuts → Mission Control

Varsayılanlar:
- Mission Control: `^↑` (Ctrl+Up)
- Application Windows: `^↓` (Ctrl+Down)
- Move left a space: `^←` (Ctrl+Left)
- Move right a space: `^→` (Ctrl+Right)

## Windows'ta kısayollar çalışmıyor

Windows Task View kısayolu `Win+Tab` direkt çalışmalı. Sanal masaüstü kısayolları (`Win+Ctrl+Left/Right`) sadece birden fazla masaüstü oluşturulduysa çalışır.

## G300s hangi profilde? (LED rengi)

| LED Rengi | Profil |
|-----------|--------|
| Turkuaz (cyan) | F3 |
| Kırmızı | F4 |
| Mavi | F5 |

G8 butonuyla profil değiştirilir. Tüm profillere aynı atamayı yapmak önerilir.

## Ayarları sıfırlama

```bash
./remap.sh reset
```

Veya manuel:
```bash
./ratslap --modify F3 --G4 Button6 --G5 Button7 --G6 LeftCtrl+Z --G7 LeftCtrl+V --G9 DPICycle
```

## Mouse'u farklı bilgisayara taşıyınca ayarlar gidiyor mu?

Hayır. Ayarlar mouse'un flash belleğinde saklanır. Hangi bilgisayara, hangi OS'e takılırsa taksın korunur. Sıfırlamak için ratslap ile reset yapılmalı.
