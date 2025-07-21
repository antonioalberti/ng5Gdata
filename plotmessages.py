import json
import re
import argparse
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import matplotlib.pyplot as plt


def parse_records(json_file):
    """
    Reads a JSON file line by line and returns a list of records.
    Each record corresponds to a "ng -" command found in the line.
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
                # Extract all "ng -" commands and their blocks
                cmd_blocks = re.findall(r'(ng\s+-[a-zA-Z0-9_-]+[^\[]*)\[(.*?)\]', data)
                for cmd_block, ids_block in cmd_blocks:
                    # Extract the command name
                    cmd_match = re.match(r'ng\s+-([a-zA-Z0-9_-]+)', cmd_block)
                    command = cmd_match.group(1) if cmd_match else None
                    # Extract all hexadecimal IDs in the block
                    ids = re.findall(r'([0-9A-F]{8,})', ids_block)
                    # Fill up to 4 IDs (HID, OSID, PID, BID), if present
                    hid = ids[0] if len(ids) > 0 else None
                    osid = ids[1] if len(ids) > 1 else None
                    pid = ids[2] if len(ids) > 2 else None
                    bid = ids[3] if len(ids) > 3 else None
                    records.append({
                        'time': time,
                        'command': command,
                        'hid': hid,
                        'osid': osid,
                        'pid': pid,
                        'bid': bid
                    })
            except json.JSONDecodeError:
                continue
    return records


def extract_points(records):
    """
    For each record, extract time, ID position (HID, OSID, PID, BID), and ng command.
    Returns a list of tuples (time, id_index, command) and a list of unique commands.
    """
    data_points = []  # (time, id_index, command)
    commands = []

    for rec in records:
        t = rec.get('time')
        command = rec.get('command')
        if not t or not command:
            continue
        
        # For each of the 4 IDs, generate a point
        for idx, _hex in enumerate([rec['hid'], rec['osid'], rec['pid'], rec['bid']]):
            data_points.append((t, idx, command))
        
        if command not in commands:
            commands.append(command)

    return data_points, commands

def extract_points_2d(records):
    """
    For each record, extract time, command, and PID.
    Returns a list of tuples (time, command, pid), a list of unique commands, and a list of unique pids.
    """
    data_points_2d = []  # (time, command, pid)
    commands = []
    pids = []

    for rec in records:
        t = rec.get('time')
        command = rec.get('command')
        pid = rec.get('pid')
        if not t or not command or not pid:
            continue
        
        data_points_2d.append((t, command, pid))
        
        if command not in commands:
            commands.append(command)
        if pid not in pids:
            pids.append(pid)

    return data_points_2d, commands, pids


def plot_3d(data_points, commands, records):
    """
    Plots points in a 3D graph: X=time, Y=ID type, Z=ng command.
    Each unique HID, OSID, PID, BID has a different color.
    Saves the plot as 'plot_3d.pdf'.
    """
    id_labels = ['HID', 'OSID', 'PID', 'BID']
    z_map = {cmd: i for i, cmd in enumerate(commands)}
    import matplotlib.cm as cm

    # Extract unique IDs for each type
    unique_ids = {0: set(), 1: set(), 2: set(), 3: set()}
    for rec in records:
        if rec['hid']:
            unique_ids[0].add(rec['hid'])
        if rec['osid']:
            unique_ids[1].add(rec['osid'])
        if rec['pid']:
            unique_ids[2].add(rec['pid'])
        if rec['bid']:
            unique_ids[3].add(rec['bid'])

    # Create color maps for each ID type
    color_maps = {}
    id_colors = {}
    for idx in range(4):
        ids_list = list(unique_ids[idx])
        cmap = cm.get_cmap('tab20', len(ids_list))
        color_maps[idx] = cmap
        for i, id_val in enumerate(ids_list):
            id_colors[(idx, id_val)] = cmap(i)

    xs = []
    ys = []
    zs = []
    colors = []

    # Create a mapping from (time, id_type, command) to ID value
    id_value_map = {}
    for rec in records:
        t = rec['time']
        command = rec['command']
        for idx, id_val in enumerate([rec['hid'], rec['osid'], rec['pid'], rec['bid']]):
            if id_val:
                id_value_map[(t, idx, command)] = id_val

    for p in data_points:
        t, id_type, command = p
        xs.append(t)
        ys.append(id_type)
        zs.append(z_map[command])
        id_val = id_value_map.get((t, id_type, command))
        color = id_colors.get((id_type, id_val), (0.5, 0.5, 0.5, 1))
        colors.append(color)

    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(xs, ys, zs, c=colors, s=30, edgecolor='k', alpha=0.85)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('ID Type')
    ax.set_yticks(list(range(len(id_labels))))
    ax.set_yticklabels(id_labels)
    ax.set_zlabel('ng Command')
    ax.set_zticks(list(z_map.values()))
    ax.set_zticklabels(list(z_map.keys()))
    plt.title('NovaGenesis: IDs and Commands over Time (color by ID)')
    plt.tight_layout()
    plt.savefig('plot_3d.pdf')
    plt.close()

def plot_2d(data_points_2d, commands, pids):
    """
    Plots points in a 2D graph: X=time, Y=ng command.
    Points are colored by PID.
    Saves the plot as 'plot_2d.pdf'.
    """
    import matplotlib.cm as cm
    color_map = cm.get_cmap('tab20', len(pids))
    pid_colors = {pid: color_map(i) for i, pid in enumerate(pids)}

    xs = [p[0] for p in data_points_2d]
    ys = [commands.index(p[1]) for p in data_points_2d]
    colors = [pid_colors[p[2]] for p in data_points_2d]

    fig, ax = plt.subplots(figsize=(12, 7))
    scatter = ax.scatter(xs, ys, c=colors, s=30, edgecolor='k', alpha=0.85)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('ng Command')
    ax.set_yticks(list(range(len(commands))))
    ax.set_yticklabels(commands)
    plt.title('NovaGenesis: Commands over Time (color by PID) - 2D')
    plt.tight_layout()

    # Create legend for PIDs
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='w', label=pid,
                              markerfacecolor=pid_colors[pid], markersize=10, markeredgecolor='k')
                       for pid in pids]
    ax.legend(handles=legend_elements, title='PID', loc='upper right')

    plt.savefig('plot_2d.pdf')
    plt.close()

def plot_pid_vs_command(records, commands):
    """
    Plots points with PIDs on Y-axis and ng commands as colors, with time on X-axis.
    Saves the plot as 'plot_pid_vs_command.pdf'.
    """
    import matplotlib.cm as cm
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # Extract unique PIDs
    pids = []
    for rec in records:
        pid = rec.get('pid')
        if pid and pid not in pids:
            pids.append(pid)

    # Map PIDs to Y positions
    pid_to_y = {pid: i for i, pid in enumerate(pids)}

    # Map commands to colors
    color_map = cm.get_cmap('tab20', len(commands))
    cmd_colors = {cmd: color_map(i) for i, cmd in enumerate(commands)}

    xs = []
    ys = []
    colors = []

    for rec in records:
        pid = rec.get('pid')
        command = rec.get('command')
        time = rec.get('time')
        if pid is None or command is None or time is None:
            continue
        xs.append(time)
        ys.append(pid_to_y[pid])
        colors.append(cmd_colors[command])

    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(xs, ys, c=colors, s=50, edgecolor='k', alpha=0.85)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('PID')
    ax.set_yticks(list(pid_to_y.values()))
    ax.set_yticklabels(pids)
    plt.title('NovaGenesis: Time vs PIDs colored by ng Command')
    plt.tight_layout()

    # Create legend for commands
    legend_elements = [Line2D([0], [0], marker='o', color='w', label=cmd,
                              markerfacecolor=cmd_colors[cmd], markersize=10, markeredgecolor='k')
                       for cmd in commands]
    ax.legend(handles=legend_elements, title='ng Command', loc='upper right')

    plt.savefig('plot_pid_vs_command.pdf')
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plots a 3D graph of NovaGenesis messages from a JSON file.'
    )
    parser.add_argument('json_file', help='Path to the JSON file (one message per line)')
    args = parser.parse_args()

    records = parse_records(args.json_file)
    data_points, commands = extract_points(records)
    data_points_2d, commands_2d, pids_2d = extract_points_2d(records)

    if not data_points:
        print('No points to plot. Check the data format.')
        return

    plot_3d(data_points, commands, records)
    plot_2d(data_points_2d, commands_2d, pids_2d)
    plot_pid_vs_command(records, commands)


if __name__ == '__main__':
    main()
