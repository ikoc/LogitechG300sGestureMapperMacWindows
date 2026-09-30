#!/usr/bin/env python3
"""
G300s web arayüzü — yerel sunucu.

ratslap'ı sarmalar; tarayıcıdan profil okuma / yazma / mod seçme sağlar.
Sadece 127.0.0.1 üzerinde dinler. Yazma işlemleri oturum token'ı ister.

Kullanım:
    ./g300s_web.py            # http://127.0.0.1:8300
    ./g300s_web.py --open     # tarayıcıyı da açar
    ./g300s_web.py --port 9000
"""

import argparse
import fcntl
import json
import os
import re
import select
import struct
import secrets
import shutil
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
BACKUP_DIR = ROOT / "backups"
PROFILES = ("F3", "F4", "F5")
COLOURS = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
RATES = (125, 250, 500, 1000)
# Web arayüzünden değiştirilebilen butonlar. Sol/sağ/orta tık ve G8 (ModeSwitch) kilitli.
EDITABLE = ("g4", "g5", "g6", "g7", "g9")
ALL_BUTTONS = ("left", "right", "middle", "g4", "g5", "g6", "g7", "g8", "g9")
BUTTON_FLAG = {
    "left": "--left", "right": "--right", "middle": "--middle",
    "g4": "--g4", "g5": "--g5", "g6": "--g6", "g7": "--g7", "g8": "--g8", "g9": "--g9",
}

TOKEN = secrets.token_urlsafe(24)
RATSLAP_LOCK = threading.Lock()


def find_ratslap():
    for cand in (ROOT / "bin" / "ratslap", Path("/tmp/ratslap/ratslap")):
        if cand.is_file():
            return str(cand)
    found = shutil.which("ratslap")
    if found:
        return found
    raise SystemExit("ratslap bulunamadı. ./remap.sh show çalıştırarak kur veya bin/ratslap olarak kopyala.")


RATSLAP = find_ratslap()


def run_ratslap(*args, timeout=20):
    with RATSLAP_LOCK:
        proc = subprocess.run(
            [RATSLAP, *args], capture_output=True, text=True, timeout=timeout
        )
    out = proc.stdout + proc.stderr
    return proc.returncode, out


# --- Geçerli tuş isimleri (ratslap --listkeys) ---

def _expand(a, b):
    if len(a) == 1 and len(b) == 1:
        return [chr(c) for c in range(ord(a), ord(b) + 1)]
    m1, m2 = re.match(r"^(\D*)(\d+)$", a), re.match(r"^(\D*)(\d+)$", b)
    if m1 and m2 and m1.group(1) == m2.group(1):
        return [f"{m1.group(1)}{i}" for i in range(int(m1.group(2)), int(m2.group(2)) + 1)]
    return [a, b]


def load_valid_keys():
    code, out = run_ratslap("--listkeys")
    keys = set()
    for line in out.splitlines()[5:]:
        if line.strip().endswith(":") or not line.strip():
            continue
        toks = line.split()
        i = 0
        while i < len(toks):
            if i + 2 < len(toks) and toks[i + 1] == "...":
                keys.update(_expand(toks[i], toks[i + 2]))
                i += 3
            else:
                keys.add(toks[i])
                i += 1
    keys -= {"MODIFIERS:", "BUTTONS/SPECIALS:", "KEYS:"}
    return keys


VALID_KEYS = load_valid_keys()
MODIFIERS = {"LeftCtrl", "LeftShift", "LeftAlt", "Super_L", "RightCtrl", "RightShift", "RightAlt", "Super_R"}


def validate_combo(combo):
    if not isinstance(combo, str) or not combo or len(combo) > 80:
        return False
    toks = combo.split("+")
    if not all(tok in VALID_KEYS for tok in toks):
        return False
    # Sadece modifier'dan oluşan atama ratslap'ta "Super+Super" olarak saklanıyor; reddet.
    return not all(tok in MODIFIERS for tok in toks)


# --- ratslap çıktısını ayrıştırma ---

