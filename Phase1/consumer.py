from kafka import KafkaConsumer
import json
import xgboost as xgb
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

xg_model = xgb.XGBRegressor()
try:
    xg_model.load_model('/Users/shauryagulati/Developer/Kafka/xgboost_model.json')
    logging.info("XGBoost model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading model: {e}")
    raise

#Kafka consumer setup
consumer = KafkaConsumer('air_quality_topic', 
                         bootstrap_servers='localhost:9092', 
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

predictions = []

#Real-time prediction loop
for message in consumer:
    data = message.value  # Get the incoming data from Kafka
    
    #Extract features from the incoming message
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
        data['C6H6_rolling_std']
    ]
    
    features_array = np.array(features).reshape(1, -1)
    
    #Make prediction
    try:
        prediction = xg_model.predict(features_array)
        predictions.append(prediction[0])
        logging.info(f"Predicted CO(GT): {prediction[0]}")
    except Exception as e:
        logging.error(f"Error making prediction: {e}")
    
    if len(predictions) % 100 == 0:
        predictions_df = pd.DataFrame(predictions, columns=['Predicted_CO(GT)'])
        predictions_df.to_csv('predictions.csv', index=False)
        logging.info(f"Saved {len(predictions)} predictions to CSV.")

#Final save of predictions
predictions_df = pd.DataFrame(predictions, columns=['Predicted_CO(GT)'])
predictions_df.to_csv('predictions.csv', index=False)
logging.info("Final predictions saved to CSV.")