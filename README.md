# OCR Macro MVP Designer

Ein kleiner und schlanker Makro-Generator für Windows mit OCR-Unterstützung.

**Version:** 1.0.3 · **Entwickler:** Niclas Kersting  
**Aktuelles Release:** <https://github.com/NKAutomations/OCR_Macro_MVP/releases/latest>

Mit dem Programm können einfache Abläufe aus mehreren Schritten erstellt werden. Die Schritte werden anschließend automatisch in der festgelegten Reihenfolge ausgeführt.

> **Hinweis:** Das Programm ist für gewöhnlichen Bildschirmtext gedacht. Es ist nicht für das automatisierte Lösen oder Umgehen von CAPTCHAs vorgesehen.

## Funktionen

- OCR-Bereiche auf dem Bildschirm markieren
- Klickbereiche auf dem Bildschirm markieren
- Erkannte Texte in die Zwischenablage kopieren
- Inhalte aus der Zwischenablage einfügen
- Fest definierten Text direkt in ein Zielfeld einfügen
- Enter-Taste automatisch drücken
- Wartezeiten zwischen einzelnen Schritten festlegen und komfortabel bearbeiten
- Keine feste Schrittgrenze (auch umfangreiche Abläufe bis etwa 1000 Schritte sind möglich)
- Schritte hinzufügen, bearbeiten, löschen und verschieben
- Kommentare/Notizen werden gelb hervorgehoben und sind nach dem Anlegen schreibgeschützt
- Abläufe als JSON-Datei speichern und laden
- Tägliche Ausführung zu einer bestimmten Uhrzeit
- Ausführung über ein frei einstellbares Intervall
- Einstellbare Startverzögerung
- Einstellbare Mindestpause zwischen allen Schritten
- Optionales Minimieren des Designer-Fensters beim Start
- Persistente Tesseract-Einstellung
- Globaler Sicherheitsabbruch über Strg+Alt+Q
- Als Windows-EXE paketierbar

## Voraussetzungen

Benötigt werden:

- Windows
- Python 3.10 oder neuer
- Tesseract OCR
- Internetzugang für die Installation der Python-Pakete

## 1. Python installieren

Falls Python noch nicht installiert ist, kann es von der offiziellen Python-Webseite heruntergeladen werden:

<https://www.python.org/downloads/windows/>

Bei der Installation sollte die Option **Add Python to PATH** aktiviert werden.

Danach kann geprüft werden, ob Python verfügbar ist:

```bat
python --version
```

Falls der Befehl nicht funktioniert, kann alternativ dieser Befehl verwendet werden:

```bat
py --version
```

## 2. Tesseract OCR installieren

`pytesseract` ist nur die Python-Schnittstelle. Für die eigentliche Texterkennung wird zusätzlich die Tesseract-OCR-Engine benötigt.

### Windows-Installation

