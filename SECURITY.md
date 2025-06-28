# Security Policy

## Supported Versions

Attualmente supportiamo le seguenti versioni con aggiornamenti di sicurezza:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

La sicurezza è una priorità assoluta per il Voice Assistant per Navidrome. Se scopri una vulnerabilità di sicurezza, ti preghiamo di seguire la procedura di divulgazione responsabile.

### Come Segnalare

**NON** aprire una issue pubblica per vulnerabilità di sicurezza. Invece:

1. **Email**: Invia una email a `security@voice-assistant.dev`
2. **Oggetto**: `[SECURITY] Descrizione breve della vulnerabilità`
3. **Contenuto**: Includi:
   - Descrizione dettagliata della vulnerabilità
   - Passi per riprodurre il problema
   - Impatto potenziale
   - Versioni interessate
   - Eventuali mitigazioni temporanee

### Cosa Aspettarsi

- **Conferma di ricezione**: Entro 24 ore
- **Valutazione iniziale**: Entro 72 ore
- **Aggiornamenti regolari**: Ogni 7 giorni fino alla risoluzione
- **Risoluzione**: Dipende dalla severità, tipicamente entro 30 giorni

### Processo di Divulgazione

1. **Ricezione**: Riceviamo e confermiamo la segnalazione
2. **Valutazione**: Valutiamo la severità e l'impatto
3. **Sviluppo**: Sviluppiamo una fix
4. **Test**: Testiamo la fix in diversi ambienti
5. **Release**: Rilasciamo la patch di sicurezza
6. **Divulgazione**: Pubblichiamo un advisory di sicurezza

### Severità delle Vulnerabilità

Classifichiamo le vulnerabilità secondo questi criteri:

#### Critica
- Esecuzione di codice remoto
- Escalation di privilegi
- Accesso non autorizzato a dati sensibili

#### Alta
- Denial of Service
- Bypass di autenticazione
- Injection attacks

#### Media
- Information disclosure
- Cross-site scripting (XSS)
- Weak cryptography

#### Bassa
- Minor information leaks
- Configuration issues

### Riconoscimenti

Riconosciamo pubblicamente i ricercatori di sicurezza che segnalano vulnerabilità in modo responsabile, a meno che non richiedano di rimanere anonimi.

### Contatti

- **Email Sicurezza**: security@voice-assistant.dev
- **PGP Key**: [Disponibile su richiesta]
- **Response Team**: Team di sicurezza Voice Assistant

### Best Practices per gli Utenti

Per mantenere sicura la tua installazione:

1. **Aggiorna regolarmente** alla versione più recente
2. **Configura l'autenticazione** per l'interfaccia web
3. **Usa HTTPS** se esponi il servizio in rete
4. **Monitora i log** per attività sospette
5. **Limita l'accesso di rete** quando possibile
6. **Backup regolari** della configurazione

### Sicurezza by Design

Il Voice Assistant per Navidrome è progettato con la sicurezza in mente:

- **Privacy First**: Funzionamento completamente offline
- **Minimal Attack Surface**: Nessuna comunicazione cloud
- **Principle of Least Privilege**: Permessi minimi necessari
- **Input Validation**: Validazione rigorosa di tutti gli input
- **Secure Defaults**: Configurazioni sicure di default

