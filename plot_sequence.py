import json
import re
from collections import Counter
import argparse
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


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
                
                # Extract S_PID and D_PID from the ng -m command
                # Find the ng -m command block
                ng_m_match = re.search(r'ng\s+-m\s+--cl\s+[^\[]*\[(.*?)\]', data)
                
                s_pid = None
                d_pid = None
                
                if ng_m_match:
                    block_content = ng_m_match.group(1)
                    # Find all vectors in the block
                    vectors = re.findall(r'<\s*(.*?)\s*>', block_content)
                    
                    # Look for the specific pattern with "< 4 s" to extract S_PID and D_PID
                    # According to the user, S_PID is the third value in the first "< 4 s" vector
                    # and D_PID is the third value in the second "< 4 s" vector
                    four_s_pattern = r'<\s*4\s*s\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+([0-9A-F]{8})'
                    matches = re.findall(four_s_pattern, block_content)
                    
                    if len(matches) >= 2:
                        # First match: S_PID is the third value (index 2)
                        s_pid = matches[0][2]
                        # Second match: D_PID is the third value (index 2)
                        d_pid = matches[1][2]
                    elif len(matches) == 1:
                        # Only one match found, use it for S_PID
                        s_pid = matches[0][2]
                
                # Parse other "ng -X" command blocks with detailed information
                print(f"DEBUG: Full data being parsed: {data}")
                other_cmd_blocks = re.findall(r'ng\s+-(?!m)([a-zA-Z0-9_-]+)[^\[]*\[(.*?)\]', data)
                print(f"DEBUG: Found command blocks: {other_cmd_blocks}")
                
                # Create a record for this message
                message_record = {
                    'time': time,
                    's_pid': s_pid,
                    'd_pid': d_pid,
                    'other_cmds': []  # Initialize other_cmds list
                }

                # Populate other_cmds list for the plotting function with detailed descriptions
                for cmd, block in other_cmd_blocks:
                    label = None
                    detailed_info = ""
                    print(f"DEBUG: Processing command '{cmd}' with block: {block}")
                    
                    # Extract detailed information based on command type
                    if cmd == 'd':
                        # Extract file name and hash from ng -d --b command pattern
                        # Pattern: ng -d --b 0.1 [ < 1 s 18 > < 1 s HASH > < 1 s FILENAME > ]
                        # Only process commands that start with < 1 s 18 >
                        deliver_match = re.search(r'<\s*1\s+s\s+18\s*>\s*<\s*1\s+s\s+([0-9A-F]{8})\s*>\s*<\s*1\s+s\s+([^>]+)\s*>', block)
                        if deliver_match:
                            hash_value = deliver_match.group(1)
                            file_name = deliver_match.group(2)
                            detailed_info = f"Deliver: {file_name} (hash: {hash_value})"
                        else:
                            # Fallback to extracting just file name
                            file_match = re.search(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                            if file_match:
                                file_name = file_match.group(1)
                                detailed_info = f"Deliver: {file_name}"
                    elif cmd == 'notify':
                        # Extract hash from notify command - the first vector in the second < 1 s > block
                        # Pattern: ng -notify --s 0.1 [ < 1 s 18 > < 1 s HASH > < 4 s ... > ]
                        hash_match = re.search(r'<\s*1\s+s\s+[^>]*>\s*<\s*1\s+s\s+([0-9A-F]{8})\s*>', block)
                        if hash_match:
                            hash_value = hash_match.group(1)
                            detailed_info = f"Notify hash: {hash_value}"
                        else:
                            # Fallback to extracting file name if hash not found
                            file_match = re.search(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                            if file_match:
                                file_name = file_match.group(1)
                                detailed_info = f"Notify: {file_name}"
                    elif cmd == 'p':
                        # Simple search for any filename with .txt or .jpg extension
                        print(f"DEBUG: Processing ng-p --notify command, block content: {block}")
                        file_match = re.search(r'([^\s>]+?\.txt|[^\s>]+?\.jpg)', block)
                        if file_match:
                            file_name = file_match.group(1)
                            detailed_info = f"Publish: {file_name}"
                            print(f"DEBUG: Found filename: {file_name}")
                        else:
                            print(f"DEBUG: No filename found in block")
                            detailed_info = "Publish: (no file found)"
                    elif cmd == 'scn':
                        # For scn command, don't show sequence hash as requested
                        detailed_info = "Sequence command"
                    
                    rec_entry = {
                        'time': time,
                        'command': cmd,
                        'label': label,
                        'detailed_info': detailed_info
                    }
                    message_record['other_cmds'].append(rec_entry)

                # Append the message record to the main records list
                records.append(message_record)
            except json.JSONDecodeError:
                print(f"Warning: JSON decode error at line {line_number}, skipping line.")
                continue
    return records


def plot_sequence_diagram(records, json_file, start_time=None, end_time=None, figsize_width=16, figsize_height=9, y_max_value=9.5):
    """
    Plots a sequence diagram for NovaGenesis messages between S_PID and D_PID.
    """
    import os
    
    # Filter records by start and end time if specified
    if start_time is not None or end_time is not None:
        filtered_records = []
        for rec in records:
            time = rec.get('time')
            if time is None:
                continue
            if start_time is not None and time < start_time:
                continue
            if end_time is not None and time > end_time:
                continue
            filtered_records.append(rec)
        records = filtered_records
    
    # Collect messages grouped by their original record (time, S_PID, D_PID)
    message_data = []
    for rec in records:
        time = rec.get('time')
        s_pid = rec.get('s_pid')
        d_pid = rec.get('d_pid')
        other_cmds = rec.get('other_cmds', [])
        
        if other_cmds:  # Only create a message if there are ng-X commands
            # Extract command types and payload info
            command_types = []
            payload_info = None
            
            for cmd in other_cmds:
                cmd_type = cmd.get('command', '')
                detailed_info = cmd.get('detailed_info', '')
                
                # Add command type to the list
                command_types.append(cmd_type)
                
                # Check if this is a .txt or .jpg payload or notify hash
                if cmd_type == 'd' and detailed_info:
                    # Extract file name and hash from deliver detailed_info
                    file_match = re.search(r'Deliver:\s*([^\s]+\.txt|[^\s]+\.jpg)\s*\(hash:\s*([0-9A-F]{8})\)', detailed_info)
                    if file_match:
                        # Both file name and hash found - combine them
                        file_name = file_match.group(1)
                        hash_value = file_match.group(2)
                        payload_info = f"{file_name} {hash_value}"
                    else:
                        # Try to extract just file name
                        file_only_match = re.search(r'Deliver:\s*([^\s]+\.txt|[^\s]+\.jpg)', detailed_info)
                        if file_only_match:
                            payload_info = file_only_match.group(1)
                elif cmd_type == 'p' and detailed_info:
                    # Extract file name from publish detailed_info
                    file_match = re.search(r'Publish:\s*(.+?\.txt|.+?\.jpg)', detailed_info)
                    if file_match:
                        payload_info = file_match.group(1)
                    else:
                        # Fallback to extracting any file name
                        file_match = re.search(r'([^\s]+\.txt|[^\s]+\.jpg)', detailed_info)
                        if file_match:
                            payload_info = file_match.group(1)
                elif cmd_type == 'notify' and detailed_info:
                    # Extract notify hash for display
                    notify_hash_match = re.search(r'Notify hash:\s*([0-9A-F]{8})', detailed_info)
                    if notify_hash_match:
                        payload_info = notify_hash_match.group(1)
            
            # Create a single message entry
            message_data.append({
                'time': time,
                's_pid': s_pid,
                'd_pid': d_pid,
                'command_types': command_types,
                'payload_info': payload_info
            })
    
    if not message_data:
        print("No messages found for plotting")
        return
    
    # Sort messages by time
    sorted_messages = sorted(message_data, key=lambda x: x.get('time', 0))
    
    # Find min and max times for normalization
    all_times = [msg.get('time', 0) for msg in sorted_messages]
    
    # Use provided start_time and end_time if available, otherwise use data range
    if start_time is not None:
        min_time = start_time
    else:
        min_time = min(all_times)
    
    if end_time is not None:
        max_time = end_time
    else:
        max_time = max(all_times)
    
    time_range = max_time - min_time if max_time > min_time else 1
    
    # Process all messages (not just the first 4)
    messages_to_plot = sorted_messages
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    
    # Set up the diagram with time flowing from top to bottom
    ax.set_xlim(1, 12)
    
    # Remove X-axis tick labels and values as they are not important
    ax.set_xticks([])
    ax.set_xticklabels([])
    
    # Calculate time gaps between messages to identify discontinuities
    if len(messages_to_plot) > 1:
        time_gaps = []
        for i in range(1, len(messages_to_plot)):
            gap = messages_to_plot[i]['time'] - messages_to_plot[i-1]['time']
            time_gaps.append(gap)
        
        # Define a threshold for significant gaps (e.g., 10% of the total time range)
        gap_threshold = time_range * 0.1
        
        # Identify gap positions
        gap_positions = []
        for i, gap in enumerate(time_gaps):
            if gap > gap_threshold:
                gap_positions.append(i)
    
    # Set y-axis limits for visualization (not the actual time values)
    y_min = 0.5
    y_max = y_max_value
    ax.set_ylim(y_min, y_max)
    
    # Create y-axis positions with gaps - map actual time to y positions
    y_positions = []
    current_y = y_max
    
    for i, msg in enumerate(messages_to_plot):
        msg_time = msg.get('time', 0)
        
        # Calculate y position for this message
        if i == 0:
            # First message at the top
            y_pos = current_y
        else:
            # Check if there's a significant gap before this message
            if i-1 in gap_positions:
                # Add a gap in the y-axis
                gap_size = 0.5  # Fixed gap size
                current_y -= gap_size
                y_pos = current_y
            else:
                # Normal spacing
                y_pos = current_y
        
        y_positions.append(y_pos)
        
        # Move to next position
        current_y -= 1.0  # Fixed spacing between messages
    
    # Sort messages and y_positions together by time
    sorted_pairs = sorted(zip(messages_to_plot, y_positions), key=lambda x: x[0]['time'])
    messages_to_plot = [pair[0] for pair in sorted_pairs]
    y_positions = [pair[1] for pair in sorted_pairs]
    
    # Remove y-axis inversion so time flows from top to bottom (earlier times at top, later times at bottom)
    # No need to invert_yaxis()
    
    # Add grid with more visibility
    ax.grid(True, linestyle='-', alpha=0.5, color='gray')
    ax.set_axisbelow(True)  # Place grid lines below other elements
    
    # Collect all unique PIDs from messages
    all_pids = set()
    for msg in messages_to_plot:
        s_pid = msg.get('s_pid')
        d_pid = msg.get('d_pid')
        if s_pid:
            all_pids.add(s_pid)
        if d_pid:
            all_pids.add(d_pid)
    
    # Create process mapping: P1, P2, P3, etc.
    pid_to_process = {}
    process_to_pid = {}
    for i, pid in enumerate(sorted(all_pids), 1):
        process_name = f'P{i}'
        pid_to_process[pid] = process_name
        process_to_pid[process_name] = pid
    
    # Calculate x positions for each process
    num_processes = len(all_pids)
    if num_processes == 1:
        x_positions = [6]  # Center if only one process
    else:
        # Distribute processes evenly across the x-axis
        x_start = 2
        x_end = 10
        x_spacing = (x_end - x_start) / (num_processes - 1)
        x_positions = [x_start + i * x_spacing for i in range(num_processes)]
    
    # Draw lifelines for each process
    process_x_map = {}
    for i, (process_name, x_pos) in enumerate(zip(pid_to_process.values(), x_positions)):
        ax.plot([x_pos, x_pos], [y_min, y_max], 'k-', linewidth=2)
        
        # Position process labels at the very top of the plot with more space below
        label_y = y_max + 0.5
        pid = process_to_pid[process_name]
        ax.text(x_pos, label_y, f'{process_name}: {pid}', ha='center', fontsize=14, fontweight='bold')
        
        process_x_map[process_name] = x_pos
    
    # Process each message
    for i, msg in enumerate(messages_to_plot):
        msg_time = msg.get('time', 0)
        msg_command = msg.get('command', 'unknown')
        msg_label = msg.get('label', msg_command)
        s_pid = msg.get('s_pid')
        d_pid = msg.get('d_pid')
        detailed_info = msg.get('detailed_info', '')
        
        # Get the pre-calculated y position
        y_pos = y_positions[i]
        
        # All messages should go from S_PID to D_PID
        s_pid = msg.get('s_pid')
        d_pid = msg.get('d_pid')
        
        if s_pid and d_pid and s_pid in pid_to_process and d_pid in pid_to_process:
            source_process = pid_to_process[s_pid]
            dest_process = pid_to_process[d_pid]
            
            # Get x positions for source and destination
            start_x = process_x_map[source_process] 
            end_x = process_x_map[dest_process] 
            
            # All messages are blue and go from S_PID to D_PID
            color = 'blue'
            arrow_dir = '->'
        
        # Draw the message line at the correct time position
        ax.plot([start_x, end_x], [y_pos, y_pos], 
                color=color, linewidth=2, linestyle='-', alpha=0.7)
        
        # Draw arrowhead
        ax.annotate('', xy=(end_x, y_pos), xytext=(start_x, y_pos),
                    arrowprops=dict(arrowstyle=arrow_dir, lw=2, color=color))
        
        # Add command types as labels next to the destination process
        command_types = msg.get('command_types', [])
        payload_info = msg.get('payload_info')
        
        if command_types:
            # Create label with command types - limit to first 3 commands to avoid large labels
            if len(command_types) > 3:
                label_text = 'ng-' + ', ng-'.join(command_types[:3]) + '...'
            else:
                label_text = 'ng-' + ', ng-'.join(command_types)
            
            # Always position label near the destination (D_PID) which is on the right side
            # Find the rightmost process for positioning
            max_x = max(process_x_map.values()) if process_x_map else 10 - 0.2
            
            # Position label on the right side
            label_x = max_x + 0.3
            ha_alignment = 'left'
            
            ax.text(label_x, y_pos, label_text, va='center', ha=ha_alignment,
                   fontsize=12, color=color, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
        
        # If there's a .txt payload or notify hash, display it on the message line itself
        if payload_info:
            # Calculate midpoint of the message line
            mid_x = (start_x + end_x) / 2
            
            # Determine if this is a notify hash or file payload
            if 'notify' in command_types:
                # Use cyan color for notify hash instead of yellow
                box_color = 'cyan'
                text_color = 'blue'
            else:
                # Use yellow for .txt and .jpg files
                box_color = 'yellow'
                text_color = 'red'
            
            # Display payload info on the line
            ax.text(mid_x, y_pos - 0.1, payload_info, ha='center', va='top', 
                   fontsize=13, color=text_color, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor=box_color, alpha=0.9))
    
    # Format y-axis to show actual time values with discontinuities
    if len(messages_to_plot) > 1 and time_range > 0:
        # Create y-axis labels that show time with discontinuities
        y_ticks = []
        y_tick_labels = []
        
        # Add ticks for each message position
        for i, (msg, y_pos) in enumerate(zip(messages_to_plot, y_positions)):
            msg_time = msg.get('time', 0)
            
            # Add tick at this position
            y_ticks.append(y_pos)
            
            # Check if there's a gap before this message
            if i > 0 and (i-1 in gap_positions):
                # Add a discontinuity symbol with high precision
                y_tick_labels.append(f"{msg_time:.6f} ⋮")
            else:
                # Normal time label with high precision
                y_tick_labels.append(f"{msg_time:.6f}")
        
        # Add start and end time ticks at the boundaries
        y_ticks.insert(0, y_max)  # Start time at top
        y_tick_labels.insert(0, f"{min_time:.6f}")
        y_ticks.append(y_min)  # End time at bottom
        y_tick_labels.append(f"{max_time:.6f}")
        
        # Add additional grid lines for better time resolution
        # Calculate minor ticks between major ticks
        minor_y_ticks = []
        for i in range(len(y_ticks) - 1):
            y1, y2 = y_ticks[i], y_ticks[i + 1]
            # Add 4 minor ticks between major ticks
            for j in range(1, 5):
                minor_y = y1 + (y2 - y1) * j / 5
                minor_y_ticks.append(minor_y)
        
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_tick_labels)
        
        # Set minor ticks for higher resolution grid
        ax.set_yticks(minor_y_ticks, minor=True)
        
        # Enable minor grid
        ax.grid(True, which='minor', linestyle=':', alpha=0.3, color='gray')
        ax.grid(True, which='major', linestyle='-', alpha=0.5, color='gray')
        
    elif len(messages_to_plot) == 1:
        # Single message case - add start and end time boundaries
        ax.set_yticks([y_max, y_positions[0], y_min])
        ax.set_yticklabels([f"{min_time:.6f}", f"{messages_to_plot[0].get('time', 0):.6f}", f"{max_time:.6f}"])
    else:
        # No messages case - show start and end time
        ax.set_yticks([y_max, y_min])
        ax.set_yticklabels([f"{min_time:.6f}", f"{max_time:.6f}"])
    
    # Save the figure
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_filename = f"{base_name}_sequence"
    if start_time is not None:
        output_filename += f"_start{start_time:.2f}"
    if end_time is not None:
        output_filename += f"_end{end_time:.2f}"
    output_filename += ".pdf"
    
    plt.tight_layout()
    plt.savefig(output_filename)
    plt.close(fig)
    
    print(f"Sequence diagram saved as: {output_filename}")
    print(f"Processed {len(sorted_messages)} messages")


def main():
    parser = argparse.ArgumentParser(
        description='Plots a sequence diagram of NovaGenesis messages from a JSON file.'
    )
    parser.add_argument('json_file', help='Path to the JSON file (one message per line)')
    parser.add_argument('--start-time', type=float, default=None, help='Start time for X-axis (inclusive)')
    parser.add_argument('--end-time', type=float, default=None, help='End time for X-axis (inclusive)')
    parser.add_argument('--figsize-width', type=float, default=16, help='Figure width in inches')
    parser.add_argument('--figsize-height', type=float, default=9, help='Figure height in inches')
    parser.add_argument('--y-max-value', type=float, default=9.5, help='Maximum Y-axis value')
    args = parser.parse_args()

    records = parse_records(args.json_file)
    plot_sequence_diagram(records, args.json_file, start_time=args.start_time, end_time=args.end_time, 
                         figsize_width=args.figsize_width, figsize_height=args.figsize_height,
                         y_max_value=args.y_max_value)


if __name__ == '__main__':
    main()
