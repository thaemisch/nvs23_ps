import socket
import hashlib

# Define the host and port to receive packets on
HOST = '127.0.0.1'
PORT = 12345

# Create a UDP socket and bind it to the host and port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f'Listening on {HOST}:{PORT}')
print('---------------------------------')

# Receive the first packet
data, addr = sock.recvfrom(1024)  # 1024 is the buffer size
id = int.from_bytes(data[0:2], byteorder='big')
max_seq_num = int.from_bytes(data[6:10], byteorder='big')
file_name_length = len(data) - 10
file_name = data[10:10+file_name_length].decode('utf-8')
print(f'Packet 0: id={id}, maxSeqNum={max_seq_num}, fileName={file_name}')

# Receive the second packet
data, addr = sock.recvfrom(1024)
id = int.from_bytes(data[0:2], byteorder='big')
seq_num = int.from_bytes(data[2:6], byteorder='big')
packet_data = (data[6:])
print(f'Packet 1: {seq_num}: id={id}, data={packet_data}')

# Receive the third packet
data, addr = sock.recvfrom(1024)
id = int.from_bytes(data[0:2], byteorder='big')
seq_num = int.from_bytes(data[2:6], byteorder='big')
md5 = data[6:22].hex()
print(f'Packet 2: {seq_num}: id={id}, md5={md5}')

print('---------------------------------')

# Verify the MD5
packet_data_md5 = hashlib.md5(packet_data).hexdigest()

if md5 == packet_data_md5:
    print(u'\u2714''  MD5 matches')
    with open(file_name, 'wb') as f:
        f.write(packet_data)
    print(u'\u2714'f'  File {file_name} written')
    # Close the socket
    sock.close()
    print(u'\u2714''  Socket closed')
else:
    print(u'\u274C'' MD5 does not match: \n 'f' {md5} != {packet_data_md5}')