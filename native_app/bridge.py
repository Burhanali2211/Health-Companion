import sys
import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

# Ensure we can import from the backend directory
backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from companion_engine import get_companion_response, warm_up_model
from seasonal_engine import get_context

class WorkerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class CompanionTask(QRunnable):
    """
    Runs the AI generation in a background thread to prevent UI freezing.
    """
    def __init__(self, query: str, age_mode: str = "jawaan", district: str = "srinagar"):
        super().__init__()
        self.query = query
        self.age_mode = age_mode
        self.district = district
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Dynamically fetch the actual season
            ctx = get_context(district_id=self.district)
            current_season = ctx["season"]["id"]
            
            response = get_companion_response(
                query=self.query,
                age_mode=self.age_mode,
                district=self.district,
                season=current_season 
            )
            self.signals.finished.emit(response)
        except Exception as e:
            self.signals.error.emit(str(e))

class AIBridge:
    def __init__(self):
        self.thread_pool = QThreadPool()
        # Warm up model when app starts
        warm_up_model()

    def ask(self, query: str, callback):
        task = CompanionTask(query)
        task.signals.finished.connect(callback)
        task.signals.error.connect(lambda err: print(f"Bridge Error: {err}"))
        self.thread_pool.start(task)
