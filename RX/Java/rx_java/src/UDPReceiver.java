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

    private static int BUFFER_SIZE = 1478;
    private static int PORT = 12345;
    private static String IP_ADSRESS = "127.0.0.1";

    public static void main(String[] args) throws SocketException, UnknownHostException{
        UDPReceiver.run();
    }

    // packet: 
    private static short transmissionID;
    private static int maxSeqNr;
    private static String fileName = null;
    private static String MD5Hash;

    private static DatagramSocket socket;
    private static InetAddress IP;
    private static int receivedPackets = 0;
    private static Timestamp startTime;
    private static Timestamp endTime;
    private static ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
    private static ByteBuffer receiverBuffer;

    public static void run() throws UnknownHostException, SocketException {
        IP = InetAddress.getByName(IP_ADSRESS);
        socket = new DatagramSocket(PORT, IP);
        boolean done = false;
        
        System.out.println("Receiver listening (IP: " + IP.getHostAddress() + ", port: " + PORT + ")...");
        while (!done) {
            try {
                done = interpretePacket();
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

    private static boolean interpretePacket() throws IOException, NoSuchAlgorithmException{
        byte[] buf = new byte[BUFFER_SIZE];
        int seqNr = -1;
        DatagramPacket packet = new DatagramPacket(buf, buf.length, IP, PORT);
        receiverBuffer = ByteBuffer.wrap(packet.getData());
        receivedPackets++;

        try {
            socket.receive(packet);
        } catch (IOException e) {
            e.printStackTrace();
        }

        transmissionID = receiverBuffer.getShort();
        seqNr = receiverBuffer.getInt();

        if (seqNr == 0) {
            // first packet (containing maximum sequence number and file name)
            startTime = new Timestamp(System.currentTimeMillis());

            maxSeqNr = receiverBuffer.getInt() + 1;
            try{
                fileName = new String(receiverBuffer.array(), 10, 11, "UTF8");
            } catch (Exception e){
                e.printStackTrace();
            }
        } else if (seqNr == maxSeqNr) {
            // last packet (contraining MD5 Checksum)
            byte[] MD5Array = new byte[16];
            receiverBuffer = receiverBuffer.get(MD5Array);
            MD5Hash = bytesToHex(MD5Array);
            outputStream.close();
            writeToFile();
            endTime = new Timestamp(System.currentTimeMillis());
            System.out.println(endTime.toString() + ": end of transmission");
            if (checkMD5Sum()) {
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
            byte[] dataArray = new byte[packet.getLength() - receiverBuffer.position()];
            receiverBuffer.get(dataArray);
            outputStream.write(dataArray);
        }
        return false;
    }

    private static String bytesToHex(byte[] bytes) {
        return new BigInteger(1, bytes).toString(16);
    }

    private static void writeToFile() throws IOException{
        FileOutputStream out = new FileOutputStream(fileName.trim(), false);
        out.write(outputStream.toByteArray());
        out.close();
    }

    private static boolean checkMD5Sum() throws IOException, NoSuchAlgorithmException{
        byte[] data = Files.readAllBytes(Paths.get(fileName.trim()));
        byte[] hash = MessageDigest.getInstance("MD5").digest(data);

        String checksum = new BigInteger(1, hash).toString(16);
        System.out.println(MD5Hash);
        System.out.println(checksum);

        if(checksum.compareTo(MD5Hash) == 0)
            return true;
        return false;
    }
}