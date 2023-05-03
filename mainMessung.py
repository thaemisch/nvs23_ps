import pyshark
import os
import subprocess

messungs_folder = "messungen_test"

tx_list = ["Dart", "Node"] # List of all senders
rx_list = ["Java", "Python"] # List of all receivers
pktlen_list = [100, 1400, 60_000] # List of all packet lengths


for tx in tx_list:
    for rx in rx_list:
        for pktlen in pktlen_list:
            foldername = f"{messungs_folder}/{rx}_{tx}"
            filename = f"raw{pktlen}.pcap"
            os.makedirs(foldername, exist_ok=True) # Create directory if it doesn't exist
            capture = pyshark.LiveCapture(interface='Adapter for loopback traffic capture', output_file=f"{foldername}/{filename}")
            # capture.sniff(timeout=10) # Capture network traffic for 10 seconds
            # os.system(f"python other_script.py {foldername}/{filename}") # Run another script
            capture.sniff(timeout=None) # Sniff indefinitely
            proc = subprocess.Popen(['python', 'autoRun.py', "--tx", tx, "--rx", rx, "--max", str(pktlen), "--amount", "10", "--timeout", "5"])
            proc.wait() # Wait for other script to complete
            capture.close() # Stop Pyshark capture