import sys
import json
import io
import traceback
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel,
    QHBoxLayout, QPushButton, QScrollArea, QTextEdit, QSplitter,
    QListWidget, QListWidgetItem, QStackedWidget, QFrame,
    QGraphicsOpacityEffect, QMessageBox, QTabWidget, QSizePolicy,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QAction, QIcon

import qtawesome as qta


def custom_excepthook(exc_type, exc_value, exc_traceback):
    with open("f:\\watan-sehat\\crash.log", "w") as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = custom_excepthook

from components.voice_orb import VoiceOrb
from bridge import AIBridge
from seasonal_engine import get_context
from components.triage_wizard import TriageWizardWidget
from components.health_vault import HealthVaultWidget

# ── Design tokens (Minimalist / Clean) ─────────────────────────────────
BG          = "#FAFAFA"
SIDEBAR     = "#F4F4F5"
CARD        = "#FFFFFF"
BORDER      = "#E4E4E7"
TEXT        = "#18181B"
TEXT_MED    = "#52525B"
TEXT_FADE   = "#A1A1AA"
# Overriding legacy colors to map to minimalistic tones
SAFFRON     = "#18181B"  # Primary action (Black/Slate)
SAFFRON_BG  = "#F4F4F5"  # Soft gray bg for selection
CHINAR      = "#EF4444"  # Muted red for critical actions
DAL         = "#0EA5E9"  # Soft sky blue
PINE        = "#10B981"  # Soft emerald green
GOLD        = "#F59E0B"  # Soft amber
USER_BUBBLE = "#18181B"  # Dark user bubble
BOT_BUBBLE  = "#F4F4F5"  # Light gray bot bubble

SEVERITY_COLORS = {
    "extreme": "#EF4444",
    "high": "#F97316",
    "moderate": "#EAB308",
    "mild": "#10B981",
    "pleasant": "#0EA5E9",
    "warm": "#F97316",
}


# ── Season + time helpers ─────────────────────────────────────────────
def get_greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Good Morning"
    if h < 17:  return "Good Afternoon"
    return "Good Evening"

def get_season_info() -> dict:
    try:
        ctx = get_context()
        s = ctx.get("season", {})
        return {
            "name_en": s.get("name_en", ""),
            "severity": s.get("severity", "mild"),
        }
    except Exception:
        return {"name_en": "—", "severity": "mild"}


# ── Voice recording thread ────────────────────────────────────────────
class VoiceRecorderThread(QThread):
    transcript_ready = pyqtSignal(str)
    state_changed    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._should_stop = False
        self.RATE = 16000

    def stop(self):
        self._should_stop = True

    def run(self):
        try:
            import sounddevice as sd
            import scipy.io.wavfile as wavfile

            self.state_changed.emit("listening")
            chunks: list = []

            def _cb(indata, frames, time_info, status):
                if not self._should_stop:
                    chunks.append(indata.copy())

            with sd.InputStream(samplerate=self.RATE, channels=1,
                                dtype="float32", blocksize=2048, callback=_cb):
                while not self._should_stop:
                    sd.sleep(50)

            self.state_changed.emit("processing")

            if len(chunks) < 4:
                self.state_changed.emit("idle")
                return

            audio = np.concatenate(chunks, axis=0).flatten()
            audio_int16 = (audio * 32767).astype(np.int16)

            buf = io.BytesIO()
            wavfile.write(buf, self.RATE, audio_int16)
            wav_bytes = buf.getvalue()

            backend_path = str(Path(__file__).parent.parent / "backend")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from voice.stt import transcribe
            result = transcribe(wav_bytes, language="auto")
            text = result.get("text", "").strip()
            if text:
                self.transcript_ready.emit(text)
            else:
                self.state_changed.emit("idle")

        except Exception as exc:
            print(f"[voice] recorder error: {exc}")
            self.state_changed.emit("idle")


# ── TTS speaker thread ────────────────────────────────────────────────
class TTSSpeakerThread(QThread):
    speaking_done = pyqtSignal()

    # Jenny = clear female, Aria = expressive female, Guy = natural male
    VOICE = "en-US-JennyNeural"

    def __init__(self, text: str, rate: int = 165, parent=None):
        super().__init__(parent)
        self.text = text
        # edge-tts rate: "+10%" faster, "-10%" slower; 165 wpm baseline → "+0%"
        offset = int((rate - 165) / 165 * 100)
        self.rate_str = f"{'+' if offset >= 0 else ''}{offset}%"
        self._stop_requested = False

    def stop_speaking(self):
        self._stop_requested = True
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

    def run(self):
        try:
            import asyncio
            import edge_tts
            import miniaudio
            import sounddevice as sd

            async def _stream():
                communicate = edge_tts.Communicate(
                    self.text, voice=self.VOICE, rate=self.rate_str
                )
                mp3_chunks = []
                async for chunk in communicate.stream():
                    if self._stop_requested:
                        return b""
                    if chunk["type"] == "audio":
                        mp3_chunks.append(chunk["data"])
                return b"".join(mp3_chunks)

            mp3_bytes = asyncio.run(_stream())
            if not mp3_bytes or self._stop_requested:
                return

            decoded = miniaudio.decode(
                mp3_bytes,
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=1,
                sample_rate=24000,
            )
            samples = np.frombuffer(decoded.samples, dtype=np.float32)
            sd.play(samples, samplerate=24000)
            sd.wait()

        except Exception as exc:
            print(f"[tts] edge-tts error: {exc}")
            # Offline fallback to pyttsx3
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", 165)
                if not self._stop_requested:
                    engine.say(self.text)
                    engine.runAndWait()
            except Exception as exc2:
                print(f"[tts] pyttsx3 fallback error: {exc2}")
        finally:
            self.speaking_done.emit()


