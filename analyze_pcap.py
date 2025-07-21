import sys
from pcapng import FileScanner
import socket

def packet_contains_data(data, substrings):
    data_str = data.decode(errors='ignore')
    for substr in substrings:
        if substr in data_str:
            return True
    return False

def is_icmp(packet):
    # Check if the packet is ICMP by inspecting the IP protocol field
    # We need to parse the Ethernet frame and IP header to check protocol
    # Ethernet header is 14 bytes
    if len(packet) < 34:
        return False
    eth_proto = int.from_bytes(packet[12:14], byteorder='big')
    # 0x0800 is IPv4
    if eth_proto != 0x0800:
        return False
    ip_proto = packet[23]
    # ICMP protocol number is 1
    return ip_proto == 1


# Global substrings list to be used throughout the program
SUBSTRINGS = ["ng -notify", "ng -p", "ng -d", "ng -s"]

def main():
    import datetime
    import json
    filename = 'ORIGINAL.pcapng'
    output_file = 'extracted_data.json'

    def mac_addr(mac_bytes):
        return ':'.join(f'{b:02x}' for b in mac_bytes)

    def clean_string(s):
        # Remove control characters and other non-printable characters that may corrupt JSON
        return ''.join(c for c in s if c.isprintable())

    first_timestamp = None
    norm_time = None
    first_written = False

    with open(filename, 'rb') as fp, open(output_file, 'w', encoding='utf-8') as out_fp:
        scanner = FileScanner(fp)
        for block in scanner:
            if hasattr(block, 'packet_data'):
                packet = block.packet_data
                if is_icmp(packet):
                    continue
                # Extract timestamp from block if available
                timestamp = None
                if hasattr(block, 'timestamp'):
                    timestamp = block.timestamp
                elif hasattr(block, 'timestamp_high') and hasattr(block, 'timestamp_low'):
                    # Combine high and low to get timestamp in microseconds
                    timestamp = (block.timestamp_high << 32) + block.timestamp_low
                    # Convert to seconds float
                    timestamp = timestamp / 1_000_000
                # Normalize time to first sample
                if timestamp is not None:
                    if first_timestamp is None and not first_written:
                        first_timestamp = timestamp
                        norm_time = 0.0
                        first_written = True
                    else:
                        norm_time = float(timestamp - first_timestamp)
                else:
                    norm_time = None
                # Extract source and destination MAC addresses from Ethernet header
                if len(packet) < 14:
                    continue
                dst_mac = packet[0:6]
                src_mac = packet[6:12]
                src_mac_str = mac_addr(src_mac)
                dst_mac_str = mac_addr(dst_mac)

                # Extract only the data part (payload)
                eth_header_len = 14
                if len(packet) < eth_header_len + 20:
                    continue
                ip_header = packet[eth_header_len:eth_header_len+20]
                ip_header_len = (ip_header[0] & 0x0F) * 4
                protocol = ip_header[9]
                if protocol == 6:  # TCP
                    tcp_header_start = eth_header_len + ip_header_len
                    if len(packet) < tcp_header_start + 20:
                        continue
                    tcp_header = packet[tcp_header_start:tcp_header_start+20]
                    tcp_header_len = ((tcp_header[12] >> 4) & 0xF) * 4
                    data_start = tcp_header_start + tcp_header_len
                    data = packet[data_start:]
                elif protocol == 17:  # UDP
                    udp_header_start = eth_header_len + ip_header_len
                    udp_header_len = 8
                    data_start = udp_header_start + udp_header_len
                    data = packet[data_start:]
                else:
                    # For other protocols, just take data after IP header
                    data_start = eth_header_len + ip_header_len
                    data = packet[data_start:]
                try:
                    data_str = data.decode(errors='ignore')
                    # Apply filter on the extracted data string
                    if not packet_contains_data(data_str.encode(), SUBSTRINGS):
                        continue
                    # Show match and time before saving
                    #print("MATCH FOUND:")
                    #print("Normalized time:", norm_time if norm_time is not None else None)
                    #print("Data:", data_str[:200] + ("..." if len(data_str) > 200 else ""))
                    #input("Press Enter to continue...")
                    # Remove everything before the first "ng -" (any command)
                    import re
                    match = re.search(r'ng\s+-[a-zA-Z0-9_-]+', data_str)
                    if match:
                        data_str = data_str[match.start():]
                    else:
                        data_str = data_str.lstrip(' \r\n\t\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f')
                    # Remove non-printable characters from the start of the string
                    data_str = data_str.lstrip(' \r\n\t\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f')

                    # Clean data string to remove any special characters that may corrupt JSON
                    data_str_clean = clean_string(data_str)

                    # Prepare JSON object
                    json_obj = {
                        "time": norm_time if norm_time is not None else None,  # normalized time (first sample = 0)
                        "src_mac": src_mac_str,
                        "dst_mac": dst_mac_str,
                        "data": data_str_clean
                    }

                    # Write JSON object as a single line
                    out_fp.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
                except Exception:
                    # If decoding fails, skip
                    continue

def filter_relevant_messages(input_file='extracted_data.json', output_file='relevant.json'):
    import json
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
