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
    private static int BUFFER_SIZE = 1472;
    private static int PORT = 12345;
    private static String IP_ADDRESS = "127.0.0.1";

    public static void main(String[] args) throws SocketException, UnknownHostException{
        if (args.length > 0) {
            // Parse the arguments and set the variables accordingly
            for (int i = 0; i < args.length; i += 2) {
                String arg = args[i];
                String value = args[i+1];
                switch (arg) {
                    case "--host":
                        IP_ADDRESS = value;
                        break;
                    case "--port":
                        PORT = Integer.parseInt(value);
                        break;
                    case "--max":
                        BUFFER_SIZE = Integer.parseInt(value);
                        break;
                    case "--help":
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
        UDPReceiver.run();
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

    /**
    * This method contains a loop that terminates once the last packet is received.
    * @throws UnknownHostException if IP-address is unknown
    * @throws SocketException if there is an error creating socket object
    */
    public static void run() throws UnknownHostException, SocketException {
        IP = InetAddress.getByName(IP_ADDRESS);
        socket = new DatagramSocket(PORT, IP);
        boolean done = false;
        
        System.out.println("Receiver listening (IP: " + IP.getHostAddress() + ", port: " + PORT + ")...");
        
        // loop runs until done == false which means the last packet was received (see interpretPacket())
        while (!done) {
            try {
                done = interpretPacket();
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
    private static boolean interpretPacket() throws IOException, NoSuchAlgorithmException{
        byte[] buf = new byte[BUFFER_SIZE]; // BUFFER_SIZE = data-size + 6Byte (Header)
        int seqNr = -1;
        DatagramPacket packet = new DatagramPacket(buf, buf.length, IP, PORT);
        receiverBuffer = ByteBuffer.wrap(packet.getData());
        receivedPackets++;

        try {
            socket.receive(packet);
        } catch (IOException e) {
            e.printStackTrace();
        }

        transmissionID = receiverBuffer.getShort(); // get 2 Byte (short) transmission ID
        seqNr = receiverBuffer.getInt();    // get 4 Byte (Integer) sequence number 

        if (seqNr == 0) { // first packet (containing maximum sequence number and file name)
            startTime = new Timestamp(System.currentTimeMillis());  // set start time stamp

            maxSeqNr = receiverBuffer.getInt() + 1; // get max. sequence number and increase by 1 to know when to stop
            try{
                fileName = new String(receiverBuffer.array(), 10, 11, "UTF8");  // extract file name
            } catch (Exception e){  // could result in Exception if charsetName is unknown to Java-String
                e.printStackTrace();
            }
        } else if (seqNr == maxSeqNr) { // last packet (containing MD5 Checksum)
            byte[] MD5Array = new byte[16];
            receiverBuffer = receiverBuffer.get(MD5Array);  // get MD5 hash and save in byte array
            MD5Hash = bytesToHex(MD5Array); // convert to hex-number as String

            outputStream.close();   // now the output-stream can be closed 

            writeToFile();  // write data to file (data is written to file after the transmission is complete)

            endTime = new Timestamp(System.currentTimeMillis());

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
            outputStream.write(dataArray);  // write data to output-stream
        }
        return false;
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