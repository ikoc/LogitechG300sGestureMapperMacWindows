# Logitech G300s HID Protocol Reference

Reverse-engineered protocol documentation. Sources: ratslap, libratbag, USB sniffing.

## Overview

G300s **custom HID protocol** kullanır. Logitech HID++ 1.0 veya 2.0 ile ilgisi yok — tamamen farklı.

- **VID**: `0x046D` (Logitech)
- **PID**: `0xC246` (G300s)
- **USB Class**: HID (Human Interface Device)
- **Interfaces**: 2 adet

## USB Interface Yapısı

| Interface | Class | SubClass | Protocol | Endpoint | Kullanım |
|-----------|-------|----------|----------|----------|----------|
| 0 | HID | Boot Interface (1) | Mouse (2) | EP 0x81 IN, 7 byte | Mouse input (hareket, tık, scroll) |
| 1 | HID | None (0) | Keyboard (1) | EP 0x82 IN, 7 byte | Konfigürasyon + keyboard macro output |

### Interface 0 — Mouse Input
Standart HID mouse raporu. macOS `IOHIDFamily.kext` bunu otomatik yakalar ve `CGEvent` olarak iletir.

- X/Y hareket, scroll wheel, mouse butonları
- Buton ataması firmware'de `0x01`-`0x09` (mouse button) olan butonlar buradan gönderilir

### Interface 1 — Configuration + Keyboard
İki görevi var:
1. **Feature report** ile profil okuma/yazma (konfigürasyon)
2. **Input report** ile keyboard macro çıktısı (buton ataması `0x00` = keyboard macro olanlar)

## Feature Report'lar

Konfigürasyon USB HID Feature Report'ları ile yapılır. Interface 1'e gönderilir.

### USB Control Transfer Formatı

**Okuma (GET_REPORT):**
```
bmRequestType: 0xA1  (Device→Host, Class, Interface)
bRequest:      0x01  (GET_REPORT)
wValue:        0x03XX (0x03 = Feature report type, XX = Report ID)
wIndex:        0x0001 (Interface 1)
wLength:       35
```

**Yazma (SET_REPORT):**
```
bmRequestType: 0x21  (Host→Device, Class, Interface)
bRequest:      0x09  (SET_REPORT)
wValue:        0x03XX
wIndex:        0x0001
wLength:       35
```

### Report ID'leri

| Report ID | Boyut | Kullanım |
|-----------|-------|----------|
| `0xF0` | 3 byte | Aktif profil ve DPI seviyesi seçimi |
| `0xF3` | 35 byte | Profil F3 (Mode 1) — tam profil verisi |
| `0xF4` | 35 byte | Profil F4 (Mode 2) |
| `0xF5` | 35 byte | Profil F5 (Mode 3) |
| `0xF1` | ? | LED durumu (detay az) |

### Report 0xF0 — Aktif Profil Seçimi

```
Byte 0: Report ID (0xF0)
Byte 1: Aktif profil (0x00=F3, 0x01=F4, 0x02=F5)
Byte 2: Aktif DPI seviyesi (0x00-0x03)
```

### Report 0xF3/F4/F5 — Profil Verisi (35 byte)

```
Offset  Boyut  Alan
------  -----  ----
0       1      Report ID (0xF3, 0xF4, veya 0xF5)
1       1      LED rengi
2       1      Polling rate
3       4      DPI seviyeleri (4 adet)
7       1      DPI shift
8       27     Buton atamaları (9 buton × 3 byte)
```

#### LED Rengi (Byte 1)
Bit mask — birden fazla renk birleştirilebilir:

| Bit | Renk |
|-----|------|
| 0 (0x01) | Blue |
| 1 (0x02) | Green |
| 2 (0x04) | Red |

Kombinasyonlar: `0x03`=Cyan, `0x05`=Magenta, `0x06`=Yellow, `0x07`=White, `0x00`=Off/Black

#### Polling Rate (Byte 2)

| Değer | Rate |
|-------|------|
| 0x00 | 125 Hz |
| 0x01 | 250 Hz |
| 0x02 | 500 Hz |
| 0x03 | 1000 Hz |

#### DPI Seviyeleri (Byte 3-6)

Her byte bir DPI seviyesi. Formül: `DPI = (değer + 1) × 250`

| Değer | DPI |
|-------|-----|
| 0x00 | 250 |
| 0x01 | 500 |
| 0x02 | 750 |
| 0x03 | 1000 |
| ... | ... |
| 0x0F | 4000 |

Özel değerler (>= 0x80): Logitech'in hassas DPI mapping'i, tam formül bilinmiyor. Örnekler:
- `0x82` → ~32750 (gözlemlenen)
- `0x86` → ~34750 (gözlemlenen)

#### DPI Shift (Byte 7)
DPI Shift butonuna basılı tutulduğunda geçici olarak kullanılan DPI. `0x00` = devre dışı.

#### Buton Atamaları (Byte 8-34)

9 buton, her biri 3 byte: `[kod, modifier, tuş]`

