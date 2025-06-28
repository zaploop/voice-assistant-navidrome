# Documentazione API Subsonic/Navidrome

## Panoramica
Navidrome implementa l'API Subsonic per compatibilità con client esistenti. L'API utilizza autenticazione MD5 salted e supporta formati XML/JSON.

## Autenticazione
- Username: parametro `u`
- Token: parametro `t` = md5(password + salt)
- Salt: parametro `s` (stringa random di almeno 6 caratteri)
- Versione: parametro `v` (es. "1.16.1")
- Client: parametro `c` (identificativo client)

## Endpoint Principali per Voice Assistant

### System
- `ping` - Test connessione
- `getLicense` - Info licenza

### Browsing/Search
- `getArtists` - Lista artisti (ID3)
- `getArtist` - Dettagli artista
- `getAlbum` - Dettagli album
- `getSong` - Dettagli brano
- `search3` - Ricerca universale
- `getRandomSongs` - Brani casuali
- `getSongsByGenre` - Brani per genere

### Playback Control
- `stream` - Stream audio brano
- `download` - Download brano
- `getNowPlaying` - Stato riproduzione corrente

### Playlists
- `getPlaylists` - Lista playlist
- `getPlaylist` - Contenuto playlist
- `createPlaylist` - Crea playlist
- `updatePlaylist` - Modifica playlist
- `deletePlaylist` - Elimina playlist

### Media Info
- `getCoverArt` - Copertina album
- `getLyrics` - Testi brani
- `getGenres` - Lista generi

## Parametri Comuni
- `id` - ID elemento (artista, album, brano)
- `name` - Nome per ricerca
- `query` - Testo ricerca
- `count` - Numero risultati (default 20)
- `offset` - Offset risultati (paginazione)
- `musicFolderId` - ID cartella musica

## Formati Risposta
- XML (default): `f=xml`
- JSON: `f=json`
- JSONP: `f=jsonp&callback=function_name`

## Codici Errore
- 0: Errore generico
- 10: Parametro mancante
- 20: Versione client incompatibile
- 30: Versione server incompatibile
- 40: Username/password errati
- 50: Operazione non autorizzata
- 70: Dati non trovati

## Note Implementazione
- Navidrome supporta subset API Subsonic
- Preferire endpoint ID3 (getArtists, getArtist, getAlbum)
- Usare search3 per ricerca universale
- Stream endpoint per riproduzione audio
- Gestire paginazione con offset/count

