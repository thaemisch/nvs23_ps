import java.io.FileOutputStream;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.math.BigInteger;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Timestamp;
import java.util.Arrays;
import java.util.PriorityQueue;

/**
 * A UDP-Receiver class for receiving packets in the following structure.
 * Packet {
 *  Transmission ID (16),
 *  Sequence Number (32),
 *  Data (..)
 * }
 * 
 * SeqNr=0 Packet {
 *  Transmission ID (16),
 *  Sequence Number (32),
 *  Max Sequence Number (32),
 *  File Name (8..2048)
 * }
 * 
 * Seq=MaxSeq Packet {
 *  Transmission ID (16),
 *  Sequence Number (32),
 *  MD5 (128)
 * }
 *
 * @author Waleed Ahmad
 * @version 1.0
 */
public class UDPReceiver extends Thread{

    private static final char[] HEX_ARRAY = "0123456789abcdef".toCharArray(); // char array for hexadecimal MD5

    public static void main(String[] args) throws SocketException, UnknownHostException{
        UDPReceiver udpReceiver = new UDPReceiver(12345);
        udpReceiver.run();
    }

    // private inner class for a queue entry (Comparable)
    private class QueueEntry implements Comparable<QueueEntry>{
        private int seqNr;
        private byte[] data;

        public QueueEntry(int seqNr, byte[] data){
            this.seqNr = seqNr;
            this.data = data;
        }

        @Override
        public int compareTo(QueueEntry entry) {
            return Integer.compare(this.seqNr, entry.seqNr);
        }
    }

    private DatagramSocket socket;
    private int port;
    private InetAddress IP;
    private int maxSeqNr;
    private String MD5Hash;
    private int transmissionID;
    private String fileName = null;
    private PriorityQueue<QueueEntry> dataQueue = new PriorityQueue<QueueEntry>();
    private int receivedPackets = 0;
    private Timestamp startTime;
    private Timestamp endTime;

    public UDPReceiver(int port, String IP) throws SocketException, UnknownHostException {
        this.port = port;
        this.IP = InetAddress.getByName(IP);
        socket = new DatagramSocket(this.port, this.IP);
    }

    public UDPReceiver(int port) throws SocketException, UnknownHostException {
        this.port = port;
        this.IP = InetAddress.getByName("127.0.0.1");
        socket = new DatagramSocket(this.port, this.IP);
    }

    public void run() {
        boolean done = false;
        
        System.out.println("Receiver listening (IP: " + this.IP.getHostAddress() + ", port: " + this.port + ")...");
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

    private boolean interpretePacket() throws IOException, NoSuchAlgorithmException{
        byte[] buf = new byte[1500];
        int seqNr = -1;
        DatagramPacket packet = new DatagramPacket(buf, buf.length, IP, port);
        receivedPackets++;

        try {
            socket.receive(packet);
        } catch (IOException e) {
            e.printStackTrace();
        }

        transmissionID = extractTransmissionID(buf);
        seqNr = extractSeqNr(buf);

        if (seqNr == 0) {
            // first packet (containing maximum sequence number and file name)
            startTime = new Timestamp(System.currentTimeMillis());
            System.out.println(startTime.toString() + ": begin of transmission");

            maxSeqNr = extractMaxSeqNr(buf) + 1;
            try{
                fileName = extractFileName(buf);
            } catch (Exception e){
                e.printStackTrace();
            }
        } else if (seqNr == maxSeqNr) {
            // last packet (contraining MD5 Checksum)
            MD5Hash = extractMD5Sum(buf);
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
            System.out.println("\t" + (endTime.getTime() - startTime.getTime()) + "ms");
            
            //end of transmission
            //clearBuffer(buf);
            return true;
        } else {
            // normale data pocket (containing only data)
            dataQueue.add(new QueueEntry(extractSeqNr(buf), extractData(buf)));
        }

        //clearBuffer(buf);
        return false;
    }

    private int extractTransmissionID(byte[] buf){
        return (buf[0] << 8) + buf[1];
    }

    private int extractSeqNr(byte[] buf){
        return (((buf[2] << 24) + (buf[3] << 16)) + (buf[4] << 8)) + buf[5];
    }

    private int extractMaxSeqNr(byte[] buf){
        return (((buf[6] << 24) + (buf[7] << 16)) + (buf[8] << 8)) + buf[9];
    }

    private String extractFileName(byte[] buf) throws UnsupportedEncodingException{
        return new String(buf, 10, 266, "UTF8");
    }

    private byte[] extractData(byte[] buf){
        return Arrays.copyOfRange(buf, 6, buf.length);
    }

    private String extractMD5Sum(byte[] buf){
        byte md5Buf[] = new byte[16];
        md5Buf = Arrays.copyOfRange(buf, 6, 22);
        return bytesToHex(md5Buf);
    }

    private static String bytesToHex(byte[] bytes) {
        char[] hexChars = new char[bytes.length * 2];
        for (int j = 0; j < bytes.length; j++) {
            int v = bytes[j] & 0xFF;
            hexChars[j * 2] = HEX_ARRAY[v >>> 4];
            hexChars[j * 2 + 1] = HEX_ARRAY[v & 0x0F];
        }
        return new String(hexChars);
    }

    private void writeToFile() throws IOException{
        FileOutputStream out = new FileOutputStream(fileName.trim(), false);
        while(!dataQueue.isEmpty()){
            out.write(trimByteArray(dataQueue.poll().data));
        }
        out.close();
    }

    private static byte[] trimByteArray(byte[] bytes) {
        int i = bytes.length - 1;
        while (i >= 0 && bytes[i] == 0) {
            --i;
        }
        return Arrays.copyOf(bytes, i + 1);
    }

    private boolean checkMD5Sum() throws IOException, NoSuchAlgorithmException{
        byte[] data = Files.readAllBytes(Paths.get(fileName.trim()));
        byte[] hash = MessageDigest.getInstance("MD5").digest(data);

        String checksum = new BigInteger(1, hash).toString(16);

        if(checksum.compareTo(MD5Hash) == 0)
            return true;
        return false;
    }
}
