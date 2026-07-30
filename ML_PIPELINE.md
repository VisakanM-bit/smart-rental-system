# FleetSight ML Pipeline

The ML layer is isolated in `app/ml/`, so the dashboard consumes saved models without knowing whether they were trained from generated or uploaded records.

## Hybrid models

| Need | Model | Output |
| --- | --- | --- |
| Telemetry / rental anomalies | Isolation Forest | Statistical outlier flag |
| Maintenance risk | XGBoost classifier | Probability of service/fault risk |
| Overdue risk | XGBoost classifier | Probability of return risk |
| Misuse risk | XGBoost classifier | Probability of abnormal use |
| Machine health | XGBoost multiclass classifier | Healthy, Watch, Warning, Critical |
| Demand | Holt-Winters Exponential Smoothing | Next seven-day demand by site/type |

## First training and switching data

Open **ML models** in the app and select **synthetic** for the first reproducible demo training run. Models and evaluation metrics are saved to `data/models/`.

Select **uploaded** to retrain from the five CSV files in `data/uploaded/`. No code or import path changes are required: `app/ml/datasets.py` emits the same frame contract for each source and `app/ml/features.py` applies the same feature engineering.

The equivalent command-line call is:

```powershell
.\.venv\Scripts\python.exe -c "from app.ml.pipeline import train_all; print(train_all('synthetic'))"
```

Replace `synthetic` with `uploaded` when ready.

## Feature engineering

The model matrix joins telemetry with machine capability/service context and rental status. It includes engine hours, idle hours, fuel level and consumption, temperature, hydraulic pressure, vibration, RPM, distance from site, machine age, maximum daily capacity, service age/interval, overdue days, equipment type, movement status, and normalized geofence status.

The rule health score begins at 100 and deducts points for excessive engine hours, high idle time, low fuel, high temperature, high vibration, exceeded service interval, geofence exit, and overdue rental days. Its bands are Healthy (80–100), Watch (65–79), Warning (45–64), and Critical (0–44).

## Training safeguards

- Numeric values use median imputation; categorical values use most-frequent imputation and one-hot encoding.
- Classifiers use a reproducible stratified 80/20 train/test split.
- Binary models report accuracy, weighted precision/recall/F1, and ROC-AUC. Health classification reports weighted multi-class metrics.
- The overdue model intentionally excludes `overdue_days` as an input, because it is an outcome and would cause target leakage.
- Synthetic outcomes are generated/rule-derived solely to demonstrate the complete train/evaluate/save/infer workflow. Replace them with reviewed operational labels for production calibration.
- Isolation Forest flags statistically unusual behavior; it is an investigation signal, not a fault verdict.

## Artifacts and inference

`data/models/` holds model `.joblib` files plus `metrics.json`. `predict_risks()` returns the three probabilities and the health class for engineered feature rows; `detect_anomalies()` applies saved Isolation Forest models; `demand_predictions()` reads the saved seven-day forecast.
