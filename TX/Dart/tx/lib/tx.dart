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

late final RawDatagramSocket socket;
late final Stream<RawSocketEvent> stream;
late final int id;
late final Uint8List fileBytes;
late final int maxSeqNum;
late final Uint8List md5Hash;
late final int slidingWindow;
late final int version;
late final bool quiet;
bool send = true;


Future<void> sendFirstPacket(int maxSeqNum,
    String fileName) async {
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
  if (version > 1){
    try {
      await waitForAck(0).timeout(Duration(seconds: 2));
    } catch (e) {
      return sendFirstPacket(maxSeqNum, fileName);
    }
  }
}

Future<void> sendPacket(int seqNum,
    Uint8List data,
    {bool md5 = false}) async {
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
    if (version == 2) await waitForAck(seqNum);
  }
}

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

bool _processAckPacket(Uint8List data, int seqNr) {
  final transmissionId = data.buffer.asByteData().getUint16(0);
  final sequenceNumber = data.buffer.asByteData().getUint32(2);
  if (version == 3) {
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
  parser.addOption('version', abbr: 'v', defaultsTo: '3');
  parser.addOption('sliding-window',abbr: 's',defaultsTo: '10' );
  parser.addFlag('quiet', abbr: 'q', defaultsTo: false);
  var results = parser.parse(args);
  HOST = results['host'] as String;
  PORT = int.parse(results['port'] as String);
  MAX_PACKET_SIZE = int.parse(results['max'] as String);
  file = (results['file'] as String).replaceAll('\\', '/');
  version = int.parse(results['version'] as String);
  quiet = results['quiet'] as bool;
  slidingWindow = int.parse(results['sliding-window'] as String);

  // ------------------- initialize Variables -------------------
  socket =
      await RawDatagramSocket.bind(InternetAddress(HOST), 0 /*PORT*/);
  stream = socket.asBroadcastStream();
  id = Random().nextInt(65535); // Random transmission ID (0-65535)
  fileBytes = await File(file).readAsBytes(); // File as bytes
  maxSeqNum = (fileBytes.length / (MAX_PACKET_SIZE - 6)).ceil() + 1;
  md5Hash = md5.convert(fileBytes).bytes as Uint8List; // MD5 hash of the file
  RegExpMatch? fileameForPrint = RegExp(r"(?<=/)[^/]*$").firstMatch(file
      .replaceAll("\\\\", "/")
      .replaceAll("\\", "/")); // Filename after last slash
  file = fileameForPrint != null
      ? file.substring(fileameForPrint.start, fileameForPrint.end)
      : file;

  // ------------------ Send the file ------------------
  printiffalse(
      '\n-------------------------- Sending file: $file with Transmission ID: $id --------------------------\n',
      quiet);

  await sendFirstPacket(maxSeqNum, file); // Send the first packet

  await sendFile(); // Send the file

  if(version != 3) {
    await sendLastPacket(); // Send the last packet
  }
  printiffalse(
      '-------------------------- File sent --------------------------\n',
      quiet);

  socket.close();

}

Future<void> sendLastPacket() async {
  // Send the MD5 hash as the last packet
  final lastPacket = Uint8List.fromList(md5Hash);
  await sendPacket(maxSeqNum, lastPacket);
}

Future<int> sendNPackages(int seqNum, int maxSeqNum,
    Uint8List data,
    {bool quiet = false}) async {
  int n = slidingWindow;
  while (n > 0) {
    if(!send) {
      continue;
    }
    final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
    final end = min(seqNum * (MAX_PACKET_SIZE - 6), data.length);
    final packetData = data.sublist(start, end);
    await sendPacket(seqNum, packetData);
    seqNum++;
    n--;
    if (seqNum == maxSeqNum) {
      break;
    }

  }
  return seqNum;
}

Future<void> sendFile() async{
  if (version < 3) {
    for (int seqNum = 1; seqNum < maxSeqNum; seqNum++) {
      // Send the data packets
      final start = (seqNum - 1) * (MAX_PACKET_SIZE - 6);
      final end = min(seqNum * (MAX_PACKET_SIZE - 6), fileBytes.length);
      final data = fileBytes.sublist(start, end);
      await sendPacket(seqNum, data);
    }
  } else {

    int seqNum = 1;
    Set<int> possibleDupAck = {};

    Future<void> getPacket(
        int maxSeqNum,
        Uint8List fileBytes
        ) async {
      await for (var event in stream) {
        if (event == RawSocketEvent.read) {
          Datagram? datagram = socket.receive();
          if (datagram != null &&  datagram.data.length == 6) {
            final int transmissionId = datagram.data.buffer.asByteData().getUint16(0);
            final int seqNr = datagram.data.buffer.asByteData().getUint32(2);
            if(transmissionId != id) {
              continue;
            }
            if (possibleDupAck.contains(seqNr)) {
              send = false;
              printiffalse('Received DupAck: $seqNr', quiet);
              possibleDupAck.remove(seqNr);

              // Resend packet
              int value = seqNr + 1;
              if (value < maxSeqNum) {
                final start = (value - 1) * (MAX_PACKET_SIZE - 6);
                final end = min(value * (MAX_PACKET_SIZE - 6), fileBytes.length);
                await sendPacket(value, fileBytes.sublist(start, end));
              }
              else {
                // Send the MD5 hash as the last packet again
                final md5Packet = Uint8List.fromList(md5Hash);
                await sendPacket(maxSeqNum, md5Packet,
                    md5: true);
              }
              send = true;
            } else {
              printiffalse('Received Ack: $seqNr', quiet);
              possibleDupAck.add(seqNr);
            }
          }
        }
      }
    }

    // Start listening for acks
    getPacket(maxSeqNum, fileBytes);

    while (seqNum < maxSeqNum) {
      printiffalse('Sliding window send: $seqNum', quiet);
      seqNum = await sendNPackages(
          seqNum,
          maxSeqNum,
          fileBytes, quiet: quiet);
      printiffalse('Sliding window wait: ${seqNum - 1}', quiet);
      if(seqNum != maxSeqNum) {
        while(!possibleDupAck.contains(seqNum - 1)) {
          await Future.delayed(Duration(milliseconds: 1));
        }
      }
      else {
        sendLastPacket();
      }
    }
  }
}