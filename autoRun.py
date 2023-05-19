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
    print(f'\r|{filled_bar}{empty_bar}| {i} / {amount} ({progress:.1%})', end='')

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--tx', type=str)
parser.add_argument('--rx', type=str)
parser.add_argument('--max', type=str, default="1500")
parser.add_argument('--amount', type=int, default=10)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--file', type=str, default="test.txt")

# Parse the arguments
args = parser.parse_args()

# Set the variables
tx = args.tx.lower()
rx = args.rx.lower()
max_pack = args.max
amount = args.amount
timeout = args.timeout
file_path = os.path.abspath(args.file)
print(file_path)

# TX-Variables
dart_path = "TX/Dart/tx/lib/tx.dart"
node_path = "TX/NodeJS/main.js"

# RX-Variables
python_path = "RX/Python/main.py"
java_path = "RX/Java/rx_java/src/UDPReceiver"

totalTimeouts = 0
successes = 0

# Execute the TX/RX scripts
for i in range(amount):
    progressBar(i, 2*i)
        
    # Execute the RX script
    if rx == "python":
        rx_proc = subprocess.Popen(['python', python_path, '--max', max_pack, '--quiet', '--file', file_path])
    elif rx == "java":
        os.system("javac " + java_path + ".java")
        rx_proc = subprocess.Popen(['java', '-classpath', 'RX/Java/rx_java/src', 'UDPReceiver', '--max', max_pack , '--quiet', '--file', file_path])
    else:
        print("Invalid RX name entered")
        exit()
    # waiting for the RX script to start, 
    time.sleep(0.1) # increase this if the RX script do weard stuff
    
    progressBar(i, 2*i+1)

    # Execute the TX script
    if tx == "dart":
        tx_proc = subprocess.Popen(['dart', 'run', dart_path, '--max', max_pack, '--quiet' , '--file', file_path])
    elif tx == "node":
        tx_proc = subprocess.Popen(['node', node_path, '--max', max_pack, '--quiet' , '--file', file_path])
    else:
        print("Invalid TX name entered")
        break
    # print("Packet " + str(i) + " sent!")
    
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
print(f"\r{tx} -> {rx}: Mit {max_pack} Packetsize ({amount} Versuche): {successes} Erfolge, {totalTimeouts} Timeouts. In {end - start:.2f} Sekunden\n", end="")
