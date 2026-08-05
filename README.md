# 🚚 Compfest18 — Smart Logistics & Fraud Detection

**COMPFEST 18 AIC (Penyisihan)** · Smart Logistics System dengan deteksi fraud COD dan optimasi rute pengiriman berbasis AI lokal (XGBoost + OR-Tools).

## ✨ Fitur

- **Optimasi Rute** — OR-Tools CP-SAT (TSP) menentukan urutan pengiriman paling efisien
- **Deteksi Fraud COD** — XGBoost Classifier dilatih dari 1.000+ transaksi CSV sintetis, skor risiko per order
- **Prediksi ETA** — XGBoost Regressor + faktor kondisi lalu lintas & cuaca
- **Cuaca Real-time** — BMKG API (prakiraan per kelurahan/desa via `wilayah.sql`)
- **Geocoding & Peta** — OpenCage API + OpenRouteService, visualisasi rute di Leaflet
- **Narasi AI (Opsional)** — DeepSeek V4-Flash menerjemahkan skor fraud jadi penjelasan bahasa Indonesia
- **Fallback Otomatis** — aplikasi tetap jalan walau API eksternal mati (mode mock/Haversine)
- **Docker** — satu perintah untuk menjalankan seluruh sistem

## 🏗️ Arsitektur

```
┌───────────────────────────┐        ┌──────────────────────────────────────────┐
│  Frontend (React 18)      │  HTTP  │  Backend (FastAPI - Python 3.11)         │
│  ┌─────────┬───────────┐  │ ─────► │  POST /api/run-simulation                 │
│  │Input    │ MapDisplay│  │        │  ├── Geocoding (OpenCage)                 │
│  │Panel    │ (Leaflet) │  │        │  ├── Cuaca (BMKG)                         │
│  ├─────────┴───────────┤  │        │  ├── Distance Matrix (ORS / Haversine)    │
│  │ ResultPanel (ETA +  │  │        │  ├── Routing (OR-Tools CP-SAT)            │
│  │ Kartu Fraud)        │  │        │  ├── ETA (XGBoost Regressor)              │
│  └─────────────────────┘  │        │  ├── Fraud (XGBoost Classifier)           │
└───────────┬───────────────┘        │  └── Directions (ORS / polyline)          │
            │                        └──────────────────────────────────────────┘
```

## 🚀 Cara Menjalankan

### Prasyarat
- Docker + Docker Compose
- API keys (opsional jika pakai `USE_MOCK_MODE=true`): [OpenCage](https://opencagedata.com/api) & [OpenRouteService](https://openrouteservice.org/dev/#/api-docs/v2)

### Langkah

```bash
# 1. Konfigurasi API keys
cp .env.example .env
# isi OPENCAGE_API_KEY dan ORS_API_KEY

# 2. (Opsional) Latih ulang model XGBoost dari CSV
python training-scripts/generate_label.py
python training-scripts/train_fraud_model.py
python training-scripts/train_eta_model.py

# 3. Build & jalankan
docker-compose up --build
```

Buka **http://localhost:3000** di browser. Backend API di **http://localhost:8000** (dokumentasi Swagger di `/docs`).

### Tanpa Docker (Development)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (terminal terpisah)
cd frontend
npm install
npm start
```

## 🧪 Alur Demo

1. Isi 3+ alamat di textarea (1 per baris, mis. `Jl. Sudirman No.5, Jakarta`)
2. Pilih kondisi lalu lintas: Normal / Macet / Hujan
3. Klik **"🚀 Jalankan AI & Deteksi Fraud"**
4. Tunggu 1–3 detik → peta rute, tabel ETA + cuaca, dan kartu fraud muncul
5. Order berisiko tinggi tampil sebagai **kartu merah** dengan skor AI & rekomendasi

## 📦 Struktur Repo

```
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile · requirements.txt · main.py
│   ├── api/routes.py
│   ├── core/config.py · database.py   # auto-import wilayah.sql
│   └── services/
│       ├── geocoding_service.py       # OpenCage + mock
│       ├── weather_service.py         # BMKG + fallback
│       ├── distance_service.py        # ORS Matrix + Haversine
│       ├── directions_service.py      # ORS Directions + polyline
│       ├── routing_service.py         # OR-Tools CP-SAT (TSP)
│       ├── eta_service.py             # XGBoost Regressor
│       └── fraud_service.py           # XGBoost Classifier + DeepSeek
├── frontend/
│   ├── Dockerfile · nginx.conf
│   └── src/
│       ├── App.js
│       ├── components/ (InputPanel, MapDisplay, ResultPanel, LoadingSpinner)
│       └── services/api.js
├── ai-models/                         # fraud_model.pkl & eta_model.pkl
├── training-scripts/                  # generate_label, train_fraud, train_eta
├── data/                              # wilayah.sql (91.000+ kode BMKG)
└── kb/                                # (opsional) knowledge base RAG
```

## 🧠 Model AI

| Model | Tugas | Data Training | Metrik |
| :---- | :---- | :------------ | :----- |
| `fraud_model.pkl` | Deteksi fraud COD | `cod_fraud_synthetic_data.csv` (1.000+ baris, label dari aturan bisnis) | Akurasi 100% (test set) |
| `eta_model.pkl` | Prediksi durasi antar titik | Dataset sintetis (jarak × faktor trafik/cuaca + noise) | MAE ±1.4 menit |

**Fitur fraud model:** `item_value`, `gps_distance_m`, one-hot `customer_report` (Not Received / Rejected-Unreachable / Received).

> **Clarification untuk juri:** CSV hanya dipakai saat **training**. Saat demo, model menerima **data real-time** dari input user + API eksternal (jarak GPS dari OpenRouteService, cuaca dari BMKG, nilai COD dari user) sehingga tetap bisa mendeteksi fraud pada skenario baru.

## 🔌 Endpoint API

### `POST /api/run-simulation`

```json
{
  "addresses": ["Jl. Sudirman No.5, Jakarta", "Jl. Gatot Subroto No.10, Jakarta"],
  "cod_amounts": [100000, 250000],
  "traffic_condition": "normal"
}
```

Response: `route.order`, `route.coordinates`, `polyline`, `eta_list[]`, `fraud_alerts[]`, `processing_time_ms`.

### `GET /api/health` — cek status backend.

## ⚙️ Konfigurasi (`.env`)

| Variabel | Default | Fungsi |
| :------- | :------ | :----- |
| `OPENCAGE_API_KEY` | — | Geocoding alamat → koordinat |
| `ORS_API_KEY` | — | Distance matrix & directions |
| `USE_MOCK_MODE` | `false` | `true` = tanpa API eksternal |
| `ENABLE_FALLBACK` | `true` | Fallback mock saat API gagal |
| `USE_DEEPSEEK` / `DEEPSEEK_API_KEY` | `false` | Narasi fraud opsional |
| `FRAUD_THRESHOLD` | `0.7` | Ambang skor fraud |
| `ORIGIN_LAT` / `ORIGIN_LNG` | Jakarta | Titik awal (gudang) |

## 📄 License

Proyek kompetisi — COMPFEST 18 AIC.
