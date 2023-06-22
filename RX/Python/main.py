import re
import socket
import hashlib
import sys
import argparse
import io
import signal

class TimeoutException(Exception):
    pass 

def timeout_handler(signum, frame):
    raise TimeoutException("Function timed out")

if len(sys.argv) > 1:
    if sys.argv[1] == '--help' or sys.argv[1] == '-h':
        print('Options:')
        print('  --version <version> Version of the protocol (default: 1)')
        print('  --host <host>       Host to receive from (default: 127.0.0.1)')
        print('  --port <port>       Port to receive from (default: 12345)')
        print('  --max <size>        Maximum packet size (default: 1500)')
        print('  --window <size>     Window size (default: 5)')
        print('  --quiet             Do not print anything to the terminal')
        print('  --save              Save the received file to disk')
        print('  --help              Show this help')
        sys.exit(0)

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--version', type=int, default=1, help='Version of the protocol (default: 1)')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to send to (default: 127.0.0.1)')
parser.add_argument('--port', type=int, default=12345, help='Port to send to (default: 12345)')
parser.add_argument('--max', type=int, default=1500, help='Maximum packet size (default: 1500)')
parser.add_argument('--window', type=int, default=10, help='Window size (default: 5)')
parser.add_argument('--quiet', action='store_true', help='Do not print anything to the terminal')
parser.add_argument('--save', action='store_true', help='Save the received file to disk')

# Parse the arguments
args = parser.parse_args()

# Set the variables
version = args.version
HOST = args.host
PORT = args.port
max_pack = args.max
quiet = args.quiet
save = args.save
window_size = args.window

# Define the variables
seq_num = 0
max_seq_num = 0
data_output = io.BytesIO()
md5received = False
md5 = ""
transmID = 0

# Create a UDP socket and bind it to the host and port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
if not quiet:
    print(f'Listening on {HOST}:{PORT}')
    print('---------------------------------')

def sendAck():
    response_data = id.to_bytes(2, byteorder='big') + seq_num.to_bytes(4, byteorder='big')
    sock.sendto(response_data, addr)

def sendAckBySQN(sqn):
    response_data = id.to_bytes(2, byteorder='big') + sqn.to_bytes(4, byteorder='big')
    sock.sendto(response_data, addr)

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
if not version == 1:
    sendAck()


####
#Versions
####
# Receive the data packet(s)
if version == 1 or version == 2:
    while seq_num < max_seq_num-1:
        data, addr = sock.recvfrom(max_pack)
        id = int.from_bytes(data[0:2], byteorder='big')
        seq_num = int.from_bytes(data[2:6], byteorder='big')
        if id == transmID:
            packet_data = (data[6:])
            data_output.write(packet_data)
            if not quiet:
                print(f'Packet {seq_num}: id={id}, data={packet_data}')
            if version == 2:
                sendAck()
elif version == 3:
    window_start = 1
    window_end = window_start + window_size - 1
    received_packets = [False] * max_seq_num
    last_seq_num = 1
    while True:
        data, addr = sock.recvfrom(max_pack)
        id = int.from_bytes(data[0:2], byteorder='big')
        seq_num = int.from_bytes(data[2:6], byteorder='big')
        if id == transmID and seq_num >= window_start and seq_num <= window_end and last_seq_num+1 == seq_num:
            packet_data = (data[6:])
            data_output.write(packet_data)
            received_packets[seq_num] = True
            if seq_num == window_end:
                # Check if all packets in the window have been received
                window_closed = True
                for i in range(window_start, window_end+1):
                    if not received_packets[i]:
                        window_closed = False
                        break
                if window_closed:
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
                            sendAckBySQN(i)
                            break
        elif not last_seq_num+1 == seq_num:
            # Send duplicate ACK
            sendAckBySQN(last_seq_num)
        elif id == transmID:
            # Send duplicate ACK
            sendAck()
else:
    print("Invalid Version (can be 1-3)")
    print("Version 1: Basic")
    print("Version 2: + ACK")
    print("Version 3: + Sliding Window + cumulative ACK")
    sys.exit(0)
####
#
####

# Receive the md5 packet
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(20)

try:
    data, addr = sock.recvfrom(max_pack)
    id = int.from_bytes(data[0:2], byteorder='big')
    seq_num = int.from_bytes(data[2:6], byteorder='big')
    if id == transmID:
        md5 = data[6:22].hex()
        if not quiet:
            print(f'Packet {seq_num} (md5): id={id}, md5={md5}')

        sendAck()
except TimeoutException as ex:
    print("No MD5 packet received after 20 seconds")
    print("Exiting...")
    sys.exit(1)

####
#Finishing Up
####

if not quiet:
    print('---------------------------------')

# Close the socket
sock.close()
if not quiet:
    print(u'\u2714''  Socket closed')

if not quiet:
    print('---------------------------------')

# Verify the MD5
final_data = data_output.getvalue()
final_data_md5 = hashlib.md5(final_data).hexdigest()

if md5 == final_data_md5:
    if not quiet:
        print(u'\u2714''  MD5 matches')
    if save:
        with open(file_name, 'wb') as f:
            f.write(final_data)
        if not quiet:
            print(u'\u2714'f'  File {file_name} written')
else:
    if not quiet:
        print(u'\u274C'' MD5 does not match: \n 'f' {md5} != {final_data_md5}')