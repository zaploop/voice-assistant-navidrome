"""
Navidrome API Client
Client per integrazione con server Navidrome tramite API Subsonic
"""

import asyncio
import logging
import hashlib
import secrets
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
import xml.etree.ElementTree as ET
import json

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """Tipi di ricerca supportati"""
    ARTIST = "artist"
    ALBUM = "album"
    SONG = "song"
    ANY = "any"


@dataclass
class Artist:
    """Rappresentazione di un artista"""
    id: str
    name: str
    album_count: int = 0
    starred: Optional[str] = None
    cover_art: Optional[str] = None


@dataclass
class Album:
    """Rappresentazione di un album"""
    id: str
    name: str
    artist: str
    artist_id: str
    song_count: int = 0
    duration: int = 0
    year: Optional[int] = None
    genre: Optional[str] = None
    cover_art: Optional[str] = None
    starred: Optional[str] = None


@dataclass
class Song:
    """Rappresentazione di un brano"""
    id: str
    title: str
    artist: str
    artist_id: str
    album: str
    album_id: str
    track: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    size: int = 0
    duration: int = 0
    bit_rate: Optional[int] = None
    path: Optional[str] = None
    cover_art: Optional[str] = None
    starred: Optional[str] = None


@dataclass
class Playlist:
    """Rappresentazione di una playlist"""
    id: str
    name: str
    comment: Optional[str] = None
    owner: Optional[str] = None
    public: bool = False
    song_count: int = 0
    duration: int = 0
    created: Optional[str] = None
    changed: Optional[str] = None
    cover_art: Optional[str] = None


@dataclass
class SearchResult:
    """Risultato di ricerca"""
    artists: List[Artist]
    albums: List[Album]
    songs: List[Song]


class NavidromeAPIError(Exception):
    """Eccezione per errori API Navidrome"""
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error {code}: {message}")


