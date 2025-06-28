"""
Music Controller
Coordina l'esecuzione di comandi musicali su Navidrome
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time

from navidrome_client import NavidromeClient, Song, Artist, Album, Playlist
from nlp_processor import ParsedCommand, CommandType, PlaybackAction, MusicEntity

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Stati di riproduzione"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class PlaybackStatus:
    """Stato corrente della riproduzione"""
    state: PlaybackState
    current_song: Optional[Song] = None
    position: int = 0  # secondi
    volume: int = 50  # 0-100
    shuffle: bool = False
    repeat: bool = False
    queue: List[Song] = None
    queue_position: int = 0


@dataclass
class CommandResult:
    """Risultato esecuzione comando"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    playback_status: Optional[PlaybackStatus] = None


class MusicController:
    """
    Controller principale per gestione musica su Navidrome
    """
    
    def __init__(self, config: Dict[str, Any], navidrome_client: NavidromeClient):
        self.config = config
        self.navidrome_client = navidrome_client
        
        # Stato riproduzione
        self.playback_status = PlaybackStatus(
            state=PlaybackState.STOPPED,
            queue=[]
        )
        
        # Callback per notifiche
        self.status_callbacks = []
        
        # Statistiche
        self.stats = {
            'commands_executed': 0,
            'songs_played': 0,
            'total_playtime': 0,
            'errors': 0
        }
    
    def add_status_callback(self, callback: Callable[[PlaybackStatus], None]):
        """Aggiunge callback per notifiche stato"""
        self.status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[PlaybackStatus], None]):
        """Rimuove callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_status_change(self):
        """Notifica cambio stato a tutti i callback"""
        for callback in self.status_callbacks:
            try:
                callback(self.playback_status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    async def execute_command(self, command: ParsedCommand) -> CommandResult:
        """Esegue comando musicale"""
        self.stats['commands_executed'] += 1
        
        try:
            if command.command_type == CommandType.PLAY:
                return await self._execute_play_command(command)
            elif command.command_type == CommandType.PAUSE:
                return await self._execute_pause_command()
            elif command.command_type == CommandType.STOP:
                return await self._execute_stop_command()
            elif command.command_type == CommandType.NEXT:
                return await self._execute_next_command()
            elif command.command_type == CommandType.PREVIOUS:
                return await self._execute_previous_command()
            elif command.command_type == CommandType.VOLUME:
                return await self._execute_volume_command(command)
            elif command.command_type == CommandType.SHUFFLE:
                return await self._execute_shuffle_command()
            elif command.command_type == CommandType.REPEAT:
                return await self._execute_repeat_command()
            elif command.command_type == CommandType.INFO:
                return await self._execute_info_command()
            else:
                return CommandResult(
                    success=False,
                    message=f"Comando non supportato: {command.command_type.value}"
                )
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error executing command: {e}")
            return CommandResult(
                success=False,
                message=f"Errore nell'esecuzione del comando: {str(e)}"
            )
    
    async def _execute_play_command(self, command: ParsedCommand) -> CommandResult:
        """Esegue comando di riproduzione"""
        if not command.action:
            return CommandResult(
                success=False,
                message="Azione di riproduzione non specificata"
            )
        
        try:
            if command.action == PlaybackAction.PLAY_ARTIST:
                return await self._play_artist(command)
            elif command.action == PlaybackAction.PLAY_ALBUM:
                return await self._play_album(command)
            elif command.action == PlaybackAction.PLAY_SONG:
                return await self._play_song(command)
            elif command.action == PlaybackAction.PLAY_PLAYLIST:
                return await self._play_playlist(command)
            elif command.action == PlaybackAction.PLAY_GENRE:
                return await self._play_genre(command)
            elif command.action == PlaybackAction.PLAY_RANDOM:
                return await self._play_random()
            else:
                return CommandResult(
                    success=False,
                    message=f"Azione non supportata: {command.action.value}"
                )
                
        except Exception as e:
            logger.error(f"Error in play command: {e}")
            return CommandResult(
                success=False,
                message=f"Errore nella riproduzione: {str(e)}"
            )
    
    async def _play_artist(self, command: ParsedCommand) -> CommandResult:
        """Riproduce brani di un artista"""
        artist_id = command.parameters.get('entity_id')
        artist_name = command.target
        
        if not artist_id:
            return CommandResult(
                success=False,
                message=f"Artista '{artist_name}' non trovato"
            )
        
        # Ottieni dettagli artista
        artist = await self.navidrome_client.get_artist(artist_id)
        if not artist:
            return CommandResult(
                success=False,
                message=f"Impossibile ottenere dettagli artista '{artist_name}'"
            )
        
        # Cerca brani dell'artista tramite ricerca
        search_results = await self.navidrome_client.search(
            artist_name, 
            search_type=SearchType.SONG,
            count=50
        )
        
        if not search_results.songs:
            return CommandResult(
                success=False,
                message=f"Nessun brano trovato per l'artista '{artist_name}'"
            )
        
        # Filtra brani dell'artista specifico
        artist_songs = [song for song in search_results.songs 
                       if song.artist_id == artist_id]
        
        if not artist_songs:
            artist_songs = search_results.songs  # Fallback
        
        # Avvia riproduzione
        await self._start_playback(artist_songs)
        
        return CommandResult(
            success=True,
            message=f"Riproduzione avviata: {artist_name} ({len(artist_songs)} brani)",
            data={'artist': artist_name, 'song_count': len(artist_songs)},
            playback_status=self.playback_status
        )
    
    async def _play_album(self, command: ParsedCommand) -> CommandResult:
        """Riproduce brani di un album"""
        album_id = command.parameters.get('entity_id')
        album_name = command.target
        
        if not album_id:
            return CommandResult(
                success=False,
                message=f"Album '{album_name}' non trovato"
            )
        
        # Ottieni brani dell'album
        songs = await self.navidrome_client.get_album_songs(album_id)
        
        if not songs:
            return CommandResult(
                success=False,
                message=f"Nessun brano trovato nell'album '{album_name}'"
            )
        
        # Avvia riproduzione
        await self._start_playback(songs)
        
        return CommandResult(
            success=True,
            message=f"Riproduzione album: {album_name} ({len(songs)} brani)",
            data={'album': album_name, 'song_count': len(songs)},
            playback_status=self.playback_status
        )
    
    async def _play_song(self, command: ParsedCommand) -> CommandResult:
        """Riproduce un brano specifico"""
        song_id = command.parameters.get('entity_id')
        song_title = command.target
        
        if not song_id:
            return CommandResult(
                success=False,
                message=f"Brano '{song_title}' non trovato"
            )
        
        # Crea queue con singolo brano
        # In un'implementazione reale, otterremmo il Song object completo
        song_metadata = command.parameters.get('metadata', {})
        song = Song(
            id=song_id,
            title=song_title,
            artist=song_metadata.get('artist', 'Unknown'),
            artist_id=song_metadata.get('artist_id', ''),
            album=song_metadata.get('album', 'Unknown'),
            album_id=song_metadata.get('album_id', '')
        )
        
        # Avvia riproduzione
        await self._start_playback([song])
        
        return CommandResult(
            success=True,
            message=f"Riproduzione brano: {song_title}",
            data={'song': song_title},
            playback_status=self.playback_status
        )
    
    async def _play_playlist(self, command: ParsedCommand) -> CommandResult:
        """Riproduce una playlist"""
        playlist_id = command.parameters.get('entity_id')
        playlist_name = command.target
        
        if not playlist_id:
            return CommandResult(
                success=False,
                message=f"Playlist '{playlist_name}' non trovata"
            )
        
        # Ottieni brani della playlist
        songs = await self.navidrome_client.get_playlist_songs(playlist_id)
        
        if not songs:
            return CommandResult(
                success=False,
                message=f"Playlist '{playlist_name}' è vuota"
            )
        
        # Avvia riproduzione
        await self._start_playback(songs)
        
        return CommandResult(
            success=True,
            message=f"Riproduzione playlist: {playlist_name} ({len(songs)} brani)",
            data={'playlist': playlist_name, 'song_count': len(songs)},
            playback_status=self.playback_status
        )
    
    async def _play_genre(self, command: ParsedCommand) -> CommandResult:
        """Riproduce brani di un genere"""
        genre_name = command.target
        
        # Ottieni brani casuali del genere
        songs = await self.navidrome_client.get_random_songs(
            count=50,
            genre=genre_name
        )
        
        if not songs:
            return CommandResult(
                success=False,
                message=f"Nessun brano trovato per il genere '{genre_name}'"
            )
        
        # Avvia riproduzione
        await self._start_playback(songs)
        
        return CommandResult(
            success=True,
            message=f"Riproduzione genere: {genre_name} ({len(songs)} brani)",
            data={'genre': genre_name, 'song_count': len(songs)},
            playback_status=self.playback_status
        )
    
    async def _play_random(self) -> CommandResult:
        """Riproduce brani casuali"""
        songs = await self.navidrome_client.get_random_songs(count=30)
        
        if not songs:
            return CommandResult(
                success=False,
                message="Impossibile ottenere brani casuali"
            )
        
        # Avvia riproduzione
        await self._start_playback(songs)
        
        return CommandResult(
            success=True,
            message=f"Riproduzione casuale avviata ({len(songs)} brani)",
            data={'song_count': len(songs)},
            playback_status=self.playback_status
        )
    
    async def _start_playback(self, songs: List[Song]):
        """Avvia riproduzione di una lista di brani"""
        if not songs:
            return
        
        # Aggiorna stato
        self.playback_status.queue = songs
        self.playback_status.queue_position = 0
        self.playback_status.current_song = songs[0]
        self.playback_status.state = PlaybackState.PLAYING
        self.playback_status.position = 0
        
        # Aggiorna statistiche
        self.stats['songs_played'] += 1
        
        # Notifica cambio stato
        self._notify_status_change()
        
        logger.info(f"Started playback: {songs[0].title} by {songs[0].artist}")
    
    async def _execute_pause_command(self) -> CommandResult:
        """Esegue comando pausa"""
        if self.playback_status.state == PlaybackState.PLAYING:
            self.playback_status.state = PlaybackState.PAUSED
            self._notify_status_change()
            
            return CommandResult(
                success=True,
                message="Riproduzione in pausa",
                playback_status=self.playback_status
            )
        elif self.playback_status.state == PlaybackState.PAUSED:
            self.playback_status.state = PlaybackState.PLAYING
            self._notify_status_change()
            
            return CommandResult(
                success=True,
                message="Riproduzione ripresa",
                playback_status=self.playback_status
            )
        else:
            return CommandResult(
                success=False,
                message="Nessuna riproduzione attiva"
            )
    
    async def _execute_stop_command(self) -> CommandResult:
        """Esegue comando stop"""
        self.playback_status.state = PlaybackState.STOPPED
        self.playback_status.current_song = None
        self.playback_status.position = 0
        self._notify_status_change()
        
        return CommandResult(
            success=True,
            message="Riproduzione fermata",
            playback_status=self.playback_status
        )
    
    async def _execute_next_command(self) -> CommandResult:
        """Esegue comando prossimo brano"""
        if not self.playback_status.queue:
            return CommandResult(
                success=False,
                message="Nessuna coda di riproduzione attiva"
            )
        
        current_pos = self.playback_status.queue_position
        
        if current_pos < len(self.playback_status.queue) - 1:
            self.playback_status.queue_position += 1
            self.playback_status.current_song = self.playback_status.queue[self.playback_status.queue_position]
            self.playback_status.position = 0
            
            if self.playback_status.state != PlaybackState.STOPPED:
                self.playback_status.state = PlaybackState.PLAYING
            
            self._notify_status_change()
            
            return CommandResult(
                success=True,
                message=f"Prossimo brano: {self.playback_status.current_song.title}",
                playback_status=self.playback_status
            )
        else:
            return CommandResult(
                success=False,
                message="Fine della coda di riproduzione"
            )
    
    async def _execute_previous_command(self) -> CommandResult:
        """Esegue comando brano precedente"""
        if not self.playback_status.queue:
            return CommandResult(
                success=False,
                message="Nessuna coda di riproduzione attiva"
            )
        
        current_pos = self.playback_status.queue_position
        
        if current_pos > 0:
            self.playback_status.queue_position -= 1
            self.playback_status.current_song = self.playback_status.queue[self.playback_status.queue_position]
            self.playback_status.position = 0
            
            if self.playback_status.state != PlaybackState.STOPPED:
                self.playback_status.state = PlaybackState.PLAYING
            
            self._notify_status_change()
            
            return CommandResult(
                success=True,
                message=f"Brano precedente: {self.playback_status.current_song.title}",
                playback_status=self.playback_status
            )
        else:
            return CommandResult(
                success=False,
                message="Inizio della coda di riproduzione"
            )
    
    async def _execute_volume_command(self, command: ParsedCommand) -> CommandResult:
        """Esegue comando volume"""
        volume_level = command.parameters.get('level')
        
        if volume_level is not None:
            self.playback_status.volume = volume_level
            self._notify_status_change()
            
            return CommandResult(
                success=True,
                message=f"Volume impostato al {volume_level}%",
                playback_status=self.playback_status
            )
        else:
            return CommandResult(
                success=False,
                message="Livello volume non specificato"
            )
    
    async def _execute_shuffle_command(self) -> CommandResult:
        """Esegue comando shuffle"""
        self.playback_status.shuffle = not self.playback_status.shuffle
        self._notify_status_change()
        
        status = "attivato" if self.playback_status.shuffle else "disattivato"
        
        return CommandResult(
            success=True,
            message=f"Shuffle {status}",
            playback_status=self.playback_status
        )
    
    async def _execute_repeat_command(self) -> CommandResult:
        """Esegue comando repeat"""
        self.playback_status.repeat = not self.playback_status.repeat
        self._notify_status_change()
        
        status = "attivato" if self.playback_status.repeat else "disattivato"
        
        return CommandResult(
            success=True,
            message=f"Repeat {status}",
            playback_status=self.playback_status
        )
    
    async def _execute_info_command(self) -> CommandResult:
        """Esegue comando informazioni"""
        if self.playback_status.current_song:
            song = self.playback_status.current_song
            info = f"In riproduzione: {song.title} di {song.artist}"
            
            if song.album:
                info += f" dall'album {song.album}"
            
            return CommandResult(
                success=True,
                message=info,
                data={
                    'song': song.title,
                    'artist': song.artist,
                    'album': song.album,
                    'state': self.playback_status.state.value
                },
                playback_status=self.playback_status
            )
        else:
            return CommandResult(
                success=True,
                message="Nessuna riproduzione attiva",
                playback_status=self.playback_status
            )
    
    def get_playback_status(self) -> PlaybackStatus:
        """Restituisce stato corrente riproduzione"""
        return self.playback_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche controller"""
        return self.stats.copy()


