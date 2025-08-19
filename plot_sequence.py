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
                        # Extract sequence hash
                        seq_hash = re.search(r'<\s*[^>]*?\s*([0-9A-F]{8})\s*>', block)
                        if seq_hash:
                            detailed_info = f"Sequence hash: {seq_hash.group(1)}"
                    
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
    
    # Collect all messages with their S_PID and D_PID and detailed info
    message_data = []
    for rec in records:
        time = rec.get('time')
        s_pid = rec.get('s_pid')
        d_pid = rec.get('d_pid')
        other_cmds = rec.get('other_cmds', [])
        
        for cmd in other_cmds:
            detailed_info = cmd.get('detailed_info', '')
            message_data.append({
                'time': time,
                's_pid': s_pid,
                'd_pid': d_pid,
                'command': cmd.get('command', 'unknown'),
                'label': cmd.get('label', ''),
                'detailed_info': detailed_info
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
    
    ax.invert_yaxis()  # Invert y-axis so time flows from top to bottom
    
    # Add grid with more visibility
    ax.grid(True, linestyle='-', alpha=0.5, color='gray')
    ax.set_axisbelow(True)  # Place grid lines below other elements
    
    # Draw lifelines using the S_PID and D_PID from the first message
    s_x = 2
    d_x = 10
    y_start = y_min
    y_end = y_max
    
    if messages_to_plot:
        first_s_pid = messages_to_plot[0].get('s_pid', 'Unknown')
        first_d_pid = messages_to_plot[0].get('d_pid', 'Unknown')
        
        # S_PID lifeline
        ax.plot([s_x, s_x], [y_start, y_end], 'k-', linewidth=2)
        ax.text(s_x, y_start - 0.3, f'S_PID: {first_s_pid}', ha='center', fontsize=12, fontweight='bold')
        
        # D_PID lifeline
        ax.plot([d_x, d_x], [y_start, y_end], 'k-', linewidth=2)
        ax.text(d_x, y_start - 0.3, f'D_PID: {first_d_pid}', ha='center', fontsize=12, fontweight='bold')
    
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
        
        # Determine message direction and color based on command type
        if msg_command in ['info', 'send', 'request', 'notify', 'd', 'p']:
            # Message from S_PID to D_PID
            start_x, end_x = s_x + 0.2, d_x - 0.2
            color = 'blue'
            arrow_dir = '->'
        elif msg_command in ['response', 'reply', 's', 'scn']:
            # Message from D_PID to S_PID
            start_x, end_x = d_x - 0.2, s_x + 0.2
            color = 'green'
            arrow_dir = '->'
        else:
            # Unknown command, use gray
            start_x, end_x = s_x + 0.2, d_x - 0.2
            color = 'gray'
            arrow_dir = '->'
        
        # Draw the message line at the correct time position
        ax.plot([start_x, end_x], [y_pos, y_pos], 
                color=color, linewidth=2, linestyle='-', alpha=0.7)
        
        # Draw arrowhead
        ax.annotate('', xy=(end_x, y_pos), xytext=(start_x, y_pos),
                    arrowprops=dict(arrowstyle=arrow_dir, lw=2, color=color))
        
        # Add detailed command labels next to the axes
        if msg_command in ['info', 'send', 'request', 'notify', 'd', 'p']:
            # Label near D_PID axis with detailed info
            if detailed_info:
                # Split detailed info into multiple lines if too long
                if len(detailed_info) > 30:
                    # Split by comma or space to break into lines
                    words = detailed_info.split(', ')
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 25:
                            current_line += word + ", "
                        else:
                            lines.append(current_line.rstrip(", "))
                            current_line = word + ", "
                    if current_line:
                        lines.append(current_line.rstrip(", "))
                    
                    # Draw text with multiple lines
                    y_offset = 0
                    for line in lines:
                        ax.text(d_x + 0.5, y_pos + y_offset, line, va='center', 
                               fontsize=9, color=color, fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
                        y_offset -= 0.25
                else:
                    ax.text(d_x + 0.5, y_pos, detailed_info, va='center', 
                           fontsize=10, color=color, fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            else:
                ax.text(d_x + 0.5, y_pos, f"ng -{msg_command}", va='center', 
                       fontsize=10, color=color, fontweight='bold')
        elif msg_command in ['response', 'reply', 's', 'scn']:
            # Label near S_PID axis with detailed info
            if detailed_info:
                # Split detailed info into multiple lines if too long
                if len(detailed_info) > 30:
                    # Split by comma or space to break into lines
                    words = detailed_info.split(', ')
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 25:
                            current_line += word + ", "
                        else:
                            lines.append(current_line.rstrip(", "))
                            current_line = word + ", "
                    if current_line:
                        lines.append(current_line.rstrip(", "))
                    
                    # Draw text with multiple lines
                    y_offset = 0
                    for line in lines:
                        ax.text(s_x - 0.5, y_pos + y_offset, line, va='center', 
                               fontsize=9, color=color, fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
                        y_offset -= 0.25
                else:
                    ax.text(s_x - 0.5, y_pos, detailed_info, va='center', 
                           fontsize=10, color=color, fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            else:
                ax.text(s_x - 0.5, y_pos, f"ng -{msg_command}", va='center', 
                       fontsize=10, color=color, fontweight='bold')
    
    # Add time scale reference with actual time values
    time_text = f"Time range: {min_time:.3f}s to {max_time:.3f}s"
    ax.text(6, 0.5, time_text, ha='center', fontsize=10, 
            bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.7))
    
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
