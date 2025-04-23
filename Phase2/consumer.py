from kafka import KafkaConsumer
import json
import xgboost as xgb
import numpy as np
import pandas as pd
import logging
import mlflow.xgboost
from evidently.dashboard import Dashboard
from evidently.tabs import DataDriftTab

logging.basicConfig(level=logging.INFO)

# xg_model = xgb.XGBRegressor()
# try:
#     xg_model.load_model('/Users/shauryagulati/Developer/Kafka/xgboost_model.json')
#     logging.info("XGBoost model loaded successfully.")
# except Exception as e:
#     logging.error(f"Error loading model: {e}")
#     raise

model_uri = "runs:/2ade5c308a7c457f8602d29c3e001000/xgb_model_100_10"
try:
    model = mlflow.xgboost.load_model(model_uri)
    logging.info(f"✅ Model loaded successfully from MLflow: {model_uri}")
except Exception as e:
    logging.error(f"❌ Error loading model from MLflow: {e}")
    raise

# Load reference dataset
try: 
    ref_data = pd.read_csv('C:/airqual-project/reference_data.csv') # Adjust file path
    logging.info('Reference data loaded successfully.')
except Exception as e:
    logging.error(f'Error loading reference data: {e}')
    raise

#Kafka consumer setup
consumer = KafkaConsumer('air_quality_topic', 
                         bootstrap_servers='localhost:9092', 
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

feature_records = [] # for Evidently
predictions = []

#Real-time prediction loop
for message in consumer:
    data = message.value

    try:
        # ✅ Ensure all 19 features are extracted in the correct order
        features = [
            data['hour'],
            data['day_of_week'],
            data['month'],
            data['CO_lag1'],
            data['CO_lag2'],
            data['NOx_lag1'],
            data['NOx_lag2'],
            data['C6H6_lag1'],
            data['C6H6_lag2'],
            data['CO_rolling_mean'],
            data['CO_rolling_std'],
            data['NOx_rolling_mean'],
            data['NOx_rolling_std'],
            data['C6H6_rolling_mean'],
            data['C6H6_rolling_std'],
            data['PT08.S1(CO)'],
            data['PT08.S3(NOx)'],
            data['PT08.S4(NO2)'],
            data['PT08.S5(O3)']
        ]

        feature_df = pd.DataFrame([features], columns=[
            'hour', 'day_of_week', 'month',
            'CO_lag1', 'CO_lag2',
            'NOx_lag1', 'NOx_lag2',
            'C6H6_lag1', 'C6H6_lag2',
            'CO_rolling_mean', 'CO_rolling_std',
            'NOx_rolling_mean', 'NOx_rolling_std',
            'C6H6_rolling_mean', 'C6H6_rolling_std',
            'PT08.S1(CO)', 'PT08.S3(NOx)', 'PT08.S4(NO2)', 'PT08.S5(O3)'
        ])

        # Save for monitoring
        feature_records.append(feature_df)

        # ✅ Predict
        prediction = model.predict(feature_df)[0]
        predictions.append(prediction)
        logging.info(f"📈 Predicted CO(GT): {prediction:.4f}")

        # ✅ Periodically save predictions --> UPDATED CODE
        if len(feature_records) >= 100:
            current_df = pd.concat(feature_records, ignore_index=True)
            predictions_df = pd.DataFrame(predictions, columns=['Predicted_CO(GT)'])
            predictions_df.to_csv('predictions.csv', index=False)
            logging.info(f"💾 Saved {len(predictions)} predictions to CSV.")

            # Evidently data drift dashboard
            dashboard = Dashboard(tabs=[DataDriftTab()])
            dashboard.calculate(ref_data, current_df)
            dashboard.save("drift_dashboard.html")
            logging.info("📊 Data drift dashboard saved.")

            # Reset records
            feature_records =[]
            predictions = []

    except KeyError as e:
        logging.error(f"❌ Missing feature in message: {e}")
    except Exception as e:
        logging.error(f"❌ Error during prediction or monitoring: {e}")

# ✅ Final save
predictions_df = pd.DataFrame(predictions, columns=['Predicted_CO(GT)'])
predictions_df.to_csv('predictions.csv', index=False)
logging.info("✅ Final predictions saved to CSV.")

if feature_records:
    current_df = pd.concat(feature_records, ignore_index=True)
    dashboard = Dashboard(tabs=[DataDriftTab()])
    dashboard.calculate(ref_data, current_df)
    dashboard.save("drift_dashboard.html")
    logging.info("📊 Final drift dashboard saved.")