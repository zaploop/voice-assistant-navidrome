#!/bin/bash
# Script di installazione automatica Voice Assistant per Navidrome
# Versione: 1.0
# Autore: Manus AI

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utilità
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
🎵 Voice Assistant per Navidrome
================================
Sistema di controllo vocale offline
per la tua libreria musicale personale
EOF
echo -e "${NC}"

# Verifica sistema operativo
log_info "Verifica compatibilità sistema..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_error "Sistema operativo non supportato. Richiesto Linux."
    exit 1
fi

# Verifica architettura
ARCH=$(uname -m)
if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    log_warning "Architettura $ARCH potrebbe non essere completamente supportata"
fi

# Verifica privilegi sudo
if ! sudo -n true 2>/dev/null; then
    log_error "Sono necessari privilegi sudo per l'installazione"
    exit 1
fi

log_success "Sistema compatibile rilevato: $(lsb_release -d | cut -f2)"

# Aggiornamento sistema
log_info "Aggiornamento pacchetti sistema..."
sudo apt update -qq
sudo apt upgrade -y -qq

# Installazione dipendenze sistema
log_info "Installazione dipendenze sistema..."
sudo apt install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    build-essential pkg-config \
    portaudio19-dev libasound2-dev \
    alsa-utils pulseaudio pulseaudio-utils \
    git curl wget unzip \
    redis-server \
    ffmpeg \
    || {
        log_error "Errore durante l'installazione delle dipendenze"
        exit 1
    }

log_success "Dipendenze sistema installate"

# Configurazione audio
log_info "Configurazione sistema audio..."
sudo usermod -a -G audio $USER

# Avvio Redis
log_info "Configurazione Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Creazione directory progetto
PROJECT_DIR="$HOME/voice-assistant-navidrome"
log_info "Creazione directory progetto: $PROJECT_DIR"

if [ -d "$PROJECT_DIR" ]; then
    log_warning "Directory già esistente. Backup in ${PROJECT_DIR}.backup"
    mv "$PROJECT_DIR" "${PROJECT_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Copia file dal sandbox (simulazione download)
