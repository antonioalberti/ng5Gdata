# Project Overview

This project contains Python scripts for analyzing and visualizing NovaGenesis message data from JSON files. The main focus is on parsing message records and plotting timelines of commands associated with process IDs (D_PID).

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

#### Example

```bash
python3 plotmessages.py relevant.json --start-time 5675 --end-time 5675.3 --label-offset-factor 0.5
```

This command will parse the `relevant.json` file, filter messages between 5675 and 5675.3 seconds, and generate a timeline plot with labels offset by half the bar width.

---

## Additional Notes

- The JSON input file should contain one JSON object per line, each representing a NovaGenesis message.
- The plot is saved as a PDF file named `plot_d_pid_commands_timeline.pdf` in the current directory.
- The script prints processing information and warnings to the console for transparency.
- The bar widths and label positions automatically adjust based on the selected time range for optimal visualization.

---

For any questions or issues, please refer to the source code comments or contact the project maintainer.
