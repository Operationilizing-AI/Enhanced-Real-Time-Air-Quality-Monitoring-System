# consumer.py
from kafka import KafkaConsumer
import json
import pandas as pd
import logging
import requests
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)

# Kafka consumer setup
consumer = KafkaConsumer('air-quality-topic', 
                         bootstrap_servers='localhost:9092', 
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

# API endpoint URL - update this with your actual API endpoint
API_URL = "http://localhost:8000/predict"  # Change this to your API endpoint
CSV_FILE = 'predictions.csv'

# Real-time prediction loop
for message in consumer:
    data = message.value  # Get the incoming data from Kafka
    
    logging.info(f"Consumer Received message: {data}")
    
    # Extract Date and Time from the message data
    datetime_str = None
    try:
        row_data = data.get('data', {})
        date_str = row_data.get('Date', '')
        time_str = row_data.get('Time', '')
        
        if date_str and time_str:
            # Parse the datetime string (assuming format: "12/03/2004" and "05.00.00")
            datetime_obj = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H.%M.%S")
            datetime_str = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # If date/time not available, use current datetime
            datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
    except Exception as e:
        logging.warning(f"Error parsing datetime from message: {e}")
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Send the data directly to the API
    try:
        response = requests.post(API_URL, json={'data': data['data']})
        
        if response.status_code == 200:
            prediction_result = response.json()
            prediction = prediction_result.get('prediction')
            
            # Create DataFrame for the current prediction
            new_row = pd.DataFrame({
                'DateTime': [datetime_str],
                'Predicted_CO(GT)': [prediction]
            })
            
            # Check if CSV file exists
            if os.path.exists(CSV_FILE):
                # Load existing data and append new row
                existing_df = pd.read_csv(CSV_FILE)
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            else:
                # Create new DataFrame if file doesn't exist
                updated_df = new_row
            
            # Save updated DataFrame to CSV
            updated_df.to_csv(CSV_FILE, index=False)
            logging.info(f"Saved prediction: {prediction} for datetime: {datetime_str}")
            
        else:
            logging.error(f"API request failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making API request: {e}")
    except Exception as e:
        logging.error(f"Error saving prediction: {e}")