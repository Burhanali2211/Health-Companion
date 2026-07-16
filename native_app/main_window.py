import sys
import tempfile
import re
import json
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
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction

import qtawesome as qta


def custom_excepthook(exc_type, exc_value, exc_traceback):
    with open("crash.log", "w") as f:
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
    recording_finished = pyqtSignal(str)      # Emits temp file path
    amplitude_changed = pyqtSignal(float)     # Emits current amplitude level

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False
        self.temp_dir = Path(tempfile.gettempdir())
        self.filepath = self.temp_dir / "kiosk_mic_input.wav"

    def stop_recording(self):
        self._stop_requested = True

    def run(self):
        try:
            import sounddevice as sd
            import scipy.io.wavfile as wavfile
            import numpy as np
        except ImportError as e:
            print(f"[recorder] Missing voice dependencies: {e}")
            self.recording_finished.emit("")
            return

        self._stop_requested = False
        sample_rate = 16000
        channels = 1
        chunk_size = 1024
        recording_data = []

        try:
            # Open stream
            with sd.InputStream(samplerate=sample_rate, channels=channels, dtype='int16') as stream:
                while not self._stop_requested:
                    data, overflowed = stream.read(chunk_size)
                    recording_data.append(data.copy())
                    if len(data) > 0:
                        amplitude = float(np.max(np.abs(data)) / 32768.0)
                        self.amplitude_changed.emit(amplitude)
            
            # Save to WAV
            if recording_data:
                full_data = np.concatenate(recording_data, axis=0)
                wavfile.write(self.filepath, sample_rate, full_data)
                self.recording_finished.emit(str(self.filepath))
            else:
                self.recording_finished.emit("")
        except Exception as e:
            print(f"[recorder] Error recording audio: {e}")
            self.recording_finished.emit("")


class TranscribeWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, filepath: str, backend_url: str = None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.backend_url = backend_url

    def run(self):
        try:
            if self.backend_url:
                import urllib.request
                import json
                import uuid
                
                boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
                
                with open(self.filepath, "rb") as f:
                    file_bytes = f.read()
                
                body = (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="file"; filename="stt_audio.wav"\r\n'
                    f"Content-Type: audio/wav\r\n\r\n"
                ).encode("utf-8")
                
                body += file_bytes
                body += f"\r\n--{boundary}--\r\n".encode("utf-8")
                
                url = f"{self.backend_url}/api/voice/stt"
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                        "Content-Length": str(len(body))
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if res_data.get("status") == "ok" and res_data.get("data"):
                        self.finished.emit(res_data["data"].get("transcript", ""))
                    else:
                        raise Exception(res_data.get("message", "API error"))
            else:
                from voice.stt import transcribe
                with open(self.filepath, "rb") as f:
                    audio_bytes = f.read()
                res = transcribe(audio_bytes, language="auto")
                text = res.get("text", "")
                self.finished.emit(text)
        except Exception as e:
            print(f"[transcribe] Error during voice STT: {e}")
            self.finished.emit("")


