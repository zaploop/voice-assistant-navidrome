FROM python:3.11-slim

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    libasound2-dev \
    libspeexdsp-dev \
    ffmpeg \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    && rm -rf /var/lib/apt/lists/*

# Crea utente non-root
RUN useradd -m -u 1000 voiceassistant

# Imposta directory di lavoro
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia codice sorgente
COPY src/ ./src/
COPY config/ ./config/

# Crea directory per dati e log
RUN mkdir -p data logs models && \
    chown -R voiceassistant:voiceassistant /app

# Cambia a utente non-root
USER voiceassistant

# Esponi porte per monitoring
EXPOSE 8000 8001

# Comando di avvio
CMD ["python", "src/main.py", "--config", "config/config.yaml"]

