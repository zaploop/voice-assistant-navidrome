"""
Speech Recognition Engine
Motore ibrido che utilizza Vosk per latenza bassa e Whisper per accuratezza alta
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Callable
import threading
import queue
import time
import json
from dataclasses import dataclass
from enum import Enum

# Vosk imports
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk not available")

# Whisper imports  
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("Whisper not available")

logger = logging.getLogger(__name__)


class RecognitionEngine(Enum):
    """Tipi di engine di riconoscimento"""
    VOSK = "vosk"
    WHISPER = "whisper"
    AUTO = "auto"


@dataclass
class RecognitionResult:
    """Risultato del riconoscimento vocale"""
    text: str
    confidence: float
    engine: RecognitionEngine
    processing_time: float
    timestamp: float
    alternatives: Optional[List[str]] = None


class MockRecognitionEngine:
    """Mock engine per testing quando le librerie non sono disponibili"""
    
    def __init__(self, engine_type: str):
        self.engine_type = engine_type
        self.frame_count = 0
        
    def recognize(self, audio_data: np.ndarray) -> Optional[RecognitionResult]:
        """Simula riconoscimento basato su pattern audio"""
        self.frame_count += 1
        
        # Simula riconoscimento ogni 20 frame se c'è audio
        volume = np.sqrt(np.mean(audio_data ** 2))
        
        if self.frame_count % 20 == 0 and volume > 0.1:
            mock_texts = [
                "riproduci musica",
                "pausa",
                "volume alto",
                "prossimo brano",
                "stop"
            ]
            
            text = mock_texts[self.frame_count % len(mock_texts)]
            
            return RecognitionResult(
                text=text,
                confidence=0.85,
                engine=RecognitionEngine(self.engine_type),
                processing_time=0.1,
                timestamp=time.time()
            )
        
        return None


class VoskRecognitionEngine:
    """Engine Vosk per riconoscimento streaming a bassa latenza"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_path = config.get('model_path', 'models/vosk-model-it-0.22')
        self.sample_rate = config.get('sample_rate', 16000)
        self.max_alternatives = config.get('max_alternatives', 3)
        
        self.model = None
        self.recognizer = None
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Inizializza modello Vosk"""
        if not VOSK_AVAILABLE:
            logger.warning("Vosk not available, using mock")
            self.model = MockRecognitionEngine("vosk")
            return
            
        try:
            logger.info(f"Loading Vosk model from {self.model_path}")
            
            # Carica modello
            self.model = vosk.Model(self.model_path)
            
            # Crea recognizer
            self.recognizer = vosk.KaldiRecognizer(
                self.model, 
                self.sample_rate
            )
            
            # Configura per alternative multiple
            self.recognizer.SetMaxAlternatives(self.max_alternatives)
            
            logger.info("Vosk model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}")
            self.model = MockRecognitionEngine("vosk")
    
    def recognize(self, audio_data: np.ndarray) -> Optional[RecognitionResult]:
        """Riconosce speech da audio data"""
        if isinstance(self.model, MockRecognitionEngine):
            return self.model.recognize(audio_data)
            
        start_time = time.time()
        
        try:
            # Converti audio a bytes (16-bit PCM)
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            
            # Processa audio
            if self.recognizer.AcceptWaveform(audio_bytes):
                # Riconoscimento completo
                result = json.loads(self.recognizer.Result())
                
                if result.get('text'):
                    processing_time = time.time() - start_time
                    
                    # Estrai alternative se disponibili
                    alternatives = []
                    if 'alternatives' in result:
                        alternatives = [alt.get('text', '') for alt in result['alternatives']]
                    
                    return RecognitionResult(
                        text=result['text'],
                        confidence=result.get('confidence', 0.0),
                        engine=RecognitionEngine.VOSK,
                        processing_time=processing_time,
                        timestamp=time.time(),
                        alternatives=alternatives
                    )
            else:
                # Riconoscimento parziale (opzionale)
                partial = json.loads(self.recognizer.PartialResult())
                if partial.get('partial'):
                    # Per ora ignoriamo i risultati parziali
                    pass
                    
        except Exception as e:
            logger.error(f"Vosk recognition error: {e}")
        
        return None


class WhisperRecognitionEngine:
    """Engine Whisper per riconoscimento ad alta accuratezza"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_size = config.get('model_size', 'medium')
        self.language = config.get('language', 'it')
        self.temperature = config.get('temperature', 0.0)
        
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Inizializza modello Whisper"""
        if not WHISPER_AVAILABLE:
            logger.warning("Whisper not available, using mock")
            self.model = MockRecognitionEngine("whisper")
            return
            
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            
            self.model = whisper.load_model(self.model_size)
            
            logger.info("Whisper model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = MockRecognitionEngine("whisper")
    
    def recognize(self, audio_data: np.ndarray) -> Optional[RecognitionResult]:
        """Riconosce speech da audio data"""
        if isinstance(self.model, MockRecognitionEngine):
            return self.model.recognize(audio_data)
            
        start_time = time.time()
        
        try:
            # Whisper richiede audio normalizzato
            if len(audio_data) < 16000:  # Minimo 1 secondo
                return None
                
            # Normalizza audio
            audio_normalized = audio_data.astype(np.float32)
            if np.max(np.abs(audio_normalized)) > 0:
                audio_normalized = audio_normalized / np.max(np.abs(audio_normalized))
            
            # Riconosci con Whisper
            result = self.model.transcribe(
                audio_normalized,
                language=self.language,
                temperature=self.temperature,
                word_timestamps=False
            )
            
            processing_time = time.time() - start_time
            
            if result['text'].strip():
                return RecognitionResult(
                    text=result['text'].strip(),
                    confidence=1.0,  # Whisper non fornisce confidence score
                    engine=RecognitionEngine.WHISPER,
                    processing_time=processing_time,
                    timestamp=time.time()
                )
                
        except Exception as e:
            logger.error(f"Whisper recognition error: {e}")
        
        return None


class SpeechRecognitionEngine:
    """
    Motore principale che coordina Vosk e Whisper per riconoscimento ottimale
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_engine = config.get('primary_engine', 'vosk')
        self.fallback_engine = config.get('fallback_engine', 'whisper')
        self.auto_switch_threshold = config.get('auto_switch_threshold', 0.7)
        self.max_audio_length = config.get('max_audio_length', 30.0)  # secondi
        
        # Inizializza engines
        self.vosk_engine = None
        self.whisper_engine = None
        
        if 'vosk' in [self.primary_engine, self.fallback_engine]:
            vosk_config = config.get('vosk', {})
            vosk_config['sample_rate'] = config.get('sample_rate', 16000)
            self.vosk_engine = VoskRecognitionEngine(vosk_config)
        
        if 'whisper' in [self.primary_engine, self.fallback_engine]:
            whisper_config = config.get('whisper', {})
            self.whisper_engine = WhisperRecognitionEngine(whisper_config)
        
        # Stato interno
        self.is_active = False
        self.audio_queue = queue.Queue(maxsize=10)
        self.recognition_thread = None
        self.callbacks = []
        
        # Buffer per accumulo audio
        self.audio_buffer = []
        self.buffer_start_time = None
        self.sample_rate = config.get('sample_rate', 16000)
        
        # Statistiche
        self.stats = {
            'recognitions': 0,
            'vosk_used': 0,
            'whisper_used': 0,
            'avg_confidence': 0.0,
            'avg_processing_time': 0.0
        }
    
    def add_callback(self, callback: Callable[[RecognitionResult], None]):
        """Aggiunge callback per risultati riconoscimento"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[RecognitionResult], None]):
        """Rimuove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def start_recognition(self, audio_data: Optional[np.ndarray] = None):
        """Avvia riconoscimento vocale"""
        if audio_data is not None:
            # Riconoscimento immediato di audio fornito
            self._process_audio_immediate(audio_data)
        else:
            # Avvia modalità streaming
            self._start_streaming_recognition()
    
    def _start_streaming_recognition(self):
        """Avvia riconoscimento streaming"""
        if self.is_active:
            return
            
        logger.info("Starting speech recognition engine...")
        
        self.is_active = True
        self.audio_buffer = []
        self.buffer_start_time = time.time()
        
        # Avvia thread di processing
        self.recognition_thread = threading.Thread(
            target=self._recognition_loop,
            daemon=True
        )
        self.recognition_thread.start()
        
        logger.info("Speech recognition engine started")
    
    def stop_recognition(self):
        """Ferma riconoscimento"""
        if not self.is_active:
            return
            
        logger.info("Stopping speech recognition engine...")
        
        self.is_active = False
        
        # Processa audio rimanente nel buffer
        if self.audio_buffer:
            self._process_accumulated_audio()
        
        # Aspetta che il thread finisca
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=2.0)
        
        logger.info("Speech recognition engine stopped")
    
    def process_audio_frame(self, audio_data: np.ndarray):
        """Processa frame audio per riconoscimento streaming"""
        if not self.is_active:
            return
            
        # Aggiungi al buffer
        self.audio_buffer.extend(audio_data)
        
        # Controlla se è tempo di processare
        current_time = time.time()
        buffer_duration = len(self.audio_buffer) / self.sample_rate
        
        if (buffer_duration >= 3.0 or  # Buffer di 3 secondi
            current_time - self.buffer_start_time >= 5.0):  # Timeout di 5 secondi
            
            # Aggiungi alla queue per processing
            try:
                audio_to_process = np.array(self.audio_buffer)
                self.audio_queue.put_nowait(audio_to_process)
                
                # Reset buffer
                self.audio_buffer = []
                self.buffer_start_time = current_time
                
            except queue.Full:
                logger.warning("Recognition queue full, dropping audio")
    
    def _recognition_loop(self):
        """Loop principale per riconoscimento"""
        logger.info("Speech recognition loop started")
        
        while self.is_active:
            try:
                # Ottieni audio dalla queue
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # Processa audio
                result = self._recognize_audio(audio_data)
                
                if result:
                    self._handle_recognition_result(result)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in recognition loop: {e}")
        
        logger.info("Speech recognition loop stopped")
    
    def _process_audio_immediate(self, audio_data: np.ndarray):
        """Processa audio immediatamente (non streaming)"""
        result = self._recognize_audio(audio_data)
        if result:
            self._handle_recognition_result(result)
    
    def _process_accumulated_audio(self):
        """Processa audio accumulato nel buffer"""
        if not self.audio_buffer:
            return
            
        audio_data = np.array(self.audio_buffer)
        result = self._recognize_audio(audio_data)
        
        if result:
            self._handle_recognition_result(result)
        
        self.audio_buffer = []
    
    def _recognize_audio(self, audio_data: np.ndarray) -> Optional[RecognitionResult]:
        """Riconosce audio utilizzando engine appropriato"""
        if len(audio_data) == 0:
            return None
            
        # Determina quale engine utilizzare
        engine_to_use = self._select_engine(audio_data)
        
        result = None
        
        if engine_to_use == RecognitionEngine.VOSK and self.vosk_engine:
            result = self.vosk_engine.recognize(audio_data)
            if result:
                self.stats['vosk_used'] += 1
                
        elif engine_to_use == RecognitionEngine.WHISPER and self.whisper_engine:
            result = self.whisper_engine.recognize(audio_data)
            if result:
                self.stats['whisper_used'] += 1
        
        # Fallback se il primo engine fallisce
        if not result and engine_to_use == RecognitionEngine.VOSK and self.whisper_engine:
            logger.debug("Vosk failed, trying Whisper fallback")
            result = self.whisper_engine.recognize(audio_data)
            if result:
                self.stats['whisper_used'] += 1
                
        elif not result and engine_to_use == RecognitionEngine.WHISPER and self.vosk_engine:
            logger.debug("Whisper failed, trying Vosk fallback")
            result = self.vosk_engine.recognize(audio_data)
            if result:
                self.stats['vosk_used'] += 1
        
        return result
    
    def _select_engine(self, audio_data: np.ndarray) -> RecognitionEngine:
        """Seleziona engine appropriato basato su caratteristiche audio"""
        audio_duration = len(audio_data) / self.sample_rate
        
        # Usa Vosk per audio breve (comandi rapidi)
        if audio_duration < 2.0:
            return RecognitionEngine.VOSK
        
        # Usa Whisper per audio lungo (query complesse)
        if audio_duration > 5.0:
            return RecognitionEngine.WHISPER
        
        # Per durata media, usa engine primario configurato
        if self.primary_engine == 'vosk':
            return RecognitionEngine.VOSK
        else:
            return RecognitionEngine.WHISPER
    
    def _handle_recognition_result(self, result: RecognitionResult):
        """Gestisce risultato del riconoscimento"""
        logger.info(f"Recognition result: '{result.text}' "
                   f"(confidence: {result.confidence:.3f}, "
                   f"engine: {result.engine.value}, "
                   f"time: {result.processing_time:.3f}s)")
        
        # Aggiorna statistiche
        self.stats['recognitions'] += 1
        self.stats['avg_confidence'] = (
            self.stats['avg_confidence'] * 0.9 + result.confidence * 0.1
        )
        self.stats['avg_processing_time'] = (
            self.stats['avg_processing_time'] * 0.9 + result.processing_time * 0.1
        )
        
        # Notifica callback
        for callback in self.callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in recognition callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche riconoscimento"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistiche"""
        self.stats = {
            'recognitions': 0,
            'vosk_used': 0,
            'whisper_used': 0,
            'avg_confidence': 0.0,
            'avg_processing_time': 0.0
        }


