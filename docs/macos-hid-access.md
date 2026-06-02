# macOS HID Device Access — Sorunlar ve Çözümler

macOS'ta USB HID cihazlara (mouse, keyboard vb.) erişimde karşılaşılan sorunlar ve çözüm yöntemleri.

## Sorun Özeti

macOS'ta HID cihazlara yazma erişimi çok kısıtlı. Linux'ta `libusb_detach_kernel_driver` + `libusb_claim_interface` ile yapılabilen işlemler macOS'ta engellenebilir.

## Erişim Katmanları

### 1. IOKit HIDManager (Kullanıcı alanı)
```
Uygulama → IOHIDManager → IOHIDDevice → Kernel HID Driver → USB Device
```

- **Okuma**: Feature report okuma genellikle çalışır (`IOHIDDeviceGetReport`)
- **Yazma**: `IOHIDDeviceSetReport` başarı dönebilir ama veri cihaza iletilmeyebilir
- **Neden**: Kernel HID driver (AppleUserUSBHostHIDDevice) yazma isteklerini filtreleyebilir
- **İzin**: Accessibility/Input Monitoring izni gerekir

### 2. libusb (Kullanıcı alanı, raw USB)
```
Uygulama → libusb → USB Host Controller → USB Device
```

- **Root gerektirir** (sudo)
- **`libusb_detach_kernel_driver`**: macOS'ta desteklenmiyor (LIBUSB_ERROR_NOT_SUPPORTED döner)
- Kernel driver her zaman bağlı kalır, control transfer'leri engelleyebilir
- **SIP (System Integrity Protection)**: `DYLD_LIBRARY_PATH` gibi env değişkenleri sudo altında silinir

### 3. hidapi (C kütüphanesi, Python binding)
```
Uygulama → hidapi → IOHIDManager → Kernel HID Driver → USB Device
```

- `hid.darwin_set_open_exclusive(0)` bazı versiyonlarda yoktur
- Exclusive mode açıldığında mouse'u ele geçirir (normal kullanım durur)
- Non-exclusive mode'da yazma çalışmayabilir

### 4. pyusb + libusb backend
- `usb.backend.libusb1.get_backend()` → libusb bulamazsa None döner
- `find_library` ile explicit path verilse bile `get_backend` None dönebilir (versiyon uyumsuzluğu)
- `ctypes.cdll.LoadLibrary` ile libusb doğrudan yüklenebilir ama pyusb backend wrapper bunu kabul etmeyebilir

## macOS Specific Sorunlar

### SIP ve DYLD_LIBRARY_PATH
macOS System Integrity Protection, `sudo` altında `DYLD_*` environment değişkenlerini siler. Bu nedenle:

```bash
# ÇALIŞMAZ:
sudo DYLD_LIBRARY_PATH=/opt/homebrew/lib python3 script.py

# Çözüm 1: ctypes ile doğrudan yükle
ctypes.cdll.LoadLibrary("/opt/homebrew/lib/libusb-1.0.dylib")

# Çözüm 2: Full Python path kullan
sudo /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 script.py
```

### Conda/Homebrew Python Karışıklığı
`sudo python3.12` farklı bir Python binary çalıştırabilir:

```
Normal:  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
Sudo:    /opt/miniconda3/bin/python3.12  (PATH sırası değişir)
```

Çözüm: Absolute path kullan.

### IOKit Feature Report Yazma "Başarısı"
`IOHIDDeviceSetReport` return code `0x00000000` (success) dönebilir ama veri gerçekten cihaza yazılmamış olabilir. Kernel driver yazma isteğini sessizce yutabilir.

Test: Write sonrası hemen read yapıp veriyi doğrula.

## Çalışan Çözümler

### Çözüm 1: Linux Kullan (Önerilen)
- `libusb_detach_kernel_driver` Linux'ta çalışır
- ratslap, libratbag gibi araçlar direkt kullanılabilir
- udev rule ile sudo bile gerekmez
- Ayarlar flash'a yazıldığı için sonra cihaz macOS'a takılabilir

### Çözüm 2: IOKit + ctypes (Sadece Okuma)
Profil okuma için çalışır, yazma güvenilmez:

```python
import ctypes, ctypes.util
iokit = ctypes.cdll.LoadLibrary(ctypes.util.find_library("IOKit"))
# IOHIDManagerCreate → SetDeviceMatching → Open → CopyDevices → GetReport
```

### Çözüm 3: Karabiner-Elements (Sadece Keyboard Remap)
- Mouse button'ları keyboard tuşlarına remap edebilir
- Ama sadece macOS tarafında, firmware'e yazmaz
- Cihaz değişince yeniden ayarlamak gerekir

## CGEventTap ile Mouse Event Yakalama

macOS'ta mouse ekstra butonlarını yakalamak için CGEventTap kullanılır:

```python
from Quartz import (
    CGEventTapCreate, kCGHIDEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionDefault, kCGEventOtherMouseDown,
    kCGMouseEventButtonNumber, CGEventGetIntegerValueField
)

mask = (1 << kCGEventOtherMouseDown)
tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap,
                       kCGEventTapOptionDefault, mask, callback, None)
```

**Gereksinim**: Terminal veya uygulama System Settings → Privacy & Security → Accessibility'de izinli olmalı.

**Kapsam**: Sadece standart mouse button event'lerini yakalar. Keyboard macro olarak atanmış butonlar `kCGEventKeyDown` olarak gelir, `kCGEventOtherMouseDown` olarak değil.

## CGEvent ile Gesture Simülasyonu

macOS gesture'larını keyboard shortcut ile tetikleme:

```python
from Quartz import (
    CGEventCreateKeyboardEvent, CGEventSetFlags, CGEventPost,
    kCGSessionEventTap, kCGEventFlagMaskControl, kCGEventFlagMaskCommand
)

# Mission Control (Ctrl+Up)
event = CGEventCreateKeyboardEvent(None, 0x7E, True)  # Up arrow
CGEventSetFlags(event, kCGEventFlagMaskControl)
CGEventPost(kCGSessionEventTap, event)
```

**macOS Keycode'lar:**

| Keycode | Tuş |
|---------|-----|
| 0x7B | Left Arrow |
| 0x7C | Right Arrow |
| 0x7D | Down Arrow |
| 0x7E | Up Arrow |
| 0x21 | [ |
| 0x1E | ] |
| 0x63 | F3 |
| 0x67 | F11 |

## Özet Karar Tablosu

| İşlem | macOS | Linux |
|-------|-------|-------|
| HID device okuma | IOKit ✅ | libusb ✅ |
| HID device yazma | IOKit ❌ (güvenilmez) | libusb ✅ |
| Kernel driver detach | ❌ (SIP engeli) | ✅ |
| Mouse button yakalama | CGEventTap ✅ | evdev/hidraw ✅ |
| Gesture simülasyonu | CGEvent keyboard ✅ | xdotool ✅ |
| Firmware flash yazma | ❌ → Linux'ta yap | ratslap ✅ |
