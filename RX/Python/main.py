import re
import socket
import hashlib
import sys
import argparse
import io

def sendAck():
    response_data = id.to_bytes(2, byteorder='big') + seq_num.to_bytes(4, byteorder='big')
    sock.sendto(response_data, addr)

if len(sys.argv) > 1:
    if sys.argv[1] == '--help' or sys.argv[1] == '-h':
        print('Options:')
        print('  --host <host>       Host to send to (default: 127.0.0.1)')
        print('  --port <port>       Port to send to (default: 12345)')
        print('  --max <size>        Maximum packet size (default: 1500)')
        print('  --quiet             Do not print anything to the terminal')
        print('  --help              Show this help')
        sys.exit(0)

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to send to (default: 127.0.0.1)')
parser.add_argument('--port', type=int, default=12345, help='Port to send to (default: 12345)')
parser.add_argument('--max', type=int, default=1500, help='Maximum packet size (default: 1500)')
parser.add_argument('--quiet', action='store_true', help='Do not print anything to the terminal')

# Parse the arguments
args = parser.parse_args()

# Set the variables
HOST = args.host
PORT = args.port
max_pack = args.max
quiet = args.quiet

####
#
####

# Define the variables
seq_num = 0
data_output = io.BytesIO()
md5received = False
md5 = ""

# Create a UDP socket and bind it to the host and port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
if not quiet:
    print(f'Listening on {HOST}:{PORT}')
    print('---------------------------------')

# Receive the first packet
data, addr = sock.recvfrom(max_pack)
id = int.from_bytes(data[0:2], byteorder='big')
transmID = id
max_seq_num = int.from_bytes(data[6:10], byteorder='big')
file_name_length = len(data) - 10
file_nameU = data[10:10+file_name_length].decode('utf-8')
file_name = re.sub(r'.*/', '', file_nameU)
if not quiet:
    print(f'Packet 0 (init): id={id}, maxSeqNum={max_seq_num}, fileName={file_name}')

sendAck()

# Receive the data packet(s)
window_size = 5
window_start = 1
window_end = window_start + window_size - 1
received_packets = [False] * max_seq_num
while True:
    data, addr = sock.recvfrom(max_pack)
    id = int.from_bytes(data[0:2], byteorder='big')
    seq_num = int.from_bytes(data[2:6], byteorder='big')
    if id == transmID and seq_num >= window_start and seq_num <= window_end:
        packet_data = (data[6:])
        data_output.write(packet_data)
        received_packets[seq_num] = True
        if seq_num == window_end:
            # Check if all packets in the window have been received
            all_received = True
            for i in range(window_start, window_end+1):
                if not received_packets[i]:
                    all_received = False
                    break
            if all_received:
                # Send cumulative ACK
                sendAck()
                # Move the window
                window_start += window_size
                window_end += window_size
                if window_end >= max_seq_num:
                    window_end = max_seq_num - 1
                # Check for any missing packets
                for i in range(window_start, window_end+1):
                    if not received_packets[i]:
                        # Send duplicate ACK
                        sendAck()
                        break
    elif id == transmID:
        # Send duplicate ACK
        sendAck()

# Receive the md5 packet
while md5received == False:
    data, addr = sock.recvfrom(max_pack)
    id = int.from_bytes(data[0:2], byteorder='big')
    seq_num = int.from_bytes(data[2:6], byteorder='big')
    if id == transmID:
        md5 = data[6:22].hex()
        md5received = True
        if not quiet:
            print(f'Packet {seq_num} (md5): id={id}, md5={md5}')

        sendAck()
    else:
        md5received = False

if not quiet:
    print('---------------------------------')

final_data = data_output.getvalue()

# Verify the MD5
final_data_md5 = hashlib.md5(final_data).hexdigest()

if md5 == final_data_md5:
    if not quiet:
        print(u'\u2714''  MD5 matches')
    # with open(file_name, 'wb') as f:
    #     f.write(final_data)
    # if not quiet:
    #     print(u'\u2714'f'  File {file_name} written')
else:
    if not quiet:
        print(u'\u274C'' MD5 does not match: \n 'f' {md5} != {final_data_md5}')

# Close the socket
sock.close()
if not quiet:
    print(u'\u2714''  Socket closed')