# Test del modulo
if __name__ == "__main__":
    import time
    from audio_input import AudioInputManager
    from wake_word import WakeWordDetectionService, WakeWordEvent
    
    # Configurazioni
    speech_config = {
        'primary_engine': 'vosk',
        'fallback_engine': 'whisper',
        'sample_rate': 16000,
        'vosk': {
            'model_path': 'models/vosk-model-it-0.22',
            'max_alternatives': 3
        },
        'whisper': {
            'model_size': 'base',
            'language': 'it'
        }
    }
    
    wake_word_config = {
        'wake_words': [{'name': 'hey_jarvis', 'threshold': 0.5}],
        'default_threshold': 0.5
    }
    
    audio_config = {
        'sample_rate': 16000,
        'channels': 1,
        'chunk_size': 1024
    }
    
    # Stato del sistema
    listening_for_command = False
    command_start_time = None
    
    # Callback per riconoscimento
    def on_speech_recognized(result: RecognitionResult):
        print(f"\n🗣️  SPEECH RECOGNIZED!")
        print(f"   Text: '{result.text}'")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Engine: {result.engine.value}")
        print(f"   Processing time: {result.processing_time:.3f}s")
        if result.alternatives:
            print(f"   Alternatives: {result.alternatives}")
        print()
    
    # Callback per wake word
    def on_wake_word(event: WakeWordEvent):
        global listening_for_command, command_start_time
        print(f"\n🎯 Wake word detected: {event.wake_word}")
        print("   Listening for command...")
        
        listening_for_command = True
        command_start_time = time.time()
        
        # Avvia riconoscimento
        speech_engine.start_recognition()
        
        # Auto-stop dopo timeout
        def auto_stop():
            time.sleep(10)  # 10 secondi timeout
            if listening_for_command:
                print("   Command timeout, stopping recognition")
                speech_engine.stop_recognition()
        
        threading.Thread(target=auto_stop, daemon=True).start()
    
    # Inizializza componenti
    speech_engine = SpeechRecognitionEngine(speech_config)
    wake_word_service = WakeWordDetectionService(wake_word_config)
    audio_manager = AudioInputManager(audio_config)
    
    # Collega callback
    speech_engine.add_callback(on_speech_recognized)
    wake_word_service.add_callback(on_wake_word)
    
    # Collega audio processing
    audio_manager.add_callback(wake_word_service.process_audio)
    
    def audio_for_speech(audio_data):
        if listening_for_command:
            speech_engine.process_audio_frame(audio_data)
    
    audio_manager.add_callback(audio_for_speech)
    
    try:
        # Avvia servizi
        wake_word_service.start()
        audio_manager.start_recording()
        
        print("🎤 Voice Assistant Test")
        print("Say 'hey jarvis' then give a command")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(5)
            
            # Mostra statistiche
            speech_stats = speech_engine.get_stats()
            wake_stats = wake_word_service.get_stats()
            
            print(f"Stats - Speech recognitions: {speech_stats['recognitions']}, "
                  f"Wake word detections: {wake_stats['detections']}, "
                  f"Avg confidence: {speech_stats['avg_confidence']:.3f}")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        speech_engine.stop_recognition()
        wake_word_service.stop()
        audio_manager.stop_recording()
        print("Test completed")

