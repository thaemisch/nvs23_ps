import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.math.BigInteger;
import java.net.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;

public class UDPReceiver {
    // constants / defaults
    private static final int BUFFER_SIZE = 1472;
    private static final int PORT = 12345;
    private static final String HOST = "127.0.0.1";
    private static final int PACKET_TIMEOUT = 1000;
    private static final int DUP_ACK_DELAY = 0;

    private static final int WINDOW_SIZE = 10;

    private enum Version {
        VERSION_ONE,
        VERSION_TWO,
        VERSION_THREE
    }

    private static boolean verbose = false; // detailed logging
    private static boolean quiet = false; // no output

    public static void main(String[] args) {
        // set defaults
        String host = HOST;
        int bufferSize = BUFFER_SIZE;
        int port = PORT;
        Version userVersionChoice = Version.VERSION_THREE;
        int dupAckDelay = DUP_ACK_DELAY;
        int slidingWindowSize = WINDOW_SIZE;
        int receiveTimeOut = PACKET_TIMEOUT;
        boolean throwAway = false;

        // run arguments
        if (args.length > 0) {
            // Parse the arguments and set the variables accordingly
            for (int i = 0; i < args.length; i++) {
                String arg = args[i];
                switch (arg) {
                    case "--host":
                    case "-h":
                        host = args[i + 1];
                        i++;
                        break;
                    case "--port":
                    case "-p":
                        port = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "--max":
                    case "-m":
                        bufferSize = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "--quiet":
                    case "-q":
                        quiet = true;
                        if (verbose) {
                            verbose = false;
                        }
                        break;
                    case "--verbose":
                    case "-v":
                        if (!quiet) {
                            verbose = true;
                        }
                        break;
                    case "-V":
                    case "--version":
                        if ("2".equals(args[i + 1])) {
                            userVersionChoice = Version.VERSION_TWO;
                        } else if ("1".equals(args[i + 1])) {
                            userVersionChoice = Version.VERSION_ONE;
                        }
                        i++;
                        break;
                    case "-n":
                    case "--sliding-window":
                        userVersionChoice = Version.VERSION_THREE;
                        slidingWindowSize = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "-t":
                    case "--timeout":
                        receiveTimeOut = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "-d":
                    case "--dup-ack-delay":
                        dupAckDelay = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "--windows":
                        dupAckDelay = Integer.parseInt(args[i + 1]);
                        i++;
                        receiveTimeOut = Integer.parseInt(args[i + 1]);
                        i++;
                        break;
                    case "--throwaway":
                        throwAway = true;
                        break;
                    case "--help":
                    case "-?":
                        printHelp();
                        System.exit(0);
                    default:
                        System.err.println("Unknown argument: " + arg);
                        System.out.println("Following arguments supported");
                        printHelp();
                        System.exit(1);
                }
            }
        }

        try {
            log("Receiver started with host=" + host + ", port=" + port + ", version=" + userVersionChoice
                    + " and buffer-size=" + bufferSize, false);
            if (userVersionChoice == Version.VERSION_THREE) {
                log("window-size=" + slidingWindowSize, false);
            }
            run(host, port, bufferSize, slidingWindowSize, userVersionChoice, throwAway, receiveTimeOut, dupAckDelay);
        } catch (IOException | NoSuchAlgorithmException | InterruptedException e) {
            e.printStackTrace();
        }
    }

    private static void printHelp() {
        System.out.println("Options:");
        System.out.println("-h, --host <host>                           Host to receive from (default: 127.0.0.1)");
        System.out.println("-p, --port <port>                           Port (default: 12345)");
        System.out.println("-m, --max <size>                            Maximum packet size (default: 1472)");
        System.out.println("-q, --quiet                                 Suppress log output (overrides -v)");
        System.out.println("-v, --verbose                               Verbose log output");
        System.out.println("-V, --version <version>                     Version of the protocol (default: 3)");
        System.out.println("-n, --sliding-window <window-size>          Window site (default: 10)");
        System.out.println("--throwaway                                 Throw away some packets on purpose (testing)");
        System.out.println("-t, --timeout <timeout [ms]>                Timeout for packets [ms] (default: 1000 ms)");
        System.out.println(
                "-w, --windows <delay [ms]> <timeout [ms]>   DupAck delay [ms] and timeout for packets [ms] (default: 0 ms and 1000 ms)");
        System.out.println("-d, --dup-ack-delay <delay [ms]>            Delay between DupAck [ms] (default: 0 ms)");
        System.out.println("-?, --help                                  Show this help");
    }

