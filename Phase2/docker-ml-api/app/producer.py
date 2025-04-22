from kafka import KafkaProducer
import json
import time
import csv

# Initialize the Kafka producer
# - 'bootstrap_servers' defines Kafka server(s)
# - 'value_serializer' converts data to JSON and encodes it to bytes
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],  
    value_serializer=lambda v: json.dumps(v).encode('utf-8')  
)

# Function to send messages to the Kafka topic
def send_message():
    with open('./air+quality/AirQualityUCI.csv', 'r', newline='') as file:
        reader = csv.reader(file, delimiter=';')
        # header = next(reader)
        for number, row in enumerate(reader):
            if number == 0:
                message = {'number': number, 'message': f"Header: {row}"}
            else:
                message = {'number': number, 'message': f"Row: {row}"}
            
            producer.send('air-quality-topic', message)  # Send the message to the topic
            print(f"Type: {type(row)}")  # Print the sent message
            print(f"Sent: {message}")
            time.sleep(1) # will update to 3600 after testing

if __name__ == '__main__':
    send_message()
    producer.flush()
    producer.close()