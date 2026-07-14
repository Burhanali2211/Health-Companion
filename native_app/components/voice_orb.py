import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QRadialGradient
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF

class VoiceOrb(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, size=240, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._scale = size / 240.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(30)
        
        self._time = 0.0
        self._state = "idle" # idle, listening, speaking
        
        # Initialize variables
        self._glow_radius = 60 * self._scale
        self._core_radius = 45 * self._scale

    def _update_animation(self):
        self._time += 0.05
        s = self._scale
        if self._state == "idle":
            self._glow_radius = (65 + 10 * math.sin(self._time)) * s
            self._core_radius = (45 + 2 * math.cos(self._time * 1.5)) * s
        elif self._state == "listening":
            self._glow_radius = (80 + 15 * math.sin(self._time * 2)) * s
            self._core_radius = (50 + 5 * math.cos(self._time * 3)) * s
        else: # speaking
            self._glow_radius = (70 + 25 * math.sin(self._time * 4)) * s
            self._core_radius = (48 + 8 * math.cos(self._time * 5)) * s
            
        self.update()

    def set_state(self, state: str):
        self._state = state

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            cx = float(self.rect().center().x())
            cy = float(self.rect().center().y())
            
            glow_r = float(self._glow_radius)
            core_r = float(self._core_radius)
            
            # Siri/ChatGPT inspired vibrant colors
            if self._state == "idle":
                outer_color = QColor(0, 122, 255, 60)   # iOS Blue
                inner_color = QColor(0, 122, 255, 180)
                core_color1 = QColor(100, 200, 255)
                core_color2 = QColor(0, 122, 255)
            elif self._state == "listening":
                outer_color = QColor(255, 59, 48, 80)   # iOS Red
                inner_color = QColor(255, 59, 48, 200)
                core_color1 = QColor(255, 150, 150)
                core_color2 = QColor(255, 59, 48)
            else: # speaking
                outer_color = QColor(175, 82, 222, 80)  # iOS Purple
                inner_color = QColor(88, 86, 214, 200)  # iOS Indigo
                core_color1 = QColor(200, 150, 255)
                core_color2 = QColor(175, 82, 222)

            # Draw outer glowing halo
            gradient = QRadialGradient(QPointF(cx, cy), glow_r)
            gradient.setColorAt(0, inner_color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)
            
            # Draw solid pulsating core
            core_gradient = QRadialGradient(QPointF(cx, cy), core_r)
            core_gradient.setColorAt(0, core_color1)
            core_gradient.setColorAt(1, core_color2)
                
            painter.setBrush(core_gradient)
            painter.drawEllipse(QPointF(cx, cy), core_r, core_r)
        finally:
            painter.end()

    def mousePressEvent(self, event):
        self.clicked.emit()