log_info "Preparazione file progetto..."
cp -r /home/ubuntu/voice_assistant/* .

# Creazione ambiente virtuale
log_info "Creazione ambiente virtuale Python..."
python3 -m venv venv
source venv/bin/activate

# Aggiornamento pip
pip install --upgrade pip -q

# Installazione dipendenze Python
log_info "Installazione dipendenze Python..."
pip install -r requirements.txt -q || {
    log_error "Errore durante l'installazione delle dipendenze Python"
    exit 1
}

log_success "Dipendenze Python installate"

# Creazione directory per modelli
log_info "Preparazione directory modelli..."
mkdir -p models cache logs

# Download modelli (simulato)
log_info "Preparazione modelli machine learning..."
cat > models/README.md << EOF
# Modelli Machine Learning

Per completare l'installazione, scarica i seguenti modelli:

## Vosk (Riconoscimento Vocale Italiano)
- Modello leggero: https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip
- Modello completo: https://alphacephei.com/vosk/models/vosk-model-it-0.22.zip

## Whisper (Fallback alta accuratezza)
I modelli Whisper verranno scaricati automaticamente al primo utilizzo.

## openWakeWord
I modelli per wake word detection sono inclusi nella libreria.

Estrai i modelli Vosk in questa directory mantenendo la struttura delle cartelle.
EOF

# Configurazione iniziale
log_info "Configurazione iniziale..."
if [ ! -f config/config.yaml ]; then
    cp config/config.example.yaml config/config.yaml
    log_success "File di configurazione creato"
else
    log_warning "File di configurazione già esistente"
fi

# Creazione script di avvio
log_info "Creazione script di avvio..."
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main.py
EOF
chmod +x start.sh

# Creazione file di servizio systemd
log_info "Configurazione servizio sistema..."
sudo tee /etc/systemd/system/voice-assistant-navidrome.service > /dev/null << EOF
[Unit]
Description=Voice Assistant for Navidrome
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable voice-assistant-navidrome

log_success "Servizio sistema configurato"

# Test installazione base
log_info "Test installazione base..."
python -c "
import sys
print(f'Python: {sys.version}')

try:
    import fastapi
    print(f'FastAPI: {fastapi.__version__}')
except ImportError:
    print('FastAPI: Non installato')

try:
    import redis
    r = redis.Redis()
    r.ping()
    print('Redis: Connesso')
except:
    print('Redis: Errore connessione')

print('Test base completato')
"

# Creazione file di configurazione esempio personalizzato
log_info "Creazione configurazione personalizzata..."
cat > config/config.yaml << EOF
# Configurazione Voice Assistant per Navidrome
# Generata automaticamente il $(date)

audio:
  sample_rate: 16000
  channels: 1
  buffer_size: 1024
  vad_threshold: 0.3
  noise_reduction: true

speech_recognition:
  primary_engine: "vosk"
  fallback_engine: "whisper"
  confidence_threshold: 0.7
  fallback_timeout: 2.0
  vosk_model: "models/vosk-model-it-0.22"
  whisper_model: "medium"

nlp:
  language: "it"
  fuzzy_threshold: 0.6
  context_timeout: 300

navidrome:
  base_url: "http://localhost:4533"
  username: "INSERISCI_USERNAME"
  password: "INSERISCI_PASSWORD"
  connection_pool_size: 10
  request_timeout: 10

system:
  log_level: "INFO"
  web_port: 8080
  api_port: 5000

web:
  enable_auth: false
  host: "0.0.0.0"
  port: 8080
EOF

# Creazione script di test
cat > test_system.sh << 'EOF'
#!/bin/bash
echo "🧪 Test Sistema Voice Assistant"
echo "=============================="

cd "$(dirname "$0")"
source venv/bin/activate

echo "1. Test Python e dipendenze..."
python -c "
import sys
print(f'✓ Python {sys.version.split()[0]}')

modules = ['fastapi', 'redis', 'numpy', 'asyncio']
for module in modules:
    try:
        __import__(module)
        print(f'✓ {module}')
    except ImportError:
        print(f'✗ {module} - MANCANTE')
"

echo -e "\n2. Test Redis..."
python -c "
import redis
try:
    r = redis.Redis()
    r.ping()
    print('✓ Redis connesso')
except:
    print('✗ Redis non disponibile')
"

echo -e "\n3. Test configurazione..."
if [ -f "config/config.yaml" ]; then
    echo "✓ File configurazione presente"
else
    echo "✗ File configurazione mancante"
fi

echo -e "\n4. Test modelli..."
if [ -d "models" ]; then
    echo "✓ Directory modelli presente"
    if ls models/*.zip >/dev/null 2>&1 || ls models/vosk-model-* >/dev/null 2>&1; then
        echo "✓ Modelli rilevati"
    else
        echo "⚠️  Modelli da scaricare (vedi models/README.md)"
    fi
else
    echo "✗ Directory modelli mancante"
fi

echo -e "\n5. Test servizio..."
if systemctl is-enabled voice-assistant-navidrome >/dev/null 2>&1; then
    echo "✓ Servizio configurato"
else
    echo "✗ Servizio non configurato"
fi

echo -e "\n📋 Prossimi passi:"
echo "1. Scarica i modelli (vedi models/README.md)"
echo "2. Configura Navidrome in config/config.yaml"
echo "3. Avvia: sudo systemctl start voice-assistant-navidrome"
echo "4. Interfaccia web: http://localhost:8080"
EOF
chmod +x test_system.sh

# Completamento installazione
echo
log_success "Installazione completata con successo!"
echo
echo -e "${YELLOW}📋 PROSSIMI PASSI OBBLIGATORI:${NC}"
echo
echo "1. 📥 Scarica i modelli Vosk:"
echo "   cd $PROJECT_DIR"
echo "   # Segui le istruzioni in models/README.md"
echo
echo "2. ⚙️  Configura Navidrome:"
echo "   nano config/config.yaml"
echo "   # Modifica username e password Navidrome"
echo
echo "3. 🧪 Testa l'installazione:"
echo "   ./test_system.sh"
echo
echo "4. 🚀 Avvia il servizio:"
echo "   sudo systemctl start voice-assistant-navidrome"
echo
echo "5. 🌐 Accedi all'interfaccia web:"
echo "   http://localhost:8080"
echo
echo -e "${BLUE}📖 Documentazione completa:${NC}"
echo "   docs/voice_assistant_documentation.pdf"
echo
echo -e "${GREEN}🎉 Benvenuto nel tuo assistente vocale privato!${NC}"

