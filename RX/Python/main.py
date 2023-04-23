import re
import socket
import hashlib

# Define the host and port to receive packets on
HOST = '127.0.0.1'
PORT = 12345

# Define the variables
seq_num = 0
final_data = b''

# Create a UDP socket and bind it to the host and port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f'Listening on {HOST}:{PORT}')
print('---------------------------------')

# Receive the first packet
data, addr = sock.recvfrom(1472)
id = int.from_bytes(data[0:2], byteorder='big')
max_seq_num = int.from_bytes(data[6:10], byteorder='big')
file_name_length = len(data) - 10
file_nameU = data[10:10+file_name_length].decode('utf-8')
file_name = re.sub(r'.*/', '', file_nameU)
print(f'Packet 0 (init): id={id}, maxSeqNum={max_seq_num}, fileName={file_name}')

# Receive the data packet(s)
while seq_num < max_seq_num:
    data, addr = sock.recvfrom(1472)
    id = int.from_bytes(data[0:2], byteorder='big')
    seq_num = int.from_bytes(data[2:6], byteorder='big')
    packet_data = (data[6:])
    final_data += packet_data
    print(f'Packet {seq_num}: id={id}, data={packet_data}')

# Receive the md5 packet
data, addr = sock.recvfrom(1472)
id = int.from_bytes(data[0:2], byteorder='big')
seq_num = int.from_bytes(data[2:6], byteorder='big')
md5 = data[6:22].hex()
print(f'Packet {seq_num} (md5): id={id}, md5={md5}')

print('---------------------------------')

# Verify the MD5
final_data_md5 = hashlib.md5(final_data).hexdigest()

if md5 == final_data_md5:
    print(u'\u2714''  MD5 matches')
    with open(file_name, 'wb') as f:
        f.write(final_data)
    print(u'\u2714'f'  File {file_name} written')
else:
    print(u'\u274C'' MD5 does not match: \n 'f' {md5} != {final_data_md5}')

# Close the socket
sock.close()
print(u'\u2714''  Socket closed')