    public static void run(String host, int port, int bufferSize, int slidingWindowSize, Version userVersionChoice,
            boolean throwaway,
            int timeout, int dupAckDelay) throws IOException, InterruptedException, NoSuchAlgorithmException {
        InetAddress IP = InetAddress.getByName(host);
        DatagramSocket socket = new DatagramSocket(port, IP);
        byte[] buf = new byte[bufferSize];

        // transmission/packet variables
        short transmissionID = -3;
        int seqNr = -1;
        int maxSeqNr = -2;
        String fileName = "";
        String MD5Sum;

        boolean throwAwayPacket = false;
        int nextWindow = slidingWindowSize;
        TreeMap<Integer, byte[]> windowPackets = new TreeMap<>();
        boolean[] packetReceivedLog = new boolean[slidingWindowSize];
        int dupAckCounter = 0;
        int receivedPackets = 0;
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ByteBuffer receiverBuffer;
        DatagramPacket packet = new DatagramPacket(buf, buf.length, IP, port);

        Arrays.fill(packetReceivedLog, false);
        log("Receiver listening", false);
        try {
            socket.receive(packet);
            receivedPackets++;
        } catch (IOException e) {
            e.printStackTrace();
        }
        receiverBuffer = ByteBuffer.wrap(packet.getData());
        transmissionID = receiverBuffer.getShort();
        seqNr = receiverBuffer.getInt();

        while (seqNr != maxSeqNr) {
            if (throwaway && (seqNr == 3 || seqNr == 66 || seqNr == 70 || seqNr == 450)) {
                throwAwayPacket = true;
            }
            if (!throwAwayPacket) {
                verboseLog("Packet " + seqNr + " received");
                if (seqNr == 0) {
                    if (userVersionChoice == Version.VERSION_THREE) {
                        socket.setSoTimeout(timeout);
                    }
                    maxSeqNr = receiverBuffer.getInt(); // get max. sequence number to know when to stop
                    try {
                        fileName = new String(receiverBuffer.array(), 10, 11, StandardCharsets.UTF_8); // extract file
                                                                                                       // name
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                    receivedPackets++;
                    if (userVersionChoice != Version.VERSION_ONE)
                        sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
                } else {
                    byte[] dataArray = new byte[packet.getLength() - receiverBuffer.position()]; // data byte array of
                                                                                                 // packet size minus
                                                                                                 // current position of
                                                                                                 // ByteBuffer (will 6
                                                                                                 // Bytes)
                    receiverBuffer.get(dataArray); // get data

                    if (userVersionChoice == Version.VERSION_THREE) {
                        windowPackets.put(seqNr, dataArray);
                        packetReceivedLog[(seqNr - 1) % slidingWindowSize] = true;
                        if (seqNr == nextWindow) {
                            for (int i = 0; i < packetReceivedLog.length; i++) {
                                if (!packetReceivedLog[i]) {
                                    sendDupAckAndReceivePacket(nextWindow - (slidingWindowSize - i), transmissionID,
                                            socket, packet, dupAckDelay, windowPackets);
                                    dupAckCounter++;
                                    receivedPackets++;
                                }
                            }
                            Arrays.fill(packetReceivedLog, false);
                            while (!windowPackets.isEmpty()) {
                                Map.Entry<Integer, byte[]> tmpEntry = windowPackets.pollFirstEntry();
                                outputStream.write(tmpEntry.getValue());
                            }
                            sendACKPacket(nextWindow, transmissionID, socket, packet.getPort(), packet.getAddress());
                            nextWindow += slidingWindowSize;
                        }
                    } else {
                        outputStream.write(dataArray); // write data to output-stream
                    }
                    if (userVersionChoice == Version.VERSION_TWO) {
                        sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
                    }
                }
            }
            throwAwayPacket = false;
            try {
                socket.receive(packet);
                receivedPackets++;
                receiverBuffer = ByteBuffer.wrap(packet.getData());
                short tempTransmissionID = receiverBuffer.getShort();
                if (tempTransmissionID != transmissionID) {
                    throwAwayPacket = true;
                }
                seqNr = receiverBuffer.getInt();
            } catch (SocketTimeoutException e) {
                for (int i = 0; i < packetReceivedLog.length; i++) {
                    if (!packetReceivedLog[i]) {
                        sendDupAckAndReceivePacket(nextWindow - (slidingWindowSize - i), transmissionID, socket, packet,
                                dupAckDelay, windowPackets);
                        dupAckCounter++;
                        receivedPackets++;
                    }
                }
                if (seqNr == nextWindow) {
                    Arrays.fill(packetReceivedLog, false);
                    while (!windowPackets.isEmpty()) {
                        Map.Entry<Integer, byte[]> tmpEntry = windowPackets.pollFirstEntry();
                        outputStream.write(tmpEntry.getValue());
                    }
                    nextWindow += slidingWindowSize;
                    sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
                }

            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        if (seqNr == maxSeqNr) {
            verboseLog("Packet " + seqNr + " received");
            if (userVersionChoice == Version.VERSION_THREE) {
                for (int i = 0; i < windowPackets.size(); i++) {
                    if (!packetReceivedLog[i]) {
                        sendDupAckAndReceivePacket(nextWindow - (slidingWindowSize - i), transmissionID, socket, packet,
                                dupAckDelay, windowPackets);
                        dupAckCounter++;
                        receivedPackets++;
                    }
                }
                while (!windowPackets.isEmpty()) {
                    Map.Entry<Integer, byte[]> tmpEntry = windowPackets.pollFirstEntry();
                    outputStream.write(tmpEntry.getValue());
                }
            }
            byte[] MD5Array = new byte[16];
            receiverBuffer = receiverBuffer.get(MD5Array); // get MD5 hash and save in byte array
            MD5Sum = bytesToHex(MD5Array); // convert to hex-number as String

            outputStream.close(); // now the output-stream can be closed
            if (userVersionChoice != Version.VERSION_ONE) {
                sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
            }
            writeToFile(outputStream, fileName); // write data to file (data is written to file after the transmission
                                                 // is complete)
            verboseLog("");

            if (checkMD5Sum(fileName, MD5Sum)) { // check the MD5 hash
                log("MD5 Checksums are equal.", false);
            } else {
                log("MD5 Checksums are different! Files might not be the same.", true);
            }
            log(" ", false);
            log("Statistics:", false);
            log("\t" + receivedPackets + " packets received", false);
            log("\tDupACKs = " + dupAckCounter, false);
        }
    }

    private static void sendACKPacket(int seqNr, short transmissionID, DatagramSocket socket, int port,
            InetAddress transmitterAddress) {
        try {
            ByteBuffer messageBuffer = ByteBuffer.allocate(6);
            messageBuffer.putShort(transmissionID);
            messageBuffer.putInt(seqNr);

            DatagramPacket packet = new DatagramPacket(messageBuffer.array(), messageBuffer.array().length,
                    transmitterAddress, port);

            socket.send(packet);
            verboseLog("ACK for packet " + seqNr + " sent");

        } catch (Exception e) {
            System.err.println(e);
        }
    }

    private static void sendDupAckAndReceivePacket(int seqNr, short transmissionID, DatagramSocket socket,
            DatagramPacket packet,
            int dupAckDelay, TreeMap<Integer, byte[]> windowPackets) throws InterruptedException, IOException {
        sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
        Thread.sleep(dupAckDelay);
        sendACKPacket(seqNr, transmissionID, socket, packet.getPort(), packet.getAddress());
        socket.receive(packet);
        ByteBuffer receiverBuffer = ByteBuffer.wrap(packet.getData());
        transmissionID = receiverBuffer.getShort();
        seqNr = receiverBuffer.getInt();
        verboseLog("Packet " + seqNr + " received");
        byte[] dataArray = new byte[packet.getLength() - receiverBuffer.position()];
        receiverBuffer.get(dataArray);
        windowPackets.put(seqNr, dataArray);
    }

    private static String bytesToHex(byte[] bytes) {
        return new BigInteger(1, bytes).toString(16);
    }

    /**
     * writes output-stream to file.
     *
     * @throws IOException
     */
    private static void writeToFile(ByteArrayOutputStream outputStream, String fileName) throws IOException {
        FileOutputStream out = new FileOutputStream(fileName.trim(), false);
        out.write(outputStream.toByteArray());
        out.close();
    }

    /**
     * creates MD5-sum of transmitted file and compares both.
     *
     * @return true if they are equal
     * @return false otherwise
     * @throws IOException
     * @throws NoSuchAlgorithmException
     */
    private static boolean checkMD5Sum(String fileName, String MD5Hash) throws IOException, NoSuchAlgorithmException {
        byte[] data = Files.readAllBytes(Paths.get(fileName.trim()));
        byte[] hash = MessageDigest.getInstance("MD5").digest(data);
        String checksum = new BigInteger(1, hash).toString(16);
        return checksum.equals(MD5Hash);
    }

    private static void verboseLog(String text) {
        if (verbose) {
            System.out.println(text);
        }
    }

    private static void log(String text, boolean error) {
        if (!quiet) {
            if (error)
                System.err.println(text);
            else
                System.out.println(text);
        }
    }
}