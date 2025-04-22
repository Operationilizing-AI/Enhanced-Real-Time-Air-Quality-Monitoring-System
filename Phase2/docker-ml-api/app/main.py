from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import xgboost
import numpy as np
import os
import logging
import pickle
import pandas as pd
import re
from datetime import datetime
import math
import csv
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)

app = FastAPI()

try:
    with open("app/models/xgboost_model.pkl", "rb") as f:
        model = pickle.load(f)
    logging.info("Model loaded from xgboost_model.pkl")
except Exception as e:
    logging.error(f"❌ Failed to load model: {e}")
    raise

class StreamData(BaseModel):
    """
    Input data format for streamed data from Kafka service.
    Contains a dictionary with headers as keys and values as lists.
    """
    data: Dict[str, str]  # Headers and their values as strings
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "Date": "12/03/2004",
                    "Time": "05.00.00",
                    "CO(GT)": "0,6",
                    "PT08.S1(CO)": "847",
                    "NMHC(GT)": "7",
                    "C6H6(GT)": "1,0",
                    "PT08.S2(NMHC)": "501",
                    "NOx(GT)": "30",
                    "PT08.S3(NOx)": "1895",
                    "NO2(GT)": "44",
                    "PT08.S4(NO2)": "1155",
                    "PT08.S5(O3)": "394",
                    "T": "6,3",
                    "RH": "65,0",
                    "AH": "0,6233",
                    "": "",
                    "": ""
                }
            }
        }

class AirQualityRecord(BaseModel):
    # Time features
    hour: int
    day_of_week: int
    month: int

    # Lag features
    CO_lag1: float
    CO_lag2: float
    NOx_lag1: float
    NOx_lag2: float
    C6H6_lag1: float
    C6H6_lag2: float
    
    # Gas sensors features
    PT08_S1_CO: float
    PT08_S3_NOx: float
    PT08_S4_NO2: float
    PT08_S5_O3: float
    
    # Rolling statistics features
    CO_rolling_mean: float
    CO_rolling_std: float
    NOx_rolling_mean: float
    NOx_rolling_std: float
    C6H6_rolling_mean: float
    C6H6_rolling_std: float
    
    def to_features_array(self) -> np.ndarray:
        """Convert the record to a numpy array for model prediction."""
        features = [
            self.hour, self.day_of_week, self.month,
            self.CO_lag1, self.CO_lag2, self.NOx_lag1, self.NOx_lag2,
            self.C6H6_lag1, self.C6H6_lag2,
            self.PT08_S1_CO, self.PT08_S3_NOx, self.PT08_S4_NO2, self.PT08_S5_O3,
            self.CO_rolling_mean, self.CO_rolling_std, self.NOx_rolling_mean,
            self.NOx_rolling_std, self.C6H6_rolling_mean, self.C6H6_rolling_std
        ]
        return np.array([features])

# Helper functions
def is_empty_row(data_dict: Dict[str, str]) -> bool:
    """Check if a row is empty."""
    return not data_dict or all(not value for value in data_dict.values())

def clean_and_filter_data(data_dict: Dict[str, str]) -> Dict[str, Optional[float]]:
    """Clean data by removing unwanted columns, replacing commas, and handling missing values."""
    columns_to_keep = [
        'Date', 'Time', 'CO(GT)', 'PT08.S1(CO)', 'C6H6(GT)', 
        'PT08.S2(NMHC)', 'NOx(GT)', 'PT08.S3(NOx)', 'NO2(GT)', 
        'PT08.S4(NO2)', 'PT08.S5(O3)', 'T', 'RH', 'AH'
    ]
    
    processed_data = {}
    
    for col in columns_to_keep:
        if col in data_dict:
            value = data_dict[col]
            if value == '-200' or value == '':
                processed_data[col] = None
            else:
                if col not in ['Date', 'Time']:
                    value = value.replace(',', '.')
                processed_data[col] = value
    
    return processed_data

def parse_datetime(processed_data: Dict[str, Optional[str]]) -> tuple[int, int, int]:
    """Parse date and time to extract hour, day of week, and month."""
    try:
        date_str = processed_data['Date']
        time_str = processed_data['Time']
        date_obj = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H.%M.%S")
        return date_obj.hour, date_obj.weekday(), date_obj.month
    except ValueError as e:
        logging.error(f"Error parsing date/time: {e}")
        return 0, 0, 1  # Default values

def convert_numeric_values(processed_data: Dict[str, Optional[str]]) -> Dict[str, Optional[float]]:
    """Convert numeric values to floats."""
    for col in processed_data:
        if col not in ['Date', 'Time'] and processed_data[col] is not None:
            try:
                processed_data[col] = float(processed_data[col])
            except (ValueError, TypeError):
                processed_data[col] = None
    return processed_data

def update_cached_csv(processed_data: Dict[str, Optional[float]], columns_to_keep: List[str]) -> pd.DataFrame:
    """Update the cached CSV file with new data."""
    csv_path = 'cached_data.csv'
    file_exists = os.path.isfile(csv_path)
    
    if file_exists:
        cached_df = pd.read_csv(csv_path)
        if len(cached_df) >= 23:
            cached_df = cached_df.tail(23)
    else:
        cached_df = pd.DataFrame(columns=columns_to_keep)
    
    # Handle missing values with interpolation
    for col in processed_data:
        if col not in ['Date', 'Time'] and processed_data[col] is None:
            if not cached_df.empty and col in cached_df.columns and not cached_df[col].isna().all():
                interpolated_series = cached_df[col].interpolate(method='linear')
                if len(interpolated_series) > 0:
                    processed_data[col] = interpolated_series.iloc[-1]
                else:
                    processed_data[col] = 0.0
            else:
                processed_data[col] = 0.0
    
    new_row_df = pd.DataFrame([processed_data])
    updated_df = pd.concat([cached_df, new_row_df], ignore_index=True)
    updated_df.to_csv(csv_path, index=False)
    
    return updated_df

