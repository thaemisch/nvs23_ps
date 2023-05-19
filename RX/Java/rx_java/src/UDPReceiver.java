import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.math.BigInteger;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Timestamp;

public class UDPReceiver{

    // adjust according to TX
    private static final int BUFFER_SIZE = 1472;
    private static final int PORT = 12345;
    private static final String HOST = "127.0.0.1";

    public static void main(String[] args) throws SocketException, UnknownHostException{
        String host = HOST;
        int bufferSize = BUFFER_SIZE;
        int port = PORT;
        if (args.length > 0) {
            // Parse the arguments and set the variables accordingly
            for (int i = 0; i < args.length; i += 2) {
                String arg = args[i];
                String value = args[i+1];
                switch (arg) {
                    case "--host", "-h":
                        host = value;
                        break;
                    case "--port", "-p":
                        port = Integer.parseInt(value);
                        break;
                    case "--max", "-m":
                        bufferSize = Integer.parseInt(value);
                        break;
                    case "--quiet", "-q":
                        quiet = true;
                        break;
                    case "--help", "-?":
                        System.out.println("Options:");
                        System.out.println("--host <host>       Host to send to (default: 127.0.0.1)");
                        System.out.println("--port <port>       Port to send to (default: 12345)");
                        System.out.println("--max <size>        Maximum packet size (default: 1472)");
                        System.out.println("--help              Show this help");
                        System.exit(1);
                    default:
                        System.err.println("Unknown argument: " + arg);
                        System.exit(1);
                }
            }
        }
        UDPReceiver.run(host, port, bufferSize);
    }

    // packet variables
    private static short transmissionID;
    private static int maxSeqNr;
    private static String fileName = null;
    private static String MD5Hash;

    private static DatagramSocket socket;
    private static InetAddress IP;
    private static int receivedPackets = 0; // counter for received packets
    private static Timestamp startTime; // to save start time (first packet received)
    private static Timestamp endTime;   // to save end time (last packet received)
    private static ByteArrayOutputStream outputStream = new ByteArrayOutputStream();    // to write packet data to stream
    private static ByteBuffer receiverBuffer;   // simplifies extraction of header and data part in packet (byte array with lots of bitwise shifts could be used as well)
    private static boolean quiet = false;

    /**
    * This method contains a loop that terminates once the last packet is received.
    * @throws UnknownHostException if IP-address is unknown
    * @throws SocketException if there is an error creating socket object
    */
    public static void run(String host, int port, int bufferSize) throws UnknownHostException, SocketException {
        IP = InetAddress.getByName(host);
        socket = new DatagramSocket(port, IP);
        boolean done = false;
        byte[] buf = new byte[bufferSize]; // BUFFER_SIZE = data-size + 6Byte (Header)
        DatagramPacket packet = new DatagramPacket(buf, buf.length, IP, port);
        
        System.out.println("Receiver listening (IP: " + IP.getHostAddress() + ", port: " + port + "buffer size" + bufferSize + ")...");
        
        // loop runs until done == false which means the last packet was received (see interpretPacket())
        while (!done) {
            try {
                try {
                    socket.receive(packet);
                } catch (IOException e) {
                    e.printStackTrace();
                }
                done = interpretPacket(packet);
            } catch (UnsupportedEncodingException e) {
                e.printStackTrace();
            } catch (IOException e) {
                e.printStackTrace();
            } catch (NoSuchAlgorithmException e) {
                e.printStackTrace();
            }
        }
        socket.close();
    }

