# Netze PS 2023 
### Ahmad Waleed, Hämisch Tim, Lankes Manuel, Oberhofer Julian

## Dokumentation der einzelnen Programme

Die Dokumentation der einzelnen Programme befindet sich in den jeweiligen Docu Ordnern als `README.md` Datei.

- TX
    - [Dart](docs/TX/Dart/README.md)
    - [NodeJS](docs/TX/NodeJS/README.md)
- RX
    - [Java](docs/RX/Java/README.md)
    - [Python](docs/RX/Python/README.md)

## Automatisches Testen

### Voraussetzungen

- Python installiert
- Python-Module `pyshark` und `matplotlib` installiert
- Windows:
    - Wireshark installiert und in der PATH-Variable eingetragen \
    (Es muss `tshark` im Terminal ausführbar sein)
- Linux:
    - Je nach Distribution kann es `tshark` heißen oder `wireshark-cli` (für mehr Informationen siehe [tshark setup Guid](https://tshark.dev/setup/install/))
    - Falls `wireshark-cli` installiert ist, sollte eine Alias für `tshark` erstellt werden, da das Skript sonst nicht funktioniert (z.B. `alias tshark=wireshark-cli` in der `.bashrc`)
- Wireshark muss ohne Root/Admin gestartet werden können \
(Theoretisch sollte es auch mit Root/Admin funktionieren, aber das Skript wurde nicht darauf getestet und es wird davon abgeraten)

### Ausführen

- `python mainMessung.py --help` im Terminal ausführen für alle Optionen

### Beispiel

Eine Messreihe mit 10 Messungen zwischen allen TX und RX mit Paketgröße 100, 1400 und 60000 Bytes. (Standard und kann nicht parametrisiert werden) \
Jede Messung überträgt jeweils eine 1MB große Datei, mit Version 3 des Protokolls, sliding window größe 10 und einer timeout Zeit von 60 Sekunden:

```python mainMessung.py --folder messungen/V3/1MB --size 1MB --version 3 --sliding-window 10 --timeout 60 --interface eth0```

Alles was jetzt noch zu tun ist, ist zu warten, bis die Messungen fertig sind. \
Je nach Parameter kann das einige Zeit dauern.
