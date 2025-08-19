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
                    # According to the user, S_PID is in the first "< 4 s" and D_PID in the second "< 4 s"
                    four_s_pattern = r'<\s*4\s*s\s+([0-9A-F]{8})\s+([0-9A-F]{8})'
                    matches = re.findall(four_s_pattern, block_content)
                    
                    if len(matches) >= 2:
                        # First match gives S_PID
                        s_pid = matches[0][0]
                        # Second match gives D_PID
                        d_pid = matches[1][0]
                    elif len(matches) == 1:
                        # Only one match found, use it for S_PID
                        s_pid = matches[0][0]
                
                # Parse other "ng -X" command blocks with detailed information
                other_cmd_blocks = re.findall(r'ng\s+-(?!m)([a-zA-Z0-9_-]+)[^\[]*\[(.*?)\]', data)
                
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
                    
                    # Extract detailed information based on command type
                    if cmd == 'info':
                        angle_contents = re.findall(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                        if angle_contents:
                            label = angle_contents[-1]
                            detailed_info = f"Payload: {label}"
                    elif cmd == 'notify':
                        # Extract file name from notify command
                        file_match = re.search(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                        if file_match:
                            file_name = file_match.group(1)
                            detailed_info = f"Notify: {file_name}"
                    elif cmd == 'p':
                        # Check if it's --notify or --b
                        if '--notify' in block:
                            file_match = re.search(r'<\s*[^>]*?\s*([^ >]+)\s*>', block)
                            if file_match:
                                file_name = file_match.group(1)
                                detailed_info = f"Publish & Notify: {file_name}"
                        elif '--b' in block:
                            # Extract hashes from publish command
                            hashes = re.findall(r'<\s*[^>]*?\s*([0-9A-F]{8})\s*>', block)
                            if hashes:
                                detailed_info = f"Publish hashes: {', '.join(hashes[:3])}{'...' if len(hashes) > 3 else ''}"
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


def plot_sequence_diagram(records, json_file, start_time=None, end_time=None):
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
                
                # Check if this is a .txt payload
                if cmd_type == 'info' and detailed_info:
                    # Extract payload name and check if it's .txt
                    payload_match = re.search(r'Payload:\s*([^\s]+\.txt)', detailed_info)
                    if payload_match:
                        payload_info = payload_match.group(1)
            
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
    min_time = min(all_times)
    max_time = max(all_times)
    time_range = max_time - min_time if max_time > min_time else 1
    
    # Process all messages (not just the first 4)
    messages_to_plot = sorted_messages
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Set up the diagram with time flowing from top to bottom
    ax.set_xlim(0, 12)
    
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
        
        # Set y-axis limits
        y_min = 0.5
        y_max = 9.5
        ax.set_ylim(y_min, y_max)
        
        # Create y-axis positions with gaps
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
    else:
        # Handle case with only one message
        y_min = 0.5
        y_max = 9.5
        ax.set_ylim(y_min, y_max)
        y_positions = [y_max - 1.0]  # Center the single message
    
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
        
        # Position process labels at the very top of the plot
        label_y = y_max + 0.2
        pid = process_to_pid[process_name]
        ax.text(x_pos, label_y, f'{process_name}: {pid}', ha='center', fontsize=10, fontweight='bold')
        
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
        
        # Get source and destination process names
        s_pid = msg.get('s_pid')
        d_pid = msg.get('d_pid')
        
        if s_pid and d_pid and s_pid in pid_to_process and d_pid in pid_to_process:
            source_process = pid_to_process[s_pid]
            dest_process = pid_to_process[d_pid]
            
            # Get x positions for source and destination
            start_x = process_x_map[source_process] + 0.2
            end_x = process_x_map[dest_process] - 0.2
            
            # Determine color based on direction
            if source_process == dest_process:
                color = 'gray'  # Self-message
            elif source_process == 'P1' and dest_process == 'P2':
                color = 'blue'  # P1 to P2 messages
            elif source_process == 'P2' and dest_process == 'P1':
                color = 'green'  # P2 to P1 messages
            else:
                color = 'blue'  # Default for other directions
            
            arrow_dir = '->'
        else:
            # Fallback to default positions
            start_x = 2 + 0.2
            end_x = 10 - 0.2
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
        
        if command_types and d_pid in pid_to_process:
            # Create label with command types - limit to first 3 commands to avoid large labels
            if len(command_types) > 3:
                label_text = 'ng-' + ', ng-'.join(command_types[:3]) + '...'
            else:
                label_text = 'ng-' + ', ng-'.join(command_types)
            
            dest_process = pid_to_process[d_pid]
            dest_x = process_x_map[dest_process]
            
            # Position label on the appropriate side with consistent justification
            if start_x < end_x:  # Message goes left to right
                label_x = dest_x + 0.5
                ha_alignment = 'left'
            else:  # Message goes right to left
                label_x = dest_x - 0.5
                ha_alignment = 'right'
            
            ax.text(label_x, y_pos, label_text, va='center', ha=ha_alignment,
                   fontsize=8, color=color, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
        
        # If there's a .txt payload, display it on the message line itself
        if payload_info:
            # Calculate midpoint of the message line
            mid_x = (start_x + end_x) / 2
            # Display payload info on the line
            ax.text(mid_x, y_pos - 0.1, payload_info, ha='center', va='top', 
                   fontsize=9, color='red', fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='yellow', alpha=0.9))
    
    # Remove time scale reference as requested
    
    # Format y-axis to show actual time values with discontinuities
    if len(messages_to_plot) > 1 and time_range > 0:
        # Create y-axis labels that show time with discontinuities
        y_ticks = []
        y_tick_labels = []
        
        for i, (msg, y_pos) in enumerate(zip(messages_to_plot, y_positions)):
            msg_time = msg.get('time', 0)
            
            # Add tick at this position
            y_ticks.append(y_pos)
            
            # Check if there's a gap before this message
            if i > 0 and (i-1 in gap_positions):
                # Add a discontinuity symbol
                y_tick_labels.append(f"{msg_time:.3f} ⋮")
            else:
                # Normal time label
                y_tick_labels.append(f"{msg_time:.3f}")
        
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_tick_labels)
    elif len(messages_to_plot) == 1:
        # Single message case
        ax.set_yticks([y_positions[0]])
        ax.set_yticklabels([f"{messages_to_plot[0].get('time', 0):.3f}"])
    else:
        ax.set_yticklabels([f"{min_time:.3f}"])
    
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
    args = parser.parse_args()

    records = parse_records(args.json_file)
    plot_sequence_diagram(records, args.json_file, start_time=args.start_time, end_time=args.end_time)


if __name__ == '__main__':
    main()
