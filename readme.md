# NovaGenesis 5G Network Analysis Toolkit

## Table of Contents
- [Project Overview](#project-overview)
- [Recommended Workflow](#recommended-workflow)
- [Script Documentation](#script-documentation)
  - [analyze_pcap.py](#analyze_pcappy)
  - [filter.py](#filterpy)
  - [plotmessages.py](#plotmessagespy)
  - [plot_sequence.py](#plot_sequencepy)
  - [plotdata.py](#plotdatapy)
- [Setup & Dependencies](#setup--dependencies)
- [File Structure](#file-structure)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Project Overview

This toolkit provides Python scripts for analyzing and visualizing NovaGenesis message data from network captures (PCAPNG) and performance metrics. Key capabilities include:

- Packet capture analysis and message extraction
- Advanced message filtering
- Timeline visualization of command sequences
- Performance metric plotting (transfer rates, delays)

## Recommended Workflow

1. **Capture Analysis**  
   ```bash
   python analyze_pcap.py
   ```
   - Processes `ORIGINAL.pcapng`
   - Outputs: `extracted_data.json`

2. **Message Filtering**  
   ```bash
   python filter.py --input_file extracted_data.json --output_file relevant.json \
     --begin_interval 4913.24 --end_interval 4914.00
   ```

3. **Timeline Visualization**  
   ```bash
   python plotmessages.py relevant.json --start-time 4913.24 --end-time 4914.00
   ```

4. **Sequence Diagram Generation**  
   ```bash
   python plot_sequence.py extracted_data.json --start-time 4913 --end-time 4914 --figsize-width 16 --figsize-height 3
   ```

5. **Performance Analysis**  
   ```bash
   python plotdata.py
   ```

## Script Documentation

### analyze_pcap.py

**Purpose**: Extract NovaGenesis messages from network captures

**Features**:
- TCP/UDP payload extraction
- Timestamp normalization
- MAC address tracking
- Automatic relevant message filtering

**Output Files**:
- `extracted_data.json` (raw extracted messages)
- `relevant.json` (filtered messages)

### filter.py

**Purpose**: Filter messages by command type and time range

**Parameters**:
```bash
--input_file     Input JSON file (default: extracted_data.json)
--output_file    Output JSON file (default: relevant.json)  
--begin_interval Start time in seconds
--end_interval   End time in seconds
```

### plotmessages.py

**Purpose**: Visualize command timelines

**Example**:
```bash
python plotmessages.py relevant.json \
  --start-time 5190.00 \
  --end-time 5200.00 \
  --label-offset-factor 0.3
```

**Output**: `plot_d_pid_commands_timeline.pdf`

### plot_sequence.py

**Purpose**: Generate sequence diagrams with accurate time representation and discontinuities

**Features**:
- Extracts S_PID and D_PID from ng -m command blocks
- Parses ng -X commands (info, notify, p, scn) for detailed information
- Accurate Y-axis time representation with discontinuities for large gaps
- Process mapping (P1, P2, P3, etc.) for better visualization
- Configurable figure dimensions
- High-precision time labels (6 decimal places)
- Color-coded message arrows based on direction
- Payload information display for .txt and .jpg files

**Parameters**:
```bash
json_file         Input JSON file (one message per line)
--start-time      Start time for filtering (inclusive)
--end-time        End time for filtering (inclusive)
--figsize-width   Figure width in inches (default: 16)
--figsize-height  Figure height in inches (default: 9)
```

**Example**:
```bash
python plot_sequence.py extracted_data.json --start-time 4913 --end-time 4914 --figsize-width 16 --figsize-height 3
```

**Output**: `extracted_data_sequence_start4913.00_end4914.00.pdf`

### plotdata.py

**Purpose**: Generate performance graphs

**Output Files**:
- `data_transfer_rate_plot.pdf`
- `delay_plot.pdf`

## Setup & Dependencies

**Requirements**:
- Python 3.8+
- pip 20.0+

**Setup**:
```bash
bash setup_venv.sh
```

**Dependencies** (see requirements.txt):
- matplotlib==3.5.1
- pandas==1.3.5  
- scapy==2.4.5
- numpy==1.21.4

## File Structure

```
.
├── analyze_pcap.py       # Packet analysis
├── filter.py             # Message filtering
├── plotmessages.py       # Timeline plotting
├── plot_sequence.py      # Sequence diagram generation
├── plotdata.py           # Performance plotting
├── data.csv              # Performance metrics
├── ORIGINAL.pcapng       # Network capture
├── requirements.txt      # Dependencies
└── setup_venv.sh         # Setup script
```

## Examples

**Sample Filtered Output** (relevant.json):
```json
{"timestamp": 4913.24, "command": "ng -m", "pid": "PID_123"}
{"timestamp": 4913.45, "command": "ng -info", "pid": "PID_456"}
```

**Generated Plot**:
![Timeline Example](extracted_data_timeline_start4913.24_end4914.00_named.png)

## Troubleshooting

**Common Issues**:
1. Missing PCAPNG file: Ensure `ORIGINAL.pcapng` exists
2. Dependency errors: Run `pip install -r requirements.txt`
3. Plot rendering issues: Try different matplotlib backends

For additional help, consult the source code comments or contact the maintainer.
