import argparse
import os
import subprocess
import time

# start time
start = time.time()

def progressBar(i, step):
    bar_length = 50
    steps = 2*amount
    step_size = steps / bar_length
    progress = step / steps
    filled_length = int(round(bar_length * progress))  
    remaining_length = bar_length - filled_length 
    filled_bar = '█' * filled_length
    empty_bar = '░' * remaining_length 
    print(f'\r{tx} -> {rx}: |{filled_bar}{empty_bar}| {i} / {amount} ({progress:.1%})', end='')
# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--tx', type=str, help="The sender to use")
parser.add_argument('--rx', type=str, help="The receiver to use")
parser.add_argument('--max', type=int, default=1500, help="The maximum packet length to use")
parser.add_argument('--amount', type=int, default=10, help="The amount of packets to send")
parser.add_argument('--timeout', type=int, default=10, help="The timeout for a single file transfer")
parser.add_argument('--file', type=str, default="test.txt", help="The file to send")
parser.add_argument('--version', type=int, default=3, help="The version of the protocol to use")
parser.add_argument('--sliding-window', type=int, default=10, help="The size of the sliding window, only used for version 3")
                    
# Parse the arguments
args = parser.parse_args()

# Set the variables
tx = args.tx.lower()
rx = args.rx.lower()
if rx == "java":
    rx = " java "
max_pack = args.max
amount = args.amount
timeout = args.timeout
file_path = os.path.abspath(args.file)
version = args.version
sliding_window = args.sliding_window

# TX-Variables
dart_path = "TX/Dart/tx/lib/tx.dart"
node_path = "TX/NodeJS/main.js"

# RX-Variables
python_path = "RX/Python/main.py"
java_path = "RX/Java/rx_java/src/UDPReceiver"

totalTimeouts = 0
successes = 0
rx_sleep = 0.1

# Execute the TX/RX scripts
i = 0
while i < amount and totalTimeouts < 10:
    progressBar(i, 2*i)
        
    # Execute the RX script
    if rx == "python":
        rx_proc = subprocess.Popen(['python', python_path, '--max', str(max_pack), '--quiet', '--version', str(version), '--sliding-window', str(sliding_window)])
    elif rx == " java ":
        os.system("javac " + java_path + ".java")
        rx_proc = subprocess.Popen(['java', '-classpath', 'RX/Java/rx_java/src', 'UDPReceiver', '--max', str(max_pack), '--quiet', '--version', str(version), '--sliding-window', str(sliding_window)])
    else:
        print("Invalid RX name entered")
        exit()
    # waiting for the RX script to start, 
    time.sleep(rx_sleep) # increase this if the RX script do weard stuff
    
    progressBar(i, 2*i+1)

    # Execute the TX script
    if tx == "dart":
        tx_proc = subprocess.Popen(['dart', 'run', dart_path, '--max', str(max_pack), '--quiet', '--file', file_path, '--version', str(version), '--sliding-window', str(sliding_window)])
    elif tx == "node":
        tx_proc = subprocess.Popen(['node', node_path, '--max', str(max_pack), '--quiet', '--file', file_path, '--version', str(version), '--sliding-window', str(sliding_window)])
    else:
        print("Invalid TX name entered")
        break
    # print("Packet " + str(i) + " sent!")

    i += 1
    
    # waiting for the TX script to finish
    tmp = 0.01
    while tmp < timeout:
        rx_exit_code = rx_proc.poll()
        tx_exit_code = tx_proc.poll()
        if rx_exit_code is not None and tx_exit_code is not None:
            # Both processes have terminated
            successes += 1
            break
        time.sleep(tmp)
        tmp *= 2
    else:
        # if RX process is still running, terminate it
        tx_exit_code = tx_proc.poll()
        if tx_exit_code is None:
            tx_proc.terminate()
            tx_proc.wait()
            print("TX process terminated")
        # if TX process is still running, terminate it
        rx_exit_code = rx_proc.poll()
        if rx_exit_code is None:
            rx_proc.terminate()
            rx_proc.wait()
            print("RX process terminated")
        totalTimeouts += 1
        amount += 1
    
# Clear the progress bar
print("\r" + " " * 100 + "\r", end="")
# End Timer
end = time.time()
# Print the results
print(f"\r{tx} -> {rx}: Mit {str(max_pack).ljust(5)} Packetsize ({amount} Versuche): {successes} Erfolge, {totalTimeouts} Timeouts. In {end - start:5.2f} Sekunden ({(end - start) / amount - rx_sleep:.2f} s/V)")
