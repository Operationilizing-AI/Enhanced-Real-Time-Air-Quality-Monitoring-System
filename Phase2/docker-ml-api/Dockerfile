FROM python:3.12.4-slim 

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt 

# Copy the entire app directory
COPY . .

# Make sure the command specifies the correct path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000