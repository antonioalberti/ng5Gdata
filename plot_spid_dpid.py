import json
import re
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
import argparse

def parse_spid_dpid_records(json_file):
    """
    Parses the JSON file to extract S_PID, D_PID, time, and other ng commands per message.
    Returns a list of dicts with keys: time, s_pid, d_pid, other_cmds (list).
    """
    records = []
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                time = rec.get('time')
                data = rec.get('data', '')
                # Extract the ng -m --cl 0.1 command block
                m_match = re.search(r'ng\s+-m\s+--cl\s+0\.1\s+\[(.*?)\]', data)
                if not m_match:
                    continue
                m_block = m_match.group(1)
                # Extract the S_PID and D_PID groups from m_block
                # The format is: < 1 s DID > < 4 s S_HID S_OSID S_PID S_BID > < 4 s D_HID D_OSID D_PID D_BID >
                # We want the third and sixth hex values for S_PID and D_PID respectively
                hex_groups = re.findall(r'([0-9A-F]{8,})', m_block)
                if len(hex_groups) < 6:
                    continue
                s_pid = hex_groups[2]
                d_pid = hex_groups[5]

                # Extract other ng commands in the message (excluding the ng -m --cl 0.1)
                other_cmds = []
                cmd_blocks = re.findall(r'(ng\s+-[a-zA-Z0-9_-]+[^\[]*)\[(.*?)\]', data)
                for cmd_block, ids_block in cmd_blocks:
                    cmd_match = re.match(r'ng\s+-([a-zA-Z0-9_-]+)', cmd_block)
                    command = cmd_match.group(1) if cmd_match else None
                    if command and command != 'm':
                        other_cmds.append(command)

                records.append({
                    'time': time,
                    's_pid': s_pid,
                    'd_pid': d_pid,
                    'other_cmds': other_cmds
                })
            except json.JSONDecodeError:
                continue
    return records

def plot_spid_dpid(records):
    """
    Plots S_PID vs D_PID with markers and colors representing other ng commands.
    Time is represented as a color gradient.
    Saves plots as PDF files.
    """
    # Extract unique S_PIDs, D_PIDs, and other commands
    s_pids = sorted(set(rec['s_pid'] for rec in records))
    d_pids = sorted(set(rec['d_pid'] for rec in records))
    all_other_cmds = sorted(set(cmd for rec in records for cmd in rec['other_cmds']))

    # Map S_PID and D_PID to indices for plotting
    s_pid_to_x = {pid: i for i, pid in enumerate(s_pids)}
    d_pid_to_y = {pid: i for i, pid in enumerate(d_pids)}

    # Map other commands to marker styles and colors
    marker_styles = ['o', 's', '^', 'D', 'v', 'P', '*', 'X', 'h', '8']
    color_map = plt.get_cmap('tab10')
       # Use pyplot.get_cmap to avoid AttributeError
    cmd_to_marker = {}
    cmd_to_color = {}
    for i, cmd in enumerate(all_other_cmds):
        cmd_to_marker[cmd] = marker_styles[i % len(marker_styles)]
        cmd_to_color[cmd] = color_map(i)

    # Prepare figure
    fig, ax = plt.subplots(figsize=(14, 10))

    # Normalize time for color gradient
    times = [rec['time'] for rec in records]
    min_time, max_time = min(times), max(times)
    norm_times = [(t - min_time) / (max_time - min_time) if max_time > min_time else 0.5 for t in times]
    time_cmap = plt.get_cmap('viridis')
       # Use pyplot.get_cmap to avoid AttributeError

    # Plot points
    for rec, norm_t in zip(records, norm_times):
        x = s_pid_to_x[rec['s_pid']]
        y = d_pid_to_y[rec['d_pid']]
        # If multiple other commands, plot multiple points with different markers/colors
        if rec['other_cmds']:
            for cmd in rec['other_cmds']:
                ax.scatter(x, y, marker=cmd_to_marker[cmd], color=cmd_to_color[cmd], 
                           edgecolor='k', s=100, alpha=0.8)
        else:
            # If no other commands, plot with default marker and color by time
            ax.scatter(x, y, marker='o', color=time_cmap(norm_t), edgecolor='k', s=100, alpha=0.8)

    # Set axis labels and ticks
    ax.set_xlabel('Source PID (S_PID)')
    ax.set_ylabel('Destination PID (D_PID)')
    ax.set_xticks(range(len(s_pids)))
    ax.set_xticklabels(s_pids, rotation=90)
    ax.set_yticks(range(len(d_pids)))
    ax.set_yticklabels(d_pids)
    ax.set_title('S_PID vs D_PID with other ng commands as markers/colors')

    # Create legend for other commands
    legend_elements = [Line2D([0], [0], marker=cmd_to_marker[cmd], color=cmd_to_color[cmd], 
                              label=cmd, linestyle='None', markersize=10, markeredgecolor='k') 
                       for cmd in all_other_cmds]
    ax.legend(handles=legend_elements, title='Other ng Commands', loc='upper right')

    plt.tight_layout()
    plt.savefig('spid_dpid_plot.pdf')
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Plot S_PID vs D_PID with other ng commands.')
    parser.add_argument('json_file', help='Path to the JSON file (one message per line)')
    args = parser.parse_args()

    records = parse_spid_dpid_records(args.json_file)
    if not records:
        print('No valid records found in the file.')
        return

    plot_spid_dpid(records)

if __name__ == '__main__':
    main()
