# Training pipeline

Training data di repository bersifat sintetis dan dipakai untuk demonstrasi, bukan bukti performa produksi.

## Fraud

1. `python training-scripts/generate_label.py`
2. `python training-scripts/train_fraud_model.py`

`fraud_label_rules.py` adalah satu-satunya sumber aturan label. Pola fraud mencakup `Not Received`, `Rejected/Unreachable` dengan GPS lebih dari 1.500 meter, serta `Received` dengan GPS lebih dari 5.000 meter dan nilai lebih dari Rp750.000. Output selalu memiliki satu kolom `fraud`.

`fraud_model.pkl` dipakai saat inferensi runtime. Feature order harus tetap sama dengan `train_fraud_model.py` dan `backend/services/fraud_service.py`.

## ETA

`python training-scripts/train_eta_model.py` menghasilkan `eta_model.pkl` sebagai artifact eksperimen offline. Runtime API tidak memakai model ini; ETA production menggunakan durasi ORS Matrix atau fallback Haversine yang dikalibrasi dengan trafik dan cuaca BMKG.

Semua script memakai seed tetap agar output training dapat direproduksi. Jalankan ulang training hanya jika artifact model memang ingin diperbarui.