# Test del modulo
if __name__ == "__main__":
    import asyncio
    from navidrome_client import NavidromeClient
    from nlp_processor import NaturalLanguageProcessor, ParsedCommand, CommandType, PlaybackAction
    
    async def test_controller():
        """Test del music controller"""
        # Mock client
        class MockNavidromeClient:
            async def get_random_songs(self, count=10, genre=None):
                return [
                    Song(id='1', title='Test Song 1', artist='Test Artist', 
                         artist_id='a1', album='Test Album', album_id='al1'),
                    Song(id='2', title='Test Song 2', artist='Test Artist', 
                         artist_id='a1', album='Test Album', album_id='al1')
                ]
        
        # Test controller
        mock_client = MockNavidromeClient()
        controller = MusicController({}, mock_client)
        
        # Callback per status
        def on_status_change(status):
            print(f"Status changed: {status.state.value}")
            if status.current_song:
                print(f"  Current song: {status.current_song.title}")
        
        controller.add_status_callback(on_status_change)
        
        # Test comandi
        test_commands = [
            ParsedCommand(
                command_type=CommandType.PLAY,
                action=PlaybackAction.PLAY_RANDOM,
                confidence=0.9,
                raw_text="riproduci musica casuale"
            ),
            ParsedCommand(
                command_type=CommandType.PAUSE,
                confidence=0.9,
                raw_text="pausa"
            ),
            ParsedCommand(
                command_type=CommandType.NEXT,
                confidence=0.9,
                raw_text="prossimo"
            ),
            ParsedCommand(
                command_type=CommandType.VOLUME,
                parameters={'level': 75},
                confidence=0.9,
                raw_text="volume al 75"
            ),
            ParsedCommand(
                command_type=CommandType.INFO,
                confidence=0.9,
                raw_text="che cosa sta suonando"
            )
        ]
        
        print("Testing Music Controller:")
        print("=" * 50)
        
        for command in test_commands:
            result = await controller.execute_command(command)
            
            print(f"Command: {command.command_type.value}")
            print(f"  Success: {result.success}")
            print(f"  Message: {result.message}")
            if result.data:
                print(f"  Data: {result.data}")
            print()
        
        # Statistiche
        print("Controller Statistics:")
        print(controller.get_stats())
    
    # Esegui test
    asyncio.run(test_controller())

