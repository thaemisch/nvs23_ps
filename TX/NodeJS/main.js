const dgram = require('dgram');
const fs = require('fs');
const crypto = require('crypto');
let PORT = 12345; // Port, auf dem die Daten übertragen werden sollen
let HOST = '127.0.0.1'; // IP-Adresse des Empfängers
let MAX_PACKET_SIZE = 1500 - 20 - 8; // Maximale Größe eines UDP-Pakets is 65507 Byte, davon werden 20 Byte für den IP-Header und 8 Byte für den UDP-Header benötigt
// 1500 - 20 - 8 = 1472, damit es (hoffentlich) nicht fragmentiert wird/werden muss
let FILE = 'test.txt'; // Datei, die übertragen werden 
let quiet = false; // Flag, ob die Logausgabe unterdrückt werden soll
let sendStats = [0, 0]; // Statistiken über die gesendeten Pakete
let sb = ""; // "Stringbuilder" für die Logausgabe

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
    case '--help':
    case '-?':
      console.log('Usage: node myApp.js [options]');
      console.log('Options:');
      console.log('  -h, --host, <host>      Host to send to (default: 127.0.0.1)');
      console.log('  -p, --port <port>       Port to send to (default: 12345)');
      console.log('  -m, --max <size>        Maximum packet size (default: 1500)');
      console.log('  -f, --file <filename>   File to send (default: test.txt)');
      console.log('  -q, --quiet             Suppress log output (except start and final summary)');
      console.log('  -?, --help              Show this help'); 
      process.exit(0);
    default:
      console.log(`Invalid option: ${args[i]}`);
      break;
  }
}
console.log(`Sending file "${FILE}" to ${HOST}:${PORT} with max packet size ${MAX_PACKET_SIZE}`);

// Funktion zum Senden eines Pakets
function sendFirstPacket(id, maxSeqNum, fileName, length) {
  const buffer = Buffer.allocUnsafe(10 + length); // Paketgröße = 16/8 + 32/8 + 32/8 + "File Name" size
  //Buffer ist "Byteadresiert" 
  buffer.writeUInt16BE(id, 0);
  buffer.writeUInt32BE(0, 2);
  buffer.writeUInt32BE(maxSeqNum, 6);
  buffer.write(fileName, 10, length, 'utf-8');

  socket.send(buffer, 0, buffer.length, PORT, HOST, (err) => {
    if (err) {
      endLog(`Fehler beim Senden vom Initial Paket 0: ${err}`, true);
      sendStats[1]++;
    } else {
      endLog(`Paket 0 (init) erfolgreich gesendet`);
      sendStats[0]++;
    }
  });
}

function sendPacket(id , seqNum, data, length) {
    const buffer = Buffer.allocUnsafe(6 + length); // Paketgröße = 16/8 + 32/8 + "packetinhalt" size
    //Buffer ist "Byteadresiert" 
    buffer.writeUInt16BE(id, 0);
    buffer.writeUInt32BE(seqNum, 2);
    buffer.write(data, 6, length, 'base64');
  
    socket.send(buffer, 0, buffer.length, PORT, HOST, (err) => {
      if (err) {
        endLog(`Fehler beim Senden von Paket ${seqNum}: ${err}`, true);
        sendStats[1]++;
      } else {
        endLog(`Paket ${seqNum} erfolgreich gesendet`);
        sendStats[0]++;
      }
    });
  }

  async function sendLastPacket(id, seqNum, md5) {
    const buffer = Buffer.allocUnsafe(22); // Paketgröße = 16/8 + 32/8 + 128/8
    //Buffer ist "Byteadresiert" 
    buffer.writeUInt16BE(id, 0);
    buffer.writeUInt32BE(seqNum, 2);
    buffer.write(md5 , 6, 16, 'hex');
    await socket.send(buffer, 0, buffer.length, PORT, HOST, (err) => {
      if (err) {
        endLog(`Fehler beim Senden vom End Paket ${seqNum}: ${err}`, true);
        sendStats[1]++;
      } else {
        endLog(`Paket ${seqNum} (MD5) erfolgreich gesendet`);
        sendStats[0]++;
      }
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
  const fileName = filename.split('/').pop();
  sendFirstPacket(id, maxSeqNum, fileName, fileName.length);
  await waitForAckPacket(id, 0);
  seqNum++;

  // Lesen und Übertragen der Dateidaten
  const fileStream = fs.createReadStream(filename, { highWaterMark: MAX_PACKET_SIZE - 6});
  fileStream.on('data', async (data) => {
    sendPacket(id , seqNum, data.toString('base64'), data.length);
    await waitForAckPacket(id, seqNum);
    seqNum++;
  });

  // Senden des letzten Pakets mit der MD5-Prüfsumme
  fileStream.on('close', async () => {
    const fileData = fs.readFileSync(filename);
    const md5sum = crypto.createHash('md5').update(fileData).digest('hex');
    sendLastPacket(id , seqNum, md5sum);
    await waitForAckPacket(id, seqNum);
    socket.close();
    endLog('UDP-Socket geschlossen');
    if(!quiet)
      console.log(sb);
    console.log(`Datei gesendet in ${seqNum + 1} Paketen mit ${sendStats[0]} erfolgreichen und ${sendStats[1]} fehlgeschlagenen Paketen`);
  });
}

async function waitForAckPacket(transmissionId, sequenceNumber) {
  return new Promise((resolve) => {
    function messageHandler(msg) {
      const receivedTransmissionId = msg.readUInt16BE(0);
      const receivedSequenceNumber = msg.readUInt32BE(2);
      if (receivedTransmissionId === transmissionId && receivedSequenceNumber === sequenceNumber) {
        socket.off('message', messageHandler);
        resolve();
      }
    }

    socket.on('message', messageHandler);
  });
}


// Funktion zum Loggen von Nachrichten
function endLog(message, error = false) {
  if(!quiet)
    sb += (`${message}\n`);
}

// Erstellen des UDP-Sockets
const socket = dgram.createSocket('udp4');

// Senden der Datei
sendFile(FILE);


//Man könnte auf das sendPacket in eine Funktion in die richtung:
/*function sendPacket(packet, seqNum) {
    const buffer = Buffer.allocUnsafe(6 +); // Paketgröße = 16/8 + 32/8 + "packetinhalt"
    //Buffer ist "Byteadresiert" 
    buffer.writeUInt16BE(packet['Transmission ID'], 0);
    buffer.writeUInt32BE(seqNum, 2);
    buffer.writeUInt32BE(packet['Max Sequence Number'] || 0, 6);
    console.log(buffer);
    buffer.write(packet['File Name'] || '', 10, 2048, 'utf-8');
    buffer.write(packet['MD5'] || '', 2058, 128, 'hex');
    buffer.write(packet['Data'] || '', 2186, 1396, 'base64');
  
    socket.send(buffer, 0, buffer.length, PORT, HOST, (err) => {
      if (err) {
        console.error(`Fehler beim Senden von Paket ${seqNum}: ${err}`);
      } else {
        console.log(`Paket ${seqNum} erfolgreich gesendet`);
      }
    });
  }*/
// machen aber mir wurde dann dass alloc berechnen zu kompliziert.
