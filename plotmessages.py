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


def plot_3d(data_points, commands, records):
    """
    Plots points in a 3D graph: X=time, Y=ID type, Z=ng command.
    Each "ng -" command has a different color.
    """
    id_labels = ['HID', 'OSID', 'PID', 'BID']
    z_map = {cmd: i for i, cmd in enumerate(commands)}
    import matplotlib.cm as cm
    color_map = cm.get_cmap('tab20', len(commands))
    cmd_colors = {cmd: color_map(i) for i, cmd in enumerate(commands)}

    xs = [p[0] for p in data_points]
    ys = [p[1] for p in data_points]
    zs = [z_map[p[2]] for p in data_points]
    colors = [cmd_colors[p[2]] for p in data_points]

    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(xs, ys, zs, c=colors, s=30, edgecolor='k', alpha=0.85)

    ax.set_xlabel('Tempo (s)')
    ax.set_ylabel('Tipo de ID')
    ax.set_yticks(list(range(len(id_labels))))
    ax.set_yticklabels(id_labels)
    ax.set_zlabel('Comando ng')
    ax.set_zticks(list(z_map.values()))
    ax.set_zticklabels(list(z_map.keys()))
    plt.title('NovaGenesis: IDs e Comandos ao longo do tempo (cores por comando)')
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plots a 3D graph of NovaGenesis messages from a JSON file.'
    )
    parser.add_argument('json_file', help='Path to the JSON file (one message per line)')
    args = parser.parse_args()

    records = parse_records(args.json_file)
    data_points, commands = extract_points(records)

    if not data_points:
        print('No points to plot. Check the data format.')
        return

    plot_3d(data_points, commands, records)


if __name__ == '__main__':
    main()