# ── Animated mic button ──────────────────────────────────────────────
class MicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._phase = 0
        self._mode = "idle"  # idle | listening | speaking
        self._set_idle()

    def _set_idle(self):
        self._timer.stop()
        self._mode = "idle"
        self.setIcon(qta.icon("fa5s.microphone", color="white"))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {SAFFRON};
                border-radius: 22px; border: none;
            }}
            QPushButton:hover {{ background-color: #3F3F46; }}
        """)
        self.setToolTip("Click to speak")

    def _pulse(self):
        self._phase = 1 - self._phase
        if self._mode == "listening":
            border_clr = "#FFCCBC" if self._phase else CHINAR
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CHINAR};
                    border-radius: 22px;
                    border: 3px solid {border_clr};
                }}
            """)
            self.setIcon(qta.icon("fa5s.stop", color="white"))
        else:  # speaking
            border_clr = "#E0B0FF" if self._phase else "#AF52DE"
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #AF52DE;
                    border-radius: 22px;
                    border: 3px solid {border_clr};
                }}
            """)
            self.setIcon(qta.icon("fa5s.volume-up", color="white"))

    def set_listening(self, on: bool):
        if on:
            self._mode = "listening"
            self._phase = 0
            self._timer.start(400)
            self.setToolTip("Tap to stop recording")
        else:
            self._set_idle()

    def set_speaking(self, on: bool):
        if on:
            self._mode = "speaking"
            self._phase = 0
            self._timer.start(600)
            self.setToolTip("Tap to stop speaking")
        else:
            self._set_idle()


# ── Input widget ──────────────────────────────────────────────────────
class ChatInputEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.return_pressed = None
        self.setPlaceholderText("Type a health question or press the mic to speak…")
        self.setFont(QFont("Segoe UI", 12))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {TEXT};
            }}
        """)

    def keyPressEvent(self, event):
        if (event.key() == Qt.Key.Key_Return
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.return_pressed:
                self.return_pressed()
            return
        super().keyPressEvent(event)


# ── Chat bubble ───────────────────────────────────────────────────────
class ChatBubble(QWidget):
    def __init__(self, text: str, is_user: bool = False, source: str = ""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 12))
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setMaximumWidth(520)

        if is_user:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: {USER_BUBBLE};
                    color: white;
                    padding: 12px 16px;
                    border-radius: 18px;
                    border-top-right-radius: 4px;
                }}
            """)
            layout.addStretch()
            layout.addWidget(self.label)
        else:
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: {BOT_BUBBLE};
                    color: {TEXT};
                    padding: 12px 16px;
                    border-radius: 18px;
                    border-top-left-radius: 4px;
                    border: 1px solid {BORDER};
                }}
            """)
            vbox.addWidget(self.label)

            footer_row = QHBoxLayout()
            footer_row.setContentsMargins(0, 0, 0, 0)
            footer_row.setSpacing(8)

            if source and source not in ("", "error"):
                src_lbl = QLabel(f"⊙ {source}")
                src_lbl.setFont(QFont("Segoe UI", 8))
                src_lbl.setStyleSheet(f"color: {TEXT_FADE}; border: none;")
                footer_row.addWidget(src_lbl)

            footer_row.addStretch()

            btn_s = (f"QPushButton {{ border: none; background: transparent; padding: 2px; }}"
                     f"QPushButton:hover {{ background-color: {BORDER}; border-radius: 4px; }}")

            copy_btn = QPushButton(qta.icon("fa5s.copy", color=TEXT_FADE), "")
            copy_btn.setFixedSize(24, 24)
            copy_btn.setStyleSheet(btn_s)
            copy_btn.setToolTip("Copy")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(text))
            footer_row.addWidget(copy_btn)

            self.action_widget = QWidget()
            self.action_widget.setLayout(footer_row)
            self.opacity_eff = QGraphicsOpacityEffect()
            self.opacity_eff.setOpacity(0.0)
            self.action_widget.setGraphicsEffect(self.opacity_eff)
            self.action_widget.setEnabled(False)

            vbox.addWidget(self.action_widget)
            layout.addLayout(vbox)
            layout.addStretch()

    def enterEvent(self, event):
        if hasattr(self, "opacity_eff"):
            self.opacity_eff.setOpacity(1.0)
            self.action_widget.setEnabled(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if hasattr(self, "opacity_eff"):
            self.opacity_eff.setOpacity(0.0)
            self.action_widget.setEnabled(False)
        super().leaveEvent(event)


# ── Medicine card ─────────────────────────────────────────────────────
class MedicineCard(QFrame):
    def __init__(self, entry: dict):
        super().__init__()
        self.entry = entry
        self.expanded = False
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {SAFFRON}; }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 12, 14, 12)
        self.main_layout.setSpacing(6)

        header_row = QHBoxLayout()
        name_lbl = QLabel(entry.get("name", "Unknown"))
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"color: {TEXT}; border: none;")

        self.expand_btn = QPushButton("▼")
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setFont(QFont("Segoe UI", 9))
        self.expand_btn.setStyleSheet(f"""
            QPushButton {{ border: none; background: transparent; color: {TEXT_FADE}; }}
            QPushButton:hover {{ color: {SAFFRON}; }}
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_row.addWidget(name_lbl, stretch=1)
        header_row.addWidget(self.expand_btn)
        self.main_layout.addLayout(header_row)

        usage_lbl = QLabel(entry.get("usage", ""))
        usage_lbl.setFont(QFont("Segoe UI", 10))
        usage_lbl.setWordWrap(True)
        usage_lbl.setStyleSheet(f"color: {TEXT_MED}; border: none;")
        self.main_layout.addWidget(usage_lbl)

        flags = QHBoxLayout()
        flags.setSpacing(8)
        for icon_name, ok_val, label_text in [
            ("fa5s.user", entry.get("safe_for_elderly", True), "Elderly"),
            ("fa5s.child", entry.get("safe_for_children", True), "Child"),
        ]:
            ok = bool(ok_val)
            clr = PINE if ok else CHINAR
            ico_lbl = QLabel()
            ico_lbl.setPixmap(qta.icon(icon_name, color=clr).pixmap(12, 12))
            txt_lbl = QLabel(f"{label_text} {'✓' if ok else '✗'}")
            txt_lbl.setFont(QFont("Segoe UI", 9))
            txt_lbl.setStyleSheet(f"color: {clr}; border: none;")
            flags.addWidget(ico_lbl)
            flags.addWidget(txt_lbl)
        flags.addStretch()
        self.main_layout.addLayout(flags)

        self.detail_widget = QWidget()
        self.detail_widget.setStyleSheet("border: none;")
        det_layout = QVBoxLayout(self.detail_widget)
        det_layout.setContentsMargins(0, 8, 0, 0)
        det_layout.setSpacing(6)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {BORDER};")
        det_layout.addWidget(sep)

        for key, label, text_clr, bg_clr in [
            ("contraindications", "⚠ Caution",  "#92400e", "#FEF3C7"),
            ("season_warnings",   "🌿 Season",   "#1E40AF", "#EFF6FF"),
            ("text_content",      "ℹ Info",      TEXT_MED,  SAFFRON_BG),
        ]:
            val = entry.get(key, "")
            if val:
                self._add_detail_box(det_layout, label, val, text_clr, bg_clr)

        self.main_layout.addWidget(self.detail_widget)
        self.detail_widget.hide()

    def _add_detail_box(self, layout, label, text, text_clr, bg_clr):
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background-color: {bg_clr}; border-radius: 8px; border: none; }}"
        )
        bl = QVBoxLayout(box)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(3)
        lh = QLabel(label)
        lh.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lh.setStyleSheet(f"color: {text_clr}; border: none; background: transparent;")
        lb = QLabel(text)
        lb.setFont(QFont("Segoe UI", 10))
        lb.setWordWrap(True)
        lb.setStyleSheet(f"color: {text_clr}; border: none; background: transparent;")
        bl.addWidget(lh)
        bl.addWidget(lb)
        layout.addWidget(box)

    def toggle_expand(self):
        self.expanded = not self.expanded
        self.detail_widget.setVisible(self.expanded)
        self.expand_btn.setText("▲" if self.expanded else "▼")


# ── Medical kit screen ───────────────────────────────────────────────
class MedicalKitWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("🩺  Household Medical Kit")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(title)

        sub = QLabel("Common medicines & first aid for Kashmir households. Tap ▼ for details.")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet(f"color: {TEXT_FADE};")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER}; border-radius: 8px; background: {CARD};
            }}
            QTabBar::tab {{
                padding: 8px 18px; font-size: 11px; font-family: 'Segoe UI';
                color: {TEXT_MED}; background: transparent;
            }}
            QTabBar::tab:selected {{
                color: {SAFFRON}; font-weight: bold;
                border-bottom: 2px solid {SAFFRON};
            }}
            QTabBar::tab:hover {{ color: {TEXT}; }}
        """)
        layout.addWidget(self.tabs)
        self.load_data()

    def _make_scroll_tab(self, entries: list) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        for entry in entries:
            vbox.addWidget(MedicineCard(entry))
        scroll.setWidget(container)
        return scroll

    def load_data(self):
        knowledge_dir = (
            Path(__file__).parent.parent / "backend" / "data" / "knowledge" / "medications"
        )
        if not knowledge_dir.exists():
            self.tabs.addTab(QLabel("  No data found."), "Error")
            return

        category_map: dict = {}
        for fpath in sorted(knowledge_dir.rglob("*.json")):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                cat = data.get("category", fpath.stem).replace("_", " ").title()
                entries = data.get("entries", [])
                if entries:
                    category_map[cat] = entries
            except Exception:
                pass

        if not category_map:
            self.tabs.addTab(QLabel("  No entries found."), "Empty")
            return

        for cat, entries in category_map.items():
            self.tabs.addTab(self._make_scroll_tab(entries), f"{cat}  ({len(entries)})")


