# Dokumentation für Java

## Kompilieren und starten des Programms

    javac .\UDPReceiver.java
    java UDPReceiver --help

## Optionen

    Options:
    -h, --host <host>                           Host to receive from (default: 127.0.0.1)
    -p, --port <port>                           Port (default: 12345)
    -m, --max <size>                            Maximum packet size (default: 1472)
    -q, --quiet                                 Suppress log output (overrides -v)
    -v, --verbose                               Verbose log output
    -V, --version <version>                     Version of the protocol (default: 3)
    -n, --sliding-window <window-size>          Window site (default: 10)
    --throwaway                                 Throw away some packets on purpose (testing)
    -t, --timeout <timeout [ms]>                Timeout for packets [ms] (default: 1000 ms)
    -w, --windows <delay [ms]> <timeout [ms]>   DupAck delay [ms] and timeout for packets [ms] (default: 0 ms and 1000 ms)
    -d, --dup-ack-delay <delay [ms]>            Delay between DupAck [ms] (default: 0 ms)
    -?, --help                                  Show this help

## Versionen

Der Receiver kann in drei Versionen betrieben werden. Dies kann über das Argument `-v` oder `--version` eingestellt werden. Version 1 verwendet dabei keine ACKs, Version 2 ein ACK nach jedem Paket und Version 3 nach jedem Fenster. Die restlichen Parameter und dazugehörige Beschreibungen sind oben gelistet.

## Funktionsweise des Codes

Wird das Programm gestartet, so wird zunächst in der Methode `main` auf die Argumente geprüft. Werden keine eingegeben, so läuft der RX mit den Defaults. Die Funktion ruft dann `run` mit den entsprechenden Parametern auf. Hier werden vereinfacht erklärt in einer Schleife Pakete empfangen und je nach Sequenz-Nummer bearbeitet. Handelt es sich um Datenpakete, so werden diese (bei Version 3) in eine `TreeMap` mit der Sequenz-Nummer als Key gespeichert (so wird die korrekte Ordnung gewährleistet). Gleichzeitig wird in einem Boolean-Array das entsprechende Feld (je nach Sequenz-Nummer) auf true gesetzt. Wenn ein Fenster zu Ende ist, dann wird dieses Array durchlaufen und für jedes `false` wird ein DupAck für das entsprechende Paket geschickt. Diese wird dann empfange und in die `TreeMap` gespeichert. Wenn alle Pakete der Window nur vorhanden sind, werden die Daten in ein `ByteArrayOutputStream` geschrieben und dann ein Cumulative ACK versendet. Das Prozedere wiederholt sich bis wir das letzte Paket haben. Der Unterschied bei Version 1 und 2 ist, dass die Pakete nicht in einer zwischengespeichert werden sondern direkt in der Stream geschrieben werden. Bei Version 2 wird zusätzlich nach jedem Paket ein ACK geschickt.\
\
Der `ByteArrayOutputStream` wird über eine `FileOutputStream` in der Funktion `writeToFile` in ein File geschrieben und dann werden mittels `checkMD5Sum` die beiden MD5-Hashes verglichen und entsprechender Output ausgegeben.\
\
Wichtig zu erwähnen ist, dass für Version 3 ein Timeout gesetzt werden kann wenn ein Paket nicht ankommt. Dies ist z.B. hilfreich wenn das letzte Paket in einem Fenster innerhalb der gesetzten Zeit (Default 1000ms) nicht empfangen wurde. Des Weiteren kann auch die Zeit zwischen den DupACKs eingestellt werden.