    /**
    * This method interprets a packet.
    * @throws IOException 
    * @throws NoSuchAlgorithmException 
    * @return true if last packet is received
    * @return false if last transmission is still ongoing (last packet not received yet)
    */
    private static boolean interpretPacket(DatagramPacket packet) throws IOException, NoSuchAlgorithmException{
        receiverBuffer = ByteBuffer.wrap(packet.getData());
        int seqNr = -1;
        short receivedTransmissionID = receiverBuffer.getShort(); // get 2 Byte (short) transmission ID
        if(receivedPackets > 0 && receivedTransmissionID != transmissionID){
            return false;
        }
        transmissionID = receivedTransmissionID;
        seqNr = receiverBuffer.getInt();    // get 4 Byte (Integer) sequence number 

        if (seqNr == 0) { // first packet (containing maximum sequence number and file name)
            startTime = new Timestamp(System.currentTimeMillis());  // set start time stamp

            maxSeqNr = receiverBuffer.getInt(); // get max. sequence number to know when to stop
            try{
                fileName = new String(receiverBuffer.array(), 10, 11, "UTF8");  // extract file name
            } catch (Exception e){  // could result in Exception if charsetName is unknown to Java-String
                e.printStackTrace();
            }
            log("Packet " + seqNr + " received");
        } else if (seqNr == maxSeqNr) { // last packet (containing MD5 Checksum)
            byte[] MD5Array = new byte[16];
            receiverBuffer = receiverBuffer.get(MD5Array);  // get MD5 hash and save in byte array
            MD5Hash = bytesToHex(MD5Array); // convert to hex-number as String
            
            outputStream.close();   // now the output-stream can be closed 
            log("Packet " + seqNr + " received");
            sendACKPacket(seqNr, packet.getPort(), packet.getAddress());
            writeToFile();  // write data to file (data is written to file after the transmission is complete)
            endTime = new Timestamp(System.currentTimeMillis());
            log("");

            if (checkMD5Sum()) {    // check the MD5 hash
                System.out.println("MD5 Checksums are equal.");
            } else {
                System.err.println("MD5 Checksums are different! Files might not be the same.");
            }
            System.out.println();
            System.out.println("Statistics:");
            System.out.println("\t" + receivedPackets + " packets received");
            System.out.println("\t" + (endTime.getTime() - startTime.getTime()) + "ms time");
            //end of transmission
            return true;
        } else {
            // normal data packet (containing only data)
            byte[] dataArray = new byte[packet.getLength() - receiverBuffer.position()];    // data byte array of packet size minus current position of ByteBuffer (will 6 Bytes)
            receiverBuffer.get(dataArray);  // get data
            log("Packet " + seqNr + " received");
            outputStream.write(dataArray);  // write data to output-stream
        }
        receivedPackets++;
        sendACKPacket(seqNr, packet.getPort(), packet.getAddress());
        return false;
    }

    private static void log(String text){
        if (!quiet){
            System.out.println(text);
        }
    }

    /**
    * Sends an ACK-packet to Transmitter after receiving a packet
    * @param seqNr 
    * @param port
    * @param transmitterAddress
    */
    private static void sendACKPacket(int seqNr, int port, InetAddress transmitterAddress){
        try {
            ByteBuffer messageBuffer = ByteBuffer.allocate(6);
            messageBuffer.putShort(transmissionID);
            messageBuffer.putInt(seqNr);

            DatagramPacket packet = new DatagramPacket(messageBuffer.array(), messageBuffer.array().length, transmitterAddress, port);
            
            socket.send(packet);
            log("ACK for packet " + seqNr + " sent");

        } catch (Exception e) {
            System.err.println(e);
        }
    }

    /**
    * Converts byte array to hex-number as String. (used for MD5 Hash)
    * @param hex-number as byte array
    * @return hex-number as string
    */
    private static String bytesToHex(byte[] bytes) {
        return new BigInteger(1, bytes).toString(16);
    }

    /**
    * writes output-stream to file.
    * @throws IOException 
    */
    private static void writeToFile() throws IOException{
        FileOutputStream out = new FileOutputStream(fileName.trim(), false);
        out.write(outputStream.toByteArray());  
        out.close();
    }

    /**
    * creates MD5-sum of transmitted file and compares both.
    * @throws IOException
    * @throws NoSuchAlgorithmException 
    * @return true if they are equal
    * @return false otherwise
    */
    private static boolean checkMD5Sum() throws IOException, NoSuchAlgorithmException{
        byte[] data = Files.readAllBytes(Paths.get(fileName.trim()));
        byte[] hash = MessageDigest.getInstance("MD5").digest(data);

        String checksum = new BigInteger(1, hash).toString(16);

        return checksum.equals(MD5Hash);
    }
}