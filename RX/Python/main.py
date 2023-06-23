import re
import socket
import hashlib
import sys
import argparse
import io
import time


# Create an argument parser
parser = argparse.ArgumentParser(description='command line arguments.')

# Add arguments to the parser
parser.add_argument('-q', '--quiet', action='store_true', help='Do not print anything to the terminal')
parser.add_argument('-s', '--save', action='store_true', help='Save the received file to disk')
parser.add_argument('-v', '--version', metavar='$', type=int, default=3, help='Version of the protocol (default: 3)')
parser.add_argument('-m', '--max', metavar='$', type=int, default=1500, help='Maximum packet size (default: 1500)')
parser.add_argument('-n', '--window', metavar='$', type=int, default=10, help='Window size (default: 10)')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to receive from (default: 127.0.0.1)')
parser.add_argument('--port', type=int, default=12345, help='Port to receive from (default: 12345)')

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

def sendDupAckBySQN(sqn):
    sendAckBySQN(sqn)
    time.sleep(0.5)
    sendAckBySQN(sqn)

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
                print(f'Packet {seq_num}: id={id}')
            if version == 2:
                sendAck()
elif version == 3:
    window_start = 1
    window_end = window_start + window_size - 1
    if window_end == max_seq_num:
        window_end = max_seq_num - 1
    received_packets = [False] * max_seq_num
    packets_map = {}
    missing_packet = 1
    packet_missing = False
    packet_was_missing = False
    allDataReceived = False
    skippedAlready = False
    while not allDataReceived:
        if packet_missing:
            sendDupAckBySQN(missing_packet-1)
            packet_missing = False
            packet_was_missing = True
        # Timeout for receiving packet
        sock.settimeout(1)
        try:
            data, addr = sock.recvfrom(max_pack)
            id = int.from_bytes(data[0:2], byteorder='big')
            seq_num = int.from_bytes(data[2:6], byteorder='big')
        except socket.timeout:
            sendDupAckBySQN(seq_num-1)
            print(f'Timeout: Packet {seq_num-1} is missing, sending duplicate ACK')
            continue
        if id == transmID and seq_num >= window_start and seq_num <= window_end:
            # Test duplicate ACKs by skipping the 3rd packet once
            if seq_num == 3 and not skippedAlready:
                skippedAlready = True
                continue
            else:
                packet_data = (data[6:])
                packets_map[seq_num] = packet_data
                received_packets[seq_num] = True
                if not quiet:
                    print(f'Packet {seq_num}: id={id}')
                if seq_num == window_end or packet_was_missing:
                    packet_was_missing = False
                    # Check if all packets in the window have been received
                    window_closed = True
                    for i in range(window_start, window_end+1):
                        if not received_packets[i]:
                            window_closed = False
                            missing_packet = i
                            packet_missing = True
                            if not quiet:
                                print(f'Packet {i} is missing, sending duplicate ACK')
                            break
                    if window_closed:
                        if seq_num == max_seq_num-1:
                            allDataReceived = True
                        old_window_end = window_end
                        old_window_start = window_start
                        # Move the window
                        window_start += window_size
                        window_end += window_size
                        if window_end >= max_seq_num:
                            window_end = max_seq_num - 1
                        # Send cumulative ACK
                        if not quiet:
                            print(f'Window closed: {old_window_start}-{old_window_end}')
                            print(f'Sending cumulative ACK for {old_window_start}-{old_window_end}')
                        sendAckBySQN(old_window_end)
    if not quiet:
        print("All data received")

else:
    print("Invalid Version (can be 1-3)")
    print("Version 1: Basic")
    print("Version 2: + ACK")
    print("Version 3: + Sliding Window")
    sys.exit(1)
####
#
####
# Receive the last packet (md5)
data, addr = sock.recvfrom(max_pack)
id = int.from_bytes(data[0:2], byteorder='big')
seq_num = int.from_bytes(data[2:6], byteorder='big')
if id == transmID:
    md5 = data[6:22].hex()
    if not quiet:
        print(f'Packet {seq_num} (md5): id={id}, md5={md5}')

    sendAck()


# Piecing the puzzle together
for i in range(1, max_seq_num):
    data_output.write(packets_map[i])
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