class NavidromeClient:
    """
    Client per API Navidrome/Subsonic
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get('base_url', 'http://localhost:4533')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.client_name = config.get('client_name', 'VoiceAssistant')
        self.api_version = config.get('api_version', '1.16.1')
        self.timeout = config.get('timeout_seconds', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        # Normalizza base URL
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        if not self.base_url.endswith('rest/'):
            self.base_url += 'rest/'
            
        # Session HTTP
        self.session = None
        
        # Cache per ridurre chiamate API
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minuti
        
        # Statistiche
        self.stats = {
            'requests': 0,
            'errors': 0,
            'cache_hits': 0,
            'avg_response_time': 0.0
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Inizializza connessione HTTP"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
        # Test connessione
        try:
            await self.ping()
            logger.info(f"Connected to Navidrome at {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Navidrome: {e}")
            raise
    
    async def disconnect(self):
        """Chiude connessione HTTP"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _generate_auth_params(self) -> Dict[str, str]:
        """Genera parametri di autenticazione"""
        salt = secrets.token_hex(8)
        token = hashlib.md5((self.password + salt).encode('utf-8')).hexdigest()
        
        return {
            'u': self.username,
            't': token,
            's': salt,
            'v': self.api_version,
            'c': self.client_name,
            'f': 'json'
        }
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Genera chiave cache per richiesta"""
        # Escludi parametri di auth dalla cache key
        cache_params = {k: v for k, v in params.items() 
                       if k not in ['u', 't', 's', 'v', 'c', 'f']}
        
        key_data = f"{endpoint}:{json.dumps(cache_params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Verifica se cache è ancora valida"""
        return time.time() - timestamp < self.cache_ttl
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Esegue richiesta HTTP all'API"""
        if not self.session:
            await self.connect()
        
        # Prepara parametri
        request_params = self._generate_auth_params()
        if params:
            request_params.update(params)
        
        # Controlla cache
        cache_key = self._get_cache_key(endpoint, request_params)
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                self.stats['cache_hits'] += 1
                return cached_data
        
        # Esegui richiesta
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        for attempt in range(self.retry_attempts):
            try:
                async with self.session.get(url, params=request_params) as response:
                    self.stats['requests'] += 1
                    
                    if response.status != 200:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    
                    data = await response.json()
                    
                    # Aggiorna statistiche
                    response_time = time.time() - start_time
                    self.stats['avg_response_time'] = (
                        self.stats['avg_response_time'] * 0.9 + response_time * 0.1
                    )
                    
                    # Controlla errori API
                    subsonic_response = data.get('subsonic-response', {})
                    if subsonic_response.get('status') == 'failed':
                        error = subsonic_response.get('error', {})
                        error_code = error.get('code', 0)
                        error_message = error.get('message', 'Unknown error')
                        
                        self.stats['errors'] += 1
                        raise NavidromeAPIError(error_code, error_message)
                    
                    # Salva in cache
                    self.cache[cache_key] = (data, time.time())
                    
                    return data
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    self.stats['errors'] += 1
                    raise
                
                # Backoff esponenziale
                await asyncio.sleep(2 ** attempt)
    
    async def ping(self) -> bool:
        """Test connessione al server"""
        try:
            await self._make_request('ping.view')
            return True
        except Exception:
            return False
    
    async def search(self, query: str, search_type: SearchType = SearchType.ANY,
                    count: int = 20, offset: int = 0) -> SearchResult:
        """Ricerca universale"""
        params = {
            'query': query,
            'artistCount': count if search_type in [SearchType.ARTIST, SearchType.ANY] else 0,
            'albumCount': count if search_type in [SearchType.ALBUM, SearchType.ANY] else 0,
            'songCount': count if search_type in [SearchType.SONG, SearchType.ANY] else 0,
            'artistOffset': offset if search_type in [SearchType.ARTIST, SearchType.ANY] else 0,
            'albumOffset': offset if search_type in [SearchType.ALBUM, SearchType.ANY] else 0,
            'songOffset': offset if search_type in [SearchType.SONG, SearchType.ANY] else 0
        }
        
        data = await self._make_request('search3.view', params)
        search_result = data['subsonic-response'].get('searchResult3', {})
        
        # Parse risultati
        artists = []
        for artist_data in search_result.get('artist', []):
            artists.append(Artist(
                id=artist_data['id'],
                name=artist_data['name'],
                album_count=artist_data.get('albumCount', 0),
                starred=artist_data.get('starred'),
                cover_art=artist_data.get('coverArt')
            ))
        
        albums = []
        for album_data in search_result.get('album', []):
            albums.append(Album(
                id=album_data['id'],
                name=album_data['name'],
                artist=album_data['artist'],
                artist_id=album_data['artistId'],
                song_count=album_data.get('songCount', 0),
                duration=album_data.get('duration', 0),
                year=album_data.get('year'),
                genre=album_data.get('genre'),
                cover_art=album_data.get('coverArt'),
                starred=album_data.get('starred')
            ))
        
        songs = []
        for song_data in search_result.get('song', []):
            songs.append(Song(
                id=song_data['id'],
                title=song_data['title'],
                artist=song_data['artist'],
                artist_id=song_data['artistId'],
                album=song_data['album'],
                album_id=song_data['albumId'],
                track=song_data.get('track'),
                year=song_data.get('year'),
                genre=song_data.get('genre'),
                size=song_data.get('size', 0),
                duration=song_data.get('duration', 0),
                bit_rate=song_data.get('bitRate'),
                path=song_data.get('path'),
                cover_art=song_data.get('coverArt'),
                starred=song_data.get('starred')
            ))
        
        return SearchResult(artists=artists, albums=albums, songs=songs)
    
    async def get_artists(self, music_folder_id: Optional[str] = None) -> List[Artist]:
        """Ottiene lista artisti"""
        params = {}
        if music_folder_id:
            params['musicFolderId'] = music_folder_id
        
        data = await self._make_request('getArtists.view', params)
        artists_data = data['subsonic-response'].get('artists', {})
        
        artists = []
        for index in artists_data.get('index', []):
            for artist_data in index.get('artist', []):
                artists.append(Artist(
                    id=artist_data['id'],
                    name=artist_data['name'],
                    album_count=artist_data.get('albumCount', 0),
                    starred=artist_data.get('starred'),
                    cover_art=artist_data.get('coverArt')
                ))
        
        return artists
    
    async def get_artist(self, artist_id: str) -> Optional[Artist]:
        """Ottiene dettagli artista"""
        params = {'id': artist_id}
        
        try:
            data = await self._make_request('getArtist.view', params)
            artist_data = data['subsonic-response'].get('artist', {})
            
            return Artist(
                id=artist_data['id'],
                name=artist_data['name'],
                album_count=artist_data.get('albumCount', 0),
                starred=artist_data.get('starred'),
                cover_art=artist_data.get('coverArt')
            )
        except NavidromeAPIError as e:
            if e.code == 70:  # Data not found
                return None
            raise
    
    async def get_album(self, album_id: str) -> Optional[Album]:
        """Ottiene dettagli album"""
        params = {'id': album_id}
        
        try:
            data = await self._make_request('getAlbum.view', params)
            album_data = data['subsonic-response'].get('album', {})
            
            return Album(
                id=album_data['id'],
                name=album_data['name'],
                artist=album_data['artist'],
                artist_id=album_data['artistId'],
                song_count=album_data.get('songCount', 0),
                duration=album_data.get('duration', 0),
                year=album_data.get('year'),
                genre=album_data.get('genre'),
                cover_art=album_data.get('coverArt'),
                starred=album_data.get('starred')
            )
        except NavidromeAPIError as e:
            if e.code == 70:  # Data not found
                return None
            raise
    
    async def get_album_songs(self, album_id: str) -> List[Song]:
        """Ottiene brani di un album"""
        params = {'id': album_id}
        
        data = await self._make_request('getAlbum.view', params)
        album_data = data['subsonic-response'].get('album', {})
        
        songs = []
        for song_data in album_data.get('song', []):
            songs.append(Song(
                id=song_data['id'],
                title=song_data['title'],
                artist=song_data['artist'],
                artist_id=song_data['artistId'],
                album=song_data['album'],
                album_id=song_data['albumId'],
                track=song_data.get('track'),
                year=song_data.get('year'),
                genre=song_data.get('genre'),
                size=song_data.get('size', 0),
                duration=song_data.get('duration', 0),
                bit_rate=song_data.get('bitRate'),
                path=song_data.get('path'),
                cover_art=song_data.get('coverArt'),
                starred=song_data.get('starred')
            ))
        
        return songs
    
    async def get_random_songs(self, count: int = 10, genre: Optional[str] = None,
                              from_year: Optional[int] = None, to_year: Optional[int] = None,
                              music_folder_id: Optional[str] = None) -> List[Song]:
        """Ottiene brani casuali"""
        params = {'size': count}
        
        if genre:
            params['genre'] = genre
        if from_year:
            params['fromYear'] = from_year
        if to_year:
            params['toYear'] = to_year
        if music_folder_id:
            params['musicFolderId'] = music_folder_id
        
        data = await self._make_request('getRandomSongs.view', params)
        random_songs = data['subsonic-response'].get('randomSongs', {})
        
        songs = []
        for song_data in random_songs.get('song', []):
            songs.append(Song(
                id=song_data['id'],
                title=song_data['title'],
                artist=song_data['artist'],
                artist_id=song_data['artistId'],
                album=song_data['album'],
                album_id=song_data['albumId'],
                track=song_data.get('track'),
                year=song_data.get('year'),
                genre=song_data.get('genre'),
                size=song_data.get('size', 0),
                duration=song_data.get('duration', 0),
                bit_rate=song_data.get('bitRate'),
                path=song_data.get('path'),
                cover_art=song_data.get('coverArt'),
                starred=song_data.get('starred')
            ))
        
        return songs
    
    async def get_playlists(self, username: Optional[str] = None) -> List[Playlist]:
        """Ottiene lista playlist"""
        params = {}
        if username:
            params['username'] = username
        
        data = await self._make_request('getPlaylists.view', params)
        playlists_data = data['subsonic-response'].get('playlists', {})
        
        playlists = []
        for playlist_data in playlists_data.get('playlist', []):
            playlists.append(Playlist(
                id=playlist_data['id'],
                name=playlist_data['name'],
                comment=playlist_data.get('comment'),
                owner=playlist_data.get('owner'),
                public=playlist_data.get('public', False),
                song_count=playlist_data.get('songCount', 0),
                duration=playlist_data.get('duration', 0),
                created=playlist_data.get('created'),
                changed=playlist_data.get('changed'),
                cover_art=playlist_data.get('coverArt')
            ))
        
        return playlists
    
    async def get_playlist_songs(self, playlist_id: str) -> List[Song]:
        """Ottiene brani di una playlist"""
        params = {'id': playlist_id}
        
        data = await self._make_request('getPlaylist.view', params)
        playlist_data = data['subsonic-response'].get('playlist', {})
        
        songs = []
        for song_data in playlist_data.get('entry', []):
            songs.append(Song(
                id=song_data['id'],
                title=song_data['title'],
                artist=song_data['artist'],
                artist_id=song_data['artistId'],
                album=song_data['album'],
                album_id=song_data['albumId'],
                track=song_data.get('track'),
                year=song_data.get('year'),
                genre=song_data.get('genre'),
                size=song_data.get('size', 0),
                duration=song_data.get('duration', 0),
                bit_rate=song_data.get('bitRate'),
                path=song_data.get('path'),
                cover_art=song_data.get('coverArt'),
                starred=song_data.get('starred')
            ))
        
        return songs
    
    def get_stream_url(self, song_id: str, max_bit_rate: Optional[int] = None,
                      format: Optional[str] = None) -> str:
        """Ottiene URL per streaming brano"""
        auth_params = self._generate_auth_params()
        auth_params['id'] = song_id
        
        if max_bit_rate:
            auth_params['maxBitRate'] = str(max_bit_rate)
        if format:
            auth_params['format'] = format
        
        # Costruisci URL
        url = f"{self.base_url}stream.view"
        param_string = '&'.join([f"{k}={v}" for k, v in auth_params.items()])
        
        return f"{url}?{param_string}"
    
    def get_cover_art_url(self, cover_art_id: str, size: Optional[int] = None) -> str:
        """Ottiene URL per copertina"""
        auth_params = self._generate_auth_params()
        auth_params['id'] = cover_art_id
        
        if size:
            auth_params['size'] = str(size)
        
        # Costruisci URL
        url = f"{self.base_url}getCoverArt.view"
        param_string = '&'.join([f"{k}={v}" for k, v in auth_params.items()])
        
        return f"{url}?{param_string}"
    
    async def get_genres(self) -> List[str]:
        """Ottiene lista generi"""
        data = await self._make_request('getGenres.view')
        genres_data = data['subsonic-response'].get('genres', {})
        
        genres = []
        for genre_data in genres_data.get('genre', []):
            genres.append(genre_data['value'])
        
        return sorted(genres)
    
    def get_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche client"""
        return self.stats.copy()
    
    def clear_cache(self):
        """Pulisce cache"""
        self.cache.clear()


# Test del modulo
if __name__ == "__main__":
    import asyncio
    
    async def test_client():
        """Test del client Navidrome"""
        config = {
            'base_url': 'http://localhost:4533',
            'username': 'admin',
            'password': 'password',
            'client_name': 'VoiceAssistantTest'
        }
        
        async with NavidromeClient(config) as client:
            try:
                # Test connessione
                print("Testing connection...")
                if await client.ping():
                    print("✓ Connection successful")
                else:
                    print("✗ Connection failed")
                    return
                
                # Test ricerca
                print("\nTesting search...")
                results = await client.search("beethoven", count=5)
                print(f"Found: {len(results.artists)} artists, {len(results.albums)} albums, {len(results.songs)} songs")
                
                if results.artists:
                    artist = results.artists[0]
                    print(f"First artist: {artist.name} (ID: {artist.id})")
                
                # Test artisti
                print("\nTesting artists...")
                artists = await client.get_artists()
                print(f"Total artists: {len(artists)}")
                
                if artists:
                    artist_detail = await client.get_artist(artists[0].id)
                    if artist_detail:
                        print(f"Artist detail: {artist_detail.name}")
                
                # Test brani casuali
                print("\nTesting random songs...")
                random_songs = await client.get_random_songs(count=3)
                print(f"Random songs: {len(random_songs)}")
                
                for song in random_songs:
                    print(f"  - {song.title} by {song.artist}")
                    stream_url = client.get_stream_url(song.id)
                    print(f"    Stream URL: {stream_url[:100]}...")
                
                # Test playlist
                print("\nTesting playlists...")
                playlists = await client.get_playlists()
                print(f"Playlists: {len(playlists)}")
                
                # Test generi
                print("\nTesting genres...")
                genres = await client.get_genres()
                print(f"Genres: {len(genres)} - {genres[:10]}")
                
                # Statistiche
                print(f"\nClient stats: {client.get_stats()}")
                
            except Exception as e:
                print(f"Error: {e}")
    
    # Esegui test
    asyncio.run(test_client())