# ── Health Dashboard ─────────────────────────────────────────────────
class HealthDashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Health Dashboard")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(title)

        tip_frame = QFrame()
        tip_frame.setStyleSheet(
            f"background-color: {SAFFRON_BG}; border: 1px solid {SAFFRON}; border-radius: 10px;"
        )
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(14, 12, 14, 12)
        tip_layout.setSpacing(10)
        tip_ico = QLabel()
        tip_ico.setPixmap(qta.icon("fa5s.sun", color=SAFFRON).pixmap(20, 20))
        tip_ico.setStyleSheet("border: none; background: transparent;")
        tip_ico.setFixedWidth(24)
        tip_ico.setAlignment(Qt.AlignmentFlag.AlignTop)
        tip_layout.addWidget(tip_ico)
        self.tip_label = QLabel()
        self.tip_label.setWordWrap(True)
        self.tip_label.setFont(QFont("Segoe UI", 11))
        self.tip_label.setStyleSheet(f"color: #7A3500; border: none; background: transparent;")
        tip_layout.addWidget(self.tip_label, stretch=1)
        layout.addWidget(tip_frame)
        self._update_tip()

        row = QHBoxLayout()

        hyd = QFrame()
        hyd.setStyleSheet(f"background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px;")
        hl = QVBoxLayout(hyd)
        hl.addWidget(self._section_title("fa5s.tint", "Daily Hydration", "#1e3a8a", "#2563EB"))
        self.water_count = 0
        self.water_lbl = QLabel(f"{self.water_count} Glasses")
        self.water_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.water_lbl.setStyleSheet("color: #2563EB; border: none;")
        self.water_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(self.water_lbl)
        btn = QPushButton("+ Drink Water")
        btn.setStyleSheet(
            f"QPushButton {{ background: {DAL}; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #0284C7; }}"
        )
        btn.clicked.connect(self._add_water)
        hl.addWidget(btn)
        row.addWidget(hyd)

        symp = QFrame()
        symp.setStyleSheet(f"background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px;")
        sl = QVBoxLayout(symp)
        sl.addWidget(self._section_title("fa5s.clipboard-list", "Symptom Logger", "#9A3412", "#C05621"))
        self.symp_input = QTextEdit()
        self.symp_input.setPlaceholderText("Log your symptoms here…")
        self.symp_input.setStyleSheet(
            f"QTextEdit {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px; color: {TEXT}; }}"
        )
        sl.addWidget(self.symp_input)
        sbtn = QPushButton("Save Symptom")
        sbtn.setStyleSheet(
            f"QPushButton {{ background: {SAFFRON}; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #3F3F46; }}"
        )
        sbtn.clicked.connect(self._save_symptom)
        sl.addWidget(sbtn)
        row.addWidget(symp)

        layout.addLayout(row)
        layout.addStretch()

    def _section_title(self, icon_name: str, text: str, text_color: str, icon_color: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        ico = QLabel()
        ico.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(16, 16))
        ico.setStyleSheet("border: none; background: transparent;")
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
        hl.addWidget(ico)
        hl.addWidget(lbl)
        hl.addStretch()
        return row

    def _update_tip(self):
        tips = {
            "chilla_kalan":  "Winter is here! Drink Kahwa to stay warm, protect joints with mustard oil.",
            "chilla_khurd":  "Late winter — keep warm, avoid drafts.",
            "chilla_bachha": "Winter easing — guard cold nights, watch for spring allergies.",
            "sonth":         "Spring arrived! Watch for pollen allergies, keep Cetirizine handy.",
            "wahaar":        "Early summer — enjoy fresh local vegetables to boost immunity.",
            "grind":         "Summer peak! Stay well-hydrated and prefer light, seasonal foods.",
            "harud":         "Harvest season — stock up on walnuts for Omega-3!",
            "early_winter":  "Winter approaching — begin warm diet, check your Kangri for CO safety.",
        }
        try:
            ctx = get_context()
            sid = ctx["season"]["id"]
            tip = tips.get(sid, "Stay healthy and drink plenty of water today!")
        except Exception:
            tip = "Stay healthy and drink plenty of water today!"
        self.tip_label.setText(f"Seasonal Tip: {tip}")

    def _add_water(self):
        self.water_count += 1
        self.water_lbl.setText(f"{self.water_count} Glasses")

    def _save_symptom(self):
        text = self.symp_input.toPlainText().strip()
        if text:
            try:
                with open("f:\\watan-sehat\\symptoms_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{date.today().isoformat()}] {text}\n")
                self.symp_input.clear()
                QMessageBox.information(self, "Saved", "Symptom logged successfully.")
            except Exception as exc:
                QMessageBox.warning(self, "Error", str(exc))


