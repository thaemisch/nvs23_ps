import pandas as pd
import matplotlib.pyplot as plt

# Read the capture file into a pandas DataFrame
capture_file = 'capture.pcap'
df = pd.read_csv(capture_file, header=None, names=['time', 'seq'], usecols=[0,2])

# Split the DataFrame into 10 transmissions based on the sequence number
dfs = []
for i in range(10):
    start = i * 1000
    end = (i + 1) * 1000
    dfs.append(df.loc[start:end])

# Plot each transmission in a different color
colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w', 'orange', 'purple']
fig, ax = plt.subplots()
for i, df in enumerate(dfs):
    ax.plot(df['time'], df['seq'], color=colors[i], label=f'Transmission {i+1}')
ax.legend()
ax.set_xlabel('Time')
ax.set_ylabel('Sequence number')

# Save the plot as an image
plt.savefig('plot.png')

plt.show()