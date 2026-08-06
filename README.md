# Compfest18 — Smart Logistics & Fraud Detection

Aplikasi web simulasi logistik untuk optimasi rute pengiriman dan analisis risiko fraud COD. Backend memakai FastAPI, OR-Tools, XGBoost untuk fraud, ORS/Haversine untuk jarak dan ETA, BMKG untuk cuaca, serta React Leaflet untuk peta.

## Fitur

- Optimasi rute **closed route**: gudang → seluruh stop → gudang.
- Deteksi fraud COD dengan XGBoost lokal; heuristik dipakai jika artifact model tidak tersedia.
- ETA berbasis durasi OpenRouteService Matrix atau Haversine saat fallback, dikalibrasi dengan trafik dan cuaca BMKG.
- Autocomplete alamat Photon dengan fallback OpenCage.
- Cuaca BMKG berdasarkan metadata lokasi dan kode wilayah yang tersedia.
- Mode simulasi demo deterministik dengan seed tetap.
- Mode normal yang menerima data transaksi secara eksplisit.
- Fallback eksternal dengan warning yang ditampilkan; alamat gagal di mode real tidak disamarkan sebagai gudang.
- Reverse proxy Nginx `/api/` dan Docker Compose.

## Arsitektur

```text
React + Leaflet
     │ /api melalui Nginx
     ▼
FastAPI
 ├─ geocoding Photon/OpenCage
 ├─ weather BMKG
 ├─ distance ORS Matrix/Haversine
 ├─ closed route OR-Tools
 ├─ ETA ORS/Haversine + trafik/cuaca
 └─ fraud XGBoost + narasi DeepSeek opsional
```

## Menjalankan dengan Docker

```bash
cp .env.example .env
# isi API key bila ingin memakai provider eksternal

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

Frontend production memakai URL relatif `/api`, sehingga request browser melewati proxy Nginx. Port backend tetap tersedia untuk debugging lokal.

## Development tanpa Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal lain: frontend
cd frontend
npm ci --include=dev
npm start
```

Jika frontend dijalankan melalui CRA di port 3000 dan backend di port 8000, set `REACT_APP_API_URL=http://localhost:8000` hanya untuk development direct. Build Docker tidak memerlukan variabel tersebut.

## Training model

```bash
python training-scripts/generate_label.py
python training-scripts/train_fraud_model.py
python training-scripts/train_eta_model.py
```

`training-scripts/fraud_label_rules.py` adalah satu sumber aturan label fraud. Data training bersifat sintetis dan tidak boleh dipresentasikan sebagai metrik produksi.

`fraud_model.pkl` digunakan saat runtime. `eta_model.pkl` adalah artifact eksperimen offline; runtime sengaja memakai durasi ORS/Haversine langsung agar ETA tetap berbasis data jaringan jalan dan fallback yang dapat dijelaskan.

## Mode input fraud

### Mode simulasi demo

Frontend default memakai mode ini. Backend membuat nominal COD, laporan customer, dan status pengiriman secara deterministik berdasarkan `simulation_seed`. Response menampilkan metadata dan warning bahwa data transaksi sintetis.

Request contoh:

```json
{
  "demo_mode": true,
  "simulation_seed": 42,
  "addresses": [
    {"address": "Jl. Sudirman No. 5, Jakarta"},
    {"address": "Jl. Gatot Subroto No. 10, Jakarta"}
  ],
  "traffic_condition": "normal",
  "optimization": "distance"
}
```

### Mode normal

Setiap alamat harus berisi `cod_amount`, `customer_report`, dan `system_status`. Backend tidak menebak atau mengacak fakta transaksi.

```json
{
  "demo_mode": false,
  "addresses": [
    {
      "address": "Jl. Sudirman No. 5, Jakarta",
      "lat": -6.2088,
      "lng": 106.8456,
      "cod_amount": 750000,
      "customer_report": "Not Received",
      "system_status": "Delivered"
    }
  ],
  "traffic_condition": "congested",
  "optimization": "time"
}
```

Nilai yang diterima:

- `traffic_condition`: `normal`, `congested`, `hujan`
- `optimization`: `distance`, `time`
- `customer_report`: `Received`, `Not Received`, `Rejected/Unreachable`
- `system_status`: `Delivered`, `Failed`

Maksimal 15 alamat per simulasi. `lat` dan `lng` harus dikirim berpasangan dan berada pada range geografis valid.

## Response route

`route.order` adalah indeks node tertutup. Node `0` adalah gudang dan node terakhir juga `0`, contohnya `[0, 2, 1, 0]`. `route.coordinates` tetap berdasarkan indeks input; frontend menggunakan `route.order` untuk menyamakan posisi marker, alamat, ETA, dan tabel.

Response juga berisi:

- `ordered_coordinates`: koordinat dalam urutan closed route.
- `eta_list`: ETA setiap stop delivery dengan `order_index` asli.
- `return_leg`: perjalanan stop terakhir kembali ke gudang.
- `locations`: sumber dan confidence koordinat serta data cuaca.
- `warnings`: fallback atau mode simulasi yang perlu diketahui operator.
- `fraud_alerts`: score, fakta transaksi, status, alasan, dan rekomendasi.

## Konfigurasi

Salin `.env.example` menjadi `.env`.

| Variabel | Default | Fungsi |
|---|---:|---|
| `OPENCAGE_API_KEY` | kosong | Fallback geocoding dan autocomplete |
| `ORS_API_KEY` | kosong | Matrix dan directions |
| `USE_MOCK_MODE` | `false` | Tidak memanggil API eksternal; koordinat/cuaca mock |
| `ENABLE_FALLBACK` | `true` | Izinkan fallback distance/directions/weather |
| `FRONTEND_ORIGINS` | localhost:3000 | Allowlist CORS |
| `REQUEST_TIMEOUT` | `6` | Timeout provider eksternal |
| `TOTAL_TIMEOUT` | `30` | Batas total simulasi |
| `DEEPSEEK_TIMEOUT` | `3` | Timeout narasi DeepSeek |
| `FRAUD_THRESHOLD` | `0.7` | Ambang fraud |
| `ORIGIN_LAT/LNG` | Jakarta | Koordinat gudang |

DeepSeek hanya memperkaya narasi fraud. Score tetap berasal dari model fraud lokal dan hasil inti tetap berjalan tanpa DeepSeek.

## Verifikasi

```bash
python -m compileall -q backend training-scripts
python -m pytest backend/tests -q
cd frontend && npm ci --include=dev && npm test -- --watchAll=false
npm run build
```

## Catatan operasional

- Mode mock menandai lokasi dengan `source=mock` dan `confidence=0`; hasil tidak boleh dianggap koordinat nyata.
- Jika geocoding mode real gagal, API mengembalikan error terstruktur per alamat.
- Database SQLite dibuat/migrasi saat startup dan `wilayah.sql` diimpor secara idempotent.
- API key lokal hanya boleh berada di `.env`; jika pernah dibagikan, revoke dan rotate key tersebut.
