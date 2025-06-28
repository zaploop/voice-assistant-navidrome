"""
Applicazione principale del Voice Assistant
"""

import asyncio
import logging
import signal
import sys
import yaml
import os
from pathlib import Path
from typing import Dict, Any

# Import dei moduli del sistema
from audio_input import AudioInputManager
from wake_word import WakeWordDetectionService, WakeWordEvent
from speech_recognition import SpeechRecognitionEngine, RecognitionResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    Classe principale che coordina tutti i componenti del sistema
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Componenti del sistema
        self.audio_manager = None
        self.wake_word_service = None
        self.speech_engine = None
        
        # Stato del sistema
        self.is_running = False
        self.is_listening_for_command = False
        self.command_timeout = 10  # secondi
        
        # Setup signal handlers per shutdown graceful
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self) -> Dict[str, Any]:
        """Carica configurazione da file YAML"""
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                # Usa configurazione di esempio se non esiste
                example_config = Path("config/config.example.yaml")
                if example_config.exists():
                    logger.warning(f"Config file {self.config_path} not found, "
                                 f"using example config")
                    config_file = example_config
                else:
                    raise FileNotFoundError(f"No config file found at {self.config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Espandi variabili d'ambiente
            config = self._expand_env_vars(config)
            
            logger.info(f"Configuration loaded from {config_file}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _expand_env_vars(self, obj):
        """Espande variabili d'ambiente nella configurazione"""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        else:
            return obj
    
    def _signal_handler(self, signum, frame):
        """Gestisce segnali di sistema per shutdown graceful"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _initialize_components(self):
        """Inizializza tutti i componenti del sistema"""
        logger.info("Initializing voice assistant components...")
        
        try:
            # Audio Input Manager
            audio_config = self.config.get('audio', {})
            self.audio_manager = AudioInputManager(audio_config)
            
            # Wake Word Detection Service
            wake_word_config = self.config.get('wake_word', {})
            self.wake_word_service = WakeWordDetectionService(wake_word_config)
            
            # Speech Recognition Engine
            speech_config = self.config.get('speech_recognition', {})
            self.speech_engine = SpeechRecognitionEngine(speech_config)
            
            # Collega i componenti
            self._connect_components()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _connect_components(self):
        """Collega i componenti tra loro"""
        # Audio input -> Wake word detection
        self.audio_manager.add_callback(self.wake_word_service.process_audio)
        
        # Audio input -> Speech recognition (quando attivo)
        self.audio_manager.add_callback(self._audio_for_speech_recognition)
        
        # Wake word events -> Speech recognition activation
        self.wake_word_service.add_callback(self._on_wake_word_detected)
        
        # Speech recognition results -> Command processing
        self.speech_engine.add_callback(self._on_speech_recognized)
    
    def _audio_for_speech_recognition(self, audio_data):
        """Inoltra audio al speech recognition quando attivo"""
        if self.is_listening_for_command:
            self.speech_engine.process_audio_frame(audio_data)
    
    def _on_wake_word_detected(self, event: WakeWordEvent):
        """Gestisce detection di wake word"""
        logger.info(f"Wake word detected: {event.wake_word} "
                   f"(confidence: {event.confidence:.3f})")
        
        # Attiva modalità ascolto comandi
        self.is_listening_for_command = True
        
        # Avvia speech recognition
        self.speech_engine.start_recognition()
        
        # Feedback audio (opzionale)
        self._play_activation_sound()
        
        # Setup timeout per auto-stop
        asyncio.create_task(self._command_timeout_handler())
    
    def _on_speech_recognized(self, result: RecognitionResult):
        """Gestisce risultati del riconoscimento vocale"""
        logger.info(f"Speech recognized: '{result.text}' "
                   f"(confidence: {result.confidence:.3f}, "
                   f"engine: {result.engine.value})")
        
        # Processa comando
        self._process_voice_command(result.text, result.confidence)
        
        # Ferma ascolto
        self._stop_listening_for_command()
    
    def _process_voice_command(self, text: str, confidence: float):
        """Processa comando vocale riconosciuto"""
        # Per ora, semplice logging del comando
        # In futuro, qui andrà il Natural Language Processor
        
        logger.info(f"Processing command: '{text}'")
        
        # Comandi di test semplici
        text_lower = text.lower()
        
        if 'pausa' in text_lower or 'pause' in text_lower:
            logger.info("Command: PAUSE")
            self._send_feedback("Musica in pausa")
            
        elif 'riproduci' in text_lower or 'play' in text_lower:
            logger.info("Command: PLAY")
            self._send_feedback("Avvio riproduzione")
            
        elif 'volume' in text_lower:
            logger.info("Command: VOLUME")
            self._send_feedback("Volume modificato")
            
        elif 'stop' in text_lower:
            logger.info("Command: STOP")
            self._send_feedback("Riproduzione fermata")
            
        elif 'prossimo' in text_lower or 'next' in text_lower:
            logger.info("Command: NEXT")
            self._send_feedback("Prossimo brano")
            
        else:
            logger.info(f"Command not recognized: '{text}'")
            self._send_feedback("Comando non riconosciuto")
    
    def _send_feedback(self, message: str):
        """Invia feedback vocale all'utente"""
        # Per ora, solo logging
        # In futuro, qui andrà il TTS system
        logger.info(f"Feedback: {message}")
    
    def _play_activation_sound(self):
        """Riproduce suono di attivazione"""
        # Implementazione futura per feedback audio
        pass
    
    async def _command_timeout_handler(self):
        """Gestisce timeout per comandi vocali"""
        await asyncio.sleep(self.command_timeout)
        
        if self.is_listening_for_command:
            logger.info("Command timeout, stopping speech recognition")
            self._stop_listening_for_command()
            self._send_feedback("Timeout comando")
    
    def _stop_listening_for_command(self):
        """Ferma ascolto comandi"""
        if self.is_listening_for_command:
            self.is_listening_for_command = False
            self.speech_engine.stop_recognition()
            logger.debug("Stopped listening for commands")
    
    def start(self):
        """Avvia il voice assistant"""
        if self.is_running:
            logger.warning("Voice assistant already running")
            return
        
        logger.info("Starting Voice Assistant...")
        
        try:
            # Inizializza componenti
            self._initialize_components()
            
            # Avvia servizi
            self.wake_word_service.start()
            self.audio_manager.start_recording()
            
            self.is_running = True
            
            logger.info("🎤 Voice Assistant started successfully!")
            logger.info("Say a wake word to activate the system")
            
            # Mostra informazioni di sistema
            self._show_system_info()
            
        except Exception as e:
            logger.error(f"Failed to start voice assistant: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Ferma il voice assistant"""
        if not self.is_running:
            return
        
        logger.info("Stopping Voice Assistant...")
        
        self.is_running = False
        
        # Ferma ascolto comandi se attivo
        self._stop_listening_for_command()
        
        # Ferma servizi
        if self.wake_word_service:
            self.wake_word_service.stop()
        
        if self.audio_manager:
            self.audio_manager.stop_recording()
        
        logger.info("Voice Assistant stopped")
    
    def _show_system_info(self):
        """Mostra informazioni di sistema"""
        logger.info("=== System Information ===")
        
        # Dispositivi audio
        if self.audio_manager:
            devices = self.audio_manager.list_audio_devices()
            logger.info(f"Audio devices: {len(devices['input_devices'])} available")
            logger.info(f"Default device: {devices['default_device']}")
        
        # Wake words configurate
        if self.wake_word_service:
            wake_words = [ww.get('name', 'unknown') if isinstance(ww, dict) else str(ww) 
                         for ww in self.config.get('wake_word', {}).get('wake_words', [])]
            logger.info(f"Wake words: {', '.join(wake_words)}")
        
        # Engines speech recognition
        speech_config = self.config.get('speech_recognition', {})
        primary = speech_config.get('primary_engine', 'unknown')
        fallback = speech_config.get('fallback_engine', 'unknown')
        logger.info(f"Speech engines: {primary} (primary), {fallback} (fallback)")
        
        logger.info("========================")
    
    async def run_forever(self):
        """Esegue il voice assistant indefinitamente"""
        self.start()
        
        try:
            while self.is_running:
                await asyncio.sleep(1)
                
                # Mostra statistiche periodicamente
                if hasattr(self, '_last_stats_time'):
                    if asyncio.get_event_loop().time() - self._last_stats_time > 30:
                        self._show_stats()
                        self._last_stats_time = asyncio.get_event_loop().time()
                else:
                    self._last_stats_time = asyncio.get_event_loop().time()
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def _show_stats(self):
        """Mostra statistiche del sistema"""
        if not self.is_running:
            return
            
        stats = {}
        
        if self.audio_manager:
            stats['audio'] = self.audio_manager.get_stats()
        
        if self.wake_word_service:
            stats['wake_word'] = self.wake_word_service.get_stats()
        
        if self.speech_engine:
            stats['speech'] = self.speech_engine.get_stats()
        
        logger.info(f"Stats - Audio frames: {stats.get('audio', {}).get('frames_processed', 0)}, "
                   f"Wake word detections: {stats.get('wake_word', {}).get('detections', 0)}, "
                   f"Speech recognitions: {stats.get('speech', {}).get('recognitions', 0)}")


def main():
    """Funzione principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Voice Assistant per Navidrome')
    parser.add_argument('--config', '-c', 
                       default='config/config.yaml',
                       help='Path al file di configurazione')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='Abilita logging verbose')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Crea e avvia voice assistant
    try:
        assistant = VoiceAssistant(config_path=args.config)
        
        # Esegui in loop asincrono
        asyncio.run(assistant.run_forever())
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

