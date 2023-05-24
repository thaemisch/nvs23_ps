# Messungen

| TX/RX | &nbsp;&nbsp;&nbsp;Java&nbsp;&nbsp;&nbsp; | Python |
:-------------------------:|:-------------------------:|:-------------------------:
| Dart | ![100_Dart_Java](Dart_Java/plot100.png) 0.9 - 0.9 MB/s ![1400_Dart_Java](Dart_Java/plot1400.png) 8.2 - 8.4 MB/s ![60000_Dart_Java](Dart_Java/plot60000.png) 53.3 - 58.3 MB/s | ![100_Dart_Python](Dart_Python/plot100.png) 0.5 - 0.6 MB/s ![1400_Dart_Python](Dart_Python/plot1400.png) 3.9 - 7.7 MB/s ![60000_Dart_Python](Dart_Python/plot60000.png) 52.8 - 61.8 MB/s |
| Node | ![100_Node_Java](Node_Java/plot100.png) 1.2 - 1.3 MB/s ![1400_Node_Java](Node_Java/plot1400.png) 10.4 - 11.1 MB/s ![60000_Node_Java](Node_Java/plot60000.png) 68.2 - 76.4 MB/s | ![100_Node_Python](Node_Python/plot100.png) 0.5 - 1.0 MB/s ![1400_Node_Python](Node_Python/plot1400.png) 4.6 - 10.6 MB/s ![60000_Node_Python](Node_Python/plot60000.png) 101.3 - 120.9 MB/s |

| Source | Target | Packetsize | Duration* (sec) | Speed (MB/s) |
|:------:|:------:|:----------:|:--------------:|:------------:|
|  dart  |  java  |    100     |     3.41       |   0.9 - 0.9  |
|  dart  |  java  |    1400    |     1.96       |   8.2 - 8.4  |
|  dart  |  java  |   60000    |     1.98       |  53.3 - 58.3 |
|  dart  | python |    100     |     3.65       |   0.5 - 0.6  |
|  dart  | python |    1400    |     1.34       |   3.9 - 7.7  |
|  dart  | python |   60000    |     1.34       |  52.8 - 61.8 |
|  node  |  java  |    100     |     1.97       |   1.2 - 1.3  |
|  node  |  java  |    1400    |     0.98       |  10.4 - 11.1 |
|  node  |  java  |   60000    |     0.82       |  68.2 - 76.4 |
|  node  | python |     100    |     2.11       |   0.5 - 1.0  |
|  node  | python |    1400    |     0.27       |   4.6 - 10.6 |
|  node  | python |   60000    |     0.10       | 101.3 - 120.9|

*Duration: Program runtime (start = TX start, end = RX end)