| Offset | Buton |
|--------|-------|
| 8-10 | Button 1 (Sol tık) |
| 11-13 | Button 2 (Sağ tık) |
| 14-16 | Button 3 (Orta tık / scroll basma) |
| 17-19 | Button 4 (G4) |
| 20-22 | Button 5 (G5) |
| 23-25 | Button 6 (G6) |
| 26-28 | Button 7 (G7) |
| 29-31 | Button 8 (G8) |
| 32-34 | Button 9 (G9) |

#### Buton Kodu (Byte 0 of 3)

| Kod | Anlam |
|-----|-------|
| `0x00` | Keyboard macro — modifier ve tuş alanları aktif |
| `0x01` | Mouse Button 1 (Left) |
| `0x02` | Mouse Button 2 (Right) |
| `0x03` | Mouse Button 3 (Middle) |
| `0x04` | Mouse Button 4 |
| `0x05` | Mouse Button 5 |
| `0x06` | Mouse Button 6 |
| `0x07` | Mouse Button 7 |
| `0x08` | Mouse Button 8 |
| `0x09` | Mouse Button 9 |
| `0x0A` | DPI Up |
| `0x0B` | DPI Down |
| `0x0C` | DPI Cycle |
| `0x0D` | Profile/Mode Cycle |
| `0x0E` | DPI Alternate (DPI Shift toggle) |
| `0x0F` | DPI Default |

#### Keyboard Macro Modifier (Byte 1 of 3, sadece kod=0x00 ise)

USB HID modifier bit mask:

| Bit | Modifier |
|-----|----------|
| 0 (0x01) | Left Ctrl |
| 1 (0x02) | Left Shift |
| 2 (0x04) | Left Alt |
| 3 (0x08) | Left GUI (Cmd/Win/Super) |
| 4 (0x10) | Right Ctrl |
| 5 (0x20) | Right Shift |
| 6 (0x40) | Right Alt |
| 7 (0x80) | Right GUI |

#### Keyboard Macro Key (Byte 2 of 3, sadece kod=0x00 ise)

USB HID Usage ID (Keyboard/Keypad page 0x07). Örnekler:

| Değer | Tuş |
|-------|-----|
| 0x04 | A |
| 0x05 | B |
| ... | ... |
| 0x1D | Z |
| 0x1E | 1 |
| ... | ... |
| 0x27 | 0 |
| 0x28 | Enter |
| 0x29 | Escape |
| 0x2A | Backspace |
| 0x2B | Tab |
| 0x2C | Space |
| 0x4F | Right Arrow |
| 0x50 | Left Arrow |
| 0x51 | Down Arrow |
| 0x52 | Up Arrow |

Tam liste: USB HID Usage Tables, Section 10 (Keyboard/Keypad Page).

## Firmware Davranışı

1. **Buton basıldığında**: Firmware aktif profilin buton atamasını okur. Mouse button kodu ise Interface 0'dan HID mouse input report gönderir. Keyboard macro ise Interface 1'den HID keyboard input report gönderir.

2. **DPI/Mode Switch**: Firmware içinde kalır, OS'e herhangi bir event göndermez.

3. **Profil değişimi**: G8 (ModeSwitch) basıldığında LED rengi değişir, firmware yeni profili aktif eder. OS'e bildirim gitmez.

4. **Flash yazma**: SET_REPORT sonrası veri hemen flash'a yazılır. Kalıcı — güç kesilse bile korunur.

## Örnek Profil Dump

```
F3 profili (hex): F3 06 03 82 04 06 0A 00
                  01 00 00  ← Button 1: Mouse Left
                  02 00 00  ← Button 2: Mouse Right
                  03 00 00  ← Button 3: Mouse Middle
                  04 00 00  ← Button 4 (G4): Mouse Button 4
                  05 00 00  ← Button 5 (G5): Mouse Button 5
                  00 01 00  ← Button 6 (G6): Keyboard LCtrl + (none)
                  00 04 00  ← Button 7 (G7): Keyboard LAlt + (none)
                  0D 00 00  ← Button 8 (G8): Mode Switch
                  0C 00 00  ← Button 9 (G9): DPI Cycle
```

## CGEvent Button Numbering (macOS)

macOS CGEventTap mouse buton numaraları 0-indexed:

| HID Button | CGEvent buttonNumber | macOS Adı |
|------------|---------------------|-----------|
| 1 | 0 | Left click |
| 2 | 1 | Right click |
| 3 | 2 | Middle click |
| 4 | 3 | kCGEventOtherMouseDown |
| 5 | 4 | kCGEventOtherMouseDown |
| 6+ | 5+ | kCGEventOtherMouseDown |

**Not**: ratslap'ın `Button6`, `Button7` isimleri HID button 4, 5'e karşılık gelir (ratslap Button4/5 atlanmış). Bu nedenle:
- ratslap `Button6` → HID button 4 → CGEvent button 3
- ratslap `Button7` → HID button 5 → CGEvent button 4
- ratslap `Button8` → HID button 6 → CGEvent button 5

## Referanslar

- [ratslap](https://github.com/krayon/ratslap) — G300s Linux config tool
- [libratbag driver-logitech-g300.c](https://github.com/libratbag/libratbag) — kernel driver source
- [USB HID Usage Tables](https://usb.org/document-library/hid-usage-tables-15) — keyboard keycodes
- [ratslap G300s USB sniffing doc](https://github.com/krayon/ratslap/blob/main/G300s_USB_sniffing.txt)
