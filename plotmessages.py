import json
import re
import collections
from collections import Counter
import argparse
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator


def parse_records(json_file):
    """
    Reads a JSON file line by line and returns a list of records.
    Each record corresponds to the parsed IDs from the "ng -m" command block and other "ng -X" commands in the line.
    """
    records = []
    with open(json_file, 'r', encoding='utf-8') as f:
        line_number = 0
        for line in f:
            line_number += 1
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                time = rec.get('time')
                data = rec.get('data', '')
                
                # Improved logging: Print line number, time, and data
                print(f"Processing line {line_number}: time={time}")
                # print(f"  Data: {data}") # Optionally print full data if needed, but it can be very long. User example doesn't show full data.

                # --- Count and log occurrences of main commands ---
                main_cmd_counts = Counter()
                main_cmd_counts['ng -m'] += data.count('ng -m')
                main_cmd_counts['ng -d'] += data.count('ng -d')
                main_cmd_counts['ng -scn'] += data.count('ng -scn')
                
                if any(count > 0 for count in main_cmd_counts.values()):
                    print("  Main Command Occurrences:")
                    for cmd, count in main_cmd_counts.items():
                        if count > 0:
                            print(f"    {cmd}: {count} occurrence(s)")

                # --- Parse the "ng -m" command block specifically ---
                ng_m_match = re.search(r'ng\s+-m\s+--cl\s+[^\[]*\[(.*?)\]', data)
                
                did = s_hid = s_osid = s_pid = s_bid = None
                d_hid = d_osid = d_pid = d_bid = None
                
                parsed_ids_info = {} # Dictionary to store parsed IDs and their counts for this line

                if ng_m_match:
                    block_content = ng_m_match.group(1)
                    vectors = re.findall(r'<\s*(.*?)\s*>', block_content)
                    
                    if len(vectors) >= 3:
                        # Parse DID from first vector
                        did_ids = re.findall(r'\b([0-9A-F]{8})\b', vectors[0])
                        if did_ids:
                            did = did_ids[0]
                            parsed_ids_info['DID'] = did
                        
                        # Parse source IDs from second vector
                        src_ids = re.findall(r'\b([0-9A-F]{8})\b', vectors[1])
                        if len(src_ids) > 0:
                            s_hid = src_ids[0]
                            parsed_ids_info['S_HID'] = s_hid
                        if len(src_ids) > 1:
                            s_osid = src_ids[1]
                            parsed_ids_info['S_OSID'] = s_osid
                        if len(src_ids) > 2:
                            s_pid = src_ids[2]
                            parsed_ids_info['S_PID'] = s_pid
                        if len(src_ids) > 3:
                            s_bid = src_ids[3]
                            parsed_ids_info['S_BID'] = s_bid

                        # Parse destination IDs from third vector
                        dst_ids = re.findall(r'\b([0-9A-F]{8})\b', vectors[2])
                        if len(dst_ids) > 0:
                            d_hid = dst_ids[0]
                            parsed_ids_info['D_HID'] = d_hid
                        if len(dst_ids) > 1:
                            d_osid = dst_ids[1]
                            parsed_ids_info['D_OSID'] = d_osid
                        if len(dst_ids) > 2:
                            d_pid = dst_ids[2]
                            parsed_ids_info['D_PID'] = d_pid
                        if len(dst_ids) > 3:
                            d_bid = dst_ids[3]
                            parsed_ids_info['D_BID'] = d_bid
                        
                        # Print parsed IDs with counts (each ID type appears once per ng -m block)
                        if parsed_ids_info:
                            print(f"\n   Parsed ng -m IDs:")
                            for id_type, id_val in parsed_ids_info.items():
                                print(f"     {id_type}={id_val} (1)") # Each ID type is found once per ng -m block
                    else:
                        print(f"Warning: Expected at least 3 vectors in ng -m block at line {line_number}, found {len(vectors)}")
                else:
                    print(f"Warning: No ng -m command block found at line {line_number}")

                # --- Parse and count other "ng -X" command blocks ---
                other_cmd_blocks = re.findall(r'ng\s+-(?!m)([a-zA-Z0-9_-]+)[^\[]*\[(.*?)\]', data)
                
                other_cmd_counts = Counter()
                for cmd, block in other_cmd_blocks:
                    other_cmd_counts[f"ng -{cmd}"] += 1
                    # Print details for each found other command block
                    print(f"  Found other command: ng -{cmd} with block: {block}")
                
                # Print counts of other commands
                if other_cmd_counts:
                    print("  Other Command Occurrences:")
                    for cmd_str, count in other_cmd_counts.items():
                        print(f"    {cmd_str}: {count} occurrence(s)")

                # --- Prepare records for plotting function ---
                # Create a record for the ng -m command itself
                ng_m_record = {
                    'time': time,
                    'did': did,
                    's_hid': s_hid,
                    's_osid': s_osid,
                    's_pid': s_pid,
                    's_bid': s_bid,
                    'd_hid': d_hid,
                    'd_osid': d_osid,
                    'd_pid': d_pid,
                    'd_bid': d_bid,
                    'other_cmds': [] # Initialize other_cmds list
                }

                # Populate other_cmds list for the plotting function
                for cmd, block in other_cmd_blocks:
                    label = None
                    if cmd == 'info':
                        angle_contents = re.findall(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                        if angle_contents:
                            label = angle_contents[-1]
                    
                    # Only add to other_cmds if d_pid is available from the ng -m block
                    if d_pid:
                        rec_entry = {
                            'time': time,
                            'command': cmd,
                            'd_pid': d_pid
                        }
                        if label:
                            rec_entry['label'] = label
                        ng_m_record['other_cmds'].append(rec_entry)
                    else:
                        print(f"    Warning: No D_PID available from ng -m block to associate with command ng -{cmd} at line {line_number}")

                # Append the ng -m record to the main records list
                records.append(ng_m_record)

                # Add a blank line for better readability between processed lines
                print(" ")
            except json.JSONDecodeError:
                print(f"Warning: JSON decode error at line {line_number}, skipping line.")
                continue
    return records


def plot_pid_vs_command(records, commands, json_file, start_time=None, end_time=None, label_offset_factor=0.5):
    """
    Plots a timeline bar chart for each D_PID from other "ng -X" commands, showing bars for each command occurrence.
    """
    import os

    # Construct the output filename based on input parameters
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_filename = f"{base_name}_timeline"
    if start_time is not None:
        output_filename += f"_start{start_time:.2f}"
    if end_time is not None:
        output_filename += f"_end{end_time:.2f}"
    output_filename += ".pdf"

    # Collect all other_cmds from records
    other_cmd_records = []
    for rec in records:
        other_cmd_records.extend(rec.get('other_cmds', []))

    print(f"Total other command records for plotting: {len(other_cmd_records)}")

    # Build mapping: (d_pid, command) -> list of times
    dpid_command_times = {}
    for rec in other_cmd_records:
        d_pid = rec.get('d_pid')
        command = rec.get('command')
        time = rec.get('time')
        if not d_pid or not command or not time:
            continue
        key = (d_pid, command)
        if key not in dpid_command_times:
            dpid_command_times[key] = []
        dpid_command_times[key].append((time, rec.get('label')))

    print(f"D_PID-command keys for plotting: {list(dpid_command_times.keys())}")

    # --- Add detailed summary of bars to be plotted ---
    print("\n--- Plotting Summary ---")
    if not dpid_command_times:
        print("No data available for plotting.")
    else:
        # Sort keys for consistent output
        sorted_keys = sorted(dpid_command_times.keys())
        for (d_pid, command), time_label_list in dpid_command_times.items():
            print(f"D_PID: {d_pid}, Command: {command}")
            for t, label in time_label_list:
                print(f"  - Time: {t:.4f}") # Display time with 4 decimal places for consistency
                # Optionally print label if it exists and is relevant
                # if label:
                #     print(f"    Label: {label}")
    print("------------------------\n")

    # Get unique D_PIDs and commands
    d_pids = sorted(set(d_pid for d_pid, _ in dpid_command_times.keys()))
    commands_for_plot = sorted(set(command for _, command in dpid_command_times.keys()))

    # Build Y-axis labels and positions for D_PID-command combinations
    y_labels_dpid = []
    y_positions_dpid = {}
    pos = 0
    for d_pid in d_pids:
        for command in commands_for_plot:
            y_labels_dpid.append(f"{d_pid} -{command}")
            y_positions_dpid[(d_pid, command)] = pos
            pos += 1

    # Assign colors to commands for better visualization
    cmap = plt.get_cmap('tab10')
    command_colors = {cmd: cmap(i % 10) for i, cmd in enumerate(commands_for_plot)}

    # Plot bars for D_PID-command
    fig2, ax2 = plt.subplots(figsize=(14, max(6, len(y_labels_dpid)*0.5)))

    # Determine min and max time for X-axis limits
    all_times = [t for times in dpid_command_times.values() for t, _ in times]
    if all_times:
        # Use start_time and end_time from parameters if provided, else fallback to min/max times
        min_time = start_time if start_time is not None else min(all_times)
        max_time = end_time if end_time is not None else max(all_times)
        print(f"Plotting X-axis range: Min time={min_time:.4f}, Max time={max_time:.4f}")
        ax2.set_xlim(min_time, max_time)  # Use exact limits from parameters or data

        # Calculate bar width and label offset based on X axis length
        x_range = max_time - min_time
        bar_width = max(0.01, x_range * 0.005)  # 2% of x_range, minimum 0.01
        label_offset = bar_width * label_offset_factor
    else:
        print("No times found for plotting.")
        bar_width = 0.05
        label_offset = 0.025

    for (d_pid, command), time_label_list in dpid_command_times.items():
        y = y_positions_dpid[(d_pid, command)]
        color = command_colors.get(command, 'gray')

        # Log all bars to be plotted with spacing for readability
        # print(f"\nBars for D_PID: {d_pid}, Command: {command}") # This can be too verbose
        for t, label in time_label_list:
            # print(f"  Time: {t:.4f}") # This can be too verbose
            ax2.barh(y, bar_width, left=t, height=0.6, color=color, edgecolor=color, alpha=0.7)
            if command == 'info' and label:
                ax2.text(
                    round(t - label_offset, 4),
                    y,
                    label,
                    va='bottom',
                    ha='center',
                    rotation=90,
                    fontsize=8,
                    color=color,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1.5, alpha=0.8)
                )

    ax2.set_yticks(range(len(y_labels_dpid)))
    ax2.set_yticklabels(y_labels_dpid)
    ax2.set_xlabel('Time (s)')
    #ax2.set_title('NovaGenesis: Timeline of D_PID and Commands') # Title is commented out in original

    # Create legend for commands
    legend_elements = [Line2D([0], [0], color=command_colors[cmd], lw=4, label=cmd) for cmd in commands_for_plot]
    ax2.legend(handles=legend_elements, title='NovaGenesis Actions run')

    plt.tight_layout()
    # Configure denser grid lines on X-axis
    ax2.xaxis.set_minor_locator(AutoMinorLocator(5))  # Add minor ticks between major ticks
    plt.grid(True, which='both', axis='both', linestyle='--', linewidth=0.5)  # Add X and Y grids
    plt.grid(True, which='minor', axis='x', linestyle=':', linewidth=0.3, alpha=0.5)  # Add minor X grid lines
    plt.savefig(output_filename)
    plt.close(fig2)


