FROM python:3.10-slim

# Instalacja zależności systemowych dla OpenCV i MediaPipe
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Ustawienie katalogu roboczego
WORKDIR /app

# Skopiowanie pliku wymagań i ich instalacja
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiowanie reszty kodu (frontend nie jest potrzebny, ale model YOLO i katalogi tak)
COPY . .

# Ustawienie zmiennej środowiskowej portu (domyślnie 8000, ale hosting może nadpisać)
ENV PORT=8000
EXPOSE $PORT

# Komenda uruchamiająca serwer FastAPI
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}
