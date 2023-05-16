import pyshark
import matplotlib.pyplot as plt
import asyncio
import math
import os


def plot(filePath):
    fileSize = 0.88 # in MB
    folders = ['Dart_Java', 'Dart_Python', 'Node_Java', 'Node_Python'] 
    numbers = [100, 1400, 60000]
    mdParts = []
    for directFolder in folders:
        if(filePath != ''):
            folder = filePath + '/' + directFolder
        for number in numbers:
            # Check if the capture file exists
            if not os.path.exists(folder + '/raw' + str(number) + '.pcap'):
                print('File ' + folder + '/raw' + str(number) + '.pcap' + ' does not exist, generating empty plot anyway')
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
                continue

            print('Plotting ' + folder + '/raw' + str(number) + '.pcap')
            # Open the capture file and extract the packets
            capture = pyshark.FileCapture(folder + '/raw' + str(number) + '.pcap')
            packets = [p for p in capture]
            capture.close()

            # Group the packets by transmission and assign sequence numbers
            transmissions = {}
            for packet in packets:
                seq = packet.udp.stream
                if seq not in transmissions:
                    transmissions[seq] = {'packets': [], 'seq_num': 0}
                transmissions[seq]['seq_num'] += 1
                transmissions[seq]['packets'].append(packet)

            # Get the maximum packet number across all transmissions
            max_packet_num = max([len(data['packets']) for seq, data in transmissions.items()])

            # save the max time for the fastest and slowest transmission
            relative_times = [+math.inf, -math.inf]
            
            # Create a graph for each transmission
            for i, (seq, data) in enumerate(transmissions.items()):
                packets = data['packets']
                # Extract the sequence numbers and timestamps from the packets
                seq_nums = [i for i in range(len(packets))]
                timestamps = [float(p.sniff_timestamp) for p in packets]

                # Extract the timestamp of the first packet
                start_time = float(packets[0].sniff_timestamp)

                relative_timestamps = [(t - start_time) * 1000 for t in timestamps]
                # print(relative_timestamps)

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

            # Set the y-axis ticks to natural numbers
            if max_packet_num < 20:
                plt.yticks(range(max_packet_num), range(max_packet_num))
            else:
                plt.yticks(range(0, max_packet_num, math.floor(max_packet_num/20)), range(0, max_packet_num, math.floor(max_packet_num/20)))

            # Save the plot as an image
            plt.savefig(folder + '/plot' + str(number) + '.png')
            plt.close()

            # Generate the .md part
            mdParts.append(f" ![{number}_{directFolder}]({directFolder}/plot{number}.png) {fileSize/relative_times[1]*1000:.1f} - {fileSize/relative_times[0]*1000:.1f} MB/s")

    # Finish the .md file
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
    plot('messungen_copy')