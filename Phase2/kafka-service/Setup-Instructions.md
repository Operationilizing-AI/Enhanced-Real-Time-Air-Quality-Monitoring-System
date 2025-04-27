# 🧠 Air Quality Forecasting Pipeline

A complete machine learning pipeline for real-time air quality prediction using Kafka, XGBoost, and MLflow.

---


## 🔍 Key Components

### 🔬 MLflow Experiments

- Multiple hyperparameter combinations of `XGBoostRegressor`
- Tracks metrics: `mse`, `rmse`, `mae`, `r2`
- Logs each model with:
  - `signature`
  - `input_example`
  - `params`
  - Best model exported to `.pkl` and `.json`

### 🧮 Feature Engineering

Includes:
- Lag features (`CO_lag1`, `NOx_lag2`, etc.)
- Rolling mean & std
- Time features (`hour`, `day_of_week`, `month`)
- Sensor data (`PT08.S1(CO)`, ...)

All features used for model training are synced with the real-time Kafka pipeline.

### 🛰 Kafka Integration

- **Producer**: Simulates real-time air quality data
- **Consumer**: Loads the best MLflow model and predicts `CO(GT)` in real-time
- Outputs saved periodically to `predictions.csv`

---


## How to run it

### Start Kafka

Step 1: Generate UUID

- export KAFKA_UUID=$(bin/kafka-storage.sh random-uuid)

Step 2: Format metadata

- bin/kafka-storage.sh format -t $KAFKA_UUID --initial-controllers=1@CONTROLLER://localhost:9093 -c config/kraft/server.properties

Step 3: Start Kafka

- bin/kafka-server-start.sh config/kraft/server.properties


### Train Models in mlflow.py

This logs all models and exports the best one as:


- best_xgb_model.pkl


- best_xgb_model_metadata.json


## Stream Real-Time Data

python kafka/kafka_consumer.py

python kafka/kafka_producer.py