def parse_profile(text):
    p = {"colour": None, "rate": None, "dpi": [None] * 4, "default": None,
         "dpishift": None, "dpishift_enabled": False, "buttons": {}}
    names = {
        "Left Click (But1)": "left", "Right Click (But2)": "right",
        "Middle Click (But3)": "middle",
        "G4": "g4", "G5": "g5", "G6": "g6", "G7": "g7", "G8": "g8", "G9": "g9",
    }
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Colour:\s+(\w+)", line)
        if m:
            p["colour"] = m.group(1)
            continue
        m = re.match(r"Report Rate:\s+(\d+)", line)
        if m:
            p["rate"] = int(m.group(1))
            continue
        m = re.match(r"DPI #(\d):\s+(\(DEF\)\s+)?(\d+)", line)
        if m:
            idx = int(m.group(1)) - 1
            p["dpi"][idx] = int(m.group(3))
            if m.group(2):
                p["default"] = idx + 1
            continue
        m = re.match(r"DPI Shift:\s+(\d+)(\s+\[DISABLED\])?", line)
        if m:
            p["dpishift"] = int(m.group(1))
            p["dpishift_enabled"] = m.group(2) is None
            continue
        m = re.match(r"([^:]+):\s+(.+)$", line)
        if m and m.group(1) in names:
            p["buttons"][names[m.group(1)]] = re.sub(r"\s*\+\s*", "+", m.group(2).strip())
    if p["colour"] is None or None in p["dpi"] or len(p["buttons"]) != 9:
        raise ValueError("Profil çıktısı ayrıştırılamadı:\n" + text)
    return p


def read_profile(name):
    code, out = run_ratslap("--print", name)
    if code != 0 or "Printing Mode" not in out:
        raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "ratslap hata verdi")
    return parse_profile(out)


def read_all():
    return {name: read_profile(name) for name in PROFILES}


# --- Yazma ---

def validate_profile(name, data):
    if name not in PROFILES:
        raise ValueError(f"Geçersiz profil: {name}")
    if data.get("colour") not in COLOURS:
        raise ValueError("Geçersiz renk")
    if data.get("rate") not in RATES:
        raise ValueError("Geçersiz polling rate")
    dpi = data.get("dpi")
    if not (isinstance(dpi, list) and len(dpi) == 4 and
            all(isinstance(v, int) and 250 <= v <= 4000 and v % 250 == 0 for v in dpi)):
        raise ValueError("DPI değerleri 250-4000 arası, 250'nin katı olmalı")
    if data.get("default") not in (1, 2, 3, 4):
        raise ValueError("Varsayılan DPI seviyesi 1-4 olmalı")
    buttons = data.get("buttons", {})
    for b, combo in buttons.items():
        if b not in EDITABLE:
            raise ValueError(f"{b} butonu değiştirilemez")
        if not validate_combo(combo):
            raise ValueError(f"{b}: geçersiz tuş kombinasyonu '{combo}'")


def build_args(name, data):
    args = ["--modify", name,
            "--rate", str(data["rate"]),
            "--colour", data["colour"],
            "--d1", str(data["dpi"][0]), "--d2", str(data["dpi"][1]),
            "--d3", str(data["dpi"][2]), "--d4", str(data["dpi"][3]),
            "--default-dpi", str(data["default"])]
    for b in EDITABLE:
        if b in data.get("buttons", {}):
            args += [BUTTON_FLAG[b], data["buttons"][b]]
    return args


def save_backup(state, label="apply"):
    BACKUP_DIR.mkdir(exist_ok=True)
    fname = time.strftime("%Y%m%d-%H%M%S") + f"-{label}.json"
    (BACKUP_DIR / fname).write_text(json.dumps(state, indent=2))
    return fname


def apply_profiles(incoming):
    for name, data in incoming.items():
        validate_profile(name, data)
    before = read_all()
    backup = save_backup(before)
    for name, data in incoming.items():
        code, out = run_ratslap(*build_args(name, data))
        if code != 0:
            raise RuntimeError(f"{name} yazılamadı: {out.strip().splitlines()[-1] if out.strip() else code}")
    after = read_all()
    # Doğrulama: yazılan alanlar geri okununca aynı mı?
    mismatches = []
    for name, data in incoming.items():
        got = after[name]
        for k in ("colour", "rate", "dpi", "default"):
            if got[k] != data[k]:
                mismatches.append(f"{name}.{k}: beklenen {data[k]}, okunan {got[k]}")
        for b, combo in data.get("buttons", {}).items():
            if got["buttons"][b].lower() != combo.lower():
                mismatches.append(f"{name}.{b}: beklenen {combo}, okunan {got['buttons'][b]}")
    return {"state": after, "backup": backup, "mismatches": mismatches}


def list_backups():
    if not BACKUP_DIR.is_dir():
        return []
    return sorted((p.name for p in BACKUP_DIR.glob("*.json")), reverse=True)[:20]


def restore_backup(fname):
    if not re.fullmatch(r"[\w.-]+\.json", fname or ""):
        raise ValueError("Geçersiz yedek adı")
    path = BACKUP_DIR / fname
    if not path.is_file():
        raise ValueError("Yedek bulunamadı")
    saved = json.loads(path.read_text())
    incoming = {}
    for name, p in saved.items():
        incoming[name] = {
            "colour": p["colour"], "rate": p["rate"], "dpi": p["dpi"], "default": p["default"],
            "buttons": {b: p["buttons"][b] for b in EDITABLE},
        }
    return apply_profiles(incoming)



