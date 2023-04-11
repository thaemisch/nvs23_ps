const dgram = require('dgram');
const fs = require('fs');
const crypto = require('crypto');

const PORT = 12345; // Port, auf dem die Daten übertragen werden sollen
const HOST = '127.0.0.1'; // IP-Adresse des Empfängers
const MAX_PACKET_SIZE = 1472; // Maximale Größe eines UDP-Pakets (mit IPv4) ist 65507 Byte, davon werden 20 Byte für den IP-Header und 8 Byte für den UDP-Header benötigt
const file = 'test.txt'; // Datei, die übertragen werden soll

// Funktion zum Senden eines Pakets
function sendPacket(socket, packet, seqNum) {
  packet['Sequence Number'] = seqNum;
  const packetData = JSON.stringify(packet);
  const buffer = Buffer.from(packetData);
  console.log(`Paket ${seqNum} wird gesendet: ${packetData}`);
  socket.send(buffer, 0, buffer.length, PORT, HOST, (err) => {
    if (err) {
      console.error(`Fehler beim Senden von Paket ${seqNum}: ${err}`);
    } else {
      console.log(`Paket ${seqNum} erfolgreich gesendet`);
    }
  });
}

// Funktion zum Senden der Datei
function sendFile(filename) {
  // Erste Sequenznummer für die Datenpakete
  let seqNum = 0;

  // Erstellen des ersten Pakets mit Dateiinformationen
  const fileSize = fs.statSync(filename).size;
  const maxSeqNum = Math.ceil(fileSize / MAX_PACKET_SIZE) + 1;
  const fileName = filename.split('/').pop();
  const infoPacket = {
    'Transmission ID': 1234,
    'Sequence Number': seqNum,
    'Max Sequence Number': maxSeqNum,
    'File Name': fileName
  };
  sendPacket(socket, infoPacket, seqNum);
  seqNum++;

  // Lesen und Übertragen der Dateidaten
  const fileStream = fs.createReadStream(filename, { highWaterMark: MAX_PACKET_SIZE });
  fileStream.on('data', (data) => {
    const dataPacket = {
      'Transmission ID': 1234,
      'Sequence Number': seqNum,
      'Data': data.toString('base64')
    };
    sendPacket(socket, dataPacket, seqNum);
    seqNum++;
  });

  // Senden des letzten Pakets mit der MD5-Prüfsumme
  fileStream.on('close', () => {
    const fileData = fs.readFileSync(filename);
    const md5sum = crypto.createHash('md5').update(fileData).digest('hex');
    const md5Packet = {
      'Transmission ID': 1234,
      'Sequence Number': seqNum,
      'MD5': md5sum
    };
    sendPacket(socket, md5Packet, seqNum);
    seqNum++;
    console.log('Datei erfolgreich übertragen');
    socket.close();
  });
}

// Erstellen des UDP-Sockets
const socket = dgram.createSocket('udp4');

// Senden der Datei
sendFile(file);
