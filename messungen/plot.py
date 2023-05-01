"""
import pyshark
import matplotlib.pyplot as plt

# Open the capture file and extract the packets
capture = pyshark.FileCapture('/home/tim/Documents/Uni/Informatik/S4/netzePS/nvs23_ps/messungen/Node_Python/raw100.pcap')
packets = [p for p in capture]

# Group the packets by transmission
transmissions = {}
for packet in packets:
    seq = int(packet.udp.stream)
    if seq not in transmissions:
        transmissions[seq] = []
    transmissions[seq].append(packet)

# Create a graph for each transmission
for i, (seq, packets) in enumerate(transmissions.items()):
    # Extract the sequence numbers and timestamps from the packets
    seq_nums = [int(p.udp.seq) for p in packets]
    timestamps = [float(p.sniff_timestamp) for p in packets]

    # Extract the timestamp of the first packet
    start_time = float(packets[0].sniff_timestamp)

    relative_timestamps = [t - start_time for t in timestamps]

    # Plot the sequence numbers against the timestamps
    plt.plot(relative_timestamps, seq_nums, label=f'T{i}', linewidth=1.5)

# Set the axis labels and legend
plt.xlabel('Time (s)')
plt.ylabel('Sequence number')
plt.legend()

# Save the plot as an image
plt.savefig('/home/tim/Documents/Uni/Informatik/S4/netzePS/nvs23_ps/messungen/Node_Python/plot100.png')

plt.show()
"""

import pyshark
import matplotlib.pyplot as plt

# Open the capture file and extract the packets
capture = pyshark.FileCapture('/home/tim/Documents/Uni/Informatik/S4/netzePS/nvs23_ps/messungen/Node_Python/raw100.pcap')
packets = [p for p in capture]

# Group the packets by transmission and assign sequence numbers
transmissions = {}
for packet in packets:
    seq = packet.udp.stream
    if seq not in transmissions:
        transmissions[seq] = {'packets': [], 'seq_num': 0}
    packet.udp.seq = transmissions[seq]['seq_num']
    transmissions[seq]['seq_num'] += 1
    transmissions[seq]['packets'].append(packet)

# Create a graph for each transmission
for i, (seq, data) in enumerate(transmissions.items()):
    packets = data['packets']
    # Extract the sequence numbers and timestamps from the packets
    seq_nums = [int(p.udp.seq) for p in packets]
    timestamps = [float(p.sniff_timestamp) for p in packets]

    # Extract the timestamp of the first packet
    start_time = float(packets[0].sniff_timestamp)

    relative_timestamps = [t - start_time for t in timestamps]

    # Plot the sequence numbers against the timestamps
    plt.plot(relative_timestamps, seq_nums, label=f'T{i}', linewidth=1.5)

# Set the axis labels and legend
plt.xlabel('Time (s)')
plt.ylabel('Sequence number')
plt.legend()

# Save the plot as an image
plt.savefig('/home/tim/Documents/Uni/Informatik/S4/netzePS/nvs23_ps/messungen/Node_Python/plot100.png')

plt.show()