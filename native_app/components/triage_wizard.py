import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QStackedWidget,
    QHBoxLayout, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import qtawesome as qta

BG = "#FAFAFA"
CARD = "#FFFFFF"
BORDER = "#E4E4E7"
TEXT = "#18181B"
TEXT_FADE = "#A1A1AA"
CHINAR = "#EF4444"  # Red
GOLD = "#F59E0B"    # Yellow
DAL = "#0EA5E9"     # Blue

class TriageWizardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 20, 24, 20)
        
        title = QLabel("🚑 Symptom Triage Wizard")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        self.layout.addWidget(title)
        
        self.stacked = QStackedWidget()
        self.layout.addWidget(self.stacked, stretch=1)
        
        self.triage_data = self._load_data()
        self.red_flags = [e for e in self.triage_data if e.get("category") == "RED FLAG"]
        self.yellow_flags = [e for e in self.triage_data if e.get("category") == "YELLOW FLAG"]
        
        self._build_screens()
        
    def _load_data(self):
        try:
            p = Path(__file__).parent.parent.parent / "backend" / "data" / "knowledge" / "emergency" / "symptom_triage.json"
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("entries", [])
        except Exception as e:
            print("Error loading triage data:", e)
            return []
            
    def _build_screens(self):
        # Screen 0: Red Flags
        self.red_screen = self._create_question_screen(
            "Do you or the patient have any of the following severe symptoms?", 
            self.red_flags,
            self.show_red_alert,
            self.go_to_yellow
        )
        self.stacked.addWidget(self.red_screen)
        
        # Screen 1: Yellow Flags
        self.yellow_screen = self._create_question_screen(
            "Are you experiencing any of these serious symptoms?", 
            self.yellow_flags,
            self.show_yellow_alert,
            self.go_to_green
        )
        self.stacked.addWidget(self.yellow_screen)
        
        # Screen 2: Result
        self.result_screen = QWidget()
        self.result_layout = QVBoxLayout(self.result_screen)
        self.stacked.addWidget(self.result_screen)
        
    def _create_question_screen(self, question, items, on_yes, on_no):
        w = QWidget()
        l = QVBoxLayout(w)
        
        lbl = QLabel(question)
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {TEXT};")
        lbl.setWordWrap(True)
        l.addWidget(lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(10)
        
        for item in items:
            btn = QPushButton(item["title"] + "\n(" + ", ".join(item["keywords"][:3]) + ")")
            btn.setFont(QFont("Segoe UI", 12))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CARD}; border: 2px solid {BORDER};
                    border-radius: 12px; padding: 20px; text-align: left;
                    color: {TEXT};
                }}
                QPushButton:hover {{ border-color: {DAL}; }}
            """)
            btn.clicked.connect(lambda checked, idx=item: on_yes(idx))
            c_layout.addWidget(btn)
            
        c_layout.addStretch()
        scroll.setWidget(content)
        l.addWidget(scroll, stretch=1)
        
        none_btn = QPushButton("None of the above")
        none_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        none_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {TEXT}; color: white;
                border-radius: 12px; padding: 16px;
            }}
            QPushButton:pressed {{ background-color: #3F3F46; }}
        """)
        none_btn.clicked.connect(on_no)
        l.addWidget(none_btn)
        
        return w
        
    def show_red_alert(self, item):
        self._show_result("RED FLAG ALERT", item["text_content"], CHINAR, "fa5s.ambulance")
        
    def show_yellow_alert(self, item):
        self._show_result("MEDICAL ATTENTION NEEDED", item["text_content"], GOLD, "fa5s.user-md")
        
    def go_to_yellow(self):
        self.stacked.setCurrentIndex(1)
        
    def go_to_green(self):
        self._show_result(
            "Mild Symptoms", 
            "Your symptoms do not appear to be life-threatening. You can use the AI Chat Companion to look up home remedies or general advice.", 
            "#10B981", 
            "fa5s.leaf"
        )
        
    def _show_result(self, title, text, color, icon):
        while self.result_layout.count():
            i = self.result_layout.takeAt(0)
            if i.widget(): i.widget().deleteLater()
            
        f = QFrame()
        f.setStyleSheet(f"background-color: {CARD}; border: 3px solid {color}; border-radius: 16px;")
        fl = QVBoxLayout(f)
        fl.setContentsMargins(30, 30, 30, 30)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color=color).pixmap(64, 64))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(icon_lbl)
        
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(t)
        
        d = QLabel(text)
        d.setFont(QFont("Segoe UI", 14))
        d.setWordWrap(True)
        d.setStyleSheet(f"color: {TEXT}; margin-top: 10px;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(d)
        
        self.result_layout.addWidget(f)
        self.result_layout.addStretch()
        
        reset = QPushButton("Restart Triage")
        reset.setFont(QFont("Segoe UI", 12))
        reset.setStyleSheet(f"""
            QPushButton {{
                background-color: {BORDER}; color: {TEXT};
                border-radius: 12px; padding: 16px;
            }}
            QPushButton:pressed {{ background-color: #D4D4D8; }}
        """)
        reset.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.result_layout.addWidget(reset)
        
        self.stacked.setCurrentIndex(2)