# ── Draggable header widget ───────────────────────────────────────────
class _DragHandle(QWidget):
    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._window = window
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ── Chat session ──────────────────────────────────────────────────────
@dataclass
class ChatSession:
    title: str
    messages: list = field(default_factory=list)
    timestamp: str = ""


# ── Main window ───────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Health Companion — Sehat Saathi")
        self.resize(1024, 600)  # Standard Pi Touchscreen size
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()  # Ensure it fills the screen on Pi

        self.ai = AIBridge()
        self.chat_sessions: list[ChatSession] = []
        self.current_messages: list[dict] = []

        self._recorder: VoiceRecorderThread | None = None
        self._tts_thread: TTSSpeakerThread | None = None
        self._is_listening = False

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {BG}; }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 24px; margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {BORDER}; min-height: 40px; border-radius: 12px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        self._build_sidebar()
        self._build_main_area()

        self.splitter.addWidget(self.sidebar_widget)
        self.splitter.addWidget(self.main_area)
        self.splitter.setSizes([280, 744])  # Wider sidebar for touch targets
        
        self._setup_system_tray()

    def _setup_system_tray(self):
        QApplication.setQuitOnLastWindowClosed(False)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(qta.icon("fa5s.heartbeat", color=DAL))
        self.tray_icon.setToolTip("Health Companion Companion")
        
        tray_menu = QMenu()
        
        show_action = QAction("Show Application", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        
        remind_water = QAction("Remind: Drink Water", self)
        remind_water.triggered.connect(lambda: self.tray_icon.showMessage("Hydration Reminder", "It's time to drink some water!", QSystemTrayIcon.MessageIcon.Information, 5000))
        tray_menu.addAction(remind_water)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    # ── Sidebar ───────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setStyleSheet(
            f"background-color: {SIDEBAR}; border-right: 1px solid {BORDER};"
        )
        sb = QVBoxLayout(self.sidebar_widget)
        sb.setContentsMargins(16, 20, 16, 20)
        sb.setSpacing(12)

        brand_frame = QFrame()
        brand_frame.setStyleSheet(
            f"background: {SAFFRON_BG}; border: 1px solid {SAFFRON}; border-radius: 10px;"
        )
        bf = QVBoxLayout(brand_frame)
        bf.setContentsMargins(12, 10, 12, 10)
        bf.setSpacing(2)
        b1 = QLabel("Health Companion")
        b1.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        b1.setStyleSheet(f"color: {SAFFRON}; border: none;")
        b2 = QLabel("Sehat Saathi — Health Companion")
        b2.setFont(QFont("Segoe UI", 9))
        b2.setStyleSheet(f"color: {TEXT_MED}; border: none;")
        bf.addWidget(b1)
        bf.addWidget(b2)
        sb.addWidget(brand_frame)
        sb.addSpacing(8)

        for icon_name, label, color, bg, border_clr, action in [
            ("fa5s.plus",      "New Chat",         TEXT,   CARD,      BORDER,    self.start_new_chat),
            ("fa5s.clipboard-list", "Symptom Triage", CHINAR, "#FFF1F2", "#FECDD3", lambda: self.stacked_widget.setCurrentIndex(3)),
            ("fa5s.lock",      "Health Vault",      DAL,   "#F0F9FF", "#BAE6FD", lambda: self.stacked_widget.setCurrentIndex(4)),
            ("fa5s.medkit",    "Medical Kit",       CHINAR, "#FFF1F2", "#FECDD3", lambda: self.stacked_widget.setCurrentIndex(1)),
            ("fa5s.heartbeat", "Health Dashboard",  PINE,   "#F0FDF4", "#BBF7D0", lambda: self.stacked_widget.setCurrentIndex(2)),
        ]:
            btn = QPushButton(f"  {label}")
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setIconSize(qta.icon(icon_name).actualSize(btn.size()) * 1.5)  # Larger icons
            btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))  # Larger font for touch
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border: 1px solid {border_clr};
                    border-radius: 12px; padding: 16px 12px;
                    color: {TEXT}; text-align: left;
                }}
                QPushButton:hover {{ border-color: {SAFFRON}; }}
                QPushButton:pressed {{ background-color: {BORDER}; }}
            """)
            btn.clicked.connect(action)
            sb.addWidget(btn)

        sb.addSpacing(6)
        history_label = QLabel("Recent Chats")
        history_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        history_label.setStyleSheet(f"color: {TEXT_FADE}; padding: 2px 4px 0 4px; letter-spacing: 0.5px;")
        sb.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"""
            QListWidget {{ border: none; background: transparent; }}
            QListWidget::item {{ padding: 9px 8px; border-radius: 8px; color: {TEXT}; }}
            QListWidget::item:hover {{ background-color: {BORDER}; }}
            QListWidget::item:selected {{ background-color: {SAFFRON_BG}; color: {SAFFRON}; }}
        """)
        self.history_list.setFont(QFont("Segoe UI", 10))
        self.history_list.itemClicked.connect(self.restore_session)
        sb.addWidget(self.history_list, stretch=1)

        self.clear_history_btn = QPushButton("Clear History")
        self.clear_history_btn.setFont(QFont("Segoe UI", 9))
        self.clear_history_btn.setStyleSheet(f"""
            QPushButton {{ border: none; background: transparent; color: {TEXT_FADE}; padding: 4px; }}
            QPushButton:hover {{ color: {CHINAR}; }}
        """)
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.clear_history_btn.hide()
        sb.addWidget(self.clear_history_btn)

    # ── Main area ─────────────────────────────────────────────────────
    def _build_main_area(self):
        self.main_area = QWidget()
        self.main_area.setStyleSheet(f"background-color: {BG};")
        main_layout = QVBoxLayout(self.main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._build_header())

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, stretch=1)

        self.stacked_widget.addWidget(self._build_chat_screen())  # 0
        self.stacked_widget.addWidget(MedicalKitWidget())          # 1
        self.stacked_widget.addWidget(HealthDashboardWidget())     # 2
        self.stacked_widget.addWidget(TriageWizardWidget())        # 3
        self.stacked_widget.addWidget(HealthVaultWidget())         # 4

    def _build_header(self) -> QWidget:
        header = _DragHandle(self)
        header.setFixedHeight(80)
        header.setStyleSheet(f"background-color: {CARD}; border-bottom: 1px solid {BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 12, 0)
        hl.setSpacing(12)

        self.voice_orb = VoiceOrb(size=46)
        self.voice_orb.setToolTip("AI status")
        hl.addWidget(self.voice_orb)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        t1 = QLabel("Health Companion")
        t1.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {TEXT}; border: none;")
        t2 = QLabel("Kashmir Health Companion")
        t2.setFont(QFont("Segoe UI", 9))
        t2.setStyleSheet(f"color: {TEXT_FADE}; border: none;")
        title_vbox.addWidget(t1)
        title_vbox.addWidget(t2)
        hl.addLayout(title_vbox)

        hl.addStretch()

        si = get_season_info()
        sev_color = SEVERITY_COLORS.get(si["severity"], SAFFRON)
        season_frame = QFrame()
        season_frame.setStyleSheet(
            f"background: {SAFFRON_BG}; border: 1px solid {BORDER}; border-radius: 20px;"
        )
        sf = QHBoxLayout(season_frame)
        sf.setContentsMargins(12, 6, 12, 6)
        sf.setSpacing(6)

        dot = QLabel("●")
        dot.setFont(QFont("Segoe UI", 10))
        dot.setStyleSheet(f"color: {sev_color}; border: none;")

        sn_en = QLabel(si["name_en"])
        sn_en.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sn_en.setStyleSheet(f"color: {TEXT}; border: none;")

        sf.addWidget(dot)
        sf.addWidget(sn_en)
        hl.addWidget(season_frame)

        hl.addSpacing(10)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(0)
        greet_lbl = QLabel(get_greeting())
        greet_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        greet_lbl.setStyleSheet(f"color: {TEXT}; border: none;")
        date_lbl = QLabel(datetime.now().strftime("%b %d, %Y"))
        date_lbl.setFont(QFont("Segoe UI", 9))
        date_lbl.setStyleSheet(f"color: {TEXT_FADE}; border: none;")
        info_vbox.addWidget(greet_lbl)
        info_vbox.addWidget(date_lbl)
        hl.addLayout(info_vbox)

        hl.addSpacing(14)

        win_btn_specs = [
            ("fa5s.minus",  "Minimize", self.showMinimized,   "#F5C542", "#E0A800"),
            ("fa5s.expand", "Maximize", self.toggle_maximize, "#5CB85C", "#3E8E3E"),
            ("fa5s.times",  "Close",    self.hide,           "#E05C5C", "#C0392B"),
        ]
        for icon_name, tooltip, action, bg_clr, hover_clr in win_btn_specs:
            btn = QPushButton(qta.icon(icon_name, color="white", options=[{"scale_factor": 0.6}]), "")
            btn.setFixedSize(20, 20)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_clr};
                    border-radius: 10px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {hover_clr}; }}
            """)
            btn.setToolTip(tooltip)
            btn.clicked.connect(action)
            hl.addWidget(btn)

        return header

    # ── Chat screen ───────────────────────────────────────────────────
    def _build_chat_screen(self) -> QWidget:
        screen = QWidget()
        screen.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setContentsMargins(40, 40, 40, 24)
        self.chat_layout.setSpacing(18)
        self.scroll_area.setWidget(self.chat_widget)

        self.thinking_bubble = None
        self._add_welcome_message()
        layout.addWidget(self.scroll_area, stretch=1)

        # Voice status bar
        self.voice_status_bar = QFrame()
        self.voice_status_bar.setStyleSheet(
            f"background: {SAFFRON_BG}; border-top: 1px solid {SAFFRON};"
        )
        vsbl = QHBoxLayout(self.voice_status_bar)
        vsbl.setContentsMargins(40, 8, 40, 8)
        self.voice_status_lbl = QLabel("Listening… tap mic to stop")
        self.voice_status_lbl.setFont(QFont("Segoe UI", 10))
        self.voice_status_lbl.setStyleSheet(f"color: {SAFFRON}; border: none;")
        vsbl.addWidget(self.voice_status_lbl)
        vsbl.addStretch()
        self.voice_status_bar.hide()
        layout.addWidget(self.voice_status_bar)

        # Input row
        input_wrapper = QWidget()
        input_wrapper.setStyleSheet("background: transparent;")
        iw_layout = QVBoxLayout(input_wrapper)
        iw_layout.setContentsMargins(40, 8, 40, 24)

        input_box = QWidget()
        input_box.setStyleSheet(f"""
            QWidget {{
                background-color: {CARD};
                border: 1.5px solid {BORDER};
                border-radius: 16px;
            }}
        """)
        ib_layout = QHBoxLayout(input_box)
        ib_layout.setContentsMargins(10, 6, 10, 6)
        ib_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.text_input = ChatInputEdit()
        self.text_input.setFixedHeight(50)
        self.text_input.return_pressed = self.send_message

        self.mic_btn = MicButton()
        self.mic_btn.clicked.connect(self._toggle_voice)

        self.send_btn = QPushButton(qta.icon("fa5s.arrow-up", color="white"), "")
        self.send_btn.setFixedSize(38, 38)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {TEXT}; border-radius: 19px; border: none; }}
            QPushButton:hover {{ background-color: {SAFFRON}; }}
            QPushButton:disabled {{ background-color: {BORDER}; }}
        """)
        self.send_btn.clicked.connect(self.send_message)

        ib_layout.addWidget(self.text_input, stretch=1)
        ib_layout.addWidget(self.mic_btn)
        ib_layout.addSpacing(4)
        ib_layout.addWidget(self.send_btn)
        iw_layout.addWidget(input_box)
        layout.addWidget(input_wrapper)

        return screen

    # ── Voice ─────────────────────────────────────────────────────────
    def _toggle_voice(self):
        # If speaking → interrupt TTS
        if self._tts_thread and self._tts_thread.isRunning():
            self._tts_thread.stop_speaking()
            return
        # If listening → stop and process
        if self._is_listening:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self._recorder and self._recorder.isRunning():
            return
        self._is_listening = True
        self.mic_btn.set_listening(True)
        self.voice_status_bar.show()
        self.voice_status_lbl.setText("Listening… tap mic to stop")
        self.voice_orb.set_state("listening")

        self._recorder = VoiceRecorderThread(self)
        self._recorder.state_changed.connect(self._on_voice_state)
        self._recorder.transcript_ready.connect(self._on_transcript)
        self._recorder.start()

    def _stop_recording(self):
        if self._recorder:
            self._recorder.stop()
        self._is_listening = False
        self.mic_btn.set_listening(False)
        self.voice_status_lbl.setText("Processing…")

    def _on_voice_state(self, state: str):
        if state == "processing":
            self.voice_status_lbl.setText("Transcribing…")
            self.voice_orb.set_state("speaking")
        elif state == "idle":
            self.voice_status_bar.hide()
            self.voice_orb.set_state("idle")

    def _on_transcript(self, text: str):
        self.voice_status_bar.hide()
        self.voice_orb.set_state("idle")
        self.text_input.setPlainText(text)
        self.send_message()

    def _speak_response(self, text: str):
        # Interrupt any current TTS before starting new
        if self._tts_thread and self._tts_thread.isRunning():
            self._tts_thread.stop_speaking()
            self._tts_thread.wait(300)
        self._tts_thread = TTSSpeakerThread(text, rate=165, parent=self)
        self._tts_thread.speaking_done.connect(self._on_tts_done)
        self.voice_orb.set_state("speaking")
        self.mic_btn.set_speaking(True)
        self._tts_thread.start()

    def _on_tts_done(self):
        self.voice_orb.set_state("idle")
        self.mic_btn.set_speaking(False)

    # ── Session management ────────────────────────────────────────────
    def _add_welcome_message(self):
        msg = "Hello. How can I assist you with your health today?\nYou can type a question or press the mic to speak."
        self.add_bot_message(msg)

    def start_new_chat(self):
        user_msgs = [m for m in self.current_messages if m["is_user"]]
        if user_msgs:
            title = user_msgs[0]["text"][:40] + ("…" if len(user_msgs[0]["text"]) > 40 else "")
            self.chat_sessions.insert(
                0,
                ChatSession(title, list(self.current_messages), datetime.now().strftime("%H:%M")),
            )
            self._refresh_history()

        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_messages.clear()
        self.thinking_bubble = None
        self._add_welcome_message()
        self.stacked_widget.setCurrentIndex(0)
        self.text_input.setFocus()

    def _refresh_history(self):
        self.history_list.clear()
        for s in self.chat_sessions:
            item = QListWidgetItem(f"  {s.title}")
            item.setData(Qt.ItemDataRole.UserRole, s)
            item.setToolTip(s.timestamp)
            self.history_list.addItem(item)
        self.clear_history_btn.setVisible(len(self.chat_sessions) > 0)

    def restore_session(self, item: QListWidgetItem):
        session: ChatSession = item.data(Qt.ItemDataRole.UserRole)
        if not session:
            return

        user_msgs = [m for m in self.current_messages if m["is_user"]]
        if user_msgs:
            title = user_msgs[0]["text"][:40] + ("…" if len(user_msgs[0]["text"]) > 40 else "")
            existing = ChatSession(title, list(self.current_messages), datetime.now().strftime("%H:%M"))
            if not any(s.messages == existing.messages for s in self.chat_sessions):
                self.chat_sessions.insert(1, existing)

        while self.chat_layout.count():
            i = self.chat_layout.takeAt(0)
            if i.widget():
                i.widget().deleteLater()

        self.current_messages = list(session.messages)
        self.thinking_bubble = None

        for msg in session.messages:
            bubble = ChatBubble(msg["text"], is_user=msg["is_user"], source=msg.get("source", ""))
            self.chat_layout.addWidget(bubble)

        self.stacked_widget.setCurrentIndex(0)
        self._scroll_to_bottom()

    def clear_history(self):
        self.chat_sessions.clear()
        self.history_list.clear()
        self.clear_history_btn.hide()

    # ── Message helpers ───────────────────────────────────────────────
    def add_user_message(self, text: str):
        bubble = ChatBubble(text, is_user=True)
        self.chat_layout.addWidget(bubble)
        self.current_messages.append({"text": text, "is_user": True, "source": ""})
        self._scroll_to_bottom()

    def add_bot_message(self, text: str, source: str = ""):
        if self.thinking_bubble:
            self.chat_layout.removeWidget(self.thinking_bubble)
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        bubble = ChatBubble(text, is_user=False, source=source)
        self.chat_layout.addWidget(bubble)
        self.current_messages.append({"text": text, "is_user": False, "source": source})
        self._scroll_to_bottom()

    def show_thinking(self):
        self.thinking_bubble = ChatBubble("Thinking…", is_user=False)
        self.chat_layout.addWidget(self.thinking_bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QApplication.processEvents()
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Send / AI ─────────────────────────────────────────────────────
    def send_message(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            return

        # Stop any ongoing TTS before sending new message
        if self._tts_thread and self._tts_thread.isRunning():
            self._tts_thread.stop_speaking()

        self.text_input.clear()
        self.text_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.mic_btn.setEnabled(False)

        self.add_user_message(text)
        self.voice_orb.set_state("listening")
        self.show_thinking()

        QTimer.singleShot(80, lambda: self._call_ai(text))

    def _call_ai(self, text: str):
        self.voice_orb.set_state("speaking")
        self.ai.ask(text, self.handle_ai_response)

    def handle_ai_response(self, response_data: dict):
        self.voice_orb.set_state("idle")
        answer = response_data.get("response_text", "I'm sorry, an error occurred.")
        source = response_data.get("source", "")
        self.add_bot_message(answer, source=source)

        self.text_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.mic_btn.setEnabled(True)
        self.text_input.setFocus()

        # Always speak the response (tap mic or send button to interrupt)
        self._speak_response(answer)
        self._recorder = None

    # ── Window controls ───────────────────────────────────────────────
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
