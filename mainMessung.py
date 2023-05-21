import os
import subprocess
import threading
import argparse
import time
import plot
import createFile
import math


# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--folder', type=str, default="messungen_test")
parser.add_argument('--size', type=str, default="1MB")
parser.add_argument('--file', type=str, default="test.txt")

# Parse the arguments
args = parser.parse_args()

# Set the variables
messungs_folder = args.folder
size = args.size
file = args.file


# Delete the old file
try:
    os.remove(file)
except:
    pass
# Create the file
createFile.create_random_file(f"test.txt", size)

size_in_bytes = createFile.convert_size_to_bytes(size)

tx_list = ["Dart", "Node"] # List of all senders
rx_list = ["Java", "Python"] # List of all receivers
pktlen_list = [100, 1400, 60_000] # List of all packet lengths
amount = 10 # Amount of packets to send
capture_timeout = 10 # Timeout for the capture
interface = "Adapter for loopback traffic capture" # Interface to capture on
capture_filter = "udp port 12345" # Filter for the capture

for tx in tx_list:
    for rx in rx_list:
        for pktlen in pktlen_list:
            timeout = (1+ math.ceil(size_in_bytes / pktlen)* 0.001) *amount + 5
            # print(f"Timeout: {timeout}")
            foldername = f"{messungs_folder}/{tx}_{rx}"
            filename = f"raw{pktlen}.pcap"
            os.makedirs(foldername, exist_ok=True) # Create directory if it doesn't exist
            # capture = pyshark.LiveCapture(interface='Adapter for loopback traffic capture', output_file=f"{foldername}/{filename}")
            # capture.sniff(timeout=10) # Capture network traffic for 10 seconds
            command = ['tshark', '-i', interface, '-f', capture_filter, '-w', f'{foldername}/{filename}']
            capture = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(1)

            # capture_thread = threading.Thread(target=capture.sniff, kwargs={'timeout': timeout}) # Create Pyshark capture thread
            # capture_thread.start() # Start Pyshark capture

            proc = subprocess.Popen(['python', 'autoRun.py', "--tx", tx, "--rx", rx, "--max", str(pktlen), "--amount", str(amount), "--timeout", str(capture_timeout), "--file", file])
            proc.wait() # Wait for other script to complete
            
            time.sleep(1)
            # Stop the capture
            capture.terminate()
            # See if thread is still running
            #if not capture_thread.is_alive():
            #    print("Capture thread ended to early")
            #print("Waiting for capture to end...")
            #capture_thread.join() # Wait for Pyshark capture to complete
            #capture.close() # Stop Pyshark capture
            #print("\f") # Clear the console

# Plot the results
plot.plot(messungs_folder, size_in_bytes, True)

# Delete the file
try:
    os.remove(file)
except:
    pass