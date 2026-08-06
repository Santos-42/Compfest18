import os
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "wilayah.sql").exists():
            return parent
    return here.parents[2]


def _as_bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")


class Settings:
    def __init__(self):
        self.OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", "")
        self.ORS_API_KEY = os.getenv("ORS_API_KEY", "")

        self.USE_DEEPSEEK = _as_bool(os.getenv("USE_DEEPSEEK", "false"))
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

        self.USE_MOCK_MODE = _as_bool(os.getenv("USE_MOCK_MODE", "false"))
        self.ENABLE_FALLBACK = _as_bool(os.getenv("ENABLE_FALLBACK", "true"), True)

        self.ORIGIN_LAT = float(os.getenv("ORIGIN_LAT", "-6.200000"))
        self.ORIGIN_LNG = float(os.getenv("ORIGIN_LNG", "106.816666"))
        self.FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.7"))
        self.MAX_ADDRESSES = int(os.getenv("MAX_ADDRESSES", "15"))
        self.REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "6"))
        self.TOTAL_TIMEOUT = float(os.getenv("TOTAL_TIMEOUT", "30"))
        self.DEEPSEEK_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "3"))
        self.FRONTEND_ORIGINS = tuple(
            origin.strip()
            for origin in os.getenv(
                "FRONTEND_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        )

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

        configured_path = Path(os.getenv("DATABASE_PATH", "logistics.db"))
        self.DATABASE_PATH = (
            configured_path if configured_path.is_absolute() else REPO_ROOT / configured_path
        )
        self.AI_MODELS_DIR = REPO_ROOT / "ai-models"
        self.DATA_DIR = REPO_ROOT / "data"


settings = Settings()