def create_lag_features(updated_df: pd.DataFrame) -> Dict[str, float]:
    """Create lag features from the data."""
    features = {}
    
    if len(updated_df) >= 3:
        features['CO_lag1'] = updated_df['CO(GT)'].iloc[-2] if len(updated_df) > 1 else 0.0
        features['CO_lag2'] = updated_df['CO(GT)'].iloc[-3] if len(updated_df) > 2 else 0.0
        features['NOx_lag1'] = updated_df['NOx(GT)'].iloc[-2] if len(updated_df) > 1 else 0.0
        features['NOx_lag2'] = updated_df['NOx(GT)'].iloc[-3] if len(updated_df) > 2 else 0.0
        features['C6H6_lag1'] = updated_df['C6H6(GT)'].iloc[-2] if len(updated_df) > 1 else 0.0
        features['C6H6_lag2'] = updated_df['C6H6(GT)'].iloc[-3] if len(updated_df) > 2 else 0.0
    else:
        current_row = updated_df.iloc[-1]
        features['CO_lag1'] = features['CO_lag2'] = current_row['CO(GT)']
        features['NOx_lag1'] = features['NOx_lag2'] = current_row['NOx(GT)']
        features['C6H6_lag1'] = features['C6H6_lag2'] = current_row['C6H6(GT)']
    
    return features

def create_rolling_features(updated_df: pd.DataFrame) -> Dict[str, float]:
    """Create rolling statistics features."""
    features = {}
    
    if len(updated_df) >= 3:
        features['CO_rolling_mean'] = updated_df['CO(GT)'].tail(3).mean()
        features['CO_rolling_std'] = updated_df['CO(GT)'].tail(3).std()
        features['NOx_rolling_mean'] = updated_df['NOx(GT)'].tail(3).mean()
        features['NOx_rolling_std'] = updated_df['NOx(GT)'].tail(3).std()
        features['C6H6_rolling_mean'] = updated_df['C6H6(GT)'].tail(3).mean()
        features['C6H6_rolling_std'] = updated_df['C6H6(GT)'].tail(3).std()
        
        # Handle NaN in std calculations
        for col in ['CO_rolling_std', 'NOx_rolling_std', 'C6H6_rolling_std']:
            if pd.isna(features[col]):
                features[col] = 0.0
    else:
        current_row = updated_df.iloc[-1]
        features['CO_rolling_mean'] = current_row['CO(GT)']
        features['CO_rolling_std'] = 0.0
        features['NOx_rolling_mean'] = current_row['NOx(GT)']
        features['NOx_rolling_std'] = 0.0
        features['C6H6_rolling_mean'] = current_row['C6H6(GT)']
        features['C6H6_rolling_std'] = 0.0
    
    return features

def preprocess_row(stream_data: StreamData) -> AirQualityRecord:
    """
    Preprocesses a row of data from a Kafka service.
    
    Args:
        stream_data (StreamData): A dictionary with headers as keys and values as strings
    
    Returns:
        AirQualityRecord: Processed data ready for prediction
    """
    try:
        data_dict = stream_data.data
        
        # Check if row is empty
        if is_empty_row(data_dict):
            logging.info("Empty row, skipping")
            return None
        
        # Clean and filter data
        processed_data = clean_and_filter_data(data_dict)
        
        # Parse datetime
        hour, day_of_week, month = parse_datetime(processed_data)
        
        # Convert numeric values
        processed_data = convert_numeric_values(processed_data)
        
        # Update cached CSV
        updated_df = update_cached_csv(processed_data, list(processed_data.keys()))
        
        # Create features
        record_data = {
            'hour': hour,
            'day_of_week': day_of_week,
            'month': month,
        }
        
        # Add lag features
        record_data.update(create_lag_features(updated_df))
        
        # Add rolling features
        record_data.update(create_rolling_features(updated_df))
        
        # Add sensor features
        record_data.update({
            'PT08_S1_CO': processed_data['PT08.S1(CO)'],
            'PT08_S3_NOx': processed_data['PT08.S3(NOx)'],
            'PT08_S4_NO2': processed_data['PT08.S4(NO2)'],
            'PT08_S5_O3': processed_data['PT08.S5(O3)']
        })
        
        air_quality_record = AirQualityRecord(**record_data)
        logging.info(f"Successfully processed row into: {record_data}")
        return air_quality_record
        
    except Exception as e:
        logging.error(f"Error preprocessing row: {e}")
        return None

@app.post("/predict")
async def predict(data: StreamData):
    """
    Predict air quality based on streamed data.
    
    Args:
        data (StreamData): Dictionary with headers and values from Kafka stream
    
    Returns:
        dict: Prediction result or error message
    """
    air_quality_record = preprocess_row(data)
    
    if air_quality_record is None:
        return {"error": "Failed to process input data"}
    
    features_array = air_quality_record.to_features_array()
    
    try:
        prediction = model.predict(features_array)
        print(f"Prediction: {prediction}")
        
        return {"prediction": float(prediction[0])}
    except Exception as e:
        logging.error(f"Error during prediction: {e}")
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message": "ML Prediction API is running. Use /predict endpoint for predictions."}