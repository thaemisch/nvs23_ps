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
parser.add_argument('--folder', type=str, default="messungen_test")
parser.add_argument('--size', type=str, default="1MB")
parser.add_argument('--file', type=str, default="test.txt")
parser.add_argument('--timeout', type=int, default=10)

# Parse the arguments
args = parser.parse_args()

# Set the variables
messungs_folder = args.folder
size = args.size
file = args.file
capture_timeout = args.timeout

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
pktlen_list = [100, 1400, 60_000] # List of all packet lengths
amount = 10 # Amount of packets to send
interface = "Adapter for loopback traffic capture" # Interface to capture on
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

            proc = subprocess.Popen(['python', 'autoRun.py', "--tx", tx, "--rx", rx, "--max", str(pktlen), "--amount", str(amount), "--timeout", str(capture_timeout), "--file", file])
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