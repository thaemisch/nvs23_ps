# Dokumentation für Python

## Starten des Programmes
    
    python main.py --help

## Optionen (CLI Argumente)

    '-q', '--quiet'             Do not print anything to the terminal
    '-s', '--save'              Save the received file to disk
    '-v', '--version'           Version of the protocol (default: 3)
    '-m', '--max'               Maximum packet size (default: 1500)
    '-n', '--sliding-window'    Window size (default: 10)
    '-t', "--throwaway"         Throw away the 3rd packet on first time
    '--host'                    Host to receive from (default: 127.0.0.1)
    '--port'                    Port to receive from (default: 12345)

## Versionen
Die version kann mit `-v` oder `--version` spezifiziert werden.

|              | V1 | V2 | V3 |
|--------------|----|----|----|
|   MD5-Check  | ✓  | ✓  | ✓ |
|      ACK     | ✗  | ✓  | ✓ |
|Sliding Window| ✗  | ✗  | ✓ |

## Funktionsweise des Codes

1. Überprüfung auf CLI Argumente
    - gespeichert als Variablen, meist als `if` Abfragen im Code verwendet
2. UDP-Socket wird erstellt
    - host & port können über cli args festgelegt werden
3. Erstes Paket wird empfangen
    - gespeichert werden
        - transmission ID
        - max sequence number
        - filename
    - wenn  Version != 1: ACK wird gesendet
4. Überprüfung auf festgelegte Version
    1. Version 1
        - während `seq_num < max_seq_num-1` ist, werden Datenpakete empfangen.
        - es wird überprüft, ob die transmission ID übereinstimmt
            - ist das der fall, wird die packet data in eine Map mit der `seq_num` als Key gespeichert
    2. Version 2
        - wie Version 1, aber nach jedem (erfolgreichen) Packet wird ein ACK gesendet
    3. Version 3
        1. `window_start = 1` und `window_end = window_start + window_size - 1` werden gesetzt
        2. während noch nicht alle Datenpackete empfangen wurden
            1. 