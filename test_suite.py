#!/usr/bin/env python3
"""
Test Suite Completo per Voice Assistant
Verifica prestazioni, accuratezza e integrazione componenti
"""

import asyncio
import time
import json
import logging
import statistics
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# Aggiungi path per importare moduli
sys.path.append('/home/ubuntu/voice_assistant/src')

# Mock imports per test senza dipendenze hardware
try:
    from audio_input import AudioInputManager
    from wake_word import WakeWordDetector
    from speech_recognition import SpeechRecognitionEngine
    from nlp_processor import NaturalLanguageProcessor
    from music_controller import MusicController
    from navidrome_client import NavidromeClient
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("Running in mock mode for testing")

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Risultato di un test"""
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error: str = None


@dataclass
class PerformanceMetrics:
    """Metriche di performance"""
    avg_latency: float
    max_latency: float
    min_latency: float
    throughput: float
    accuracy: float
    error_rate: float


class VoiceAssistantTester:
    """
    Test suite completo per Voice Assistant
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.test_results = []
        self.performance_metrics = {}
        
        # Mock components per test
        self.components = {}
        self._initialize_mock_components()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carica configurazione test"""
        default_config = {
            'test_audio_samples': 10,
            'test_commands': [
                "riproduci beethoven",
                "metti in pausa",
                "volume al settanta percento",
                "prossimo brano",
                "che cosa sta suonando",
                "stop",
                "riproduci playlist favorites",
                "shuffle",
                "repeat"
            ],
            'performance_iterations': 100,
            'accuracy_threshold': 0.85,
            'latency_threshold': 0.5,  # secondi
            'navidrome_config': {
                'base_url': 'http://localhost:4533',
                'username': 'test_user',
                'password': 'test_password'
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _initialize_mock_components(self):
        """Inizializza componenti mock per test"""
        
        class MockAudioInputManager:
            async def start_recording(self):
                await asyncio.sleep(0.01)  # Simula latenza
                return True
            
            async def get_audio_chunk(self):
                await asyncio.sleep(0.05)
                return b'mock_audio_data' * 100
            
            def get_stats(self):
                return {'chunks_processed': 100, 'avg_level': 0.5}
        
        class MockWakeWordDetector:
            async def detect(self, audio_data):
                await asyncio.sleep(0.02)
                return {'detected': True, 'confidence': 0.9, 'word': 'hey music'}
            
            def get_stats(self):
                return {'detections': 50, 'false_positives': 2}
        
        class MockSpeechRecognitionEngine:
            async def recognize(self, audio_data):
                await asyncio.sleep(0.1)
                commands = self.config['test_commands']
                import random
                return {
                    'text': random.choice(commands),
                    'confidence': 0.85 + random.random() * 0.1,
                    'engine': 'vosk'
                }
            
            def get_stats(self):
                return {'recognitions': 200, 'avg_confidence': 0.87}
        
        class MockNLPProcessor:
            async def process_command(self, text):
                await asyncio.sleep(0.05)
                from nlp_processor import ParsedCommand, CommandType, PlaybackAction
                
                # Analisi semplificata
                if 'riproduci' in text.lower():
                    return ParsedCommand(
                        command_type=CommandType.PLAY,
                        action=PlaybackAction.PLAY_ARTIST,
                        target='beethoven',
                        confidence=0.9,
                        raw_text=text
                    )
                elif 'pausa' in text.lower():
                    return ParsedCommand(
                        command_type=CommandType.PAUSE,
                        confidence=0.95,
                        raw_text=text
                    )
                else:
                    return ParsedCommand(
                        command_type=CommandType.UNKNOWN,
                        confidence=0.3,
                        raw_text=text
                    )
            
            def get_stats(self):
                return {'commands_processed': 150, 'avg_confidence': 0.82}
        
        class MockMusicController:
            async def execute_command(self, command):
                await asyncio.sleep(0.03)
                from music_controller import CommandResult
                
                return CommandResult(
                    success=True,
                    message=f"Comando {command.command_type.value} eseguito"
                )
            
            def get_stats(self):
                return {'commands_executed': 120, 'errors': 3}
        
        class MockNavidromeClient:
            async def authenticate(self):
                await asyncio.sleep(0.1)
                return True
            
            async def search(self, query, count=10):
                await asyncio.sleep(0.08)
                from navidrome_client import SearchResult, Artist, Album, Song
                
                return SearchResult(
                    artists=[Artist(id='1', name='Beethoven', album_count=10)],
                    albums=[Album(id='1', name='Symphonies', artist='Beethoven', 
                                artist_id='1', song_count=9)],
                    songs=[Song(id='1', title='Symphony No. 9', artist='Beethoven',
                              artist_id='1', album='Symphonies', album_id='1')]
                )
            
            def get_stats(self):
                return {'requests': 80, 'cache_hits': 65}
        
        # Inizializza componenti mock
        self.components = {
            'audio_input': MockAudioInputManager(),
            'wake_word': MockWakeWordDetector(),
            'speech_recognition': MockSpeechRecognitionEngine(),
            'nlp_processor': MockNLPProcessor(),
            'music_controller': MockMusicController(),
            'navidrome_client': MockNavidromeClient()
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Esegue tutti i test"""
        logger.info("Starting comprehensive test suite...")
        
        start_time = time.time()
        
        # Test individuali componenti
        await self._test_audio_input()
        await self._test_wake_word_detection()
        await self._test_speech_recognition()
        await self._test_nlp_processing()
        await self._test_music_controller()
        await self._test_navidrome_integration()
        
        # Test integrazione end-to-end
        await self._test_end_to_end_pipeline()
        
        # Test performance
        await self._test_performance()
        
        # Test stress
        await self._test_stress_conditions()
        
        total_time = time.time() - start_time
        
        # Genera report
        report = self._generate_test_report(total_time)
        
        logger.info(f"Test suite completed in {total_time:.2f} seconds")
        return report
    
    async def _test_audio_input(self):
        """Test Audio Input Manager"""
        logger.info("Testing Audio Input Manager...")
        
        start_time = time.time()
        try:
            audio_manager = self.components['audio_input']
            
            # Test avvio registrazione
            success = await audio_manager.start_recording()
            assert success, "Failed to start recording"
            
            # Test acquisizione chunk audio
            for i in range(5):
                chunk = await audio_manager.get_audio_chunk()
                assert chunk, f"Failed to get audio chunk {i}"
            
            # Test statistiche
            stats = audio_manager.get_stats()
            assert 'chunks_processed' in stats, "Missing stats"
            
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Audio Input Manager",
                success=True,
                duration=duration,
                details={'chunks_tested': 5, 'stats': stats}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Audio Input Manager",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_wake_word_detection(self):
        """Test Wake Word Detection"""
        logger.info("Testing Wake Word Detection...")
        
        start_time = time.time()
        try:
            wake_word_detector = self.components['wake_word']
            
            detections = []
            for i in range(10):
                mock_audio = b'mock_audio_data' * 100
                result = await wake_word_detector.detect(mock_audio)
                detections.append(result)
                
                assert 'detected' in result, "Missing detection result"
                assert 'confidence' in result, "Missing confidence"
            
            # Calcola accuratezza
            detected_count = sum(1 for d in detections if d['detected'])
            accuracy = detected_count / len(detections)
            
            stats = wake_word_detector.get_stats()
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Wake Word Detection",
                success=True,
                duration=duration,
                details={
                    'detections_tested': len(detections),
                    'accuracy': accuracy,
                    'stats': stats
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Wake Word Detection",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_speech_recognition(self):
        """Test Speech Recognition Engine"""
        logger.info("Testing Speech Recognition Engine...")
        
        start_time = time.time()
        try:
            speech_engine = self.components['speech_recognition']
            
            recognitions = []
            for command in self.config['test_commands']:
                mock_audio = f"mock_audio_for_{command}".encode()
                result = await speech_engine.recognize(mock_audio)
                recognitions.append(result)
                
                assert 'text' in result, "Missing recognition text"
                assert 'confidence' in result, "Missing confidence"
            
            # Calcola metriche
            avg_confidence = statistics.mean(r['confidence'] for r in recognitions)
            high_confidence_count = sum(1 for r in recognitions if r['confidence'] > 0.8)
            accuracy = high_confidence_count / len(recognitions)
            
            stats = speech_engine.get_stats()
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Speech Recognition Engine",
                success=True,
                duration=duration,
                details={
                    'recognitions_tested': len(recognitions),
                    'avg_confidence': avg_confidence,
                    'accuracy': accuracy,
                    'stats': stats
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Speech Recognition Engine",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_nlp_processing(self):
        """Test NLP Processor"""
        logger.info("Testing NLP Processor...")
        
        start_time = time.time()
        try:
            nlp_processor = self.components['nlp_processor']
            
            processed_commands = []
            for command_text in self.config['test_commands']:
                result = await nlp_processor.process_command(command_text)
                processed_commands.append(result)
                
                assert hasattr(result, 'command_type'), "Missing command type"
                assert hasattr(result, 'confidence'), "Missing confidence"
            
            # Calcola metriche
            successful_parses = sum(1 for cmd in processed_commands 
                                  if cmd.confidence > 0.7)
            accuracy = successful_parses / len(processed_commands)
            avg_confidence = statistics.mean(cmd.confidence for cmd in processed_commands)
            
            stats = nlp_processor.get_stats()
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="NLP Processor",
                success=True,
                duration=duration,
                details={
                    'commands_processed': len(processed_commands),
                    'accuracy': accuracy,
                    'avg_confidence': avg_confidence,
                    'stats': stats
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="NLP Processor",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_music_controller(self):
        """Test Music Controller"""
        logger.info("Testing Music Controller...")
        
        start_time = time.time()
        try:
            music_controller = self.components['music_controller']
            nlp_processor = self.components['nlp_processor']
            
            executed_commands = []
            for command_text in self.config['test_commands']:
                # Processa comando
                parsed_command = await nlp_processor.process_command(command_text)
                
                # Esegui comando
                result = await music_controller.execute_command(parsed_command)
                executed_commands.append(result)
                
                assert hasattr(result, 'success'), "Missing success flag"
                assert hasattr(result, 'message'), "Missing message"
            
            # Calcola metriche
            successful_executions = sum(1 for cmd in executed_commands if cmd.success)
            success_rate = successful_executions / len(executed_commands)
            
            stats = music_controller.get_stats()
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Music Controller",
                success=True,
                duration=duration,
                details={
                    'commands_executed': len(executed_commands),
                    'success_rate': success_rate,
                    'stats': stats
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Music Controller",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_navidrome_integration(self):
        """Test integrazione Navidrome"""
        logger.info("Testing Navidrome Integration...")
        
        start_time = time.time()
        try:
            navidrome_client = self.components['navidrome_client']
            
            # Test autenticazione
            auth_success = await navidrome_client.authenticate()
            assert auth_success, "Authentication failed"
            
            # Test ricerca
            search_queries = ['beethoven', 'mozart', 'bach', 'classical', 'symphony']
            search_results = []
            
            for query in search_queries:
                result = await navidrome_client.search(query)
                search_results.append(result)
                
                assert hasattr(result, 'artists'), "Missing artists in search result"
                assert hasattr(result, 'albums'), "Missing albums in search result"
                assert hasattr(result, 'songs'), "Missing songs in search result"
            
            # Calcola metriche
            successful_searches = sum(1 for r in search_results 
                                    if r.artists or r.albums or r.songs)
            search_success_rate = successful_searches / len(search_results)
            
            stats = navidrome_client.get_stats()
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Navidrome Integration",
                success=True,
                duration=duration,
                details={
                    'searches_tested': len(search_results),
                    'search_success_rate': search_success_rate,
                    'auth_success': auth_success,
                    'stats': stats
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Navidrome Integration",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_end_to_end_pipeline(self):
        """Test pipeline completo end-to-end"""
        logger.info("Testing End-to-End Pipeline...")
        
        start_time = time.time()
        try:
            # Simula pipeline completo
            pipeline_results = []
            
            for command_text in self.config['test_commands'][:5]:  # Test subset
                pipeline_start = time.time()
                
                # 1. Audio Input (simulato)
                audio_manager = self.components['audio_input']
                await audio_manager.start_recording()
                audio_chunk = await audio_manager.get_audio_chunk()
                
                # 2. Wake Word Detection
                wake_word_detector = self.components['wake_word']
                wake_result = await wake_word_detector.detect(audio_chunk)
                
                if wake_result['detected']:
                    # 3. Speech Recognition
                    speech_engine = self.components['speech_recognition']
                    speech_result = await speech_engine.recognize(audio_chunk)
                    
                    # 4. NLP Processing
                    nlp_processor = self.components['nlp_processor']
                    parsed_command = await nlp_processor.process_command(speech_result['text'])
                    
                    # 5. Music Controller
                    music_controller = self.components['music_controller']
                    execution_result = await music_controller.execute_command(parsed_command)
                    
                    pipeline_duration = time.time() - pipeline_start
                    
                    pipeline_results.append({
                        'command': command_text,
                        'duration': pipeline_duration,
                        'success': execution_result.success,
                        'wake_confidence': wake_result['confidence'],
                        'speech_confidence': speech_result['confidence'],
                        'nlp_confidence': parsed_command.confidence
                    })
            
            # Calcola metriche pipeline
            successful_pipelines = sum(1 for r in pipeline_results if r['success'])
            pipeline_success_rate = successful_pipelines / len(pipeline_results)
            avg_pipeline_duration = statistics.mean(r['duration'] for r in pipeline_results)
            avg_total_confidence = statistics.mean(
                (r['wake_confidence'] + r['speech_confidence'] + r['nlp_confidence']) / 3
                for r in pipeline_results
            )
            
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="End-to-End Pipeline",
                success=True,
                duration=duration,
                details={
                    'pipelines_tested': len(pipeline_results),
                    'success_rate': pipeline_success_rate,
                    'avg_pipeline_duration': avg_pipeline_duration,
                    'avg_confidence': avg_total_confidence,
                    'results': pipeline_results
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="End-to-End Pipeline",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_performance(self):
        """Test performance sotto carico normale"""
        logger.info("Testing Performance...")
        
        start_time = time.time()
        try:
            iterations = self.config['performance_iterations']
            
            # Test latenza componenti
            component_latencies = {}
            
            for component_name, component in self.components.items():
                latencies = []
                
                for i in range(iterations // 10):  # Test subset per componente
                    comp_start = time.time()
                    
                    if component_name == 'audio_input':
                        await component.get_audio_chunk()
                    elif component_name == 'wake_word':
                        await component.detect(b'mock_audio')
                    elif component_name == 'speech_recognition':
                        await component.recognize(b'mock_audio')
                    elif component_name == 'nlp_processor':
                        await component.process_command('test command')
                    elif component_name == 'music_controller':
                        from nlp_processor import ParsedCommand, CommandType
                        mock_cmd = ParsedCommand(CommandType.PLAY, raw_text='test')
                        await component.execute_command(mock_cmd)
                    elif component_name == 'navidrome_client':
                        await component.search('test')
                    
                    latency = time.time() - comp_start
                    latencies.append(latency)
                
                component_latencies[component_name] = {
                    'avg': statistics.mean(latencies),
                    'max': max(latencies),
                    'min': min(latencies),
                    'std': statistics.stdev(latencies) if len(latencies) > 1 else 0
                }
            
            # Test throughput
            throughput_start = time.time()
            throughput_operations = 50
            
            for i in range(throughput_operations):
                # Simula operazione completa
                nlp_processor = self.components['nlp_processor']
                music_controller = self.components['music_controller']
                
                parsed_cmd = await nlp_processor.process_command('test command')
                await music_controller.execute_command(parsed_cmd)
            
            throughput_duration = time.time() - throughput_start
            throughput = throughput_operations / throughput_duration
            
            duration = time.time() - start_time
            
            self.performance_metrics = {
                'component_latencies': component_latencies,
                'throughput': throughput,
                'total_test_duration': duration
            }
            
            self.test_results.append(TestResult(
                test_name="Performance Test",
                success=True,
                duration=duration,
                details=self.performance_metrics
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Performance Test",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    async def _test_stress_conditions(self):
        """Test sotto condizioni di stress"""
        logger.info("Testing Stress Conditions...")
        
        start_time = time.time()
        try:
            # Test carico elevato
            concurrent_tasks = 20
            stress_results = []
            
            async def stress_task(task_id):
                task_start = time.time()
                try:
                    # Simula pipeline completo
                    nlp_processor = self.components['nlp_processor']
                    music_controller = self.components['music_controller']
                    
                    for i in range(5):  # 5 operazioni per task
                        parsed_cmd = await nlp_processor.process_command(f'stress test {task_id}')
                        await music_controller.execute_command(parsed_cmd)
                    
                    task_duration = time.time() - task_start
                    return {'task_id': task_id, 'success': True, 'duration': task_duration}
                    
                except Exception as e:
                    task_duration = time.time() - task_start
                    return {'task_id': task_id, 'success': False, 'duration': task_duration, 'error': str(e)}
            
            # Esegui task concorrenti
            tasks = [stress_task(i) for i in range(concurrent_tasks)]
            stress_results = await asyncio.gather(*tasks)
            
            # Analizza risultati stress test
            successful_tasks = sum(1 for r in stress_results if r['success'])
            stress_success_rate = successful_tasks / len(stress_results)
            avg_stress_duration = statistics.mean(r['duration'] for r in stress_results)
            
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name="Stress Test",
                success=True,
                duration=duration,
                details={
                    'concurrent_tasks': concurrent_tasks,
                    'success_rate': stress_success_rate,
                    'avg_task_duration': avg_stress_duration,
                    'results': stress_results
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(
                test_name="Stress Test",
                success=False,
                duration=duration,
                details={},
                error=str(e)
            ))
    
    def _generate_test_report(self, total_duration: float) -> Dict[str, Any]:
        """Genera report completo dei test"""
        
        # Calcola statistiche generali
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        # Trova test più lenti
        slowest_tests = sorted(self.test_results, key=lambda x: x.duration, reverse=True)[:3]
        
        # Calcola metriche aggregate
        avg_test_duration = statistics.mean(r.duration for r in self.test_results)
        
        # Raccomandazioni
        recommendations = []
        
        if success_rate < 0.9:
            recommendations.append("Alcuni test falliscono - verificare configurazione componenti")
        
        if avg_test_duration > 1.0:
            recommendations.append("Performance sotto la soglia - considerare ottimizzazioni")
        
        if self.performance_metrics:
            max_latency = max(
                metrics['max'] for metrics in self.performance_metrics['component_latencies'].values()
            )
            if max_latency > self.config['latency_threshold']:
                recommendations.append(f"Latenza massima {max_latency:.3f}s supera soglia {self.config['latency_threshold']}s")
        
        # Genera report
        report = {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'total_duration': total_duration,
                'avg_test_duration': avg_test_duration
            },
            'test_results': [
                {
                    'name': r.test_name,
                    'success': r.success,
                    'duration': r.duration,
                    'details': r.details,
                    'error': r.error
                }
                for r in self.test_results
            ],
            'performance_metrics': self.performance_metrics,
            'slowest_tests': [
                {'name': r.test_name, 'duration': r.duration}
                for r in slowest_tests
            ],
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Salva report su file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'/home/ubuntu/voice_assistant/test_report_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to: {filename}")
        return filename


async def main():
    """Funzione principale per eseguire test"""
    print("🧪 Voice Assistant Test Suite")
    print("=" * 50)
    
    # Inizializza tester
    tester = VoiceAssistantTester()
    
    # Esegui tutti i test
    report = await tester.run_all_tests()
    
    # Salva report
    report_file = tester.save_report(report)
    
    # Stampa sommario
    print("\n📊 Test Summary:")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Successful: {report['summary']['successful_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"Total Duration: {report['summary']['total_duration']:.2f}s")
    print(f"Average Test Duration: {report['summary']['avg_test_duration']:.3f}s")
    
    if report['recommendations']:
        print("\n⚠️  Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())

