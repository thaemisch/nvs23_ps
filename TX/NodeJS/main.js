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
let version = 3; // Versionsnummer
let sliding_window_n = 10; //
let fileSize, md5sum; // Variablen für die Dateigröße und den MD5-Hash

let sendStats = [0, 0]; // Statistiken über die gesendeten Pakete

// Entfernen der ersten beiden Argumente (node und main.js)
const args = process.argv.slice(2);

// Verarbeitung command line arguments
for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '--host':
    case '-h':
      let tmp = args[++i];
      if (tmp === undefined) {
        printHelp();
        return;
      }
      if(tmp.includes(':')) {
        HOST = tmp.split(':')[0];
        PORT = tmp.split(':')[1];
      } else {
        HOST = tmp;
      }
      break;
    case '--port':
    case '-p':
      PORT = args[++i];
      break;
    case '--max':
    case '-m':
      MAX_PACKET_SIZE = parseInt(args[++i]); //- 20 - 8;
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
    case '--version':
    case '-V':
      version = args[++i];
      break;
    case '--sliding-window':
    case '-n':
      sliding_window_n = args[++i];
      break;
    case '--help':
    case '-?':
      printHelp();
      return;
    default:
      console.log(`Invalid option: ${args[i]}`);
      return;
  }
}

if (quiet) {
  verbose = false; // to be sure
  console.log = function() {};
}

console.log(`Sending file "${FILE}" to ${HOST}:${PORT} with max packet size ${MAX_PACKET_SIZE}`);

// Erstellen des UDP-Sockets
const socket = dgram.createSocket('udp4');

// Senden der Datei
sendFile(FILE);


// -----------------------------------------------------------
// ----------------------- Funktionen -----------------------
// -----------------------------------------------------------

