import json
import re
import argparse
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D


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
                print(f"Processing line {line_number}: time={time}, data={data}")

                # Parse the "ng -m" command block specifically
                ng_m_match = re.search(r'ng\s+-m\s+--cl\s+[^\[]*\[(.*?)\]', data)
                did = s_hid = s_osid = s_pid = s_bid = None
                d_hid = d_osid = d_pid = d_bid = None
                if ng_m_match:
                    block_content = ng_m_match.group(1)
                    # Extract the three vectors enclosed in angle brackets <>
                    vectors = re.findall(r'<\s*(.*?)\s*>', block_content)
                    if len(vectors) >= 3:
                        # Parse DID from first vector: extract only 8-char hex strings
                        did_ids = re.findall(r'\b[0-9A-F]{8}\b', vectors[0])
                        did = did_ids[0] if did_ids else None
                        # Parse source IDs from second vector: extract only 8-char hex strings
                        src_ids = re.findall(r'\b[0-9A-F]{8}\b', vectors[1])
                        s_hid = src_ids[0] if len(src_ids) > 0 else None
                        s_osid = src_ids[1] if len(src_ids) > 1 else None
                        s_pid = src_ids[2] if len(src_ids) > 2 else None
                        s_bid = src_ids[3] if len(src_ids) > 3 else None
                        # Parse destination IDs from third vector: extract only 8-char hex strings
                        dst_ids = re.findall(r'\b[0-9A-F]{8}\b', vectors[2])
                        d_hid = dst_ids[0] if len(dst_ids) > 0 else None
                        d_osid = dst_ids[1] if len(dst_ids) > 1 else None
                        d_pid = dst_ids[2] if len(dst_ids) > 2 else None
                        d_bid = dst_ids[3] if len(dst_ids) > 3 else None
                        print(f"  Parsed ng -m IDs: DID={did}, S_HID={s_hid}, S_OSID={s_osid}, S_PID={s_pid}, S_BID={s_bid}, D_HID={d_hid}, D_OSID={d_osid}, D_PID={d_pid}, D_BID={d_bid}")
                    else:
                        print(f"Warning: Expected at least 3 vectors in ng -m block at line {line_number}, found {len(vectors)}")
                else:
                    print(f"Warning: No ng -m command block found at line {line_number}")

                # Parse other "ng -X" command blocks (excluding ng -m)
                other_cmd_blocks = re.findall(r'ng\s+-(?!m)([a-zA-Z0-9_-]+)[^\[]*\[(.*?)\]', data)
                # Extract unique commands X to consider from relevant.json or user input
                # For now, collect all commands found
                commands_found = set()
                for cmd, block in other_cmd_blocks:
                    print(f"  Found other command: ng -{cmd} with block: {block}")
                    commands_found.add(cmd)

                # For each other command block, record the command occurrence associated with the D_PID from ng -m block
                other_records = []
                for cmd, block in other_cmd_blocks:
                    print(f"  Found other command: ng -{cmd} (recording occurrence only)")
                    label = None
                    if cmd == 'info':
                        # Extract the string inside angle brackets <> in the block for label
                        angle_contents = re.findall(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                        if angle_contents:
                            label = angle_contents[-1]  # Take last string inside angle brackets as label
                    if d_pid:
                        rec_entry = {
                            'time': time,
                            'command': cmd,
                            'd_pid': d_pid
                        }
                        if label:
                            rec_entry['label'] = label
                        other_records.append(rec_entry)
                    else:
                        print(f"    Warning: No D_PID available from ng -m block to associate with command ng -{cmd}")

                # Append the ng -m record as well
                records.append({
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
                    'other_cmds': other_records
                })

                #input("Press Enter to continue to next line...")
                print(" ")
            except json.JSONDecodeError:
                print(f"Warning: JSON decode error at line {line_number}, skipping line.")
                continue
    return records


def plot_pid_vs_command(records, commands, start_time=None, end_time=None, label_offset_factor=0.5):
    """
    Plots a timeline bar chart for each D_PID from other "ng -X" commands, showing bars for each command occurrence.
    """
    # Collect all other_cmds from records
    other_cmd_records = []
    for rec in records:
        other_cmd_records.extend(rec.get('other_cmds', []))

    print(f"Total other command records: {len(other_cmd_records)}")

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

    print(f"D_PID-command keys: {list(dpid_command_times.keys())}")

    # Get unique D_PIDs and commands
    d_pids = sorted(set(d_pid for d_pid, _ in dpid_command_times.keys()))
    commands = sorted(set(command for _, command in dpid_command_times.keys()))

    # Build Y-axis labels and positions for D_PID-command combinations
    y_labels_dpid = []
    y_positions_dpid = {}
    pos = 0
    for d_pid in d_pids:
        for command in commands:
            y_labels_dpid.append(f"{d_pid} -{command}")
            y_positions_dpid[(d_pid, command)] = pos
            pos += 1

    # Assign colors to commands for better visualization
    cmap = plt.get_cmap('tab10')
    command_colors = {cmd: cmap(i % 10) for i, cmd in enumerate(commands)}

    # Plot bars for D_PID-command
    fig2, ax2 = plt.subplots(figsize=(14, max(6, len(y_labels_dpid)*0.5)))

    # Determine min and max time for X-axis limits
    all_times = [t for times in dpid_command_times.values() for t, _ in times]
    if all_times:
        # Use start_time and end_time from parameters if provided, else fallback to min/max times
        min_time = start_time if start_time is not None else min(all_times)
        max_time = end_time if end_time is not None else max(all_times)
        print(f"Min time: {min_time}, Max time: {max_time}")
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
        print(f"\nBars for D_PID: {d_pid}, Command: {command}")
        for t, label in time_label_list:
            print(f"  Time: {t:.4f}")
            ax2.barh(y, bar_width, left=t, height=0.6, color=color, edgecolor=color, alpha=0.7)
            if command == 'info' and label:
                ax2.text(
                    round(t + label_offset, 4),
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
    #ax2.set_title('NovaGenesis: Timeline of D_PID and Commands')

    # Create legend for commands
    legend_elements = [Line2D([0], [0], color=command_colors[cmd], lw=4, label=cmd) for cmd in commands]
    ax2.legend(handles=legend_elements, title='NovaGenesis actions')

    plt.tight_layout()
    plt.grid(True, which='both', axis='both', linestyle='--', linewidth=0.5)  # Add X and Y grids
    plt.savefig('plot_d_pid_commands_timeline.pdf')
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
    commands = []
    for rec in records:
        cmd = rec.get('command')
        if cmd and cmd not in commands:
            commands.append(cmd)

    plot_pid_vs_command(records, commands, start_time=args.start_time, end_time=args.end_time, label_offset_factor=args.label_offset_factor)


if __name__ == '__main__':
    main()