1. Öffne die [Tesseract-OCR-Releases auf GitHub](https://github.com/tesseract-ocr/tesseract/releases), um die offiziellen Projektversionen und Release-Informationen zu prüfen.
2. Für einen fertigen Windows-Installer kannst du die [Windows-Builds und Installationshinweise von UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) verwenden.
3. Installiere Tesseract mit den Standardoptionen. Eine Installation nach
	`C:\Program Files\Tesseract-OCR\` ist empfehlenswert.
4. Falls zusätzliche OCR-Sprachen benötigt werden, installiere die passenden Sprachdaten (`.traineddata`) mit und merke dir den Installationsordner.
5. Starte anschließend das OCR Macro MVP und wähle im Tab **Einstellungen** die Datei `tesseract.exe` aus.

Nach der Installation liegt Tesseract häufig hier:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Ob Tesseract erkannt wird, kann in der Eingabeaufforderung geprüft werden:

```bat
tesseract --version
```

Wenn Tesseract nicht über die Eingabeaufforderung gefunden wird, kann der Pfad im Tab **Einstellungen** ausgewählt werden. Die Einstellung wird persistent gespeichert.

### Geplante OCR-Einstellungen

Die aktuelle Version verwendet eine feste, für gewöhnlichen Bildschirmtext optimierte Verarbeitung: Graustufen, zweifache Bildvergrößerung, Kontrastverstärkung, Schärfung und den Tesseract-Modus `--psm 7`. Für zukünftige Versionen sind folgende Einstellungen sinnvoll:

- OCR-Sprache, zum Beispiel Deutsch oder Englisch
- frei wählbarer Tesseract-Page-Segmentation-Modus (`PSM`)
- einstellbare Bildvergrößerung
- optionales Schwarz-Weiß-Schwellenwertverfahren für schwachen Kontrast
- optionale Rauschreduzierung und Schärfung
- OCR-Timeout für langsame Rechner oder problematische Bereiche
- einstellbare Wiederholungsversuche bei leerem OCR-Ergebnis
- optionale Mindestqualität beziehungsweise Konfidenzprüfung
- Normalisierung von Leerzeichen, Zeilenumbrüchen und Sonderzeichen

Diese Optionen sollen die Erkennung bei kleinen Schriften, schlechter Darstellung und langsamen Rechnern verbessern, ohne die Standardbedienung unnötig kompliziert zu machen.

## 3. Python-Pakete installieren

Öffne eine Eingabeaufforderung im Projektordner und führe aus:

```bat
python -m pip install -r requirements.txt
```

Falls auf deinem System `python` nicht funktioniert, verwende:

```bat
py -m pip install -r requirements.txt
```

Die Pakete haben folgende Aufgaben:

| Paket | Aufgabe |
|---|---|
| `Pillow` | Bildschirmbilder und Bildverarbeitung |
| `pytesseract` | Verbindung zur Tesseract-OCR-Engine |
| `pyautogui` | Maus- und Tastatursteuerung |
| `pyperclip` | Zwischenablage verwenden |
| `pyinstaller` | Python-Programm als EXE verpacken |

## 4. Programm starten

Starte das Programm aus dem Projektordner:

```bat
python ocr_macro_mvp.py
```

Alternativ:

```bat
py ocr_macro_mvp.py
```

## Bedienung der GUI

### Edit-Modus

Im Edit-Modus wird der Ablauf zusammengestellt.

Über die Schaltflächen rechts neben der Schritteliste können neue Schritte hinzugefügt werden:

- **Klick**
- **OCR kopieren**
- **OCR einfügen**
- **Text einfügen**
- **Tab-Taste**
- **Tastenkombination**
- **Text löschen**
- **Kommentar/Notiz**
- **Enter**
- **Timer**

Es gibt keine künstliche Begrenzung der Schrittanzahl. Für sehr große Abläufe ist die Bedienung bis ungefähr 1000 Schritte ausgelegt.

### Klick

1. Einen Klickschritt hinzufügen.
2. Den Schritt auswählen.
3. Auf **Bearbeiten** klicken.
4. Auf dem Bildschirm einen Bereich markieren.
5. Das Programm klickt später auf die Mitte dieses Bereichs.

Die Desktop-Auswahl kann jederzeit mit **Esc** abgebrochen werden.

### OCR kopieren

1. Einen OCR-Schritt hinzufügen.
2. Den Schritt auswählen.
3. Auf **Bearbeiten** klicken.
4. Den Bildschirmbereich markieren, in dem der Text steht.
5. Beim Ausführen wird der Text erkannt und in die Zwischenablage kopiert.

Auch die OCR-Auswahl kann jederzeit mit **Esc** abgebrochen werden.

### OCR einfügen

Dieser Schritt fügt den aktuellen Inhalt der Zwischenablage in das aktuell fokussierte Eingabefeld ein.

Normalerweise wird vorher ein Klickschritt auf das gewünschte Eingabefeld eingefügt.

### Text einfügen

Dieser Schritt fügt einen fest definierten Text in das aktuell fokussierte Eingabefeld ein. Nach dem Hinzufügen öffnet sich ein Bearbeitungsfenster. Der eingegebene Text wird in der Schritteliste angezeigt und kann jederzeit über **Bearbeiten** oder einen Doppelklick geändert werden. Auch mehrzeiliger Text ist möglich.

### Enter

Drückt beim Ausführen automatisch die Enter-Taste.

### Tab-Taste

Wechselt mit der Tab-Taste zum nächsten fokussierbaren Element.

### Tastenkombination

Führt eine frei definierte Tastenkombination aus. Die Tasten werden mit `+` getrennt eingegeben, zum Beispiel `ctrl+shift+s`.

### Text löschen

Markiert den Inhalt des aktuell fokussierten Feldes mit `Strg+A` und löscht ihn mit der Rücktaste.

### Kommentar/Notiz

Ein Hinweis in der Schritteliste. Beim Anlegen kann der Text eingegeben werden; danach ist die Notiz schreibgeschützt und wird gelb hervorgehoben. Kommentare werden nicht ausgeführt, aber mit Zeitstempel in der Logdatei protokolliert.

### Timer

Mit einem Timer kann eine Wartezeit in Sekunden eingefügt werden. Das ist beispielsweise nützlich, wenn eine Webseite oder Anwendung nach einem Klick erst geladen werden muss. Einen Timer auswählen und **Bearbeiten** klicken (oder doppelt anklicken), um die Zeit komfortabel zu ändern.

## Beispielablauf

Ein einfacher Ablauf könnte so aussehen:

```text
1. Timer: 2 Sekunden
2. Klick: Suchfeld
3. OCR kopieren: Bereich mit einer Auftragsnummer
4. Klick: Eingabefeld
5. OCR einfügen
6. Enter
7. Timer: 5 Sekunden
8. Klick: Weiter-Schaltfläche
```

Die Schritte werden immer von oben nach unten ausgeführt.

## Schritte bearbeiten

In der Schritteliste kann ein Schritt ausgewählt werden.

Verfügbare Aktionen:

- **Bearbeiten**: Bereich oder Timer-Einstellung ändern
- **Löschen**: Schritt entfernen
- **Nach oben**: Schritt in der Reihenfolge nach vorne verschieben
- **Nach unten**: Schritt in der Reihenfolge nach hinten verschieben

## Run-Modus

Im Run-Modus kann der Ablauf gestartet werden.

### Einmalige Ausführung

Klicke auf:

```text
Einmal jetzt ausführen
```

Das Programm führt die Schritte genau in der gespeicherten Reihenfolge aus.

Im Run-Modus stehen zusätzlich folgende Optionen zur Verfügung:

- **Startverzögerung**: Der Ablauf wartet die angegebene Anzahl Sekunden, bevor der erste Schritt ausgeführt wird.
- **Mindestpause zwischen Schritten**: Nach jedem Schritt wird automatisch mindestens die angegebene Zeit gewartet. Diese Pause ist kein eigener Eintrag in der Schritteliste und ist standardmäßig auf 0,6 Sekunden gesetzt.
- **Designer-Fenster beim Start minimieren**: Wenn aktiviert, wird das OCR-Macro-Fenster vor der Verzögerung minimiert.

### Zeitplan

Im Edit-Modus kann zusätzlich ein Zeitplan eingestellt werden:

- **Deaktiviert**
- **Täglich** zu einer bestimmten Uhrzeit, zum Beispiel `09:00`
- **Intervall** in Minuten

Täglich und Intervall sind bewusst getrennt. Es kann immer nur einer der beiden Modi aktiv sein. Danach wird der ausgewählte Zeitplan über die Schaltfläche **Run-Zeitplan starten** aktiviert. In der Statusleiste wird dauerhaft der nächste Ausführungstermin angezeigt.

Die Startoptionen aus dem Run-Modus gelten auch für geplante Ausführungen:

- Startverzögerung vor jedem geplanten Ablauf
- optionales Minimieren des Designer-Fensters vor jedem geplanten Ablauf

## Konfiguration speichern

Über **Konfiguration speichern** wird der aktuelle Ablauf als JSON-Datei gespeichert.

Die Datei enthält unter anderem:

- Schrittfolge
- Klickbereiche
- OCR-Bereiche
- Timer-Werte
- Zeitplan
- Startverzögerung und Minimieren-Option

Der Tesseract-Pfad wird im Tab **Einstellungen** einmalig ausgewählt und automatisch unter `%APPDATA%\OCRMacro\settings.json` gespeichert. Danach steht er auch nach einem Neustart zur Verfügung.

Über **Konfiguration laden** kann ein gespeicherter Ablauf später wieder verwendet werden.

Die zuletzt gespeicherte Konfiguration wird beim nächsten Programmstart automatisch geladen, sofern die Datei noch vorhanden ist.

## Protokollierung

Jede Ausführung, jeder Schritt, Fehler, Abbruch und erkannte OCR-Text wird mit Zeitstempel protokolliert. Der Standardpfad ist `%APPDATA%\OCRMacro\ocr_macro.log`. Im Tab **Einstellungen** kann ein anderer Pfad ausgewählt werden.

## Sicherheitsabbruch

Wenn ein Ablauf läuft und sofort abgebrochen werden soll, drücke **Strg+Alt+Q**. Der Tastatur-Abbruch funktioniert auch dann, wenn ein anderes Fenster aktiv ist.

Der Ablauf wird dadurch beendet.

## Windows-EXE erstellen

Mit PyInstaller kann eine einzelne EXE erstellt werden.

Führe im Projektordner aus:

```bat
pyinstaller --onefile --noconsole ocr_macro_mvp.py
```

Die fertige Datei befindet sich anschließend normalerweise hier:

```text
dist\OCR_Macro_MVP_Designer.exe
```

Für den veröffentlichten v1.0.3-Release sollte diese EXE als Asset am GitHub-Release angehängt werden.

Die EXE kann anschließend auf einem Windows-Rechner gestartet werden.

Tesseract muss auf dem Zielrechner weiterhin installiert sein, sofern die OCR-Funktion verwendet wird. Alternativ muss in der GUI der Pfad zur `tesseract.exe` korrekt ausgewählt werden.

## Häufige Probleme

### Kein Text wird erkannt

- OCR-Bereich größer markieren
- auf ausreichenden Kontrast achten
- prüfen, ob der Text gut lesbar ist
- kontrollieren, ob der Tesseract-Pfad stimmt

### Klick erfolgt an der falschen Stelle

- Klickbereich erneut markieren
- bei mehreren Monitoren die Koordinaten prüfen
- Windows-Anzeigeskalierung kann die Bildschirmkoordinaten beeinflussen

### Einfügen funktioniert nicht

- zuerst einen Klickschritt auf das Eingabefeld setzen
- danach den Schritt **OCR einfügen** verwenden
- prüfen, ob das Zielfeld tatsächlich fokussiert werden kann
- bei als Administrator gestarteten Anwendungen das Programm ebenfalls als Administrator starten

### Tesseract wird nicht gefunden

In der GUI den Pfad zur Datei auswählen, zum Beispiel:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE).
