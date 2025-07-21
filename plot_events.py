import json
import re
import matplotlib.pyplot as plt

def plot_events(input_file='relevant.json', output_file='events_plot.pdf'):
    # Regex to find commands starting with "ng -"
    command_pattern = re.compile(r'(ng -[a-zA-Z0-9_-]+)')

    events = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line)
                time = obj.get("time")
                data = obj.get("data", "")
                src_mac = obj.get("src_mac", "")
                dst_mac = obj.get("dst_mac", "")
                commands = command_pattern.findall(data)
                for cmd in commands:
                    # Combine command and MAC address for category
                    # Using src_mac here; could also consider dst_mac or both
                    category = f"{cmd} | {src_mac}"
                    events.append((time, category))
            except Exception:
                continue

    if not events:
        print("No events found to plot.")
        return

    # Extract unique categories for Y axis
    unique_categories = sorted(set(cat for _, cat in events))
    category_to_y = {cat: i for i, cat in enumerate(unique_categories)}

    # Prepare data for plotting
    x = [event[0] for event in events]
    y = [category_to_y[event[1]] for event in events]

    import matplotlib.colors as mcolors

    plt.figure(figsize=(12, 8))

    # Extract unique MAC addresses for color mapping
    mac_addresses = sorted(set(cat.split(' | ')[1] for cat in unique_categories))
    colors = list(mcolors.TABLEAU_COLORS.values())
    color_map = {mac: colors[i % len(colors)] for i, mac in enumerate(mac_addresses)}

    # Prepare colors for each event based on MAC address
    event_colors = [color_map[cat.split(' | ')[1]] for cat in unique_categories]
    # Map each event's MAC to color
    colors_for_points = [color_map[cat.split(' | ')[1]] for cat in y]

    # Plot with squares instead of circles, colored by MAC
    plt.scatter(x, y, marker='s', c=colors_for_points)

    plt.yticks(range(len(unique_categories)), unique_categories)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Command | MAC Address')
    plt.title('Events over Time by Command and MAC')
    plt.grid(True, axis='x')

    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")

if __name__ == '__main__':
    plot_events()
