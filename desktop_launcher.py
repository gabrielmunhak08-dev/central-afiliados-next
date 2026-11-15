"""Inicializador Windows da Central de Afiliados."""
import os
import secrets
import threading
import time
import webbrowser
from pathlib import Path

data_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CentralDeAfiliados"
instance_dir = data_dir / "instance"
instance_dir.mkdir(parents=True, exist_ok=True)

secret_file = data_dir / "secret.key"
if secret_file.exists():
    secret = secret_file.read_text(encoding="utf-8").strip()
else:
    secret = secrets.token_urlsafe(48)
    secret_file.write_text(secret, encoding="utf-8")

os.environ["CENTRAL_SECRET_KEY"] = secret
os.environ["CENTRAL_DATABASE"] = str(instance_dir / "central.sqlite3")
os.environ["CENTRAL_UPLOAD_FOLDER"] = str(instance_dir / "uploads")
os.environ["CENTRAL_HOST"] = "127.0.0.1"
os.environ["PORT"] = "5000"

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")

threading.Thread(target=open_browser, daemon=True).start()

from app import create_app
from waitress import serve

application = create_app()
serve(application, host="127.0.0.1", port=5000, threads=4, expose_tracebacks=False)
