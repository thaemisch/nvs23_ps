const dgram = require('dgram');
const fs = require('fs');
const crypto = require('crypto');

let PORT = 12345; // Port, auf dem die Daten übertragen werden sollen
let HOST = '127.0.0.1'; // IP-Adresse des Empfängers
let MAX_PACKET_SIZE = 1500 - 20 - 8; // Maximale Größe eines UDP-Pakets is 65507 Byte, davon werden 20 Byte für den IP-Header und 8 Byte für den UDP-Header benötigt
// 1500 - 20 - 8 = 1472, damit es (hoffentlich) nicht fragmentiert wird/werden muss
let FILE = 'test.txt'; // Datei, die übertragen werden 
let quiet = false; // Flag, ob die Logausgabe unterdrückt werden soll
let verbose = false; // Flag, ob die Logausgabe erweitert werden soll
let sendStats = [0, 0]; // Statistiken über die gesendeten Pakete

// Entfernen der ersten beiden Argumente (node und main.js)
const args = process.argv.slice(2);

// Verarbeitung command line arguments
for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '--host':
    case '-h':
      HOST = args[++i];
      break;
    case '--port':
    case '-p':
      PORT = args[++i];
      break;
    case '--max':
    case '-m':
      MAX_PACKET_SIZE = args[++i] - 20 - 8;
      break;
    case '--file':
    case '-f':
      FILE = args[++i];
      break;
    case '--quiet':
    case '-q':
      quiet = true;
      break;
    case '--verbose':
    case '-v':
      verbose = true;
      break;
    case '--help':
    case '-?':
      console.log('Usage: node myApp.js [options]');
      console.log('Options:');
      console.log('  -h, --host, <host>      Host to send to (default: 127.0.0.1)');
      console.log('  -p, --port <port>       Port to send to (default: 12345)');
      console.log('  -m, --max <size>        Maximum packet size (default: 1500)');
      console.log('  -f, --file <filename>   File to send (default: test.txt)');
      console.log('  -q, --quiet             Suppress log output');
      console.log('  -v, --verbose           Verbose log output');
      console.log('  -?, --help              Show this help'); 
      process.exit(0);
    default:
      console.log(`Invalid option: ${args[i]}`);
      break;
  }
}

if (quiet) {
  verbose = false; // to be sure
  console.log = function() {};
}

console.log(`Sending file "${FILE}" to ${HOST}:${PORT} with max packet size ${MAX_PACKET_SIZE}`);

// Erstellen des UDP-Sockets
const socket = dgram.createSocket('udp4');

// einrichten des Sockets
/*socket.connect(PORT, HOST, (err) => {
  if (err) {
    console.log(`Fehler beim Verbinden mit ${HOST}:${PORT}: ${err}`, true);
    process.exit(1);
  }
  else{
    console.log(`Verbunden mit ${HOST}:${PORT}`);
    socket.setSendBufferSize(MAX_PACKET_SIZE);
    socket.setRecvBufferSize(6); // mehr brauchen wir für ACKs nicht
  }
});*/


// Senden der Datei
sendFile(FILE);


// -----------------------------------------------------------
// ----------------------- Funktionen -----------------------
// -----------------------------------------------------------

// Funktion zum senden des ersten Pakets
async function sendfirstPacket(id, maxSeqNum, fileName) {
  const buffer = Buffer.allocUnsafe(10 + fileName.length);
  buffer.writeUInt16BE(id, 0);
  buffer.writeUInt32BE(0, 2);
  buffer.writeUInt32BE(maxSeqNum, 6);
  buffer.write(fileName, 10, fileName.length, 'utf-8');

  return socket.send(buffer, PORT, HOST, (err) => {
    if (err) {
      console.error(`Fehler beim Senden des ersten Pakets: ${err}`);
      sendStats[1]++;
    } else {
      verboseLog(`Erstes Paket gesendet`);
      socket.setSendBufferSize(MAX_PACKET_SIZE);
      socket.setRecvBufferSize(6); // mehr brauchen wir für ACKs nicht
      sendStats[0]++;
    }
  });
}

