// ignore_for_file: constant_identifier_names

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

Future<void> sendFirstPacket(
    RawDatagramSocket socket, int id, int maxSeqNum, String fileName,
    [quiet = false]) async {
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
    !quiet ? print('Paket 0 (init) erfolgreich gesendet') : {};
  }
  //await waitForAcks(PORT, 0, id, quiet);
}

Future<void> sendPacket(
    RawDatagramSocket socket, int id, int seqNum, Uint8List data, quiet,
    [bool md5 = false]) async {
  final buffer = Uint8List(6 + data.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, seqNum);
  buffer.setRange(6, 6 + data.length, data);
  var result = socket.send(buffer, InternetAddress(HOST), PORT);
  int tryCount = 1;
  while (result == 0 && tryCount <= MAXTRYCOUNT) {
    if (result == 0 && !quiet) {
      md5
          ? print('Fehler beim Senden von MD5-Paket $seqNum')
          : print(
              'Fehler beim Senden von Paket $seqNum: Versuch $tryCount von $MAXTRYCOUNT');
    }
    result = socket.send(buffer, InternetAddress(HOST), PORT);
    tryCount++;
    await Future.delayed(INTERVAL);
  }
  if (result == 0 && tryCount > MAXTRYCOUNT) {
    printpaketstatus(seqNum, md5, quiet, sent: false);
  } else {
    printpaketstatus(seqNum, md5, quiet, sent: true);
    //await waitForAcks(PORT, seqNum, id, quiet);
  }
}

Future<void> waitForAcks(int port, int seqNr, int id, bool quiet) async {
  final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, port);
  await socket.listen((RawSocketEvent event) {
    if (event == RawSocketEvent.read) {
      final Datagram? dg = socket.receive();
      if (dg != null) {
        _processAckPacket(dg.data, seqNr, id, quiet);
        return;
      }
    }
  }).asFuture<void>();
}

void _processAckPacket(Uint8List data, int seqNr, int id, bool quiet) {
  if (data.length != 6) {
    !quiet ? print('Invalid ACK packet length') : {};
    return;
  }

  final transmissionId = data.buffer.asByteData().getUint16(0);
  final sequenceNumber = data.buffer.asByteData().getUint32(2);
  if (transmissionId != id) {
    print('Invalid ACK packet transmission ID');
    return;
  }
  if (sequenceNumber != seqNr) {
    print('Invalid ACK packet sequence number');
    return;
  } else {
    print(
        'ACK Paket mit Transmission ID: $transmissionId und Sequence Number: $sequenceNumber erhalten');
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
  // Parse the command line arguments
  var parser = ArgParser();
  parser.addOption('host', abbr: 'h', defaultsTo: HOST);
  parser.addOption('port', abbr: 'p', defaultsTo: PORT.toString());
  parser.addOption('max', abbr: 'm', defaultsTo: MAX_PACKET_SIZE.toString());
  parser.addOption('file', abbr: 'f', defaultsTo: file);
  parser.addFlag('quiet', abbr: 'q', defaultsTo: false);
  var results = parser.parse(args);
  HOST = results['host'] as String;
  PORT = int.parse(results['port'] as String);
  MAX_PACKET_SIZE = int.parse(results['max'] as String);
  file = results['file'] as String;
  bool quiet = results['quiet'] as bool;
  final socket = await RawDatagramSocket.bind(InternetAddress(HOST), 0);
  final id = DateTime.now().millisecondsSinceEpoch % 65536;
  final fileBytes = await File(file).readAsBytes(); // File as bytes
  final maxSeqNum = (fileBytes.length / (MAX_PACKET_SIZE - 6)).ceil();
  final md5Hash = md5.convert(fileBytes).bytes; // MD5 hash of the file

  await sendFirstPacket(
      socket, id, maxSeqNum, file, quiet); // Send the first packet

  for (int seqNum = 1; seqNum <= maxSeqNum; seqNum++) {
    // Send the data packets
    final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
    final end = min(seqNum * (MAX_PACKET_SIZE - 6), fileBytes.length);
    final data = fileBytes.sublist(start, end);
    await sendPacket(socket, id, seqNum, data, quiet);
  }
  // Send the MD5 hash as the last packet
  final md5Packet = Uint8List.fromList(md5Hash);
  await sendPacket(socket, id, maxSeqNum + 1, md5Packet, true);

  socket.close();
}
