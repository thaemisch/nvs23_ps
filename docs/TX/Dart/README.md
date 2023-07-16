# Dokumentation für Dart

## Code Location

Der Code befindet sich im Ordner [/TX/Dart/tx/lib/](/TX/Dart/tx/lib/)

## Prerequisites

- Dart installiert (https://dart.dev/get-dart)
- Falls beim Ausführen des TX eine Fehlermeldung auftritt, dass ein Package nicht gefunden wurde, einmal `dart pub get` im Ordner [/TX/Dart/tx/](/TX/Dart/tx/) ausführen

## Ausführen

Vom Root-Ordner des Projekts aus:

    dart run dart run .\TX\Dart\tx\lib\tx.dart -f <your-file-path> [options]
    oder 
    dart run .\TX\Dart\tx\lib\tx.dart -? for help

Für den Fall, dass relative Pfade nicht funktionieren, kann auch der absolute Pfad verwendet werden.

## Optionen

- `-h` or `--host` <host> : Host to send to (default: 127.0.0.1)
- `-p` or `--port` <port>: Port to send to (default: 12345)
- `-m` or `--max` <size>: Maximum packet size (default: 1472)
- `-f` or `--file` <filename>: File to send
- `-v` or `--version`: TX version to use (default: 3)
- `-n` or `--sliding-window`: Sliding windows size (Only applicable if version is 3, default is 10)
- `-t` or `--timeout`: Timeout for the first ack in seconds (Only applicable if version is 3, default: 1s)

## Flags

- `-q` or `--quiet`: Suppress log output
- `-?` or `--help`: Show usage

## Packettypen

[Hier](/docs/TX/NodeJS/README.md#Packettypen) ist eine Beschreibung der Packettypen zu finden.

## Versionen

[Hier](/docs/TX/NodeJS/README.md#Versionen) ist eine Beschreibung der Versionen zu finden.

## Funktionsweise des Senders

Zu Beginn werden alle CLI-Argumente geparst, bevor die Variablen entsprechend gesetzt werden. Danach wird der Socket geöffnet und die Datei wird eingelesen und in ein Byte-Array umgewandelt. Ebenso wird die `maxSeqNum` und der md5-Hashwert berechnet. 

Danach wird das initiale Paket gesendet. In Version 1 wird auf eine Antwort nicht gewartet. In Version 2 und 3 wird jedoch nach dem Senden solange gewartet, bis ein ACK empfangen wurde. Im Fall von Version 3 gibt es einen Timeout, der das Paket erneut sendet, falls nach dieser Zeit kein ACK empfangen wurde. Das erste Paket befindet sich also nicht in einem Sliding Window, sondern wird separat behandelt.

Nachdem das erste Paket gesendet wurde, werden die Daten der Datei übertragen. Für das Senden eines Pakets ist folgende Methode zuständig:

```dart
Future<void> sendPacket(int seqNum, Uint8List data,
    {bool md5 = false, bool wait = true}) async {
  final buffer = Uint8List(6 + data.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, seqNum);
  buffer.setRange(6, 6 + data.length, data);
  var result = socket.send(buffer, InternetAddress(HOST), PORT);
  int tryCount = 1;
  while (result == 0 && tryCount <= MAXTRYCOUNT) {
    if (result == 0 && !quiet) {
      printiffalse('Fehler beim Senden von MD5-Paket $seqNum', !md5);
      printiffalse(
          'Fehler beim Senden von Paket $seqNum: Versuch $tryCount von $MAXTRYCOUNT',
          md5);
    }
    result = socket.send(buffer, InternetAddress(HOST), PORT);
    tryCount++;
    await Future.delayed(INTERVAL);
  }
  if (result == 0 && tryCount > MAXTRYCOUNT) {
    printpaketstatus(seqNum, md5, quiet, sent: false);
  } else {
    printpaketstatus(seqNum, md5, quiet, sent: true);
    if (version == 2 && wait)  {
      await waitForAck(seqNum);
    }
  }
}
```

Es werden also zunächst die Daten in einen Buffer geschrieben. Dieser Buffer wird dann an den Empfänger gesendet. Falls das Senden fehlschlägt (kann bei dart in seltenen Fällen funktionieren) wird es nochmal versucht. Dies wird maximal `MAXTRYCOUNT` mal versucht. Falls es dann immer noch nicht funktioniert, wird das Paket nicht gesendet. Falls es funktioniert, wird im Falle von Version 2 auf ein ACK gewartet: 
    
```dart
Future<void> waitForAck(int seqNr) async {
  final completer = Completer<void>(); // Completer to signal method completion
  late StreamSubscription<RawSocketEvent> sub;
  bool valid = false;

  // Listen for data events on the socket
  sub = stream.listen((event) async {
    if (event == RawSocketEvent.read) {
      final datagram = socket.receive();
      if (datagram == null) {
        return;
      } else {
        final data = datagram.data;
        if (data.length == 6) {
          valid = _processAckPacket(data, seqNr);
          if (valid) {
            await sub.cancel();
            completer.complete();
          }
        }
      }
    }
  });
  await completer.future;
}
```

Dabei wird ein Completer verwendet, der das Ende der Methode signalisiert. Dieser wird erst aufgelöst, wenn ein ACK mit der richtigen Sequenznummer empfangen wurde. Falls ein ACK mit der falschen Sequenznummer empfangen wurde, wird dieses ignoriert. 

Bei Version 3 wird das Ganze ein wenig komplexer. Hier wird vor dem Senden die Methode `getPacket()` aufgerufen, die während dem gesamten Sendeprozess parallel läuft und auf ACKs wartet bzw. bei DupACKs das fehlende Paket erneut sendet. Die ACKs werden dabei in einem Set gespeichert. Wird ein ACK mit einer SeqNum empfangen, die sich schon im Set befindet, handelt es sich um ein DupACK und das entsprechende Paket wird erneut gesendet und die SeqNum wird aus dem Set entfernt. Nun werden jeweils `slidingWindow` viele Pakete gesendet. Danach wird solange gewartet, bis das entsprechende CumACK empfangen wurde. Dies wird solange wiederholt, bis alle Datenpakete gesendet wurden.

Nun ist noch das letzte Paket mit dem md5-Hash zu senden. Bei Version 1 wird das letzte Paket gesendet ohne auf ein ACK zu warten. Bei Version 2 und 3 wird jeweils auf ein ACK gewartet. Wichtig ist, dass das letzte Paket bei Version 3 nicht separat behandelt wird, sondern im Sliding Window gesendet wird.


    

