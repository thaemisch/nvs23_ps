// ignore_for_file: constant_identifier_names, non_constant_identifier_names

import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:args/args.dart';
import 'dart:math';

int PORT = 12345;
String HOST = '127.0.0.1';
int MAX_PACKET_SIZE = 1472;
String file =
    'D:/Program Files/Netze-PS/nvs23_ps/TX/Dart/tx/test.txt'; // Change this to the path of the file you want to send
const int MAXTRYCOUNT =
    10; // the number of tries to send one packet, if it fails more than maxTryCount times, the packet will not be sent
const Duration INTERVAL =
    Duration(milliseconds: 1); // the interval between tries

Future<void> sendFirstPacket(RawDatagramSocket socket, int id, int maxSeqNum,
    String fileName, Stream<RawSocketEvent> stream, quiet,
    {version = 2}) async {
  final fileNameBytes = utf8.encode(fileName);
  final buffer = Uint8List(10 + fileNameBytes.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, 0)
    ..setUint32(6, maxSeqNum);
  buffer.setRange(10, 10 + fileNameBytes.length, fileNameBytes);

  int result = socket.send(buffer, InternetAddress(HOST), PORT);
  int tryCount = 1;
  if (result == 0) {
    !quiet
        ? print(
            'Fehler beim Senden vom Initial Paket 0: Versuch $tryCount von $MAXTRYCOUNT')
        : {};
    while (tryCount <= MAXTRYCOUNT && result == 0) {
      //await Future.delayed(INTERVAL);
      result != 0 && !quiet
          ? print('Paket 0 (init) erfolgreich gesendet')
          : print(
              'Fehler beim Senden vom Initial Paket 0: Versuch $tryCount von $MAXTRYCOUNT');
      result = socket.send(buffer, InternetAddress(HOST), PORT);
      tryCount++;
    }
  } else {
    printiffalse('Paket 0 (init) erfolgreich gesendet', quiet);
  }
  if (version > 1) await waitForAck(socket, PORT, 0, id, stream, quiet);
}

Future<void> sendPacket(RawDatagramSocket socket, int id, int seqNum,
    Uint8List data, Stream<RawSocketEvent> stream, bool quiet,
    {bool md5 = false, version = 2}) async {
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
    if (version == 2) await waitForAck(socket, PORT, seqNum, id, stream, quiet);
  }
}



Future<void> waitForAck(RawDatagramSocket socket, int port, int seqNr, int id,
    Stream<RawSocketEvent> stream, bool quiet) async {
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
          valid = _processAckPacket(data, seqNr, id, quiet);
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

Future<int> waitForAckandGetSeqNr(RawDatagramSocket socket, int port, int id, int seqNr,
    Stream<RawSocketEvent> stream, bool quiet, int version) async {
  final completer = Completer<int>(); // Completer to signal method completion
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
          valid = _processAckPacket(data, seqNr, id, quiet);
          if (valid) {
            seqNr = data.buffer.asByteData().getUint32(2);
            await sub.cancel();
            completer.complete(seqNr);
          }
        }
      }
    }
  });
  await completer.future;
  return seqNr;
}

bool _processAckPacket(Uint8List data, int seqNr, int id, bool quiet, {int version = 2}) {
  final transmissionId = data.buffer.asByteData().getUint16(0);
  final sequenceNumber = data.buffer.asByteData().getUint32(2);
  if(version == 3) {
    return true;
  }
  if (transmissionId != id) {
    printiffalse(
        'ACK Paket mit falscher Transmission ID erhalten => SOLL: $id IST: $transmissionId',
        quiet);
    return false;
  }
  if (sequenceNumber != seqNr) {
    printiffalse(
        'ACK Paket mit falscher Sequenznummer erhalten => SOLL: $seqNr IST: $sequenceNumber',
        quiet);
    return false;
  } else {
    printiffalse(
        'ACK Paket mit Transmission ID: $transmissionId und Sequenznummer: $sequenceNumber erhalten\n',
        quiet);
    return true;
  }
}

void printiffalse(String text, bool value) {
  if (!value) {
    print(text);
  }
}

void printpaketstatus(int seqNr, bool md5, bool quiet, {required bool sent}) {
  if (quiet) return;
  if (sent) {
    md5
        ? print('MD5-Paket $seqNr erfolgreich gesendet')
        : print('Paket $seqNr erfolgreich gesendet');
  } else {
    md5
        ? print('MD5-Paket $seqNr nicht gesendet')
        : print('Paket $seqNr nicht gesendet');
  }
}

