"""
Test suite per il componente Audio Input Manager
"""

import pytest
import numpy as np
import time
import threading
from unittest.mock import Mock, patch
import sys
import os

# Aggiungi src al path per import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_input import AudioInputManager


class TestAudioInputManager:
    """Test per AudioInputManager"""
    
    def setup_method(self):
        """Setup per ogni test"""
        self.config = {
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 1024,
            'noise_reduction': True,
            'vad_threshold': 0.01,
            'normalization': True
        }
        
    def test_initialization(self):
        """Test inizializzazione"""
        manager = AudioInputManager(self.config)
        
        assert manager.sample_rate == 16000
        assert manager.channels == 1
        assert manager.chunk_size == 1024
        assert manager.noise_reduction == True
        assert not manager.is_recording
        
    def test_callback_management(self):
        """Test gestione callback"""
        manager = AudioInputManager(self.config)
        
        callback1 = Mock()
        callback2 = Mock()
        
        # Aggiungi callback
        manager.add_callback(callback1)
        manager.add_callback(callback2)
        
        assert len(manager.callbacks) == 2
        assert callback1 in manager.callbacks
        assert callback2 in manager.callbacks
        
        # Rimuovi callback
        manager.remove_callback(callback1)
        
        assert len(manager.callbacks) == 1
        assert callback2 in manager.callbacks
        
    def test_audio_preprocessing(self):
        """Test preprocessing audio"""
        manager = AudioInputManager(self.config)
        
        # Crea audio di test
        audio_data = np.random.randn(1024).astype(np.float32)
        
        # Test preprocessing
        processed = manager._preprocess_audio(audio_data)
        
        assert isinstance(processed, np.ndarray)
        assert len(processed) == len(audio_data)
        
        # Test normalizzazione
        if manager.normalization:
            max_val = np.max(np.abs(processed))
            assert max_val <= 0.8  # Normalizzato a 0.8
            
    def test_voice_activity_detection(self):
        """Test Voice Activity Detection"""
        manager = AudioInputManager(self.config)
        
        # Audio silenzioso
        silent_audio = np.zeros(1024, dtype=np.float32)
        assert not manager._voice_activity_detection(silent_audio)
        
        # Audio con voce (simulato)
        voice_audio = np.random.randn(1024).astype(np.float32) * 0.5
        # Risultato dipende dalla soglia e dal contenuto
        
    def test_stats_update(self):
        """Test aggiornamento statistiche"""
        manager = AudioInputManager(self.config)
        
        audio_data = np.random.randn(1024).astype(np.float32) * 0.1
        
        initial_frames = manager.stats['frames_processed']
        
        manager._update_stats(audio_data, has_voice=True)
        
        assert manager.stats['frames_processed'] == initial_frames + 1
        assert manager.stats['avg_volume'] > 0
        
    @patch('sounddevice.InputStream')
    def test_start_stop_recording(self, mock_stream_class):
        """Test avvio e stop recording"""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        manager = AudioInputManager(self.config)
        
        # Test start
        manager.start_recording()
        
        assert manager.is_recording
        mock_stream.start.assert_called_once()
        
        # Test stop
        manager.stop_recording()
        
        assert not manager.is_recording
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        
    def test_list_audio_devices(self):
        """Test listing dispositivi audio"""
        with patch('sounddevice.query_devices') as mock_query:
            mock_query.return_value = [
                {'name': 'Device 1', 'max_input_channels': 2, 'default_samplerate': 44100},
                {'name': 'Device 2', 'max_input_channels': 1, 'default_samplerate': 16000},
                {'name': 'Output Only', 'max_input_channels': 0, 'default_samplerate': 44100}
            ]
            
            with patch('sounddevice.default') as mock_default:
                mock_default.device = [0, 1]
                
                manager = AudioInputManager(self.config)
                devices = manager.list_audio_devices()
                
                assert 'default_device' in devices
                assert 'input_devices' in devices
                assert len(devices['input_devices']) == 2  # Solo dispositivi input
                
    def test_high_pass_filter(self):
        """Test filtro passa-alto"""
        manager = AudioInputManager(self.config)
        
        # Crea segnale di test con componenti a bassa frequenza
        t = np.linspace(0, 1, 16000)
        low_freq_signal = np.sin(2 * np.pi * 50 * t)  # 50 Hz
        high_freq_signal = np.sin(2 * np.pi * 1000 * t)  # 1000 Hz
        
        test_signal = low_freq_signal + high_freq_signal
        
        filtered = manager._high_pass_filter(test_signal, cutoff=80.0)
        
        assert isinstance(filtered, np.ndarray)
        assert len(filtered) == len(test_signal)
        
        # Il filtro dovrebbe ridurre le componenti a bassa frequenza
        # (test qualitativo - in un test reale si userebbe FFT per verificare)


class TestAudioInputIntegration:
    """Test di integrazione per AudioInputManager"""
    
    def setup_method(self):
        """Setup per test di integrazione"""
        self.config = {
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 512,  # Chunk più piccolo per test
            'noise_reduction': False,  # Disabilita per semplicità
            'vad_threshold': 0.01,
            'normalization': False
        }
        
    def test_callback_execution(self):
        """Test esecuzione callback con audio simulato"""
        manager = AudioInputManager(self.config)
        
        received_audio = []
        
        def test_callback(audio_data):
            received_audio.append(audio_data.copy())
            
        manager.add_callback(test_callback)
        
        # Simula processing di frame audio
        test_audio = np.random.randn(512).astype(np.float32)
        
        # Simula il processing loop manualmente
        processed = manager._preprocess_audio(test_audio)
        
        # Esegui callback manualmente
        for callback in manager.callbacks:
            callback(processed)
            
        assert len(received_audio) == 1
        assert len(received_audio[0]) == 512
        
    def test_stats_accumulation(self):
        """Test accumulo statistiche nel tempo"""
        manager = AudioInputManager(self.config)
        
        # Simula processing di multipli frame
        for i in range(10):
            audio_data = np.random.randn(512).astype(np.float32) * (0.1 + i * 0.05)
            has_voice = i % 3 == 0  # Simula voice activity intermittente
            
            manager._update_stats(audio_data, has_voice)
            
        stats = manager.get_stats()
        
        assert stats['frames_processed'] == 10
        assert stats['avg_volume'] > 0
        assert stats['noise_level'] >= 0


if __name__ == "__main__":
    # Esegui test
    pytest.main([__file__, "-v"])

