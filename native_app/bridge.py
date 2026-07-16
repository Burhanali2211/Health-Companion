import sys
import os
import urllib.request
import urllib.parse
import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

# Ensure we can import from the backend directory
backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from companion_engine import get_companion_response, warm_up_model
    from seasonal_engine import get_context
    HAS_LOCAL_BACKEND = True
except ImportError:
    HAS_LOCAL_BACKEND = False

class WorkerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class CompanionTask(QRunnable):
    """
    Runs the AI generation in a background thread to prevent UI freezing.
    Supports either local execution or remote API execution.
    """
    def __init__(self, query: str, age_mode: str = "jawaan", district: str = "srinagar", backend_url: str = None):
        super().__init__()
        self.query = query
        self.age_mode = age_mode
        self.district = district
        self.backend_url = backend_url
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.backend_url:
                # Remote Backend API Mode
                url = f"{self.backend_url}/api/companion/ask"
                data = json.dumps({
                    "query": self.query,
                    "age_mode": self.age_mode,
                    "district": self.district,
                    "language": "auto"
                }).encode("utf-8")
                
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if res_data.get("status") == "ok":
                        self.signals.finished.emit(res_data["data"])
                    else:
                        raise Exception(res_data.get("message", "API returned error"))
            else:
                # Local Execution Mode
                if not HAS_LOCAL_BACKEND:
                    raise Exception("Local backend engine is not available. Run with '--server' to connect to remote backend.")
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
    def __init__(self, backend_url: str = None):
        self.thread_pool = QThreadPool()
        self.backend_url = backend_url
        # Only warm up model if running locally
        if not self.backend_url and HAS_LOCAL_BACKEND:
            try:
                warm_up_model()
            except Exception as e:
                print(f"[bridge] Local model warm-up failed: {e}")

    def ask(self, query: str, callback):
        task = CompanionTask(query, backend_url=self.backend_url)
        task.signals.finished.connect(callback)
        task.signals.error.connect(lambda err: print(f"Bridge Error: {err}"))
        self.thread_pool.start(task)

