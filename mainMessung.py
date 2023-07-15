import os
import subprocess
import argparse
import time
import plot
import createFile

start = time.time()

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--folder', type=str, default="", help="The folder to save the measurements in")
parser.add_argument('--size', type=str, default="1MB", help="The size of the file to send")
parser.add_argument('--file', type=str, default="test.txt", help="The file to send")
parser.add_argument('--timeout', type=int, default=10, help="The timeout for a single file transfer")
parser.add_argument('--version', type=int, default=3, help="The version of the protocol to use")
parser.add_argument('--sliding-window', type=int, default=10, help="The size of the sliding window, only used for version 3")
parser.add_argument('--interface', type=str, default="Adapter for loopback traffic capture", help="The interface to capture on")

# Parse the arguments
args = parser.parse_args()

# Set the variables
size = args.size
file = args.file
capture_timeout = args.timeout
version = args.version
sliding_window = args.sliding_window
messungs_folder = args.folder or f'messungen/V{version}/{size}'
interface = args.interface

# Check if size is valid
size_in_bytes = createFile.convert_size_to_bytes(size)

print(f"Creating file with size {size}...")

# Delete the old file
try:
    os.remove(file)
except:
    pass
# Create the file
createFile.create_random_file(f"test.txt", size)

tx_list = ["Dart", "Node"] # List of all senders
rx_list = ["Java", "Python"] # List of all receivers
#tx_list = ["Node"]
#rx_list = ["Python"]
pktlen_list = [100, 1400, 60_000] # List of all packet lengths
amount = 10 # Amount of packets to send
capture_filter = "udp port 12345" # Filter for the capture

# clear last output
print("\r" + " "*100, end="")

for tx in tx_list:
    for rx in rx_list:
        for pktlen in pktlen_list:
            foldername = f"{messungs_folder}/{tx}_{rx}"
            filename = f"raw{pktlen}.pcap"
            os.makedirs(foldername, exist_ok=True) # Create directory if it doesn't exist
            command = ['tshark', '-i', interface, '-f', capture_filter, '-w', f'{foldername}/{filename}']
            capture = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(1)

            proc = subprocess.Popen(['python', 'autoRun.py', "--tx", tx, "--rx", rx, "--max", str(pktlen), "--amount", str(amount), "--timeout", str(capture_timeout), "--file", file, "--version", str(version), "--sliding-window", str(sliding_window)])
            proc.wait() # Wait for the process to finish

            time.sleep(1)
            # Stop the capture
            capture.terminate()

# Plot the results
plot.plot(messungs_folder, size_in_bytes, True)

# Delete the file
try:
    os.remove(file)
except:
    pass

# end time
end = time.time()
print(f"\nTotal time elapsed: {end - start:.2f}s")