def main():
    parser = argparse.ArgumentParser(
        description='Plots a graph of NovaGenesis messages from a JSON file.'
    )
    parser.add_argument('json_file', help='Path to the JSON file (one message per line)')
    parser.add_argument('--start-time', type=float, default=None, help='Start time for X-axis (inclusive)')
    parser.add_argument('--end-time', type=float, default=None, help='End time for X-axis (inclusive)')
    parser.add_argument('--label-offset-factor', type=float, default=0.5, help='Label offset factor relative to bar width')
    args = parser.parse_args()

    records = parse_records(args.json_file)

    # Filter records by start and end time if specified
    if args.start_time is not None or args.end_time is not None:
        filtered_records = []
        for rec in records:
            time = rec.get('time')
            if time is None:
                continue
            if args.start_time is not None and time < args.start_time:
                continue
            if args.end_time is not None and time > args.end_time:
                continue
            filtered_records.append(rec)
        records = filtered_records

    # Extract unique commands from records for plotting
    # This part needs to extract commands from the 'other_cmds' list within each record
    all_commands_in_records = set()
    for rec in records:
        for other_cmd_rec in rec.get('other_cmds', []):
            all_commands_in_records.add(other_cmd_rec.get('command'))
    
    # The original code used 'commands' which was not populated correctly.
    # It should be derived from the actual commands found in the records.
    # Let's use the unique commands found in other_cmd_records for plotting.
    # The plot_pid_vs_command function already derives commands from dpid_command_times keys.
    # So, this 'commands' variable might not be strictly necessary for the plotting function as it is now.
    # However, if it were used elsewhere, it would need to be populated correctly.
    # For now, let's ensure it's populated with unique commands from other_cmds.
    commands_for_plot_legend = sorted(list(all_commands_in_records))


    plot_pid_vs_command(records, commands_for_plot_legend, args.json_file, start_time=args.start_time, end_time=args.end_time, label_offset_factor=args.label_offset_factor)


if __name__ == '__main__':
    main()