// Funktion zum senden eines Pakets
async function sendPacket(id , seqNum, data) {
  const buffer = Buffer.allocUnsafe(6); // Paketgröße = 16/8 + 32/8 + "packetinhalt" size
  //Buffer ist "Byteadresiert" 
  buffer.writeUInt16BE(id, 0);
  buffer.writeUInt32BE(seqNum, 2);

  return socket.send([buffer, data], PORT, HOST, (err) => {
    if (err) {
      console.error(`Fehler beim Senden von Paket ${seqNum}: ${err}`);
      sendStats[1]++;
    } else {
      verboseLog(`Paket ${seqNum} gesendet`);
      sendStats[0]++;
    }
  });
}

// Funktion zum senden des letzten Pakets
function sendLastPacket(id, seqNum, md5) {
  const buffer = Buffer.allocUnsafe(22); // Paketgröße = 16/8 + 32/8 + 128/8
  //Buffer ist "Byteadresiert" 
  buffer.writeUInt16BE(id, 0);
  buffer.writeUInt32BE(seqNum, 2);
  buffer.write(md5 , 6, 16, 'hex');
  socket.send(buffer, PORT, HOST, (err) => {
    if (err) {
      endLog(`Fehler beim Senden vom End Paket ${seqNum}: ${err}`, true);
      sendStats[1]++;
    } else {
      endLog(`Paket ${seqNum} (MD5) gesendet`);
      sendStats[0]++;
      socket.close();
      verboseLog('UDP-Socket geschlossen');
    }
  });
}


async function waitForAckPacket(transmissionId, sequenceNumber) {
  verboseLog(`Warte auf Bestätigung für Paket ${sequenceNumber}`);
  return new Promise((resolve) => {
    function messageHandler(msg) {
      const receivedTransmissionId = msg.readUInt16BE(0);
      const receivedSequenceNumber = msg.readUInt32BE(2);
      if (receivedTransmissionId === transmissionId && receivedSequenceNumber === sequenceNumber) {
        socket.off('message', messageHandler);
        verboseLog(`Bestätigung für Paket ${sequenceNumber} erhalten`);
        resolve();
      }
    }

    socket.on('message', messageHandler);
  });
}

// Funktion zum Senden der Datei
async function sendFile(filename) {
  // Erste Sequenznummer für die Datenpakete
  let seqNum = 0;

  //random id 0 bis 16^2-1
  const id = Math.floor(Math.random() * 65535);

  // Erstellen des ersten Pakets mit Dateiinformationen
  const fileSize = fs.statSync(filename).size;
  const maxSeqNum = Math.ceil(fileSize / MAX_PACKET_SIZE);
  const fileName = filename.split('/').pop().split('\\').pop();
  await sendfirstPacket(id, maxSeqNum, fileName);
  let promise = waitForAckPacket(id, 0);
  seqNum++;

  // Lesen und Übertragen der Dateidaten
  const fileStream = fs.createReadStream(filename, { highWaterMark: MAX_PACKET_SIZE - 6});
  fileStream.on('data', async (data) => {
    await promise;
    sendPacket(id , seqNum, data);
    promise = waitForAckPacket(id, seqNum);
    seqNum++;
  });

  // Senden des letzten Pakets mit der MD5-Prüfsumme
  fileStream.on('close', () => {
    const fileData = fs.readFileSync(filename);
    const md5sum = crypto.createHash('md5').update(fileData).digest('hex');
    sendLastPacket(id , seqNum, md5sum);
    console.log(`Datei gesendet in ${seqNum + 1} Paketen mit ${sendStats[0]} erfolgreichen und ${sendStats[1]} fehlgeschlagenen Paketen`);
  });
}

// Funktion zum Loggen von Nachrichten
function verboseLog(message) {
  if(verbose)
    console.log(message);
}
