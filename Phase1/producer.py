from kafka import KafkaProducer
import json
import time
import pandas as pd
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)

# ✅ Load your dataset
data = pd.read_csv('/Users/shauryagulati/Developer/Kafka/model.csv')

# ✅ Kafka producer setup
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# ✅ Take the last 20% of the data to simulate test data
test_data = data.iloc[-int(0.2 * len(data)):]

# ✅ Send records one by one
for index, row in test_data.iterrows():
    message = {
        'hour': row['hour'],
        'day_of_week': row['day_of_week'],
        'month': row['month'],
        'CO_lag1': row['CO_lag1'],
        'CO_lag2': row['CO_lag2'],
        'NOx_lag1': row['NOx_lag1'],
        'NOx_lag2': row['NOx_lag2'],
        'C6H6_lag1': row['C6H6_lag1'],
        'C6H6_lag2': row['C6H6_lag2'],
        'CO_rolling_mean': row['CO_rolling_mean'],
        'CO_rolling_std': row['CO_rolling_std'],
        'NOx_rolling_mean': row['NOx_rolling_mean'],
        'NOx_rolling_std': row['NOx_rolling_std'],
        'C6H6_rolling_mean': row['C6H6_rolling_mean'],
        'C6H6_rolling_std': row['C6H6_rolling_std'],
        'PT08.S1(CO)': row['PT08.S1(CO)'],
        'PT08.S3(NOx)': row['PT08.S3(NOx)'],
        'PT08.S4(NO2)': row['PT08.S4(NO2)'],
        'PT08.S5(O3)': row['PT08.S5(O3)']
    }

    try:
        producer.send('air_quality_topic', value=message)
        logging.info(f"✅ Sent record {index} to Kafka.")
    except Exception as e:
        logging.error(f"❌ Error sending record {index}: {e}")

    # Simulate real-time delay
    time.sleep(1)

logging.info("✅ All test data sent to Kafka.")
