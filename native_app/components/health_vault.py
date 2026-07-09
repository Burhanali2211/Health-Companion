from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QStackedWidget,
    QHBoxLayout, QFrame, QScrollArea, QLineEdit, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import qtawesome as qta
from database import get_all_users, create_user, get_health_logs, add_health_log, init_db

BG = "#FAFAFA"
CARD = "#FFFFFF"
BORDER = "#E4E4E7"
TEXT = "#18181B"
TEXT_FADE = "#A1A1AA"
DAL = "#0EA5E9"

class HealthVaultWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 20, 24, 20)
        
        title = QLabel("🔐 Local Health Vault")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        self.layout.addWidget(title)
        
        self.stacked = QStackedWidget()
        self.layout.addWidget(self.stacked, stretch=1)
        
        self.current_user = None
        init_db()
        self._build_screens()
        self.refresh_users()
        
    def _build_screens(self):
        # 0: Profile Selection
        self.sel_screen = QWidget()
        sl = QVBoxLayout(self.sel_screen)
        
        l = QLabel("Select a Profile:")
        l.setFont(QFont("Segoe UI", 12))
        sl.addWidget(l)
        
        self.profiles_layout = QVBoxLayout()
        sl.addLayout(self.profiles_layout)
        sl.addStretch()
        
        add_btn = QPushButton(" + Create New Profile")
        add_btn.setStyleSheet(f"background: {CARD}; border: 1px solid {BORDER}; padding: 16px; border-radius: 12px; font-size: 14pt;")
        add_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        sl.addWidget(add_btn)
        self.stacked.addWidget(self.sel_screen)
        
        # 1: Create Profile
        self.create_screen = QWidget()
        cl = QVBoxLayout(self.create_screen)
        form = QFormLayout()
        
        self.name_in = QLineEdit()
        self.name_in.setStyleSheet(f"padding: 12px; border: 1px solid {BORDER}; border-radius: 8px; font-size: 12pt;")
        self.age_in = QLineEdit()
        self.age_in.setStyleSheet(f"padding: 12px; border: 1px solid {BORDER}; border-radius: 8px; font-size: 12pt;")
        self.blood_in = QComboBox()
        self.blood_in.setStyleSheet(f"padding: 12px; border: 1px solid {BORDER}; border-radius: 8px; font-size: 12pt;")
        self.blood_in.addItems(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"])
        
        form.addRow("Name:", self.name_in)
        form.addRow("Age:", self.age_in)
        form.addRow("Blood Type:", self.blood_in)
        cl.addLayout(form)
        cl.addStretch()
        
        save_btn = QPushButton("Save Profile")
        save_btn.setStyleSheet(f"background: {DAL}; color: white; padding: 16px; border-radius: 12px; font-size: 14pt;")
        save_btn.clicked.connect(self._save_profile)
        cl.addWidget(save_btn)
        
        back_btn = QPushButton("Cancel")
        back_btn.setStyleSheet(f"background: {CARD}; border: 1px solid {BORDER}; padding: 16px; border-radius: 12px; font-size: 14pt;")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        cl.addWidget(back_btn)
        self.stacked.addWidget(self.create_screen)
        
        # 2: User Dashboard
        self.dash_screen = QWidget()
        dl = QVBoxLayout(self.dash_screen)
        self.dash_title = QLabel()
        self.dash_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        dl.addWidget(self.dash_title)
        
        info = QLabel("Your medical records are stored securely on this device.")
        info.setFont(QFont("Segoe UI", 12))
        info.setStyleSheet(f"color: {TEXT_FADE};")
        dl.addWidget(info)
        
        dl.addStretch()
        
        out_btn = QPushButton("Sign Out")
        out_btn.setStyleSheet(f"background: {BORDER}; padding: 16px; border-radius: 12px; font-size: 14pt;")
        out_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        dl.addWidget(out_btn)
        self.stacked.addWidget(self.dash_screen)
        
    def refresh_users(self):
        while self.profiles_layout.count():
            i = self.profiles_layout.takeAt(0)
            if i.widget(): i.widget().deleteLater()
            
        users = get_all_users()
        for u in users:
            btn = QPushButton(f"👤 {u['name']} (Age: {u['age']})")
            btn.setStyleSheet(f"background: {CARD}; border: 1px solid {BORDER}; padding: 20px; border-radius: 12px; font-size: 14pt; text-align: left;")
            btn.clicked.connect(lambda checked, user=u: self.login(user))
            self.profiles_layout.addWidget(btn)
            
    def _save_profile(self):
        name = self.name_in.text()
        if not name: return
        create_user(name, self.age_in.text(), self.blood_in.currentText())
        self.name_in.clear()
        self.age_in.clear()
        self.refresh_users()
        self.stacked.setCurrentIndex(0)
        
    def login(self, user):
        self.current_user = user
        self.dash_title.setText(f"Welcome, {user['name']}!")
        self.stacked.setCurrentIndex(2)
