import pyshark # Replaces pcapng
import json
import re

# Global substrings list to be used throughout the program
SUBSTRINGS = ["ng -notify ", "ng -p ", "ng -d ", "ng -s ", "Client ", "Server "]

def packet_contains_data(data, substrings):
    # Ensure data is bytes for decoding
    if not isinstance(data, bytes):
        data = str(data).encode(errors='ignore')
    data_str = data.decode(errors='ignore')
    for substr in substrings:
        if substr in data_str:
            return substr # Return the matching substring
    return None # Return None if no match

def mac_addr(mac_bytes):
    return ':'.join(f'{b:02x}' for b in mac_bytes)

def clean_string(s):
    # Remove control characters and other non-printable characters that may corrupt JSON
    return ''.join(c for c in s if c.isprintable())

def main():
    filename = 'ORIGINAL.pcapng' # Using the filename from the original script
    output_file = 'extracted_data.json'

    # Timestamp normalization variables
    first_timestamp = None
    norm_time = None

    print(f"Starting packet analysis on {filename}...")

    try:
        # Use pyshark to capture packets from the file with UDP filter and port filter
        # Filter for UDP packets where destination port is 9999 or 8888
        display_filter = "udp and (udp.dstport == 9999 or udp.dstport == 8888)"
        with pyshark.FileCapture(filename, display_filter=display_filter) as cap:
            with open(output_file, 'w', encoding='utf-8') as out_fp:
                packet_count = 0
                for pkt in cap:
                    packet_count += 1
                    # Add progress indicator for main processing loop
                    if packet_count % 1000 == 0: # Provide feedback every 1k packets processed
                        print(f"  Processed {packet_count} packets...")

                    # Extract MAC addresses
                    src_mac_str = None
                    dst_mac_str = None
                    if hasattr(pkt, 'eth'):
                        src_mac_str = pkt.eth.src
                        dst_mac_str = pkt.eth.dst

                    # Extract timestamp and normalize
                    current_timestamp_raw = None
                    if hasattr(pkt, 'sniff_timestamp'):
                        current_timestamp_raw = pkt.sniff_timestamp

                    current_timestamp = None
                    if current_timestamp_raw is not None:
                        try:
                            current_timestamp = float(current_timestamp_raw)
                        except (ValueError, TypeError):
                            current_timestamp = None

                    if current_timestamp is not None:
                        if first_timestamp is None:
                            first_timestamp = current_timestamp
                            norm_time = 0.0
                        else:
                            norm_time = float(current_timestamp) - float(first_timestamp)
                    else:
                        print(f"Stopping execution: Encountered packet {packet_count} with missing or invalid timestamp.")
                        break

                    # Extract UDP payload
                    data_str = ""
                    if hasattr(pkt, 'udp') and hasattr(pkt.udp, 'payload'):
                        try:
                            hex_payload = pkt.udp.payload.replace(":", "")  # remove separadores
                            data_str = bytes.fromhex(hex_payload).decode(errors='ignore')
                        except Exception as e:
                            print(f"Error extracting UDP payload for packet {packet_count}: {e}")

                    # Remove the first two characters as requested by the user
                    if len(data_str) >= 2:
                        data_str = data_str[2:]
                    # else: data_str remains as is if it's less than 2 chars

                    # Apply the substring filter
                    matching_substring = packet_contains_data(data_str.encode(), SUBSTRINGS)
                    if matching_substring is None:
                        continue

                    print(f"  Substring match found: '{matching_substring}' in packet {packet_count}.")

                    # User request: show sample time and UDP payload, then pause for input
                    #print(f"  Sample Time: {norm_time}") # Print the normalized timestamp
                    #print(f"  UDP Payload: {data_str}") # Print the extracted payload
                    #input("  Press Enter to continue...") # Pause for user input

                    # Clean data string
                    data_str_clean = clean_string(data_str)

                    # Remove everything before the first "ng -" (any command)
                    match = re.search(r'ng\s+-[a-zA-Z0-9_-]+', data_str_clean)
                    if match:
                        data_str_clean = data_str_clean[match.start():]
                    else:
                        data_str_clean = data_str_clean.lstrip(' \r\n\t\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f')

                    data_str_clean = clean_string(data_str_clean)

                    json_obj = {
                        "time": norm_time,
                        "src_mac": src_mac_str,
                        "dst_mac": dst_mac_str,
                        "data": data_str_clean
                    }

                    if data_str_clean.startswith("ng -m --cl 0.1 ["):
                        out_fp.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
                        print(f"  Data written to {output_file} for packet {packet_count}.")

    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print("Packet analysis finished.")

def filter_relevant_messages(input_file='extracted_data.json', output_file='relevant.json'):
    with open(input_file, 'r', encoding='utf-8') as in_fp, open(output_file, 'w', encoding='utf-8') as out_fp:
        for line in in_fp:
            try:
                obj = json.loads(line)
                data_str = obj.get("data", "")
                if any(sub in data_str for sub in SUBSTRINGS):
                    out_fp.write(json.dumps(obj, ensure_ascii=False) + '\n')
            except Exception:
                continue

if __name__ == '__main__':
    main()
    filter_relevant_messages()
