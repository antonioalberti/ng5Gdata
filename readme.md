# Project Overview

This project contains Python scripts for analyzing and visualizing NovaGenesis message data from JSON files, as well as network packet capture data and performance metrics. The main focus is on parsing message records, filtering relevant data, and plotting timelines and performance graphs.

## Files in the Project

### plotmessages.py

This script reads a JSON file containing NovaGenesis messages (one JSON object per line), parses relevant command data, and generates a timeline bar chart visualization.

#### Features

- Parses "ng -m" command blocks to extract device and process IDs.
- Parses other "ng -X" command blocks to track command occurrences associated with destination process IDs (D_PID).
- Filters records by optional start and end time parameters.
- Plots a timeline bar chart showing occurrences of commands per D_PID.
- Supports customization of the X axis time range via command line arguments.
- Dynamically adjusts bar widths and label positions based on the time range.
- Adds grid lines on both X and Y axes for better readability.
- Labels for "info" commands are displayed vertically with a white background for clarity.
- Saves the plot as `plot_d_pid_commands_timeline.pdf`.

#### Usage

```bash
python3 plotmessages.py <json_file> [--start-time START] [--end-time END] [--label-offset-factor FACTOR]
```

- `<json_file>`: Path to the JSON file containing NovaGenesis messages (one JSON object per line).
- `--start-time`: (Optional) Start time (inclusive) for filtering messages and setting the X axis minimum.
- `--end-time`: (Optional) End time (inclusive) for filtering messages and setting the X axis maximum.
- `--label-offset-factor`: (Optional) Factor to control the horizontal offset of labels relative to bar width (default is 0.5).

---

### analyze_pcap.py

This script processes a PCAPNG network capture file (`ORIGINAL.pcapng`), extracts TCP/UDP packet payloads containing specific NovaGenesis commands, normalizes timestamps relative to the first packet, and outputs the extracted data as JSON lines in `extracted_data.json`. It also filters out ICMP packets and non-relevant data.

#### Features

- Parses network packets to extract NovaGenesis command data.
- Normalizes timestamps to start from zero.
- Outputs extracted data with source and destination MAC addresses.
- Filters out irrelevant packets.
- Automatically filters relevant messages into `relevant.json`.

#### Usage

```bash
python3 analyze_pcap.py
```

The script reads `ORIGINAL.pcapng` and produces `extracted_data.json` and `relevant.json`.

---

### filter.py

This script filters relevant NovaGenesis messages from a JSON lines file based on specific command substrings and optional time intervals.

#### Features

- Filters messages containing specific NovaGenesis commands.
- Supports filtering by start and end time intervals.
- Outputs filtered messages to a specified JSON lines file.

#### Usage

```bash
python3 filter.py [--input_file INPUT] [--output_file OUTPUT] [--begin_interval START] [--end_interval END]
```

- `--input_file`: Input JSON lines file (default: `extracted_data.json`).
- `--output_file`: Output JSON lines file (default: `relevant.json`).
- `--begin_interval`: Start time in seconds to include messages.
- `--end_interval`: End time in seconds to include messages.

---

### plotdata.py

This script reads performance data from `data.csv` and generates two plots:

1. Data Transfer Rate plot comparing traditional CDN and NovaGenesis.
2. Transfer Time (Delay) plot comparing traditional CDN and NovaGenesis.

#### Features

- Reads CSV data with transfer rates and times.
- Calculates cumulative averages and standard deviations.
- Plots cumulative averages with error bars and instantaneous values.
- Saves plots as `data_transfer_rate_plot.pdf` and `delay_plot.pdf`.

#### Usage

```bash
python3 plotdata.py
```

Ensure `data.csv` is present in the same directory.

---

## Additional Notes

- JSON input files should contain one JSON object per line.
- Plots are saved as PDF files in the current directory.
- Scripts print processing information and warnings to the console.
- Bar widths and label positions in plots adjust dynamically based on time ranges and user parameters.

---

For any questions or issues, please refer to the source code comments or contact the project maintainer.