# ── Animated mic button ──────────────────────────────────────────────
class MicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.is_recording = False
        self.is_speaking = False
        self.update_style()

    def set_recording(self, state: bool):
        self.is_recording = state
        self.update_style()

    def set_speaking(self, state: bool):
        self.is_speaking = state
        self.update_style()

    def update_style(self):
        if self.is_recording:
            self.setIcon(qta.icon("fa5s.stop", color="white", options=[{"scale_factor": 0.6}]))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CHINAR};
                    border-radius: 19px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #C0392B; }}
            """)
        elif self.is_speaking:
            self.setIcon(qta.icon("fa5s.volume-up", color="white", options=[{"scale_factor": 0.6}]))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DAL};
                    border-radius: 19px;
                    border: none;
                }}
            """)
        else:
            self.setIcon(qta.icon("fa5s.microphone", color="white", options=[{"scale_factor": 0.6}]))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {USER_BUBBLE};
                    border-radius: 19px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {PINE}; }}
            """)


# ── TTS speaker thread ────────────────────────────────────────────────
class TTSSpeakerThread(QThread):
    speaking_done = pyqtSignal()

    VOICE_UR = "ur-PK-UzmaNeural"   # Urdu/Kashmiri text
    VOICE_EN = "en-US-JennyNeural"  # English text fallback

    _URDU_RE = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')

    def __init__(self, text: str, backend_url: str = None, rate: int = 165, parent=None):
        super().__init__(parent)
        self.text = text
        self.backend_url = backend_url
        self.voice = self.VOICE_UR if self._URDU_RE.search(text) else self.VOICE_EN
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
            import miniaudio
            import sounddevice as sd
            import numpy as np

            if self.backend_url:
                import urllib.request
                import json
                
                url = f"{self.backend_url}/api/voice/tts"
                data = json.dumps({
                    "text": self.text,
                    "language": "auto",
                    "age_mode": "jawaan"
                }).encode("utf-8")
                
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    audio_bytes = response.read()
                
                if not audio_bytes or self._stop_requested:
                    return

                decoded = miniaudio.decode(
                    audio_bytes,
                    output_format=miniaudio.SampleFormat.FLOAT32,
                    nchannels=1,
                    sample_rate=24000,
                )
                samples = np.frombuffer(decoded.samples, dtype=np.float32)
                sd.play(samples, samplerate=24000)
                sd.wait()
            else:
                import asyncio
                import edge_tts

                async def _stream():
                    communicate = edge_tts.Communicate(
                        self.text, voice=self.voice, rate=self.rate_str
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
            print(f"[tts] Error playing speech: {exc}")
        finally:
            self.speaking_done.emit()


# ── Animated mic button ──────────────────────────────────────────────


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

        frame = QFrame()
        frame.setMaximumWidth(520)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 12, 16, 12)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 12))
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setStyleSheet("background: transparent; border: none;")
        
        frame_layout.addWidget(self.label)

        if is_user:
            self.label.setStyleSheet(self.label.styleSheet() + " color: white;")
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {USER_BUBBLE};
                    border-radius: 18px;
                    border-top-right-radius: 4px;
                }}
            """)
            layout.addStretch()
            layout.addWidget(frame)
        else:
            self.label.setStyleSheet(self.label.styleSheet() + f" color: {TEXT};")
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {BOT_BUBBLE};
                    border-radius: 18px;
                    border-top-left-radius: 4px;
                    border: 1px solid {BORDER};
                }}
            """)
            vbox.addWidget(frame)

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
    def __init__(self, backend_url: str = None):
        super().__init__()
        import os
        self.backend_url = backend_url or os.environ.get("WATAN_BACKEND_URL")
        self.setWindowTitle("Health Companion")
        self.resize(1024, 600)  # Standard Pi Touchscreen size
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()  # Ensure it fills the screen on Pi

        self.ai = AIBridge(backend_url=self.backend_url)
        self.chat_sessions: list[ChatSession] = []
        self.current_messages: list[dict] = []

        self._tts_thread: TTSSpeakerThread | None = None

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
        self.splitter.setSizes([180, 844])
        
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
        
        sync_action = QAction("Sync Offline Data (USB)", self)
        sync_action.triggered.connect(self.simulate_offline_sync)
        tray_menu.addAction(sync_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def simulate_offline_sync(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Offline Data Sync")
        msg.setText("Scanning for authorized ASHA Worker USB Drive...")
        msg.setInformativeText("Successfully synced updated medical guidelines, seasonal alerts, and security patches from USB. The kiosk is now up to date.")
        msg.setStyleSheet(f"QMessageBox {{ background-color: {CARD}; }} QLabel {{ color: {TEXT}; font-size: 14px; }}")
        msg.exec()

    def show_sos_modal(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Emergency SOS / ہنگامی حالت")
        msg.setText("<h2>Medical Emergency?</h2><br><b>Call 108</b> for Ambulance<br><b>Call 104</b> for J&K Health Helpline")
        msg.setInformativeText("For immediate clinical diagnosis or acute emergencies, this kiosk cannot replace a doctor. Please contact emergency services immediately.<br><br>ہنگامی حالت کے لئے 108 (ایمبولینس) یا 104 (ہیلتھ ہیلپ لائن) پر کال کریں۔")
        msg.setStyleSheet(f"QMessageBox {{ background-color: {CARD}; }} QLabel {{ color: {TEXT}; font-size: 14px; }}")
        msg.exec()

    # ── Sidebar ───────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(180)
        self.sidebar_widget.setStyleSheet(
            f"background-color: {SIDEBAR}; border-right: 1px solid {BORDER};"
        )
        sb = QVBoxLayout(self.sidebar_widget)
        sb.setContentsMargins(12, 12, 12, 12)
        sb.setSpacing(10)

        brand_frame = QFrame()
        brand_frame.setStyleSheet(
            f"background: {SAFFRON_BG}; border: 1px solid {SAFFRON}; border-radius: 10px;"
        )
        bf = QVBoxLayout(brand_frame)
        bf.setContentsMargins(8, 8, 8, 8)
        bf.setSpacing(2)
        b1 = QLabel("Health Companion")
        b1.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        b1.setStyleSheet(f"color: {SAFFRON}; border: none;")
        b2 = QLabel("AI Assistant")
        b2.setFont(QFont("Segoe UI", 9))
        b2.setStyleSheet(f"color: {TEXT_MED}; border: none;")
        bf.addWidget(b1)
        bf.addWidget(b2)
        sb.addWidget(brand_frame)

        for icon_name, label, color, bg, border_clr, action in [
            ("fa5s.phone-alt", "SOS 104", CHINAR, "#FEF2F2", "#FECACA", self.show_sos_modal),
            ("fa5s.plus",      "New",      TEXT,   CARD,      BORDER,    self.start_new_chat),
            ("fa5s.clipboard-list", "Triage", CHINAR, "#FFF1F2", "#FECDD3", lambda: self.stacked_widget.setCurrentIndex(3)),
            ("fa5s.lock",      "Vault",      DAL,   "#F0F9FF", "#BAE6FD", lambda: self.stacked_widget.setCurrentIndex(4)),
            ("fa5s.medkit",    "Kit",    CHINAR, "#FFF1F2", "#FECDD3", lambda: self.stacked_widget.setCurrentIndex(1)),
            ("fa5s.heartbeat", "Dash",  PINE,   "#F0FDF4", "#BBF7D0", lambda: self.stacked_widget.setCurrentIndex(2)),
        ]:
            btn = QPushButton(f"  {label}")
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg}; border: 1px solid {border_clr};
                    border-radius: 8px; padding: 12px 8px;
                    text-align: left; font-size: 11pt; color: {color}; font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {border_clr}; }}
            """)
            btn.clicked.connect(action)
            sb.addWidget(btn)

        # Past Chats Header
        history_label = QLabel("Recent Chats")
        history_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        history_label.setStyleSheet(f"color: {TEXT_MED}; margin-top: 10px; border: none; background: transparent;")
        sb.addWidget(history_label)

        # History List
        self.history_list = QListWidget()
        self.history_list.setFont(QFont("Segoe UI", 10))
        self.history_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {TEXT};
            }}
            QListWidget::item {{
                padding: 6px 4px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {SAFFRON_BG};
                color: {SAFFRON};
                font-weight: bold;
            }}
        """)
        self.history_list.itemClicked.connect(self.restore_session)
        sb.addWidget(self.history_list, stretch=1)

        # Clear History Button
        self.clear_history_btn = QPushButton("Clear History")
        self.clear_history_btn.setIcon(qta.icon("fa5s.trash-alt", color=CHINAR))
        self.clear_history_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {CHINAR};
                font-size: 9pt;
                font-weight: bold;
                padding: 6px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #FEF2F2;
                border-radius: 4px;
            }}
        """)
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.clear_history_btn.hide()  # Hidden initially
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

        self.send_btn = QPushButton(qta.icon("fa5s.arrow-up", color="white"), "")
        self.send_btn.setFixedSize(38, 38)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {TEXT}; border-radius: 19px; border: none; }}
            QPushButton:hover {{ background-color: {SAFFRON}; }}
            QPushButton:disabled {{ background-color: {BORDER}; }}
        """)
        self.send_btn.clicked.connect(self.send_message)

        self.mic_btn = MicButton()
        self.mic_btn.clicked.connect(self.toggle_recording)
        self.voice_orb.clicked.connect(self.toggle_recording)

        ib_layout.addWidget(self.text_input, stretch=1)
        ib_layout.addWidget(self.mic_btn)
        ib_layout.addWidget(self.send_btn)
        iw_layout.addWidget(input_box)
        layout.addWidget(input_wrapper)

        return screen

    # ── Voice Recording & STT Methods ─────────────────────────────────
    def toggle_recording(self):
        if self._tts_thread and self._tts_thread.isRunning():
            try:
                self._tts_thread.speaking_done.disconnect(self._on_tts_done)
            except (TypeError, RuntimeError):
                pass
            self._tts_thread.stop_speaking()
            self._tts_thread.wait(400)
            self._on_tts_done()
            return

        if hasattr(self, "_recorder_thread") and self._recorder_thread.isRunning():
            self.voice_orb.set_state("idle")
            self.mic_btn.set_recording(False)
            self.text_input.setPlaceholderText("Type a health question or press the mic to speak…")
            self._recorder_thread.stop_recording()
        else:
            self.voice_orb.set_state("listening")
            self.mic_btn.set_recording(True)
            self.text_input.setPlaceholderText("Listening... Speak now...")
            self._recorder_thread = VoiceRecorderThread(self)
            self._recorder_thread.recording_finished.connect(self.process_recorded_audio)
            self._recorder_thread.amplitude_changed.connect(self.handle_recording_amplitude)
            self._recorder_thread.start()

    def handle_recording_amplitude(self, amplitude: float):
        pass

    def process_recorded_audio(self, filepath: str):
        self.mic_btn.set_recording(False)
        self.text_input.setPlaceholderText("Type a health question or press the mic to speak…")
        if not filepath:
            self.voice_orb.set_state("idle")
            return

        self.voice_orb.set_state("processing")
        self.show_thinking()

        self._transcribe_thread = TranscribeWorker(filepath, backend_url=self.backend_url, parent=self)
        self._transcribe_thread.finished.connect(self.handle_transcription_result)
        self._transcribe_thread.start()

    def handle_transcription_result(self, text: str):
        self.voice_orb.set_state("idle")
        if self.thinking_bubble:
            self.chat_layout.removeWidget(self.thinking_bubble)
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        if text.strip():
            self.add_user_message(text)
            self.show_thinking()
            QTimer.singleShot(80, lambda: self._call_ai(text))
        else:
            QMessageBox.information(self, "Voice Input", "No speech detected. Please try again.")

    # ── TTS ───────────────────────────────────────────────────────────
    def _speak_response(self, text: str):
        # Interrupt any current TTS before starting new
        if self._tts_thread and self._tts_thread.isRunning():
            try:
                self._tts_thread.speaking_done.disconnect(self._on_tts_done)
            except (TypeError, RuntimeError):
                pass
            self._tts_thread.stop_speaking()
            self._tts_thread.wait(400)
        self._tts_thread = TTSSpeakerThread(text, backend_url=self.backend_url, rate=165, parent=self)
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

        self.add_user_message(text)
        self.show_thinking()

        QTimer.singleShot(80, lambda: self._call_ai(text))

    def _call_ai(self, text: str):
        self.voice_orb.set_state("speaking")
        self.ai.ask(text, self.handle_ai_response, self.handle_ai_error)

    def handle_ai_response(self, response_data: dict):
        self.voice_orb.set_state("idle")
        answer = response_data.get("response_text", "I'm sorry, an error occurred.")
        source = response_data.get("source", "")
        self.add_bot_message(answer, source=source)

        self.text_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.text_input.setFocus()

        self._speak_response(answer)

    def handle_ai_error(self, err_msg: str):
        self.voice_orb.set_state("idle")
        self.add_bot_message(f"Connection Error: Could not connect to backend server.\nDetails: {err_msg}", source="error")

        self.text_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.text_input.setFocus()

    # ── Window controls ───────────────────────────────────────────────
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Health Companion Client Kiosk")
    parser.add_argument("--server", type=str, default=None, help="Remote backend server URL (e.g. http://192.168.1.232:8000)")
    args, unknown = parser.parse_known_args()

    app = QApplication(sys.argv)
    window = MainWindow(backend_url=args.server)
    window.show()
    sys.exit(app.exec())
