# Contribuire a Voice Assistant per Navidrome

Siamo entusiasti che tu sia interessato a contribuire al Voice Assistant per Navidrome! Apprezziamo il tuo tempo e i tuoi sforzi per rendere questo progetto ancora migliore.

Questa guida fornisce indicazioni su come contribuire in modo efficace. Leggila attentamente prima di iniziare.

## Come Contribuire

Ci sono molti modi per contribuire al progetto:

- **Segnalare Bug**: Se trovi un bug, per favore apri una issue dettagliata nel nostro [issue tracker](https://github.com/voice-assistant/navidrome-voice/issues).
- **Suggerire Miglioramenti**: Hai idee per nuove funzionalità o miglioramenti? Apri una issue con l_etichetta `enhancement`.
- **Scrivere Codice**: Se vuoi contribuire con codice, per favore segui il workflow descritto sotto.
- **Migliorare la Documentazione**: La documentazione può sempre essere migliorata. Invia una pull request con le tue modifiche.
- **Tradurre**: Aiutaci a tradurre il progetto in altre lingue.
- **Testare**: Aiutaci a testare le nuove versioni e le pull request.

## Workflow per Contributi di Codice

1.  **Fork del Repository**: Crea un fork del repository principale sul tuo account GitHub.
2.  **Clona il Fork**: Clona il tuo fork in locale:
    ```bash
    git clone https://github.com/TUO_USERNAME/navidrome-voice.git
    cd navidrome-voice
    ```
3.  **Crea un Branch**: Crea un branch descrittivo per la tua feature o bugfix:
    ```bash
    git checkout -b feature/nome-feature-descrittiva
    # o per bugfix
    git checkout -b fix/descrizione-bug
    ```
4.  **Sviluppa**: Scrivi il tuo codice seguendo le linee guida di stile (vedi sotto).
5.  **Testa**: Assicurati che i test esistenti passino e aggiungi nuovi test per la tua feature.
    ```bash
    ./test_system.sh
    # o
    python test_suite.py
    ```
6.  **Commit**: Fai commit delle tue modifiche con messaggi chiari e concisi:
    ```bash
    git commit -m "feat: Aggiunta nuova feature X"
    # o
    git commit -m "fix: Corretto bug Y in componente Z"
    ```
    Utilizziamo [Conventional Commits](https://www.conventionalcommits.org/) per i messaggi di commit.

7.  **Push**: Fai push del tuo branch sul tuo fork:
    ```bash
    git push origin feature/nome-feature-descrittiva
    ```
8.  **Apri una Pull Request (PR)**: Vai al repository principale e apri una Pull Request dal tuo branch al branch `main` del repository principale.
    - Fornisci una descrizione chiara delle modifiche.
    - Fai riferimento a eventuali issue correlate (es. `Closes #123`).
    - Assicurati che tutti i check della CI passino.

## Linee Guida di Stile del Codice

- **Python**: Segui lo stile [PEP 8](https://www.python.org/dev/peps/pep-0008/). Utilizziamo `black` per la formattazione automatica e `flake8` per il linting.
- **JavaScript/React**: Segui le linee guida di stile comuni per React. Utilizziamo `prettier` per la formattazione.
- **Commenti**: Commenta il codice complesso o le logiche non ovvie.
- **Test**: Tutti i nuovi contributi di codice devono includere test unitari e/o di integrazione.

## Code Review

Tutte le pull request verranno revisionate da almeno un maintainer. Sii paziente e aperto ai feedback. Lavoreremo insieme per integrare il tuo contributo.

## Segnalazione di Problemi di Sicurezza

Se scopri una vulnerabilità di sicurezza, per favore **NON** aprire una issue pubblica. Invia una mail a `security@voice-assistant.dev` con i dettagli.

## Domande?

Se hai domande, apri una discussione nel [forum della community](https://github.com/voice-assistant/navidrome-voice/discussions).

Grazie per il tuo contributo!

