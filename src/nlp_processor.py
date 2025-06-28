"""
Natural Language Processor
Elabora comandi vocali e li converte in azioni per Navidrome
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import difflib

from navidrome_client import NavidromeClient, SearchType, SearchResult, Song, Artist, Album, Playlist

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Tipi di comando supportati"""
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    VOLUME = "volume"
    SEARCH = "search"
    PLAYLIST = "playlist"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
    INFO = "info"
    UNKNOWN = "unknown"


class PlaybackAction(Enum):
    """Azioni di riproduzione"""
    PLAY_SONG = "play_song"
    PLAY_ALBUM = "play_album"
    PLAY_ARTIST = "play_artist"
    PLAY_PLAYLIST = "play_playlist"
    PLAY_GENRE = "play_genre"
    PLAY_RANDOM = "play_random"


@dataclass
class ParsedCommand:
    """Comando vocale elaborato"""
    command_type: CommandType
    action: Optional[PlaybackAction] = None
    target: Optional[str] = None  # Nome artista, album, brano, etc.
    parameters: Dict[str, Any] = None
    confidence: float = 0.0
    raw_text: str = ""


@dataclass
class MusicEntity:
    """Entità musicale identificata"""
    entity_type: str  # artist, album, song, playlist, genre
    name: str
    id: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None


