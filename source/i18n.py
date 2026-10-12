"""Session language detection and UI translations. GPL-3.0-or-later.

English is the source/fallback language. LANGUAGE preferences apply unless the
message locale is C/POSIX. The privileged helper emits English diagnostics;
translation happens in the user's desktop process.
"""

import os


SUPPORTED = ('en', 'it', 'fr', 'de', 'es')


def _base(locale):
    return locale.strip().split('.')[0].split('@')[0].replace('-', '_').split('_')[0].lower()


def detect_language(environ=None):
    env = os.environ if environ is None else environ
    locale = env.get('LC_ALL') or env.get('LC_MESSAGES') or env.get('LANG') or 'C'
    if _base(locale) in ('c', 'posix'):
        return 'en'
    preferences = env.get('LANGUAGE') or locale
    for preference in preferences.split(':'):
        language = _base(preference)
        if language in SUPPORTED:
            return language
    return 'en'


# English source: Italian, French, German, Spanish.
TRANSLATIONS = {
    'Open': ('Aperta', 'Ouvert', 'Offen', 'Abierta'),
    'DEMO': ('DIMOSTRAZIONE', 'DÉMONSTRATION', 'DEMO', 'DEMOSTRACIÓN'),
    'Find hidden access points · select a radio and open Signal': ('Trova gli access point nascosti · seleziona una radio e apri Segnale', 'Trouvez les points d’accès cachés · sélectionnez une radio et ouvrez Signal', 'Versteckte Access Points finden · Funkmodul auswählen und Signal öffnen', 'Encuentra puntos de acceso ocultos · selecciona una radio y abre Señal'),
    'DEMO · simulated data, no real WiFi scanning': ('DIMOSTRAZIONE · dati simulati, nessuna scansione WiFi reale', 'DÉMONSTRATION · données simulées, aucun scan WiFi réel', 'DEMO · simulierte Daten, kein echter WLAN-Scan', 'DEMOSTRACIÓN · datos simulados, sin escaneo WiFi real'),
    '&WiFi adapter:': ('&Scheda WiFi:', '&Adaptateur WiFi :', '&WLAN-Adapter:', '&Adaptador WiFi:'),
    'Refresh adapters': ('Aggiorna schede', 'Actualiser les adaptateurs', 'Adapter aktualisieren', 'Actualizar adaptadores'),
    '&Start scan': ('&Avvia scansione', '&Démarrer le scan', '&Scan starten', '&Iniciar escaneo'),
    'S&top scan': ('&Ferma scansione', '&Arrêter le scan', 'Scan s&toppen', '&Detener escaneo'),
    '&Signal…': ('&Segnale…', '&Signal…', '&Signal…', '&Señal…'),
    'About': ('Informazioni', 'À propos', 'Über', 'Acerca de'),
    'Filter by network name or BSSID…': ('Filtra per nome della rete o BSSID…', 'Filtrer par nom de réseau ou BSSID…', 'Nach Netzwerkname oder BSSID filtern…', 'Filtrar por nombre de red o BSSID…'),
    'Network filter by SSID or BSSID': ('Filtro delle reti per SSID o BSSID', 'Filtre des réseaux par SSID ou BSSID', 'Netzwerkfilter nach SSID oder BSSID', 'Filtro de redes por SSID o BSSID'),
    'Network / SSID': ('Rete / SSID', 'Réseau / SSID', 'Netzwerk / SSID', 'Red / SSID'),
    'BSSID · radio': ('BSSID · radio', 'BSSID · radio', 'BSSID · Funkmodul', 'BSSID · radio'),
    'Channel': ('Canale', 'Canal', 'Kanal', 'Canal'),
    'Security': ('Sicurezza', 'Sécurité', 'Sicherheit', 'Seguridad'),
    'Last measurement': ('Ultima misura', 'Dernière mesure', 'Letzte Messung', 'Última medición'),
    'Detected access points; each row identifies a radio': ('Access point rilevati; ogni riga identifica una radio', 'Points d’accès détectés ; chaque ligne identifie une radio', 'Erkannte Access Points; jede Zeile bezeichnet ein Funkmodul', 'Puntos de acceso detectados; cada fila identifica una radio'),
    'Ready. Start scanning to find access points.': ('Pronto. Avvia la scansione per cercare gli access point.', 'Prêt. Lancez le scan pour trouver les points d’accès.', 'Bereit. Scan starten, um Access Points zu finden.', 'Listo. Inicia el escaneo para buscar puntos de acceso.'),
    'No WiFi adapter detected. Connect an adapter and refresh the list.': ('Nessuna scheda WiFi rilevata. Collega una scheda e aggiorna l’elenco.', 'Aucun adaptateur WiFi détecté. Branchez-en un et actualisez la liste.', 'Kein WLAN-Adapter erkannt. Adapter anschließen und Liste aktualisieren.', 'No se detectó ningún adaptador WiFi. Conecta uno y actualiza la lista.'),
    'Two access points may share an SSID: use the BSSID to tell them apart. The signal helps narrow down the area above the suspended ceiling.': ('Due access point possono avere lo stesso SSID: distinguili con il BSSID. Il segnale aiuta a restringere l’area sotto il controsoffitto.', 'Deux points d’accès peuvent partager un SSID : distinguez-les par le BSSID. Le signal aide à réduire la zone de recherche au-dessus du faux plafond.', 'Zwei Access Points können dieselbe SSID haben: anhand der BSSID unterscheiden. Das Signal grenzt den Suchbereich über der abgehängten Decke ein.', 'Dos puntos de acceso pueden compartir SSID: distínguelos por el BSSID. La señal ayuda a delimitar la zona sobre el falso techo.'),
    'No WiFi adapter detected. Check the connection and driver.': ('Nessuna scheda WiFi rilevata. Verifica collegamento e driver.', 'Aucun adaptateur WiFi détecté. Vérifiez la connexion et le pilote.', 'Kein WLAN-Adapter erkannt. Anschluss und Treiber prüfen.', 'No se detectó ningún adaptador WiFi. Comprueba la conexión y el controlador.'),
    'Stopping scan…': ('Arresto della scansione in corso…', 'Arrêt du scan…', 'Scan wird beendet…', 'Deteniendo escaneo…'),
    'Starting… confirm authorization for WiFi scanning.': ('Avvio… conferma l’autorizzazione per la scansione WiFi.', 'Démarrage… confirmez l’autorisation du scan WiFi.', 'Start… Berechtigung für den WLAN-Scan bestätigen.', 'Iniciando… confirma la autorización para escanear WiFi.'),
    'Scan stopped. Listed measurements are historical.': ('Scansione ferma. Le misure nell’elenco sono storiche.', 'Scan arrêté. Les mesures affichées sont anciennes.', 'Scan angehalten. Die angezeigten Messungen sind vergangene Werte.', 'Escaneo detenido. Las mediciones de la lista son anteriores.'),
    'Scan stopped · beeps paused': ('Scansione ferma · bip sospeso', 'Scan arrêté · bips suspendus', 'Scan angehalten · Pieptöne pausiert', 'Escaneo detenido · pitidos en pausa'),
    'Scanning all channels': ('Scansione di tutti i canali', 'Scan de tous les canaux', 'Alle Kanäle werden gescannt', 'Escaneando todos los canales'),
    ' · beeps paused': (' · bip sospeso', ' · bips suspendus', ' · Pieptöne pausiert', ' · pitidos en pausa'),
    '(hidden SSID)': ('(SSID nascosto)', '(SSID masqué)', '(versteckte SSID)', '(SSID oculto)'),
    'Signal · SysLinuxOS Wifi Analyzer': ('Segnale · SysLinuxOS Wifi Analyzer', 'Signal · SysLinuxOS Wifi Analyzer', 'Signal · SysLinuxOS Wifi Analyzer', 'Señal · SysLinuxOS Wifi Analyzer'),
    'SIGNAL': ('SEGNALE', 'SIGNAL', 'SIGNAL', 'SEÑAL'),
    'Hidden SSID': ('SSID nascosto', 'SSID masqué', 'Versteckte SSID', 'SSID oculto'),
    'Waiting for a new measurement on the target channel…': ('In attesa di una nuova misura sul canale del bersaglio…', 'En attente d’une nouvelle mesure sur le canal de la cible…', 'Warten auf eine neue Messung auf dem Zielkanal…', 'Esperando una nueva medición en el canal del objetivo…'),
    'Current: —   ·   Peak: —': ('Attuale: —   ·   Massimo: —', 'Actuel : —   ·   Maximum : —', 'Aktuell: —   ·   Maximum: —', 'Actual: —   ·   Máximo: —'),
    'Reset peak': ('Azzera massimo', 'Réinitialiser le maximum', 'Maximum zurücksetzen', 'Restablecer máximo'),
    '&Sensitivity:': ('&Sensibilità:', '&Sensibilité :', '&Empfindlichkeit:', '&Sensibilidad:'),
    'Wide search (−90 / −40 dBm)': ('Ricerca ampia (−90 / −40 dBm)', 'Recherche large (−90 / −40 dBm)', 'Breite Suche (−90 / −40 dBm)', 'Búsqueda amplia (−90 / −40 dBm)'),
    'Near the AP (−65 / −30 dBm)': ('Vicino all’AP (−65 / −30 dBm)', 'Près du point d’accès (−65 / −30 dBm)', 'Nahe am AP (−65 / −30 dBm)', 'Cerca del AP (−65 / −30 dBm)'),
    'Weak signal (−100 / −60 dBm)': ('Segnale debole (−100 / −60 dBm)', 'Signal faible (−100 / −60 dBm)', 'Schwaches Signal (−100 / −60 dBm)', 'Señal débil (−100 / −60 dBm)'),
    '&Enable beeps': ('&Bip attivo', '&Activer les bips', '&Pieptöne aktivieren', '&Activar pitidos'),
    '&Volume:': ('&Volume:', '&Volume :', '&Lautstärke:', '&Volumen:'),
    'Beep volume': ('Volume del bip', 'Volume des bips', 'Lautstärke der Pieptöne', 'Volumen del pitido'),
    'Test audio': ('Prova audio', 'Tester le son', 'Audio testen', 'Probar audio'),
    'Beeps disabled · repetition speeds up as the signal grows stronger.': ('Bip disattivato · aumenta la cadenza quando cresce il segnale.', 'Bips désactivés · la cadence augmente avec la puissance du signal.', 'Pieptöne deaktiviert · bei stärkerem Signal steigt die Wiederholrate.', 'Pitidos desactivados · la cadencia aumenta cuando la señal es más fuerte.'),
    'Walk slowly and approach from two directions. Keep height and orientation constant. The peak helps narrow down the area; it does not indicate distance or direction.': ('Cammina lentamente e ripassa da due direzioni. Mantieni altezza e orientamento costanti. Il massimo aiuta a restringere l’area; non indica metri o direzione.', 'Marchez lentement et repassez dans deux directions. Gardez une hauteur et une orientation constantes. Le maximum réduit la zone de recherche ; il n’indique ni distance ni direction.', 'Langsam gehen und aus zwei Richtungen suchen. Höhe und Ausrichtung konstant halten. Das Maximum grenzt den Bereich ein; es zeigt weder Entfernung noch Richtung an.', 'Camina despacio y pasa desde dos direcciones. Mantén constantes la altura y la orientación. El máximo delimita la zona; no indica distancia ni dirección.'),
    '&Close Signal': ('&Chiudi Segnale', '&Fermer Signal', 'Signal s&chließen', '&Cerrar Señal'),
    'Target missing from last scan · beeps paused': ('Bersaglio non rilevato nell’ultima scansione · bip sospeso', 'Cible absente du dernier scan · bips suspendus', 'Ziel im letzten Scan nicht erkannt · Pieptöne pausiert', 'Objetivo ausente en el último escaneo · pitidos en pausa'),
    'Signal lost · beeps paused': ('Segnale perso · bip sospeso', 'Signal perdu · bips suspendus', 'Signal verloren · Pieptöne pausiert', 'Señal perdida · pitidos en pausa'),
    'Waiting for a new measurement…': ('In attesa di una nuova misura…', 'En attente d’une nouvelle mesure…', 'Warten auf eine neue Messung…', 'Esperando una nueva medición…'),
    'WiFi signal gauge': ('Tachimetro del segnale WiFi', 'Jauge du signal WiFi', 'WLAN-Signalanzeige', 'Indicador de señal WiFi'),
    'No signal': ('Segnale assente', 'Aucun signal', 'Kein Signal', 'Sin señal'),
    'dBm · received signal strength': ('dBm · intensità ricevuta', 'dBm · puissance du signal reçu', 'dBm · Empfangsstärke', 'dBm · intensidad recibida'),
    'Recent signal history': ('Storico recente del segnale', 'Historique récent du signal', 'Jüngster Signalverlauf', 'Historial reciente de señal'),
    'Last 60 seconds of observations': ('Ultimi 60 secondi di osservazioni', 'Observations des 60 dernières secondes', 'Beobachtungen der letzten 60 Sekunden', 'Observaciones de los últimos 60 segundos'),
    'Audio unavailable: check the desktop audio output.': ('Audio non disponibile: verifica l’uscita audio del desktop.', 'Son indisponible : vérifiez la sortie audio du bureau.', 'Audio nicht verfügbar: Audioausgabe des Desktops prüfen.', 'Audio no disponible: comprueba la salida de audio del escritorio.'),
    'Audio ready': ('Audio pronto', 'Son prêt', 'Audio bereit', 'Audio listo'),
    'Audio loading or unavailable; try the test again.': ('Audio in caricamento o non disponibile; riprova il test.', 'Son en cours de chargement ou indisponible ; réessayez le test.', 'Audio lädt oder ist nicht verfügbar; Test wiederholen.', 'Audio cargando o no disponible; repite la prueba.'),
    'Install the .deb package to scan. You can try --demo from source.': ('Installa il pacchetto .deb per usare la scansione. Puoi provare --demo dai sorgenti.', 'Installez le paquet .deb pour scanner. Vous pouvez essayer --demo depuis les sources.', 'Zum Scannen das .deb-Paket installieren. --demo kann aus den Quellen getestet werden.', 'Instala el paquete .deb para escanear. Puedes probar --demo desde el código fuente.'),
    'Scan ended. Authorization cancelled or helper unavailable.': ('Scansione terminata. Autorizzazione annullata o helper non disponibile.', 'Scan terminé. Autorisation annulée ou assistant indisponible.', 'Scan beendet. Berechtigung abgebrochen oder Hilfsprogramm nicht verfügbar.', 'Escaneo finalizado. Autorización cancelada o programa auxiliar no disponible.'),
    'Scan response too large.': ('Risposta della scansione troppo grande.', 'Réponse du scan trop volumineuse.', 'Scan-Antwort zu groß.', 'Respuesta del escaneo demasiado grande.'),
    'Invalid scan response.': ('Risposta della scansione non valida.', 'Réponse du scan non valide.', 'Ungültige Scan-Antwort.', 'Respuesta del escaneo no válida.'),
    'Office · Demo': ('Ufficio · Demo', 'Bureau · Démo', 'Büro · Demo', 'Oficina · Demo'),
    'Invalid WiFi interface': ('Interfaccia WiFi non valida', 'Interface WiFi non valide', 'Ungültige WLAN-Schnittstelle', 'Interfaz WiFi no válida'),
    'Invalid WiFi frequency': ('Frequenza WiFi non valida', 'Fréquence WiFi non valide', 'Ungültige WLAN-Frequenz', 'Frecuencia WiFi no válida'),
    'Invalid command': ('Comando non valido', 'Commande non valide', 'Ungültiger Befehl', 'Comando no válido'),
    'Command not allowed': ('Comando non consentito', 'Commande non autorisée', 'Befehl nicht erlaubt', 'Comando no permitido'),
    'Scan timed out. Check the WiFi adapter and driver.': ('Scansione scaduta. Verifica scheda e driver WiFi.', 'Délai du scan dépassé. Vérifiez l’adaptateur WiFi et le pilote.', 'Zeitüberschreitung beim Scan. WLAN-Adapter und Treiber prüfen.', 'Tiempo de escaneo agotado. Comprueba el adaptador WiFi y el controlador.'),
    'Cannot start iw. Check the installation.': ('Impossibile avviare iw. Verifica l’installazione.', 'Impossible de lancer iw. Vérifiez l’installation.', 'iw kann nicht gestartet werden. Installation prüfen.', 'No se puede iniciar iw. Comprueba la instalación.'),
    'Adapter busy: waiting before retrying.': ('Scheda occupata: attendo prima di riprovare.', 'Adaptateur occupé : attente avant une nouvelle tentative.', 'Adapter belegt: Warten vor erneutem Versuch.', 'Adaptador ocupado: esperando antes de reintentar.'),
    'WiFi disabled or blocked. Enable it in network settings.': ('WiFi spento o bloccato. Attivalo dalle impostazioni di rete.', 'WiFi désactivé ou bloqué. Activez-le dans les paramètres réseau.', 'WLAN deaktiviert oder blockiert. In den Netzwerkeinstellungen aktivieren.', 'WiFi desactivado o bloqueado. Actívalo en los ajustes de red.'),
    'Start scanning from the installed app.': ('Avvia la scansione dall’app installata.', 'Lancez le scan depuis l’application installée.', 'Scan aus der installierten Anwendung starten.', 'Inicia el escaneo desde la aplicación instalada.'),
    'WiFi interface unavailable': ('Interfaccia WiFi non disponibile', 'Interface WiFi indisponible', 'WLAN-Schnittstelle nicht verfügbar', 'Interfaz WiFi no disponible'),
    'Command too long': ('Comando troppo lungo', 'Commande trop longue', 'Befehl zu lang', 'Comando demasiado largo'),
    'Waiting': ('In attesa', 'En attente', 'Warten', 'En espera'),
    'Increasing': ('In aumento', 'En hausse', 'Steigend', 'En aumento'),
    'Decreasing': ('In diminuzione', 'En baisse', 'Fallend', 'En descenso'),
    'Stable': ('Stabile', 'Stable', 'Stabil', 'Estable'),
    'Simulated data; no scanning or authorization': ('Dati simulati; nessuna scansione o autorizzazione', 'Données simulées ; aucun scan ni autorisation', 'Simulierte Daten; kein Scan und keine Berechtigung', 'Datos simulados; sin escaneo ni autorización'),
    'Target channel scan · {frequency} MHz': ('Ricerca sul canale del bersaglio · {frequency} MHz', 'Scan du canal de la cible · {frequency} MHz', 'Scan auf dem Zielkanal · {frequency} MHz', 'Escaneo del canal del objetivo · {frequency} MHz'),
    '{mode} · {count} radios in last scan': ('{mode} · {count} radio nell’ultima scansione', '{mode} · {count} radios au dernier scan', '{mode} · {count} Funkmodule im letzten Scan', '{mode} · {count} radios en el último escaneo'),
    '{age:.0f} s ago': ('{age:.0f} s fa', 'il y a {age:.0f} s', 'vor {age:.0f} s', 'hace {age:.0f} s'),
    '{bssid}  ·  {frequency} MHz  ·  channel {channel}': ('{bssid}  ·  {frequency} MHz  ·  canale {channel}', '{bssid}  ·  {frequency} MHz  ·  canal {channel}', '{bssid}  ·  {frequency} MHz  ·  Kanal {channel}', '{bssid}  ·  {frequency} MHz  ·  canal {channel}'),
    '{trend} · measurement {age:.1f} s ago': ('{trend} · misura di {age:.1f} s fa', '{trend} · mesure d’il y a {age:.1f} s', '{trend} · Messung vor {age:.1f} s', '{trend} · medición de hace {age:.1f} s'),
    'Current: {raw}   ·   Peak: {peak}': ('Attuale: {raw}   ·   Massimo: {peak}', 'Actuel : {raw}   ·   Maximum : {peak}', 'Aktuell: {raw}   ·   Maximum: {peak}', 'Actual: {raw}   ·   Máximo: {peak}'),
    'Scan failed: {details}': ('Scansione non riuscita: {details}', 'Échec du scan : {details}', 'Scan fehlgeschlagen: {details}', 'Error de escaneo: {details}'),
    'Access point locator with signal gauge and audible guidance.': ('Ricerca degli access point con indicatore e guida sonora.', 'Localisation des points d’accès avec jauge de signal et guidage sonore.', 'Access Points mit Signalanzeige und akustischer Führung finden.', 'Localizador de puntos de acceso con indicador de señal y guía sonora.'),
    'Parser derived from Sparrow WiFi · Copyright 2017 ghostop14': ('Parser derivato da Sparrow WiFi · Copyright 2017 ghostop14', 'Analyseur dérivé de Sparrow WiFi · Copyright 2017 ghostop14', 'Parser abgeleitet von Sparrow WiFi · Copyright 2017 ghostop14', 'Analizador derivado de Sparrow WiFi · Copyright 2017 ghostop14'),
    'License GPL-3.0-or-later. No warranty.': ('Licenza GPL-3.0-or-later. Nessuna garanzia.', 'Licence GPL-3.0-or-later. Aucune garantie.', 'Lizenz GPL-3.0-or-later. Keine Gewährleistung.', 'Licencia GPL-3.0-or-later. Sin garantía.'),
    'License and credits: /usr/share/doc/syslinuxos-wifi-analyzer/': ('Licenza e crediti: /usr/share/doc/syslinuxos-wifi-analyzer/', 'Licence et crédits : /usr/share/doc/syslinuxos-wifi-analyzer/', 'Lizenz und Urheber: /usr/share/doc/syslinuxos-wifi-analyzer/', 'Licencia y créditos: /usr/share/doc/syslinuxos-wifi-analyzer/'),
}


def tr(message, **values):
    language = detect_language()
    translations = TRANSLATIONS.get(message)
    if language != 'en' and translations:
        message = translations[SUPPORTED.index(language) - 1]
    return message.format(**values) if values else message


def scan_message(message):
    # Preserve raw iw diagnostics (including braces) as data, never a template.
    prefix = 'Scan failed: '
    if message.startswith(prefix):
        return tr('Scan failed: {details}', details=message[len(prefix):])
    return tr(message)
