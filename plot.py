import time
import pyshark
import matplotlib.pyplot as plt
import math
import os


def plot(filePath, fileSize = 90_000, with_ack = False):
    # test if the filePath exists
    if(filePath != ''):
        if not os.path.exists(filePath):
            print('File ' + filePath + ' does not exist')
            return

    # fileSize in Bytes
    folders = ['Dart_Java', 'Dart_Python', 'Node_Java', 'Node_Python'] 
    numbers = [100, 1_400, 60_000]
    mdParts = []
    for directFolder in folders:
        if(filePath != ''):
            folder = filePath + '/' + directFolder
        for number in numbers:
            start = time.time()
            # Check if the capture file exists
            if not os.path.exists(folder + '/raw' + str(number) + '.pcap'):
                print('File ' + folder + '/raw' + str(number) + '.pcap' + ' does not exist, generating empty plot anyway', end='')
                # Set the axis labels and legend
                plt.xlabel('Time (ms)')
                plt.ylabel('Sequence number')
                # plt.legend()

                plt.xticks(range(0, 5), range(0, 5))
                plt.yticks(range(0, 20), range(0, 20)) 

                # Save the plot as an image
                plt.savefig(folder + '/plot' + str(number) + '.png')
                plt.close()

                # Generate the .md part
                mdParts.append(f" ![{number}_{directFolder}]({directFolder}/plot{number}.png) 0 MB/s")
                end = time.time() - start
                print(f" in {end:.2f} seconds")
                continue
            print(('Plotting ' + folder + '/raw' + str(number) + '.pcap' ).ljust(len("Plotting /raw.pcap") + len(filePath) + len(max(folders)) + 6), end='')
            # Open the capture file and extract the packets
            capture = pyshark.FileCapture(folder + '/raw' + str(number) + '.pcap')

            # Group the packets by transmission and assign sequence numbers
            transmissions = {}
            for packet in capture:
                # Check if the packet is UDP
                if 'UDP' not in packet:
                    continue
                seq = packet.udp.stream
                if seq not in transmissions:
                    transmissions[seq] = {'packets': [], 'seq_num': []}

                # if not ack is false and 36 is true
                if not (with_ack == False and int(packet.length) == 38):
                    transmissions[seq]['packets'].append(packet)
                    byte_array = bytes.fromhex(packet.udp.payload[6:17].replace(':', '')) # Convert the hex string to a byte array
                    seq_num = int.from_bytes(byte_array, byteorder='big') # Convert the byte array to an integer
                    transmissions[seq]['seq_num'].append(seq_num)

            capture.close()
            # Get the maximum packet number across all transmissions
            max_seq_num = max([max(data['seq_num']) for seq, data in transmissions.items()]) + 1
            max_packet_num = max([len(data['packets']) for seq, data in transmissions.items()])
            if with_ack:
                if(max_seq_num * 2 != max_packet_num):
                    print(f"Missing ACKs for {max_packet_num - max_seq_num} packets")
            # save the max time for the fastest and slowest transmission
            relative_times = [+math.inf, -math.inf]

            # Check if there are any transmissions with less packets than the maximum
            keys_to_remove = []  # Store the keys to be removed

            for seq, data in transmissions.items():
                if max(data['seq_num']) + 1 < max_seq_num:
                    keys_to_remove.append(seq)

            if len(keys_to_remove) > 0:
                print(f'{len(keys_to_remove)} transmissions were too short and were ignored')

            # Remove the transmissions outside the loop
            for seq in keys_to_remove:
                del transmissions[seq]

            # Create a graph for each transmission
            for i, (seq, data) in enumerate(transmissions.items()):
                packets = data['packets']
                # Extract the sequence numbers and timestamps from the packets
                seq_nums = data['seq_num']
                timestamps = [float(p.sniff_timestamp) for p in packets]

                # Extract the timestamp of the first packet
                start_time = float(packets[0].sniff_timestamp)

                relative_timestamps = [(t - start_time) * 1000 for t in timestamps]

                # Get max relative timestamp
                max_relative_timestamp = max(relative_timestamps)
                if(max_relative_timestamp > relative_times[1]):
                    relative_times[1] = max_relative_timestamp
                if(max_relative_timestamp < relative_times[0]):
                    relative_times[0] = max_relative_timestamp

                # Plot the sequence numbers against the timestamps
                plt.plot(relative_timestamps, seq_nums, label=f'T{i}', linewidth=1.5)

            # Set the axis labels and legend
            plt.xlabel('Time (ms)')
            plt.ylabel('Sequence number')
            plt.legend()
            
            step = math.ceil(max_seq_num/20)
            # Set the y-axis ticks to natural numbers
            plt.yticks(range(0, max_seq_num, step), range(0, max_seq_num, step))

            # Save the plot as an image
            plt.savefig(folder + '/plot' + str(number) + '.png')
            plt.close()

            # Generate the .md part
            mdParts.append(f" ![{number}_{directFolder}]({directFolder}/plot{number}.png) {fileSize/relative_times[1]*1000 /1000/1000:.1f} - {fileSize/relative_times[0]*1000 /1000/1000:.1f} MB/s")
            end = time.time() - start
            print(f" in {end:.2f} seconds")

    # Finish the .md file
    print("Generating messungen.md")
    md = "# Messungen\n\n| TX/RX | &nbsp;&nbsp;&nbsp;Java&nbsp;&nbsp;&nbsp; | Python |\n:-------------------------:|:-------------------------:|:-------------------------:\n"
    md += "| Dart |" + mdParts[0]+ mdParts[1] + mdParts[2] + " |"
    md += mdParts[3] + mdParts[4] + mdParts[5] + " |\n"
    md += "| Node |" + mdParts[6] + mdParts[7] + mdParts[8] + " |"
    md += mdParts[9] + mdParts[10] + mdParts[11] + " |\n"

    # Write the .md file
    with open(filePath + '/messungen.md', 'w') as f:
        f.write(md)
    f.close()

# plt.show()

if __name__ == '__main__':
    plot('messung_V2_1KB', 1_000, True)