class NaturalLanguageProcessor:
    """
    Processore di linguaggio naturale per comandi musicali
    """
    
    def __init__(self, config: Dict[str, Any], navidrome_client: NavidromeClient):
        self.config = config
        self.navidrome_client = navidrome_client
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        
        # Cache per entità musicali
        self.artists_cache = []
        self.albums_cache = []
        self.playlists_cache = []
        self.genres_cache = []
        
        # Pattern per riconoscimento comandi
        self.command_patterns = self._build_command_patterns()
        
        # Statistiche
        self.stats = {
            'commands_processed': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'avg_confidence': 0.0
        }
        
    def _build_command_patterns(self) -> Dict[CommandType, List[str]]:
        """Costruisce pattern per riconoscimento comandi"""
        return {
            CommandType.PLAY: [
                r'riproduci\s+(.+)',
                r'suona\s+(.+)',
                r'metti\s+(.+)',
                r'ascolta\s+(.+)',
                r'play\s+(.+)',
                r'avvia\s+(.+)',
                r'inizia\s+(.+)'
            ],
            CommandType.PAUSE: [
                r'pausa',
                r'pause',
                r'ferma',
                r'stop',
                r'metti\s+in\s+pausa'
            ],
            CommandType.STOP: [
                r'stop',
                r'ferma\s+tutto',
                r'basta',
                r'smetti'
            ],
            CommandType.NEXT: [
                r'prossimo',
                r'avanti',
                r'next',
                r'salta',
                r'prossimo\s+brano',
                r'canzone\s+successiva'
            ],
            CommandType.PREVIOUS: [
                r'precedente',
                r'indietro',
                r'previous',
                r'brano\s+precedente',
                r'canzone\s+precedente'
            ],
            CommandType.VOLUME: [
                r'volume\s+(\d+)',
                r'volume\s+al\s+(\d+)',
                r'alza\s+il\s+volume',
                r'abbassa\s+il\s+volume',
                r'più\s+forte',
                r'più\s+piano'
            ],
            CommandType.SHUFFLE: [
                r'shuffle',
                r'casuale',
                r'mescola',
                r'modalità\s+casuale'
            ],
            CommandType.REPEAT: [
                r'ripeti',
                r'repeat',
                r'loop',
                r'modalità\s+ripetizione'
            ],
            CommandType.INFO: [
                r'che\s+cosa\s+sta\s+suonando',
                r'cosa\s+stai\s+riproducendo',
                r'che\s+canzone\s+è',
                r'info',
                r'informazioni'
            ]
        }
    
    async def initialize(self):
        """Inizializza cache entità musicali"""
        logger.info("Initializing NLP cache...")
        
        try:
            # Cache artisti
            self.artists_cache = await self.navidrome_client.get_artists()
            logger.info(f"Cached {len(self.artists_cache)} artists")
            
            # Cache generi
            self.genres_cache = await self.navidrome_client.get_genres()
            logger.info(f"Cached {len(self.genres_cache)} genres")
            
            # Cache playlist
            self.playlists_cache = await self.navidrome_client.get_playlists()
            logger.info(f"Cached {len(self.playlists_cache)} playlists")
            
            logger.info("NLP cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP cache: {e}")
            raise
    
    async def process_command(self, text: str) -> ParsedCommand:
        """Processa comando vocale e restituisce comando strutturato"""
        self.stats['commands_processed'] += 1
        
        # Normalizza testo
        normalized_text = self._normalize_text(text)
        
        # Identifica tipo comando
        command_type, extracted_target = self._identify_command_type(normalized_text)
        
        # Processa comando specifico
        if command_type == CommandType.PLAY:
            parsed_command = await self._process_play_command(extracted_target, normalized_text)
        elif command_type == CommandType.VOLUME:
            parsed_command = self._process_volume_command(extracted_target, normalized_text)
        else:
            parsed_command = ParsedCommand(
                command_type=command_type,
                target=extracted_target,
                confidence=0.8,
                raw_text=text
            )
        
        # Aggiorna statistiche
        if parsed_command.confidence >= self.confidence_threshold:
            self.stats['successful_matches'] += 1
        else:
            self.stats['failed_matches'] += 1
            
        self.stats['avg_confidence'] = (
            self.stats['avg_confidence'] * 0.9 + parsed_command.confidence * 0.1
        )
        
        logger.info(f"Processed command: '{text}' -> {command_type.value} "
                   f"(confidence: {parsed_command.confidence:.3f})")
        
        return parsed_command
    
    def _normalize_text(self, text: str) -> str:
        """Normalizza testo per elaborazione"""
        # Converti a minuscolo
        text = text.lower().strip()
        
        # Rimuovi punteggiatura
        text = re.sub(r'[^\w\s]', '', text)
        
        # Normalizza spazi
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _identify_command_type(self, text: str) -> Tuple[CommandType, Optional[str]]:
        """Identifica tipo di comando dal testo"""
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Estrai target se presente
                    target = match.group(1) if match.groups() else None
                    return command_type, target
        
        return CommandType.UNKNOWN, None
    
    async def _process_play_command(self, target: str, full_text: str) -> ParsedCommand:
        """Processa comando di riproduzione"""
        if not target:
            return ParsedCommand(
                command_type=CommandType.PLAY,
                confidence=0.3,
                raw_text=full_text
            )
        
        # Identifica entità musicale
        music_entity = await self._identify_music_entity(target)
        
        if not music_entity:
            return ParsedCommand(
                command_type=CommandType.PLAY,
                target=target,
                confidence=0.2,
                raw_text=full_text
            )
        
        # Determina azione di riproduzione
        action = self._determine_playback_action(music_entity)
        
        return ParsedCommand(
            command_type=CommandType.PLAY,
            action=action,
            target=music_entity.name,
            parameters={
                'entity_type': music_entity.entity_type,
                'entity_id': music_entity.id,
                'metadata': music_entity.metadata
            },
            confidence=music_entity.confidence,
            raw_text=full_text
        )
    
    def _process_volume_command(self, target: str, full_text: str) -> ParsedCommand:
        """Processa comando volume"""
        volume_level = None
        
        if target and target.isdigit():
            volume_level = int(target)
            volume_level = max(0, min(100, volume_level))  # Clamp 0-100
        elif 'alto' in full_text or 'forte' in full_text:
            volume_level = 80
        elif 'basso' in full_text or 'piano' in full_text:
            volume_level = 30
        
        return ParsedCommand(
            command_type=CommandType.VOLUME,
            parameters={'level': volume_level},
            confidence=0.9 if volume_level is not None else 0.5,
            raw_text=full_text
        )
    
    async def _identify_music_entity(self, target: str) -> Optional[MusicEntity]:
        """Identifica entità musicale dal target"""
        # Cerca tra artisti
        artist_match = self._find_best_match(target, self.artists_cache, 'name')
        if artist_match:
            return MusicEntity(
                entity_type='artist',
                name=artist_match['item'].name,
                id=artist_match['item'].id,
                confidence=artist_match['confidence'],
                metadata={'album_count': artist_match['item'].album_count}
            )
        
        # Cerca tra playlist
        playlist_match = self._find_best_match(target, self.playlists_cache, 'name')
        if playlist_match:
            return MusicEntity(
                entity_type='playlist',
                name=playlist_match['item'].name,
                id=playlist_match['item'].id,
                confidence=playlist_match['confidence'],
                metadata={'song_count': playlist_match['item'].song_count}
            )
        
        # Cerca tra generi
        genre_match = self._find_best_match(target, self.genres_cache)
        if genre_match:
            return MusicEntity(
                entity_type='genre',
                name=genre_match['item'],
                confidence=genre_match['confidence']
            )
        
        # Ricerca online se non trovato in cache
        return await self._search_online_entity(target)
    
    def _find_best_match(self, target: str, items: List[Any], 
                        attr: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Trova migliore corrispondenza in lista"""
        if not items:
            return None
        
        # Estrai nomi per confronto
        if attr:
            names = [getattr(item, attr).lower() for item in items]
        else:
            names = [str(item).lower() for item in items]
        
        target_lower = target.lower()
        
        # Cerca corrispondenza esatta
        for i, name in enumerate(names):
            if name == target_lower:
                return {
                    'item': items[i],
                    'confidence': 1.0
                }
        
        # Cerca corrispondenza parziale
        for i, name in enumerate(names):
            if target_lower in name or name in target_lower:
                confidence = len(target_lower) / len(name) if len(name) > 0 else 0
                confidence = min(confidence, 0.9)  # Max 0.9 per match parziali
                
                if confidence >= 0.6:
                    return {
                        'item': items[i],
                        'confidence': confidence
                    }
        
        # Usa difflib per similarità
        matches = difflib.get_close_matches(target_lower, names, n=1, cutoff=0.6)
        if matches:
            match_index = names.index(matches[0])
            similarity = difflib.SequenceMatcher(None, target_lower, matches[0]).ratio()
            
            return {
                'item': items[match_index],
                'confidence': similarity
            }
        
        return None
    
    async def _search_online_entity(self, target: str) -> Optional[MusicEntity]:
        """Ricerca entità online tramite API"""
        try:
            # Ricerca universale
            results = await self.navidrome_client.search(target, count=5)
            
            # Priorità: artisti, album, brani
            if results.artists:
                artist = results.artists[0]
                return MusicEntity(
                    entity_type='artist',
                    name=artist.name,
                    id=artist.id,
                    confidence=0.8,
                    metadata={'album_count': artist.album_count}
                )
            
            if results.albums:
                album = results.albums[0]
                return MusicEntity(
                    entity_type='album',
                    name=album.name,
                    id=album.id,
                    confidence=0.7,
                    metadata={
                        'artist': album.artist,
                        'artist_id': album.artist_id,
                        'song_count': album.song_count
                    }
                )
            
            if results.songs:
                song = results.songs[0]
                return MusicEntity(
                    entity_type='song',
                    name=song.title,
                    id=song.id,
                    confidence=0.6,
                    metadata={
                        'artist': song.artist,
                        'artist_id': song.artist_id,
                        'album': song.album,
                        'album_id': song.album_id
                    }
                )
            
        except Exception as e:
            logger.error(f"Error searching online entity: {e}")
        
        return None
    
    def _determine_playback_action(self, entity: MusicEntity) -> PlaybackAction:
        """Determina azione di riproduzione basata su entità"""
        entity_type = entity.entity_type
        
        if entity_type == 'artist':
            return PlaybackAction.PLAY_ARTIST
        elif entity_type == 'album':
            return PlaybackAction.PLAY_ALBUM
        elif entity_type == 'song':
            return PlaybackAction.PLAY_SONG
        elif entity_type == 'playlist':
            return PlaybackAction.PLAY_PLAYLIST
        elif entity_type == 'genre':
            return PlaybackAction.PLAY_GENRE
        else:
            return PlaybackAction.PLAY_RANDOM
    
    async def refresh_cache(self):
        """Aggiorna cache entità musicali"""
        logger.info("Refreshing NLP cache...")
        await self.initialize()
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche NLP"""
        return {
            **self.stats,
            'cache_sizes': {
                'artists': len(self.artists_cache),
                'playlists': len(self.playlists_cache),
                'genres': len(self.genres_cache)
            }
        }


# Test del modulo
if __name__ == "__main__":
    import asyncio
    from navidrome_client import NavidromeClient
    
    async def test_nlp():
        """Test del processore NLP"""
        # Configurazione mock
        navidrome_config = {
            'base_url': 'http://localhost:4533',
            'username': 'admin',
            'password': 'password'
        }
        
        nlp_config = {
            'confidence_threshold': 0.7
        }
        
        # Mock client per test
        class MockNavidromeClient:
            async def get_artists(self):
                return [
                    type('Artist', (), {'name': 'Beethoven', 'id': '1', 'album_count': 10}),
                    type('Artist', (), {'name': 'Mozart', 'id': '2', 'album_count': 15}),
                    type('Artist', (), {'name': 'Bach', 'id': '3', 'album_count': 8})
                ]
            
            async def get_genres(self):
                return ['Classical', 'Rock', 'Jazz', 'Pop', 'Electronic']
            
            async def get_playlists(self):
                return [
                    type('Playlist', (), {'name': 'Favorites', 'id': 'p1', 'song_count': 50}),
                    type('Playlist', (), {'name': 'Relax', 'id': 'p2', 'song_count': 30})
                ]
            
            async def search(self, query, count=5):
                # Mock search results
                return type('SearchResult', (), {
                    'artists': [],
                    'albums': [],
                    'songs': []
                })
        
        # Test NLP
        mock_client = MockNavidromeClient()
        nlp = NaturalLanguageProcessor(nlp_config, mock_client)
        
        await nlp.initialize()
        
        # Test comandi
        test_commands = [
            "riproduci Beethoven",
            "metti in pausa",
            "volume al 70",
            "prossimo brano",
            "suona musica classica",
            "riproduci playlist favorites",
            "che cosa sta suonando",
            "shuffle",
            "stop"
        ]
        
        print("Testing NLP commands:")
        print("=" * 50)
        
        for command in test_commands:
            result = await nlp.process_command(command)
            
            print(f"Input: '{command}'")
            print(f"  Command: {result.command_type.value}")
            print(f"  Action: {result.action.value if result.action else 'None'}")
            print(f"  Target: {result.target}")
            print(f"  Confidence: {result.confidence:.3f}")
            print(f"  Parameters: {result.parameters}")
            print()
        
        # Statistiche
        print("NLP Statistics:")
        print(nlp.get_stats())
    
    # Esegui test
    asyncio.run(test_nlp())

