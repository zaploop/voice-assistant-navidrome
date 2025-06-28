"""
Audio Input Manager
Gestisce acquisizione e preprocessing audio da microfono
"""

import asyncio
import logging
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, Dict, Any
import threading
import queue
import time

logger = logging.getLogger(__name__)


class AudioInputManager:
    """
    Gestisce acquisizione audio continua da microfono con preprocessing
    e distribuzione a componenti downstream
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sample_rate = config.get('sample_rate', 16000)
        self.channels = config.get('channels', 1)
        self.chunk_size = config.get('chunk_size', 1024)
        self.device_index = config.get('device_index', None)
        
        # Audio preprocessing settings
        self.noise_reduction = config.get('noise_reduction', True)
        self.vad_threshold = config.get('vad_threshold', 0.3)
        self.normalization = config.get('normalization', True)
        
        # Internal state
        self.is_recording = False
        self.audio_queue = queue.Queue(maxsize=100)
        self.callbacks = []
        self.stream = None
        self.recording_thread = None
        
        # Audio statistics
        self.stats = {
            'frames_processed': 0,
            'avg_volume': 0.0,
            'noise_level': 0.0,
            'last_activity': 0
        }
        
    def add_callback(self, callback: Callable[[np.ndarray], None]):
        """Aggiunge callback per ricevere frame audio"""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable[[np.ndarray], None]):
        """Rimuove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback per stream audio da sounddevice"""
        if status:
            logger.warning(f"Audio callback status: {status}")
            
        # Converti a mono se necessario
        if indata.shape[1] > 1:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata[:, 0]
            
        # Aggiungi a queue per processing asincrono
        try:
            self.audio_queue.put_nowait(audio_data.copy())
        except queue.Full:
            logger.warning("Audio queue full, dropping frame")
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Applica preprocessing all'audio"""
        processed = audio_data.copy()
        
        # Normalizzazione volume
        if self.normalization:
            max_val = np.max(np.abs(processed))
            if max_val > 0:
                processed = processed / max_val * 0.8
        
        # Riduzione rumore semplice (high-pass filter)
        if self.noise_reduction:
            # Implementazione semplificata - in produzione usare filtri più sofisticati
            processed = self._high_pass_filter(processed)
        
        return processed
    
    def _high_pass_filter(self, audio_data: np.ndarray, cutoff: float = 80.0) -> np.ndarray:
        """Filtro passa-alto semplice per ridurre rumore a bassa frequenza"""
        from scipy import signal
        
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff / nyquist
        b, a = signal.butter(2, normalized_cutoff, btype='high')
        
        return signal.filtfilt(b, a, audio_data)
    
    def _voice_activity_detection(self, audio_data: np.ndarray) -> bool:
        """Semplice Voice Activity Detection basato su energia"""
        energy = np.sum(audio_data ** 2) / len(audio_data)
        return energy > self.vad_threshold
    
    def _update_stats(self, audio_data: np.ndarray, has_voice: bool):
        """Aggiorna statistiche audio"""
        self.stats['frames_processed'] += 1
        
        # Volume medio
        volume = np.sqrt(np.mean(audio_data ** 2))
        self.stats['avg_volume'] = (self.stats['avg_volume'] * 0.9 + volume * 0.1)
        
        # Livello rumore (quando non c'è voce)
        if not has_voice:
            self.stats['noise_level'] = (self.stats['noise_level'] * 0.95 + volume * 0.05)
        
        # Ultima attività vocale
        if has_voice:
            self.stats['last_activity'] = time.time()
    
    def _processing_loop(self):
        """Loop principale per processing audio"""
        logger.info("Audio processing loop started")
        
        while self.is_recording:
            try:
                # Ottieni frame audio dalla queue
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # Preprocessing
                processed_audio = self._preprocess_audio(audio_data)
                
                # Voice Activity Detection
                has_voice = self._voice_activity_detection(processed_audio)
                
                # Aggiorna statistiche
                self._update_stats(processed_audio, has_voice)
                
                # Invia a tutti i callback registrati
                for callback in self.callbacks:
                    try:
                        callback(processed_audio)
                    except Exception as e:
                        logger.error(f"Error in audio callback: {e}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")
                
        logger.info("Audio processing loop stopped")
    
    def start_recording(self):
        """Avvia acquisizione audio"""
        if self.is_recording:
            logger.warning("Recording already started")
            return
            
        logger.info("Starting audio recording...")
        
        try:
            # Configura stream audio
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=self.chunk_size,
                device=self.device_index,
                callback=self._audio_callback
            )
            
            # Avvia stream
            self.stream.start()
            self.is_recording = True
            
            # Avvia thread di processing
            self.recording_thread = threading.Thread(
                target=self._processing_loop,
                daemon=True
            )
            self.recording_thread.start()
            
            logger.info(f"Audio recording started - Sample rate: {self.sample_rate}Hz, "
                       f"Channels: {self.channels}, Chunk size: {self.chunk_size}")
            
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}")
            self.is_recording = False
            raise
    
    def stop_recording(self):
        """Ferma acquisizione audio"""
        if not self.is_recording:
            return
            
        logger.info("Stopping audio recording...")
        
        self.is_recording = False
        
        # Ferma stream audio
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Aspetta che il thread di processing finisca
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
        
        logger.info("Audio recording stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche audio correnti"""
        return self.stats.copy()
    
    def list_audio_devices(self) -> Dict[str, Any]:
        """Lista dispositivi audio disponibili"""
        devices = sd.query_devices()
        input_devices = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        
        return {
            'default_device': sd.default.device[0],
            'input_devices': input_devices
        }


# Test del modulo
if __name__ == "__main__":
    import time
    
    # Configurazione test
    config = {
        'sample_rate': 16000,
        'channels': 1,
        'chunk_size': 1024,
        'noise_reduction': True,
        'vad_threshold': 0.01,
        'normalization': True
    }
    
    # Callback di test
    def audio_callback(audio_data):
        volume = np.sqrt(np.mean(audio_data ** 2))
        if volume > 0.01:  # Solo se c'è audio significativo
            print(f"Audio frame: {len(audio_data)} samples, volume: {volume:.4f}")
    
    # Test del sistema
    audio_manager = AudioInputManager(config)
    
    print("Dispositivi audio disponibili:")
    devices = audio_manager.list_audio_devices()
    for device in devices['input_devices']:
        print(f"  {device['index']}: {device['name']} ({device['channels']} ch)")
    
    print(f"\nDispositivo default: {devices['default_device']}")
    
    # Aggiungi callback e avvia recording
    audio_manager.add_callback(audio_callback)
    
    try:
        audio_manager.start_recording()
        print("\nRecording started. Speak into microphone...")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            stats = audio_manager.get_stats()
            print(f"Stats - Frames: {stats['frames_processed']}, "
                  f"Avg Volume: {stats['avg_volume']:.4f}, "
                  f"Noise: {stats['noise_level']:.4f}")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        audio_manager.stop_recording()
        print("Recording stopped")

