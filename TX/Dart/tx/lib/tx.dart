// ignore_for_file: constant_identifier_names

import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'dart:math';

const int PORT = 12345;
const String HOST = '127.0.0.1';
const int MAX_PACKET_SIZE = 1472;
const String file =
    'D:/Program Files/Netze-PS/nvs23_ps/TX/Dart/tx/test.txt'; // Change this to the path of the file you want to send
const int MAXTRYCOUNT =
    10; // the number of tries to send one packet, if it fails more than maxTryCount times, the packet will not be sent
const Duration INTERVAL =
    Duration(milliseconds: 1); // the interval between tries

Future<void> sendFirstPacket(
    RawDatagramSocket socket, int id, int maxSeqNum, String fileName) async {
  final fileNameBytes = utf8.encode(fileName);
  final buffer = Uint8List(10 + fileNameBytes.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, 0)
    ..setUint32(6, maxSeqNum);
  buffer.setRange(10, 10 + fileNameBytes.length, fileNameBytes);

  final result = socket.send(buffer, InternetAddress(HOST), PORT);
  int tryCount = 1;
  if (result == 0) {
    print(
        'Fehler beim Senden vom Initial Paket 0: Versuch $tryCount von $MAXTRYCOUNT');
    while (tryCount <= MAXTRYCOUNT && result == 0) {
      //await Future.delayed(INTERVAL);
      result != 0
          ? print('Paket 0 (init) erfolgreich gesendet')
          : print(
              'Fehler beim Senden vom Initial Paket 0: Versuch $tryCount von $MAXTRYCOUNT');
      tryCount++;
    }
  } else {
    print('Paket 0 (init) erfolgreich gesendet');
  }
}

Future<void> sendPacket(
    RawDatagramSocket socket, int id, int seqNum, Uint8List data,
    [bool md5 = false]) async {
  final buffer = Uint8List(6 + data.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, seqNum);
  buffer.setRange(6, 6 + data.length, data);
  var result = socket.send(buffer, InternetAddress(HOST), PORT);
  int tryCount = 1;
  while (result == 0 && tryCount <= MAXTRYCOUNT) {
    if (result == 0) {
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
    md5
        ? print('MD5-Paket $seqNum nicht gesendet')
        : print('Paket $seqNum nicht gesendet');
    return;
  }
  md5
      ? print('MD5-Paket $seqNum erfolgreich gesendet')
      : print('Paket $seqNum erfolgreich gesendet');
}

void main() async {
  final socket = await RawDatagramSocket.bind(InternetAddress(HOST), 0);
  final id = DateTime.now().millisecondsSinceEpoch % 65536;
  final fileBytes = await File(file).readAsBytes(); // File as bytes
  final maxSeqNum = (fileBytes.length / (MAX_PACKET_SIZE - 6)).ceil();
  final md5Hash = md5.convert(fileBytes).bytes; // MD5 hash of the file

  await sendFirstPacket(socket, id, maxSeqNum, file); // Send the first packet

  for (int seqNum = 1; seqNum <= maxSeqNum; seqNum++) {
    // Send the data packets
    final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
    final end = min(seqNum * (MAX_PACKET_SIZE - 6), fileBytes.length);
    final data = fileBytes.sublist(start, end);
    await sendPacket(socket, id, seqNum, data);
  }
  // Send the MD5 hash as the last packet
  final md5Packet = Uint8List.fromList(md5Hash);
  await sendPacket(socket, id, maxSeqNum + 1, md5Packet, true);

  socket.close();
}
