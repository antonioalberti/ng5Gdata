import json
from datetime import datetime
import argparse

def filter_relevant_messages(input_file='extracted_data.json', output_file='relevant.json', begin_interval=None, end_interval=None):
    substrings = ["ng -notify", "ng -p", "ng -d"]
    relevant_objs = []
    with open(input_file, 'r', encoding='utf-8') as in_fp:
        for line in in_fp:
            try:
                obj = json.loads(line)
                data_str = obj.get("data", "")
                # Show the line and filtering decision
                print("Analyzing line:")
                print(line.strip())
                decision = any(sub in data_str for sub in substrings)
                print("Will be filtered (included)?", decision)
                input("Press Enter to continue...")
                if decision:
                    relevant_objs.append(obj)
            except Exception:
                continue

    if not relevant_objs:
        # No relevant data found, create empty output file
        with open(output_file, 'w', encoding='utf-8') as out_fp:
            pass
        return

    try:
        reference_time = datetime.fromisoformat(relevant_objs[0].get("time"))
    except Exception:
        reference_time = None

    with open(output_file, 'w', encoding='utf-8') as out_fp:
        for obj in relevant_objs:
            try:
                current_time = datetime.fromisoformat(obj.get("time"))
                if reference_time is not None:
                    delta = (current_time - reference_time).total_seconds()
                    if begin_interval is not None and delta < begin_interval:
                        continue
                    if end_interval is not None and delta > end_interval:
                        break
                    obj["time"] = delta
                else:
                    obj["time"] = 0.0
                out_fp.write(json.dumps(obj, ensure_ascii=False) + '\n')
            except Exception:
                continue

def main():
    parser = argparse.ArgumentParser(description='Filter relevant messages and adjust time relative to first sample.')
    parser.add_argument('--input_file', type=str, default='extracted_data.json', help='Input JSON lines file')
    parser.add_argument('--output_file', type=str, default='relevant.json', help='Output JSON lines file')
    parser.add_argument('--begin_interval', type=float, default=None, help='Start of time interval in seconds to include in output')
    parser.add_argument('--end_interval', type=float, default=None, help='End of time interval in seconds to include in output')
    args = parser.parse_args()

    filter_relevant_messages(input_file=args.input_file, output_file=args.output_file, begin_interval=args.begin_interval, end_interval=args.end_interval)
if __name__ == '__main__':
    main()