void main(List<String> args) async {
  // ------------------- Parse command line arguments -------------------
  var parser = ArgParser();
  parser.addOption('host', abbr: 'h', defaultsTo: HOST);
  parser.addOption('port', abbr: 'p', defaultsTo: PORT.toString());
  parser.addOption('max', abbr: 'm', defaultsTo: MAX_PACKET_SIZE.toString());
  parser.addOption('file', abbr: 'f', defaultsTo: file);
  parser.addOption('version', abbr: 'v', defaultsTo: '2');
  parser.addOption('sliding-window',abbr: 's',defaultsTo: '10' );
  parser.addFlag('quiet', abbr: 'q', defaultsTo: false);
  var results = parser.parse(args);
  HOST = results['host'] as String;
  PORT = int.parse(results['port'] as String);
  MAX_PACKET_SIZE = int.parse(results['max'] as String);
  file = (results['file'] as String).replaceAll('\\', '/');
  int VERSION = int.parse(results['version'] as String);
  bool quiet = results['quiet'] as bool;
  final slidingWindow = int.parse(results['sliding-window'] as String);

  // ------------------- initialize Variables -------------------
  final socket =
      await RawDatagramSocket.bind(InternetAddress(HOST), 0 /*PORT*/);
  final stream = socket.asBroadcastStream();
  final id = Random().nextInt(65535); // Random transmission ID (0-65535)
  final fileBytes = await File(file).readAsBytes(); // File as bytes
  final maxSeqNum = (fileBytes.length / (MAX_PACKET_SIZE - 6)).ceil() + 1;
  final md5Hash = md5.convert(fileBytes).bytes; // MD5 hash of the file
  final RegExpMatch? fileameForPrint = RegExp(r"(?<=/)[^/]*$").firstMatch(file
      .replaceAll("\\\\", "/")
      .replaceAll("\\", "/")); // Filename after last slash
  file = fileameForPrint != null
      ? file.substring(fileameForPrint.start, fileameForPrint.end)
      : file;

  // ------------------ Send the file ------------------
  printiffalse(
      '\n-------------------------- Sending file: $file with Transmission ID: $id --------------------------\n',
      quiet);

  await sendFirstPacket(socket, id, maxSeqNum, file, stream, quiet,
      version: VERSION); // Send the first packet

  if(VERSION != 3) {
    for (int seqNum = 1; seqNum < maxSeqNum; seqNum++) {
      // Send the data packets
      final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
      final end = min(seqNum * (MAX_PACKET_SIZE - 6), fileBytes.length);
      final data = fileBytes.sublist(start, end);
      await sendPacket(
          socket, id, seqNum, data, stream, quiet, version: VERSION);
    }
  } else {

    int seqNum = 1;
  bool listen = true;
  Set<int> possibleDupAck = {};
    Future<void> getPacket(RawDatagramSocket socket, int id, Stream<RawSocketEvent> stream) async {
      late final int ack;
      ack = await waitForAckandGetSeqNr(socket,PORT, id, seqNum, stream, quiet, VERSION).then((value) {
        if (listen) {
          // Keep listening for Acks
          getPacket(socket, id, stream);
        }
        if (possibleDupAck.contains(value)) {
          possibleDupAck.remove(value);
          // resend packet
          seqNum++;
          if (seqNum < maxSeqNum) {
            final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
            final end = min(seqNum * (MAX_PACKET_SIZE - 6), fileBytes.length);
            sendPacket(socket, id, seqNum, fileBytes.sublist(start, end), stream, quiet);
            return value;
          } else {
            return value;
          }
        } else {
          possibleDupAck.add(ack);
          return value;
        }} );
    }
// Start listening for acks
  getPacket(socket, id, stream);

  while (seqNum < maxSeqNum) {
    seqNum = await sendNPackages(slidingWindow, id, seqNum, maxSeqNum, fileBytes, socket, stream);
    printiffalse('Sliding window wait: ${seqNum - 1}', quiet);
  }
  }
  // Send the MD5 hash as the last packet
  final md5Packet = Uint8List.fromList(md5Hash);
  await sendPacket(socket, id, maxSeqNum, md5Packet, stream, quiet,
      md5: true, version: VERSION);

  printiffalse(
      '-------------------------- File sent --------------------------\n',
      quiet);

  socket.close();

}

Future<int> sendNPackages(int n, int id, int seqNum, int maxSeqNum,
    Uint8List data, RawDatagramSocket socket, Stream<RawSocketEvent> stream,
    {bool quiet = false, int VERSION = 3}) async {
  while(n > 0){
    final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
    final end = min(seqNum * (MAX_PACKET_SIZE - 6), data.length);
    final packetData = data.sublist(start, end);
    await sendPacket(socket, id, seqNum, packetData, stream, quiet, version: VERSION);
    seqNum++;
    if (seqNum == maxSeqNum) {
      break;
    }
    n--;
  }
  return seqNum;
}

Future<int> waitForGeneralAckPacket(
    RawDatagramSocket socket, int transmissionId, Stream<RawSocketEvent> stream) async {
  final completer = Completer<int>();
  late StreamSubscription<RawSocketEvent> sub;

  void messageHandler(RawSocketEvent event) {
    if (event == RawSocketEvent.read) {
      final datagram = socket.receive();
      if (datagram == null) {
        return;
      } else {
        final data = datagram.data;
        final receivedTransmissionId = data.buffer.asByteData().getUint16(0);
        final receivedSequenceNumber = data.buffer.asByteData().getUint32(2);
        if (receivedTransmissionId == transmissionId) {
          sub.cancel();
          completer.complete(receivedSequenceNumber);
        }
      }
    }
  }

  sub = stream.listen(messageHandler);
  return await completer.future;
}

