# OCR Macro

Ein kleiner und schlanker Makro-Generator für Windows mit OCR-Unterstützung.

Mit dem Programm können einfache Abläufe aus mehreren Schritten erstellt werden. Die Schritte werden anschließend automatisch in der festgelegten Reihenfolge ausgeführt.

> **Hinweis:** Das Programm ist für gewöhnlichen Bildschirmtext gedacht. Es ist nicht für das automatisierte Lösen oder Umgehen von CAPTCHAs vorgesehen.

## Funktionen

- OCR-Bereiche auf dem Bildschirm markieren
- Klickbereiche auf dem Bildschirm markieren
- Erkannte Texte in die Zwischenablage kopieren
- Inhalte aus der Zwischenablage einfügen
- Enter-Taste automatisch drücken
- Wartezeiten zwischen einzelnen Schritten festlegen
- Bis zu 10 Schritte pro Ablauf
- Schritte hinzufügen, bearbeiten, löschen und verschieben
- Abläufe als JSON-Datei speichern und laden
- Tägliche Ausführung zu einer bestimmten Uhrzeit
- Ausführung über ein frei einstellbares Intervall
- Sicherheitsabbruch über die linke obere Bildschirmecke
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

Nach der Installation liegt Tesseract häufig hier:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Ob Tesseract erkannt wird, kann in der Eingabeaufforderung geprüft werden:

```bat
tesseract --version
```

Wenn Tesseract nicht über die Eingabeaufforderung gefunden wird, kann der Pfad später direkt in der GUI ausgewählt werden.

## 3. Python-Pakete installieren

Öffne eine Eingabeaufforderung im Projektordner und führe aus:

```bat
python -m pip install pillow pytesseract pyautogui pyperclip pyinstaller
```

Falls auf deinem System `python` nicht funktioniert, verwende:

```bat
py -m pip install pillow pytesseract pyautogui pyperclip pyinstaller
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
- **Enter**
- **Timer**

Es können maximal 10 Schritte angelegt werden.

### Klick

1. Einen Klickschritt hinzufügen.
2. Den Schritt auswählen.
3. Auf **Bearbeiten** klicken.
4. Auf dem Bildschirm einen Bereich markieren.
5. Das Programm klickt später auf die Mitte dieses Bereichs.

### OCR kopieren

1. Einen OCR-Schritt hinzufügen.
2. Den Schritt auswählen.
3. Auf **Bearbeiten** klicken.
4. Den Bildschirmbereich markieren, in dem der Text steht.
5. Beim Ausführen wird der Text erkannt und in die Zwischenablage kopiert.

### OCR einfügen

Dieser Schritt fügt den aktuellen Inhalt der Zwischenablage in das aktuell fokussierte Eingabefeld ein.

Normalerweise wird vorher ein Klickschritt auf das gewünschte Eingabefeld eingefügt.

### Enter

Drückt beim Ausführen automatisch die Enter-Taste.

### Timer

Mit einem Timer kann eine Wartezeit in Sekunden eingefügt werden. Das ist beispielsweise nützlich, wenn eine Webseite oder Anwendung nach einem Klick erst geladen werden muss.

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

### Zeitplan

Im Edit-Modus kann zusätzlich ein Zeitplan eingestellt werden:

- täglich zu einer bestimmten Uhrzeit, zum Beispiel `09:00`
- oder über ein Intervall in Minuten

Danach wird der Zeitplan über die Schaltfläche **Run-Zeitplan starten** aktiviert.

## Konfiguration speichern

Über **Konfiguration speichern** wird der aktuelle Ablauf als JSON-Datei gespeichert.

Die Datei enthält unter anderem:

- Schrittfolge
- Klickbereiche
- OCR-Bereiche
- Timer-Werte
- Zeitplan
- Tesseract-Pfad

Über **Konfiguration laden** kann ein gespeicherter Ablauf später wieder verwendet werden.

## Sicherheitsabbruch

`pyautogui` verfügt über eine Sicherheitsfunktion.

Wenn ein Ablauf läuft und sofort abgebrochen werden soll, bewege den Mauszeiger in die **linke obere Ecke des Bildschirms**.

Der Ablauf wird dadurch beendet.

## Windows-EXE erstellen

Mit PyInstaller kann eine einzelne EXE erstellt werden.

Führe im Projektordner aus:

```bat
pyinstaller --onefile --noconsole ocr_macro_mvp.py
```

Die fertige Datei befindet sich anschließend normalerweise hier:

```text
dist\ocr_macro_mvp.exe
```

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

Dieses Projekt kann je nach gewünschter Verwendung unter einer passenden Open-Source-Lizenz veröffentlicht werden, zum Beispiel MIT. Vor der Veröffentlichung sollte die gewünschte Lizenzdatei noch ergänzt werden.
