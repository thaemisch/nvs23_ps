import argparse
import os
import subprocess
import time

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--tx', type=str)
parser.add_argument('--rx', type=str)
parser.add_argument('--max', type=str, default="1500")
parser.add_argument('--amount', type=int, default=10)
parser.add_argument('--timeout', type=int, default=5)

# Parse the arguments
args = parser.parse_args()

# Set the variables
tx = args.tx.lower()
rx = args.rx.lower()
max_pack = args.max
amount = args.amount
timeout = args.timeout

# TX-Variables
dart_path = "TX/Dart/tx/lib/tx.dart"
node_path = "TX/NodeJS/main.js"

# RX-Variables
python_path = "RX/Python/main.py"
java_path = "RX/Java/rx_java/src/UDPReceiver"

# Execute the TX/RX scripts
for i in range(amount):
    # Execute the RX script
    if rx == "python":
        rx_proc = subprocess.Popen(['python', python_path, '--max', max_pack, '--quiet'])
    elif rx == "java":
        os.system("javac " + java_path + ".java")
        rx_proc = subprocess.Popen(['java', '-classpath', 'RX/Java/rx_java/src', 'UDPReceiver', '--max', max_pack])
    else:
        print("Invalid RX name entered")
        exit()

    # Execute the TX script
    if tx == "dart":
        tx_proc = subprocess.Popen(['dart', 'run', dart_path, '--max', max_pack, '--quiet'])
    elif tx == "node":
        tx_proc = subprocess.Popen(['node', node_path, '--max', max_pack, '--quiet'])
    else:
        print("Invalid TX name entered")
        break
    # print("Packet " + str(i) + " sent!")
    
    # Wait for the TX process to complete before terminating the RX process
    tx_proc.wait()
    for i in range(timeout):
        rx_exit_code = rx_proc.poll()
        if rx_exit_code is not None:
            # RX process has terminated
            break
        time.sleep(1)
    # RX process is still running, terminate it
    rx_proc.terminate()
    rx_proc.wait()
    

print("Is Great Succes!")
