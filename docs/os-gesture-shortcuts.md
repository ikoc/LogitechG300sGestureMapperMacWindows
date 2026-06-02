# OS Gesture Keyboard Shortcuts Reference

Mouse butonlarına atanabilecek klavye kısayolları — macOS, Windows, Linux.

## macOS

### Masaüstü / Window Management

| Aksiyon | Varsayılan Kısayol | Alternatif |
|---------|-------------------|------------|
| Mission Control | Ctrl+Up | F3 |
| App Exposé | Ctrl+Down | — |
| Sol masaüstüne geç | Ctrl+Left | — |
| Sağ masaüstüne geç | Ctrl+Right | — |
| Masaüstünü göster | F11 | — |
| Tüm uygulamaları göster | Ctrl+Up (2x) | — |
| Launchpad | — | F4 (bazı klavyelerde) |

> Ayarlar: System Settings → Keyboard → Keyboard Shortcuts → Mission Control

### Navigasyon

| Aksiyon | Kısayol |
|---------|---------|
| Sayfa geri | Cmd+[ |
| Sayfa ileri | Cmd+] |
| Geri (genel) | Cmd+Left (Finder vb.) |
| Tab değiştir (sol) | Ctrl+Shift+Tab |
| Tab değiştir (sağ) | Ctrl+Tab |

### Window Management

| Aksiyon | Kısayol |
|---------|---------|
| Pencereyi sola yapıştır | — (3rd party: Rectangle) |
| Pencereyi sağa yapıştır | — (3rd party: Rectangle) |
| Tam ekran toggle | Ctrl+Cmd+F |
| Pencere minimize | Cmd+M |
| Tüm pencereleri minimize | Cmd+Option+M |

## Windows 10/11

### Masaüstü / Window Management

| Aksiyon | Kısayol |
|---------|---------|
| Task View | Win+Tab |
| Sol masaüstüne geç | Win+Ctrl+Left |
| Sağ masaüstüne geç | Win+Ctrl+Right |
| Yeni masaüstü oluştur | Win+Ctrl+D |
| Masaüstünü kapat | Win+Ctrl+F4 |
| Masaüstünü göster | Win+D |
| Tüm pencereleri minimize | Win+M |

### Snap Layout

| Aksiyon | Kısayol |
|---------|---------|
| Pencereyi sola yapıştır | Win+Left |
| Pencereyi sağa yapıştır | Win+Right |
| Tam ekran | Win+Up |
| Minimize | Win+Down |
| Snap layout menüsü | Win+Z (Win 11) |

### Navigasyon

| Aksiyon | Kısayol |
|---------|---------|
| Sayfa geri | Alt+Left |
| Sayfa ileri | Alt+Right |
| Tab değiştir | Ctrl+Tab |
| Pencere değiştir | Alt+Tab |

## Linux (GNOME)

### Masaüstü / Window Management

| Aksiyon | Kısayol |
|---------|---------|
| Activities overview | Super |
| Sol workspace | Super+PageUp veya Ctrl+Alt+Left |
| Sağ workspace | Super+PageDown veya Ctrl+Alt+Right |
| Pencereyi sola yapıştır | Super+Left |
| Pencereyi sağa yapıştır | Super+Right |
| Tam ekran | Super+Up |
| Minimize | Super+H |

### Navigasyon

| Aksiyon | Kısayol |
|---------|---------|
| Sayfa geri | Alt+Left |
| Sayfa ileri | Alt+Right |

## Linux (KDE Plasma)

| Aksiyon | Kısayol |
|---------|---------|
| Desktop grid | Ctrl+F8 |
| Sol masaüstü | Ctrl+Left |
| Sağ masaüstü | Ctrl+Right |
| Present windows | Ctrl+F9 |
| Pencereyi sola | Super+Left |
| Pencereyi sağa | Super+Right |

## USB HID Keycode Tablosu (ratslap isimleri)

ratslap'ta kullanılan isimler ve karşılık gelen USB HID Usage ID'leri:

### Modifier'lar

| ratslap Adı | HID Bit | USB Usage |
|-------------|---------|-----------|
| LeftCtrl | 0x01 | 0xE0 |
| LeftShift | 0x02 | 0xE1 |
| LeftAlt | 0x04 | 0xE2 |
| Super_L | 0x08 | 0xE3 |
| RightCtrl | 0x10 | 0xE4 |
| RightShift | 0x20 | 0xE5 |
| RightAlt | 0x40 | 0xE6 |
| Super_R | 0x80 | 0xE7 |

### Sık Kullanılan Tuşlar

| ratslap Adı | HID Usage ID |
|-------------|-------------|
| A-Z | 0x04-0x1D |
| 1-0 | 0x1E-0x27 |
| Enter | 0x28 |
| Escape | 0x29 |
| Backspace | 0x2A |
| Tab | 0x2B |
| Space | 0x2C |
| [ | 0x2F |
| ] | 0x30 |
| F1-F12 | 0x3A-0x45 |
| Right | 0x4F |
| Left | 0x50 |
| Down | 0x51 |
| Up | 0x52 |
| PageUp | 0x4B |
| PageDown | 0x4E |
| Home | 0x4A |
| End | 0x4D |
| Delete | 0x4C |

### Combo Örnekleri (ratslap formatı)

```bash
# Mission Control (macOS)
--G4 LeftCtrl+Up

# Task View (Windows)
--G4 Super_L+Tab

# Ctrl+Alt+Delete
--G4 LeftCtrl+LeftAlt+Delete

# Ctrl+Shift+T (tarayıcıda kapatılan tab'ı aç)
--G4 LeftCtrl+LeftShift+T

# Cmd+Space (macOS Spotlight)
--G4 Super_L+Space
```

## Önerilen Profiller

### Genel Kullanım (OS-agnostic)

| Buton | Atama | Açıklama |
|-------|-------|----------|
| G4 | Browser Back (Button6) | Tarayıcı geri |
| G5 | Browser Forward (Button7) | Tarayıcı ileri |
| G6 | Copy (LeftCtrl+C) | Kopyala |
| G7 | Paste (LeftCtrl+V) | Yapıştır |
| G9 | Undo (LeftCtrl+Z) | Geri al |

### Gaming

| Buton | Atama | Açıklama |
|-------|-------|----------|
| G4 | Button6 | Yan buton 1 |
| G5 | Button7 | Yan buton 2 |
| G6 | DPIDown | DPI düşür |
| G7 | DPIUp | DPI yükselt |
| G9 | DPIShift | Geçici DPI |

### Productivity (IDE/Editor)

| Buton | Atama | Açıklama |
|-------|-------|----------|
| G4 | LeftCtrl+Z | Undo |
| G5 | LeftCtrl+LeftShift+Z | Redo |
| G6 | LeftCtrl+D | Satır kopyala (VSCode) |
| G7 | LeftCtrl+LeftShift+K | Satır sil (VSCode) |
| G9 | LeftCtrl+P | Quick open |
