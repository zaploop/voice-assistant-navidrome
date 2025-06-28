#!/usr/bin/env python3
"""
Mock Navidrome Server for Testing
Simula un server Navidrome per i test di integrazione
"""

import json
import hashlib
import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Mock Navidrome Server", version="0.49.3")

# Mock data
MOCK_ARTISTS = [
    {"id": "1", "name": "Ludwig van Beethoven", "albumCount": 10, "songCount": 95},
    {"id": "2", "name": "Wolfgang Amadeus Mozart", "albumCount": 15, "songCount": 120},
    {"id": "3", "name": "Johann Sebastian Bach", "albumCount": 8, "songCount": 85},
]

MOCK_ALBUMS = [
    {
        "id": "1", 
        "name": "Symphony No. 9", 
        "artist": "Ludwig van Beethoven",
        "artistId": "1",
        "songCount": 4,
        "year": 1824
    },
    {
        "id": "2",
        "name": "Piano Sonatas",
        "artist": "Ludwig van Beethoven", 
        "artistId": "1",
        "songCount": 12,
        "year": 1801
    },
]

MOCK_SONGS = [
    {
        "id": "1",
        "title": "Ode to Joy",
        "artist": "Ludwig van Beethoven",
        "artistId": "1", 
        "album": "Symphony No. 9",
        "albumId": "1",
        "duration": 240,
        "track": 4
    },
    {
        "id": "2",
        "title": "Moonlight Sonata",
        "artist": "Ludwig van Beethoven",
        "artistId": "1",
        "album": "Piano Sonatas", 
        "albumId": "2",
        "duration": 900,
        "track": 1
    },
]

MOCK_PLAYLISTS = [
    {
        "id": "1",
        "name": "Classical Favorites",
        "songCount": 25,
        "duration": 3600,
        "public": False
    },
    {
        "id": "2", 
        "name": "Beethoven Best",
        "songCount": 15,
        "duration": 2400,
        "public": True
    },
]

# Mock user credentials
MOCK_USERS = {
    "admin": {
        "password": "admin123",
        "salt": "mocksalt",
        "token": "mocktoken123"
    },
    "test_user": {
        "password": "test_password", 
        "salt": "testsalt",
        "token": "testtoken456"
    }
}

def create_auth_token(username: str, password: str, salt: str) -> str:
    """Crea token di autenticazione mock"""
    return hashlib.md5(f"{password}{salt}".encode()).hexdigest()

def verify_auth(username: str, token: str, salt: str) -> bool:
    """Verifica autenticazione mock"""
    if username not in MOCK_USERS:
        return False
    
    user = MOCK_USERS[username]
    expected_token = create_auth_token(username, user["password"], salt)
    return token == expected_token

@app.get("/rest/ping")
async def ping(
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"), 
    s: str = Query(..., description="Salt"),
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format")
):
    """Endpoint ping per verificare connettività"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {
        "subsonic-response": {
            "status": "ok",
            "version": "1.16.1",
            "type": "navidrome",
            "serverVersion": "0.49.3"
        }
    }

@app.get("/rest/search3")
async def search3(
    query: str = Query(..., description="Search query"),
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"),
    s: str = Query(..., description="Salt"), 
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format"),
    artistCount: int = Query(20, description="Max artists"),
    albumCount: int = Query(20, description="Max albums"),
    songCount: int = Query(20, description="Max songs")
):
    """Endpoint ricerca universale"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    query_lower = query.lower()
    
    # Filtra risultati in base alla query
    matching_artists = [
        artist for artist in MOCK_ARTISTS 
        if query_lower in artist["name"].lower()
    ][:artistCount]
    
    matching_albums = [
        album for album in MOCK_ALBUMS
        if query_lower in album["name"].lower() or query_lower in album["artist"].lower()
    ][:albumCount]
    
    matching_songs = [
        song for song in MOCK_SONGS
        if query_lower in song["title"].lower() or query_lower in song["artist"].lower()
    ][:songCount]
    
    return {
        "subsonic-response": {
            "status": "ok",
            "version": "1.16.1",
            "searchResult3": {
                "artist": matching_artists,
                "album": matching_albums, 
                "song": matching_songs
            }
        }
    }

@app.get("/rest/getArtists")
async def get_artists(
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"),
    s: str = Query(..., description="Salt"),
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format")
):
    """Endpoint lista artisti"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Raggruppa artisti per lettera iniziale
    artists_by_letter = {}
    for artist in MOCK_ARTISTS:
        first_letter = artist["name"][0].upper()
        if first_letter not in artists_by_letter:
            artists_by_letter[first_letter] = []
        artists_by_letter[first_letter].append(artist)
    
    indexes = []
    for letter in sorted(artists_by_letter.keys()):
        indexes.append({
            "name": letter,
            "artist": artists_by_letter[letter]
        })
    
    return {
        "subsonic-response": {
            "status": "ok", 
            "version": "1.16.1",
            "artists": {
                "index": indexes
            }
        }
    }

@app.get("/rest/getPlaylists")
async def get_playlists(
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"),
    s: str = Query(..., description="Salt"),
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format")
):
    """Endpoint lista playlist"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {
        "subsonic-response": {
            "status": "ok",
            "version": "1.16.1", 
            "playlists": {
                "playlist": MOCK_PLAYLISTS
            }
        }
    }

@app.get("/rest/getRandomSongs")
async def get_random_songs(
    size: int = Query(10, description="Number of songs"),
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"),
    s: str = Query(..., description="Salt"),
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format")
):
    """Endpoint brani casuali"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    import random
    random_songs = random.sample(MOCK_SONGS, min(size, len(MOCK_SONGS)))
    
    return {
        "subsonic-response": {
            "status": "ok",
            "version": "1.16.1",
            "randomSongs": {
                "song": random_songs
            }
        }
    }

@app.get("/rest/getNowPlaying")
async def get_now_playing(
    u: str = Query(..., description="Username"),
    t: str = Query(..., description="Token"),
    s: str = Query(..., description="Salt"),
    v: str = Query("1.16.1", description="API Version"),
    c: str = Query("voice-assistant", description="Client"),
    f: str = Query("json", description="Format")
):
    """Endpoint riproduzione corrente"""
    
    if not verify_auth(u, t, s):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Simula riproduzione corrente
    now_playing = {
        "entry": [
            {
                **MOCK_SONGS[0],
                "username": u,
                "minutesAgo": 2,
                "playerId": "voice-assistant-player"
            }
        ]
    }
    
    return {
        "subsonic-response": {
            "status": "ok",
            "version": "1.16.1", 
            "nowPlaying": now_playing
        }
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler generale per eccezioni"""
    return JSONResponse(
        status_code=500,
        content={
            "subsonic-response": {
                "status": "failed",
                "version": "1.16.1",
                "error": {
                    "code": 0,
                    "message": str(exc)
                }
            }
        }
    )

if __name__ == "__main__":
    print("🎵 Starting Mock Navidrome Server...")
    print("📍 Available at: http://localhost:4533")
    print("👤 Test credentials:")
    print("   Username: admin, Password: admin123")
    print("   Username: test_user, Password: test_password")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=4533,
        log_level="info"
    )