# --- Canlı buton testi (evdev) ---

EVIOCGRAB = 0x40044590
EV_SYN, EV_KEY, EV_REL = 0, 1, 2
REL_X, REL_Y, REL_HWHEEL, REL_WHEEL = 0, 1, 6, 8
EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

# Linux keycode -> ratslap tuş adı
KEYNAMES = {
    29: "LeftCtrl", 42: "LeftShift", 56: "LeftAlt", 125: "Super_L",
    97: "RightCtrl", 54: "RightShift", 100: "RightAlt", 126: "Super_R",
    28: "Enter", 1: "Escape", 14: "Backspace", 15: "Tab", 57: "Space", 12: "-", 13: "=",
    26: "[", 27: "]", 43: "\\", 39: ";", 40: "'", 41: "`", 51: ",", 52: ".", 53: "/",
    103: "Up", 105: "Left", 106: "Right", 108: "Down", 104: "PageUp", 109: "PageDown",
    102: "Home", 107: "End", 110: "Insert", 111: "Delete", 99: "PrintScreen",
    70: "ScrollLock", 119: "Pause", 58: "CapsLock", 113: "Mute", 114: "VolumeDown", 115: "VolumeUp",
    87: "F11", 88: "F12",
}
for _i, _c in enumerate("qwertyuiop"): KEYNAMES[16 + _i] = _c.upper()
for _i, _c in enumerate("asdfghjkl"): KEYNAMES[30 + _i] = _c.upper()
for _i, _c in enumerate("zxcvbnm"): KEYNAMES[44 + _i] = _c.upper()
for _i, _c in enumerate("1234567890"): KEYNAMES[2 + _i] = _c
for _i in range(10): KEYNAMES[59 + _i] = f"F{_i + 1}"
# Mouse butonları: (ratslap adı, evdev adı). Eşleme sezgiseldir (Button4/5 ratslap'ta yok).
BTNNAMES = {
    0x110: ("Button1", "BTN_LEFT"), 0x111: ("Button2", "BTN_RIGHT"), 0x112: ("Button3", "BTN_MIDDLE"),
    0x113: ("Button6", "BTN_SIDE"), 0x114: ("Button7", "BTN_EXTRA"), 0x115: ("Button8", "BTN_FORWARD"),
    0x116: ("Button9", "BTN_BACK"), 0x117: ("Button10", "BTN_TASK"),
}


def find_input_devices():
    """G300s'e ait /dev/input/eventN düğümleri: [(path, handlers)]"""
    found = []
    try:
        text = Path("/proc/bus/input/devices").read_text()
    except OSError:
        return found
    for block in text.split("\n\n"):
        if "G300s" not in block:
            continue
        m = re.search(r"^H: Handlers=(.*)$", block, re.M)
        if not m:
            continue
        ev = re.search(r"event\d+", m.group(1))
        if ev:
            found.append((f"/dev/input/{ev.group(0)}", m.group(1).split()))
    return found


