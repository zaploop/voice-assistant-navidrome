"""
Wake Word Detection Service
Utilizza openWakeWord per rilevamento parole di attivazione
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Callable, List, Optional
import threading
import queue
import time
from dataclasses import dataclass

try:
    import openwakeword
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logging.warning("openWakeWord not available, using mock implementation")

logger = logging.getLogger(__name__)


@dataclass
class WakeWordEvent:
    """Evento di rilevamento wake word"""
    wake_word: str
    confidence: float
    timestamp: float
    audio_data: Optional[np.ndarray] = None


class MockWakeWordModel:
    """Mock implementation per testing quando openWakeWord non è disponibile"""
    
    def __init__(self, wake_words: List[str]):
        self.wake_words = wake_words
        self.frame_count = 0
        
    def predict(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Simula detection basata su volume audio"""
        self.frame_count += 1
        
        # Simula detection ogni 100 frame se c'è audio significativo
        volume = np.sqrt(np.mean(audio_data ** 2))
        
        results = {}
        for wake_word in self.wake_words:
            if self.frame_count % 100 == 0 and volume > 0.1:
                results[wake_word] = 0.8  # Simula alta confidenza
            else:
                results[wake_word] = 0.1  # Bassa confidenza
                
        return results


class WakeWordDetectionService:
    """
    Servizio per rilevamento continuo di parole di attivazione
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.wake_words = config.get('wake_words', [])
        self.default_threshold = config.get('default_threshold', 0.5)
        self.timeout_seconds = config.get('timeout_seconds', 10)
        self.enable_speex = config.get('enable_speex', False)
        self.vad_threshold = config.get('vad_threshold', 0.3)
        
        # Stato interno
        self.is_active = False
        self.is_listening = False
        self.model = None
        self.audio_queue = queue.Queue(maxsize=50)
        self.detection_thread = None
        self.callbacks = []
        
        # Buffer audio per context
        self.audio_buffer = []
        self.buffer_size = int(16000 * 2)  # 2 secondi di audio
        
        # Statistiche
        self.stats = {
            'detections': 0,
            'false_positives': 0,
            'frames_processed': 0,
            'avg_confidence': 0.0,
            'last_detection': 0
        }
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Inizializza il modello wake word"""
        try:
            if OPENWAKEWORD_AVAILABLE:
                logger.info("Initializing openWakeWord model...")
                
                # Scarica modelli se necessario
                openwakeword.utils.download_models()
                
                # Configura modelli wake word
                model_paths = []
                for wake_word_config in self.wake_words:
                    if isinstance(wake_word_config, dict):
                        model_path = wake_word_config.get('model_path')
                        if model_path:
                            model_paths.append(model_path)
                    elif isinstance(wake_word_config, str):
                        # Usa modelli predefiniti
                        model_paths.append(wake_word_config)
                
                # Inizializza modello
                self.model = Model(
                    wakeword_models=model_paths if model_paths else None,
                    enable_speex_noise_suppression=self.enable_speex,
                    vad_threshold=self.vad_threshold if self.vad_threshold > 0 else None
                )
                
                logger.info(f"Wake word model initialized with {len(model_paths)} models")
                
            else:
                # Usa mock per testing
                wake_word_names = []
                for ww in self.wake_words:
                    if isinstance(ww, dict):
                        wake_word_names.append(ww.get('name', 'unknown'))
                    else:
                        wake_word_names.append(str(ww))
                
                self.model = MockWakeWordModel(wake_word_names)
                logger.warning("Using mock wake word model for testing")
                
        except Exception as e:
            logger.error(f"Failed to initialize wake word model: {e}")
            raise
    
    def add_callback(self, callback: Callable[[WakeWordEvent], None]):
        """Aggiunge callback per eventi di detection"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[WakeWordEvent], None]):
        """Rimuove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def process_audio(self, audio_data: np.ndarray):
        """Processa frame audio per wake word detection"""
        if not self.is_active:
            return
            
        # Aggiungi al buffer audio
        self.audio_buffer.extend(audio_data)
        if len(self.audio_buffer) > self.buffer_size:
            self.audio_buffer = self.audio_buffer[-self.buffer_size:]
        
        # Aggiungi alla queue per processing asincrono
        try:
            self.audio_queue.put_nowait(audio_data.copy())
        except queue.Full:
            logger.warning("Wake word detection queue full, dropping frame")
    
    def _detection_loop(self):
        """Loop principale per detection wake word"""
        logger.info("Wake word detection loop started")
        
        while self.is_active:
            try:
                # Ottieni frame audio
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # Processa con modello wake word
                predictions = self.model.predict(audio_data)
                
                # Aggiorna statistiche
                self.stats['frames_processed'] += 1
                
                # Controlla detection
                for wake_word, confidence in predictions.items():
                    threshold = self._get_threshold_for_wake_word(wake_word)
                    
                    if confidence > threshold:
                        self._handle_detection(wake_word, confidence, audio_data)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in wake word detection loop: {e}")
        
        logger.info("Wake word detection loop stopped")
    
    def _get_threshold_for_wake_word(self, wake_word: str) -> float:
        """Ottiene soglia specifica per wake word"""
        for ww_config in self.wake_words:
            if isinstance(ww_config, dict):
                if ww_config.get('name') == wake_word:
                    return ww_config.get('threshold', self.default_threshold)
        
        return self.default_threshold
    
    def _handle_detection(self, wake_word: str, confidence: float, audio_data: np.ndarray):
        """Gestisce detection di wake word"""
        current_time = time.time()
        
        # Evita detection multiple ravvicinate
        if current_time - self.stats['last_detection'] < 2.0:
            return
        
        logger.info(f"Wake word detected: '{wake_word}' (confidence: {confidence:.3f})")
        
        # Aggiorna statistiche
        self.stats['detections'] += 1
        self.stats['last_detection'] = current_time
        self.stats['avg_confidence'] = (
            self.stats['avg_confidence'] * 0.9 + confidence * 0.1
        )
        
        # Crea evento
        event = WakeWordEvent(
            wake_word=wake_word,
            confidence=confidence,
            timestamp=current_time,
            audio_data=np.array(self.audio_buffer) if self.audio_buffer else None
        )
        
        # Notifica callback
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")
    
    def start(self):
        """Avvia servizio wake word detection"""
        if self.is_active:
            logger.warning("Wake word detection already active")
            return
        
        logger.info("Starting wake word detection service...")
        
        self.is_active = True
        
        # Avvia thread di detection
        self.detection_thread = threading.Thread(
            target=self._detection_loop,
            daemon=True
        )
        self.detection_thread.start()
        
        logger.info("Wake word detection service started")
    
    def stop(self):
        """Ferma servizio wake word detection"""
        if not self.is_active:
            return
        
        logger.info("Stopping wake word detection service...")
        
        self.is_active = False
        
        # Aspetta che il thread finisca
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2.0)
        
        logger.info("Wake word detection service stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche detection"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistiche"""
        self.stats = {
            'detections': 0,
            'false_positives': 0,
            'frames_processed': 0,
            'avg_confidence': 0.0,
            'last_detection': 0
        }
    
    def get_available_models(self) -> List[str]:
        """Lista modelli wake word disponibili"""
        if OPENWAKEWORD_AVAILABLE:
            try:
                # Questa è una lista approssimativa dei modelli comuni
                return [
                    "alexa", "hey_jarvis", "hey_mycroft", "hey_rhasspy",
                    "ok_navidrome", "computer", "jarvis"
                ]
            except:
                return []
        else:
            return ["mock_wake_word"]


# Test del modulo
if __name__ == "__main__":
    import time
    from audio_input import AudioInputManager
    
    # Configurazione test
    wake_word_config = {
        'wake_words': [
            {
                'name': 'hey_jarvis',
                'threshold': 0.5
            }
        ],
        'default_threshold': 0.5,
        'timeout_seconds': 10,
        'enable_speex': False,
        'vad_threshold': 0.3
    }
    
    audio_config = {
        'sample_rate': 16000,
        'channels': 1,
        'chunk_size': 1024,
        'noise_reduction': True,
        'vad_threshold': 0.01,
        'normalization': True
    }
    
    # Callback per detection
    def on_wake_word_detected(event: WakeWordEvent):
        print(f"\n🎯 WAKE WORD DETECTED!")
        print(f"   Word: {event.wake_word}")
        print(f"   Confidence: {event.confidence:.3f}")
        print(f"   Timestamp: {event.timestamp}")
        print("   System is now listening for commands...\n")
    
    # Inizializza servizi
    wake_word_service = WakeWordDetectionService(wake_word_config)
    audio_manager = AudioInputManager(audio_config)
    
    # Collega audio input a wake word detection
    audio_manager.add_callback(wake_word_service.process_audio)
    wake_word_service.add_callback(on_wake_word_detected)
    
    print("Available wake word models:")
    models = wake_word_service.get_available_models()
    for model in models:
        print(f"  - {model}")
    
    try:
        # Avvia servizi
        wake_word_service.start()
        audio_manager.start_recording()
        
        print(f"\n🎤 Wake word detection active!")
        print(f"Say 'hey jarvis' to activate the system")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(5)
            
            # Mostra statistiche
            ww_stats = wake_word_service.get_stats()
            audio_stats = audio_manager.get_stats()
            
            print(f"Stats - WW Detections: {ww_stats['detections']}, "
                  f"Frames: {ww_stats['frames_processed']}, "
                  f"Audio Volume: {audio_stats['avg_volume']:.4f}")
            
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        wake_word_service.stop()
        audio_manager.stop_recording()
        print("Services stopped")

