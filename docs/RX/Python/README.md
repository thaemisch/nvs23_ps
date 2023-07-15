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
Die version kann mit `-v X` oder `--version X` spezifiziert werden.

|              | V1 | V2 | V3 |
|--------------|----|----|----|
|   MD5-Check  | ✓  | ✓  | ✓ |
|      ACK     | ✗  | ✓  | ✓ |
|Sliding Window| ✗  | ✗  | ✓ |