class LiveStream:
    """Bir HTTP isteği süresince G300s olaylarını okuyup SSE olarak yazar."""

    def __init__(self, wfile, grab):
        self.wfile = wfile
        self.want_grab = grab
        self.fds = {}       # fd -> path
        self.grabbed = []
        self.pending = {}   # fd -> batch
        self.dx = self.dy = 0
        self.last_move = 0.0

    def send(self, obj):
        self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")
        self.wfile.flush()

    def open_all(self):
        devs = find_input_devices()
        if not devs:
            raise RuntimeError("G300s olay cihazı bulunamadı (mouse takılı mı?)")
        for path, handlers in devs:
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except PermissionError:
                raise RuntimeError(
                    f"{path} okunamadı (izin yok). Bir kez şunu çalıştır: "
                    "echo 'SUBSYSTEM==\"input\", KERNEL==\"event*\", ATTRS{idVendor}==\"046d\", "
                    "ATTRS{idProduct}==\"c246\", GROUP=\"plugdev\", MODE=\"0660\"' | sudo tee "
                    "/etc/udev/rules.d/99-g300s-input.rules && sudo udevadm control --reload-rules "
                    "&& sudo udevadm trigger --subsystem-match=input --action=change")
            self.fds[fd] = path
            # Mouse cihazını asla grab etme (imleç donar); sadece makro/klavye arayüzlerini
            if self.want_grab and not any(h.startswith("mouse") for h in handlers):
                try:
                    fcntl.ioctl(fd, EVIOCGRAB, 1)
                    self.grabbed.append(path)
                except OSError:
                    pass
        self.send({"hello": True, "devices": list(self.fds.values()), "grabbed": self.grabbed})

    def close_all(self):
        for fd in self.fds:
            try:
                fcntl.ioctl(fd, EVIOCGRAB, 0)
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass
        self.fds.clear()

    def flush_move(self, force=False):
        now = time.monotonic()
        if (self.dx or self.dy) and (force or now - self.last_move > 0.04):
            self.send({"move": [self.dx, self.dy]})
            self.dx = self.dy = 0
            self.last_move = now

    def handle(self, fd, etype, code, value):
        b = self.pending.setdefault(fd, {"keys": [], "btns": [], "wheel": 0, "hwheel": 0})
        if etype == EV_KEY:
            if code in BTNNAMES and value != 2:
                b["btns"].append([BTNNAMES[code][0], BTNNAMES[code][1], value])
            elif code in KEYNAMES and value != 2:
                b["keys"].append([KEYNAMES[code], value])
            elif value != 2:
                b["keys"].append([f"KEY_{code}", value])
        elif etype == EV_REL:
            if code == REL_X: self.dx += value
            elif code == REL_Y: self.dy += value
            elif code == REL_WHEEL: b["wheel"] += value
            elif code == REL_HWHEEL: b["hwheel"] += value
        elif etype == EV_SYN:
            self.pending.pop(fd, None)
            if b["keys"] or b["btns"] or b["wheel"] or b["hwheel"]:
                self.flush_move(force=True)
                self.send(b)

    def run(self):
        try:
            self.open_all()
            last_ping = time.monotonic()
            while True:
                r, _, _ = select.select(list(self.fds), [], [], 0.25)
                for fd in r:
                    try:
                        data = os.read(fd, EVENT_SIZE * 64)
                    except BlockingIOError:
                        continue
                    for off in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                        _, _, etype, code, value = struct.unpack_from(EVENT_FMT, data, off)
                        self.handle(fd, etype, code, value)
                self.flush_move()
                if time.monotonic() - last_ping > 1:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    last_ping = time.monotonic()
        finally:
            self.close_all()


# --- HTTP ---

class Handler(BaseHTTPRequestHandler):
    server_version = "g300s-web"

    def log_message(self, fmt, *args):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, status, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        if not self._host_ok():
            return False
        if self.headers.get("X-Token") != TOKEN:
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}",
                                     f"http://localhost:{self.server.server_port}"):
            return False
        return True

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        if self.path in ("/", "/index.html"):
            html = (WEB_DIR / "index.html").read_text().replace("__TOKEN__", TOKEN)
            return self._send(200, html, "text/html")
        if not self._authorized():
            return self._send(403, {"error": "token gerekli"})
        try:
            if self.path == "/api/state":
                return self._send(200, {"state": read_all(), "editable": EDITABLE,
                                        "backups": list_backups()})
            if self.path.startswith("/api/events"):
                return self._stream_events("grab=1" in self.path)
            if self.path == "/api/backups":
                return self._send(200, {"backups": list_backups()})
        except Exception as e:
            return self._send(500, {"error": str(e)})
        self._send(404, {"error": "yok"})

    def _stream_events(self, grab):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        stream = LiveStream(self.wfile, grab)
        try:
            stream.run()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                stream.send({"error": str(e)})
            except Exception:
                pass

    def do_POST(self):
        if not self._authorized():
            return self._send(403, {"error": "token gerekli"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 100_000:
                return self._send(413, {"error": "çok büyük"})
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/apply":
                incoming = body.get("profiles")
                if not isinstance(incoming, dict) or not incoming:
                    raise ValueError("profiles gerekli")
                result = apply_profiles(incoming)
                result["backups"] = list_backups()
                return self._send(200, result)
            if self.path == "/api/select":
                mode = body.get("mode")
                if mode not in PROFILES:
                    raise ValueError("Geçersiz mod")
                code, out = run_ratslap("--select", mode)
                if code != 0:
                    raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "hata")
                return self._send(200, {"ok": True})
            if self.path == "/api/restore":
                result = restore_backup(body.get("name"))
                result["backups"] = list_backups()
                return self._send(200, result)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            return self._send(400, {"error": str(e)})
        except Exception as e:
            return self._send(500, {"error": str(e)})
        self._send(404, {"error": "yok"})


def main():
    ap = argparse.ArgumentParser(description="G300s web arayüzü")
    ap.add_argument("--port", type=int, default=8300)
    ap.add_argument("--open", action="store_true", help="tarayıcıyı aç")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"G300s arayüzü: {url}  (durdurmak için Ctrl+C)")
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