// Funktion zum senden des ersten Pakets
async function sendfirstPacket(id, maxSeqNum, fileName) {
  const buffer = Buffer.allocUnsafe(10 + fileName.length);  // Paketgröße = 16/8 + 32/8 + 32/8 + "packetinhalt" size
  //Buffer ist "Byteadresiert" 
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
function sendPacket(id , seqNum, data) {
  const buffer = Buffer.allocUnsafe(6); // Paketgröße = 16/8 + 32/8
  buffer.writeUInt16BE(id, 0);
  buffer.writeUInt32BE(seqNum, 2);

  socket.send([buffer, data], PORT, HOST, (err) => {
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
  buffer.write(md5, 6, 16, 'hex');
  socket.send(buffer, PORT, HOST, (err) => {
    if (err) {
      console.error(`Fehler beim Senden vom End Paket ${seqNum}: ${err}`);
      sendStats[1]++;
    } else {
      verboseLog(`Paket ${seqNum} (MD5) gesendet`);
      sendStats[0]++;
    }
  });
}


async function waitForAckPacket(transmissionId, sequenceNumber) {
  if(version == 1) {
    // no acks
    return;
  }
  if (version != 2) {
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
  /*if (version == 3) {
    // cumulative acks and sliding window with duplicate acks for packets in wrong order
    verboseLog(`Warte auf Bestätigung für Paket ${sequenceNumber}`);
    return new Promise((resolve, reject) => {
      function messageHandler(msg) {
        const receivedTransmissionId = msg.readUInt16BE(0);
        const receivedSequenceNumber = msg.readUInt32BE(2);
        if (receivedTransmissionId === transmissionId && receivedSequenceNumber === sequenceNumber) {
          socket.off('message', messageHandler);
          verboseLog(`Bestätigung für Paket ${sequenceNumber} erhalten`);
          resolve();
        }
        else if(receivedTransmissionId === transmissionId /* && receivedSequenceNumber < sequenceNumber*//*) {
          socket.off('message', messageHandler);
          verboseLog(`Bestätigung für Paket ${receivedSequenceNumber} erhalten aber ${sequenceNumber} erwartet`);
          reject(receivedSequenceNumber);
        }
      }

      socket.on('message', messageHandler);
    });
  }*/
}

function waitForGeneralAckPacket(transmissionId) {
  return new Promise((resolve) => {
    function messageHandler(msg) {
      const receivedTransmissionId = msg.readUInt16BE(0);
      const receivedSequenceNumber = msg.readUInt32BE(2);
      if (receivedTransmissionId === transmissionId) {
        socket.off('message', messageHandler);
        verboseLog(`ACK für ${receivedSequenceNumber} erhalten`);
        resolve(receivedSequenceNumber);
      }
    }

    socket.on('message', messageHandler);
  });
}

function sendNPackages(n, id, seqNum, maxSeqNum, data) {
  for (; n > 0; n--) {
    sendPacket(id , seqNum, data.subarray((seqNum-1)*(MAX_PACKET_SIZE-6), Math.min( seqNum*(MAX_PACKET_SIZE-6), fileSize)));
    seqNum++;
    if(seqNum == maxSeqNum){
      sendLastPacket(id, seqNum, md5sum);
      break;
    }
  }
  return seqNum;
}

// Funktion zum Senden der Datei
async function sendFile(filename) {

  //random id 0 bis 16^2-1
  const id = Math.floor(Math.random() * 65535);

  // Einlesen der Datei
  fileSize = fs.statSync(filename).size;
  const maxSeqNum = Math.ceil(fileSize / (MAX_PACKET_SIZE-6) + 1);
  const fileName = filename.split('/').pop().split('\\').pop();
  const data = fs.readFileSync(filename);
  md5sum = crypto.createHash('md5').update(data).digest('hex');

  // Senden des ersten Pakets
  await sendfirstPacket(id, maxSeqNum, fileName);
  if(version == 2)
    await waitForAckPacket(id, 0);

  // Senden der Datei
  if(version != 3) {
    //let ack =  waitForAckPacket(id);
    for (let seqNum = 1; seqNum < maxSeqNum; seqNum++) {
      sendPacket(id , seqNum, data.subarray((seqNum-1)*(MAX_PACKET_SIZE-6), Math.min( seqNum*(MAX_PACKET_SIZE-6), fileSize)));
      await waitForAckPacket(id, seqNum);
    }

    // Senden des letzten Pakets mit MD5-Hash
    sendLastPacket(id , maxSeqNum, md5sum);
    await waitForAckPacket(id, maxSeqNum);

  } else {
    // cumulative acks and sliding window with duplicate acks for packets in wrong order
    let ack;
    let listen = true;
    let possibleDupAck = new Set();
    function getPacket(){
      ack = waitForGeneralAckPacket(id).then((seqNum) => {
        if(listen)
          // keep listening for acks 
          getPacket();
        if (possibleDupAck.has(seqNum)) {
          possibleDupAck.delete(seqNum);
          // resend packet
          seqNum++;
          if(seqNum < maxSeqNum)
            sendPacket(id , seqNum, data.subarray((seqNum-1)*(MAX_PACKET_SIZE-6), Math.min( seqNum*(MAX_PACKET_SIZE-6), fileSize)));
          else
            sendLastPacket(id , seqNum, md5sum);
        } else 
          possibleDupAck.add(seqNum);
      });
    }
    // start listening for acks
    getPacket();

    let seqNum = sendNPackages(sliding_window_n-1, id, 1, maxSeqNum, data);
    verboseLog(`Sliding window wait: ${seqNum - 1}`);
    await waitForAckPacket(id, seqNum-1);
    while(seqNum < maxSeqNum) {
      seqNum = sendNPackages(sliding_window_n, id, seqNum, maxSeqNum, data);
      //waitForAckPacket(id, seqNum-1).catch((locseqNum) => {
      //  seqNum = locseqNum;
      //});
      verboseLog(`Sliding window wait: ${seqNum - 1}`);
      await waitForAckPacket(id, seqNum-1);
    }
  }

  socket.close();
  verboseLog('UDP-Socket geschlossen');
}

// Funktion zum Loggen von Nachrichten
function verboseLog(message) {
  if(verbose)
    console.log(message);
}

function printHelp() {
  console.log('Usage: node myApp.js [options]');
  console.log('Options:');
  console.log('  -h, --host, <host>      Host to send to (default: 127.0.0.1)');
  console.log('  -p, --port <port>       Port to send to (default: 12345)');
  console.log('  -m, --max <size>        Maximum packet size (default: 1472)');
  console.log('  -V, --version           TX Version to use (default: 3)');
  console.log('  -n, --sliding-window    Sliding Windows size (Only applicable if version = 3, default 10)')
  console.log('  -f, --file <filename>   File to send (default: test.txt)');
  console.log('  -q, --quiet             Suppress log output (overrides -v)');
  console.log('  -v, --verbose           Verbose log output');
  console.log('  -?, --help              Show this help'); 
  process.exit(0);
}