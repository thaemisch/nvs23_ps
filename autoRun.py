import argparse
import os

# Create an argument parser
parser = argparse.ArgumentParser(description='Process some command line arguments.')

# Add arguments
parser.add_argument('--tx', type=str)
parser.add_argument('--rx', type=str)
parser.add_argument('--amount', type=int, default=10)

# Parse the arguments
args = parser.parse_args()

# Set the variables
tx = args.tx.toLower()
rx = args.rx.toLower()
amount = args.amount

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
        os.system("python " + python_path + "&")
    elif rx == "java":
        os.system("javac " + java_path + ".java")
        os.system("java " + java_path + ".class" + "&")
    else:
        print("Invalid RX name entered")
        break
    # Execute the TX script
    if tx == "dart":
        os.system("dart run" + dart_path)
    elif tx == "node":
        os.system("node " + node_path)
    else:
        print("Invalid TX name entered")
        break
    print("Packet " + str(i) + " sent!")

print("Is Great Succes!")
    