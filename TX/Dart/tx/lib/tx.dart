// ignore_for_file: constant_identifier_names

import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'dart:math';

const int PORT = 12345;
const String HOST = '127.0.0.1';
const int MAX_PACKET_SIZE = 1472;
const String file = 'test.txt';

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
  if (result != 0) {
    print('Paket 0 (init) erfolgreich gesendet');
  } else {
    print('Fehler beim Senden vom Initial Paket 0');
  }
}

Future<void> sendPacket(
    RawDatagramSocket socket, int id, int seqNum, Uint8List data) async {
  final buffer = Uint8List(6 + data.length);
  ByteData.view(buffer.buffer)
    ..setUint16(0, id)
    ..setUint32(2, seqNum);
  buffer.setRange(6, 6 + data.length, data);

  final result = socket.send(buffer, InternetAddress(HOST), PORT);
  if (result == 0) {
    print('Fehler beim Senden von Paket $seqNum');
  }
}

void main() async {
  final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
  final id = DateTime.now().millisecondsSinceEpoch % 65536;
  final fileBytes = await File(file).readAsBytes(); // File as bytes
  final maxSeqNum = (fileBytes.length + MAX_PACKET_SIZE - 1) ~/ MAX_PACKET_SIZE;
  final md5Hash = md5.convert(fileBytes).toString(); // MD5 hash of the file

  await sendFirstPacket(socket, id, maxSeqNum, file); // Send the first packet

  for (int seqNum = 1; seqNum <= maxSeqNum; seqNum++) {
    // Send the data packets
    final start = (seqNum - 1) * MAX_PACKET_SIZE;
    final end = min(seqNum * MAX_PACKET_SIZE, fileBytes.length);
    final data = fileBytes.sublist(start, end);
    await sendPacket(socket, id, seqNum, data);
    if (seqNum == 1) {
      print('erstes Datenpaket $seqNum erfolgreich gesendet');
    }
    if (seqNum == maxSeqNum) {
      print('letztes Datenpaket $seqNum erfolgreich gesendet');
    }
  }

  // Send the MD5 hash as the last packet
  final md5Packet = Uint8List.fromList(utf8.encode(md5Hash));
  await sendPacket(socket, id, maxSeqNum + 1, md5Packet);

  socket.close();
}
