# Guida Rapida di Installazione
## Voice Assistant per Navidrome

### Prerequisiti
- Ubuntu 22.04 LTS (o distribuzione compatibile)
- Python 3.9+
- 4GB RAM (minimo 2GB)
- Microfono funzionante
- Server Navidrome attivo

### Installazione Rapida

1. **Clona il repository:**
   ```bash
   git clone https://github.com/voice-assistant/navidrome-voice.git
   cd navidrome-voice
   ```

2. **Esegui lo script di installazione:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Configura Navidrome:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   nano config/config.yaml
   ```
   
   Modifica le credenziali Navidrome:
   ```yaml
   navidrome:
     base_url: "http://localhost:4533"
     username: "tuo_username"
     password: "tua_password"
   ```

4. **Avvia il sistema:**
   ```bash
   sudo systemctl start voice-assistant
   sudo systemctl enable voice-assistant
   ```

5. **Accedi all'interfaccia web:**
   Apri http://localhost:8080 nel browser

### Comandi Vocali di Base

- **Riproduzione:** "Riproduci Beethoven"
- **Controllo:** "Pausa", "Riprendi", "Stop"
- **Volume:** "Volume al 70%", "Alza il volume"
- **Navigazione:** "Prossimo brano", "Precedente"
- **Informazioni:** "Che cosa sta suonando?"

### Risoluzione Problemi

**Microfono non funziona:**
```bash
sudo usermod -a -G audio $USER
pulseaudio --kill && pulseaudio --start
```

**Errore modelli mancanti:**
```bash
python scripts/download_models.py
```

**Connessione Navidrome fallita:**
- Verifica URL e credenziali in config.yaml
- Controlla che Navidrome sia accessibile: `curl http://localhost:4533`

### Supporto
- Documentazione completa: `docs/voice_assistant_documentation.pdf`
- Log sistema: `journalctl -u voice-assistant -f`
- Test installazione: `python scripts/test_installation.py`

