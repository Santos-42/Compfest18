import os
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    """Temukan root repo secara robust (host & Docker).

    Host:      D:/Hackathons/Compfest18/backend/core/config.py -> parents[2] = root repo
    Docker:    /app/core/config.py                              -> parents[2] = / (salah)
               Fallback cek parents[1] = /app yang berisi data/wilayah.sql
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "wilayah.sql").exists():
            return parent
    return here.parents[2]


# Root repo: D:\Hackathons\Compfest18 (host) atau /app (Docker)
REPO_ROOT = _find_repo_root()

# Muat .env dari root repo (atau CWD)
load_dotenv(REPO_ROOT / ".env")


class Settings:
    def __init__(self):
        # ===== API Eksternal =====
        self.OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", "")
        self.ORS_API_KEY = os.getenv("ORS_API_KEY", "")

        # ===== DeepSeek (opsional, penerjemah naratif) =====
        self.USE_DEEPSEEK = os.getenv("USE_DEEPSEEK", "false").lower() == "true"
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

        # ===== Mode Mock / Fallback =====
        self.USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "false").lower() == "true"
        self.ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"

        # ===== Konfigurasi Simulasi =====
        self.ORIGIN_LAT = float(os.getenv("ORIGIN_LAT", "-6.200000"))
        self.ORIGIN_LNG = float(os.getenv("ORIGIN_LNG", "106.816666"))
        self.FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.7"))
        self.TRAFFIC_FACTOR = {
            "normal": 1.0,
            "congested": 1.55,
            "hujan": 1.25,
        }
        self.WEATHER_FACTOR = {
            "Cerah": 1.0,
            "Cerah Berawan": 1.05,
            "Berawan": 1.1,
            "Berawan Tebal": 1.15,
            "Udara Kabur": 1.15,
            "Asap": 1.15,
            "Kabut": 1.2,
            "Hujan Ringan": 1.25,
            "Hujan Sedang": 1.4,
            "Hujan Lokal": 1.4,
            "Hujan Lebat": 1.6,
            "Petir": 1.6,
            "Petir Disertai Hujan": 1.6,
        }

        # ===== Path =====
        self.DATABASE_PATH = REPO_ROOT / os.getenv("DATABASE_PATH", "logistics.db")
        self.AI_MODELS_DIR = REPO_ROOT / "ai-models"
        self.DATA_DIR = REPO_ROOT / "data"
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "6"))


settings = Settings()
