# producer.py
from kafka import KafkaProducer
import json
import time
import csv
import logging

logging.basicConfig(level=logging.INFO)

# Initialize the Kafka producer
# - 'bootstrap_servers' defines Kafka server(s)
# - 'value_serializer' converts data to JSON and encodes it to bytes
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],  
    value_serializer=lambda v: json.dumps(v).encode('utf-8')  
)

def send_message():
    # Always read the full file to ensure header is available
    with open('./air+quality/AirQualityUCI.csv', 'r', newline='') as file:
        all_rows = list(csv.reader(file, delimiter=';'))
        
        # First row is always the header
        header = all_rows[0]
        
        # Process data rows
        for number, row in enumerate(all_rows[1:], start=1):
            # Create dictionary with headers as keys and values from the row
            row_dict = {}
            for i, header_name in enumerate(header):
                if i < len(row):
                    row_dict[header_name] = row[i]
                else:
                    row_dict[header_name] = ""  # Handle missing values
            
            # Create message in the format expected by the API
            message = {
                'number': number,
                'data': row_dict
            }
            
            producer.send('air-quality-topic', message)
            logging.info(f"Sent row {number}: {message}")
            
            time.sleep(1)  # will update to 3600 after testing

if __name__ == '__main__':
    try:
        send_message()
        producer.flush()
    except KeyboardInterrupt:
        logging.info("Producer stopped by user")
    except Exception as e:
        logging.error(f"Producer error: {e}")
    finally:
        producer.close()
        logging.info("Producer closed")