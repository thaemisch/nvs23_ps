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
import java.util.Arrays;
import java.util.PriorityQueue;

public class UDPReceiver extends Thread{

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
    private static int maxSeqNr;
    private static String MD5Hash;
    private static int transmissionID;
    private String fileName = null;
    static PriorityQueue<QueueEntry> dataQueue = new PriorityQueue<QueueEntry>(); 

    private static final char[] HEX_ARRAY = "0123456789abcdef".toCharArray();

    public static void main(String[] args) throws SocketException, UnknownHostException{
        UDPReceiver udpReceiver = new UDPReceiver(12345, "127.0.0.1");
        udpReceiver.run();
    }

    public UDPReceiver(int port, String IP) throws SocketException, UnknownHostException {
        this.port = port;
        this.IP = InetAddress.getByName(IP);
        socket = new DatagramSocket(this.port, this.IP);
    }

    public UDPReceiver(int port) throws SocketException, UnknownHostException {
        this.port = port;
        this.IP = InetAddress.getLocalHost();
        socket = new DatagramSocket(this.port, this.IP);
    }

    public void run() {
        boolean done = false;
        
        System.out.println("Receiver listening...");
        
        while (!done) {
            try {
                done = interpretePacket();
            } catch (UnsupportedEncodingException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            } catch (IOException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            } catch (NoSuchAlgorithmException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
        }
        socket.close();
    }

    private boolean interpretePacket() throws IOException, NoSuchAlgorithmException{
        byte[] buf = new byte[1478];
        int seqNr = -1;
        DatagramPacket packet = new DatagramPacket(buf, buf.length);
        try {
            socket.receive(packet);
        } catch (IOException e) {
            e.printStackTrace();
        }

        InetAddress address = packet.getAddress();
        int port = packet.getPort();
        packet = new DatagramPacket(buf, buf.length, address, port);

        transmissionID = extractTransmissionID(buf);
        seqNr = extractSeqNr(buf);

        if (seqNr == 0) {
            System.out.println("begin");
            //initial packet contains maximal sequence Number
            maxSeqNr = extractMaxSeqNr(buf) + 1;
            try{
                fileName = extractFileName(buf);
            } catch (Exception e){
                e.printStackTrace();
            }
        } else if (seqNr == maxSeqNr) {
            MD5Hash = extractMD5Sum(buf);
            System.out.println(MD5Hash);
            writeToFile();
            checkMD5Sum();
            System.out.println("end");
            //end of transmission
            clearBuffer(buf);
            return true;
        } else {
            dataQueue.add(new QueueEntry(extractSeqNr(buf), extractData(buf)));
        }

        clearBuffer(buf);
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
        byte dataBuf[] = new byte[buf.length - 6];
        for(int i = 6; i < buf.length; i++){
            dataBuf[i - 6] = buf[i];
        }
        
        return dataBuf;
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
    
    private void clearBuffer(byte buf[]){
        for(int i = 0; i < buf.length; i++){
            buf[i] = 0;
        }
    }

    private void writeToFile() throws IOException{
        FileOutputStream out = new FileOutputStream(fileName.trim(), false);
        System.out.println(dataQueue.size());
        while(!dataQueue.isEmpty()){
            out.write(trim(dataQueue.poll().data));
        }

        out.close();
    }

    private static byte[] trim(byte[] bytes) {
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
        System.out.println(checksum);
        if(checksum.compareTo(MD5Hash) == 0)
            return true;
        return false;
    }
}
