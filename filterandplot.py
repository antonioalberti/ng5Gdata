import json
from datetime import datetime
import argparse

def filter_relevant_messages(input_file='extracted_data.json', output_file='relevant.json', max_duration=None):
    substrings = ["ng -notify", "ng -p", "ng -d"]
    relevant_objs = []
    with open(input_file, 'r', encoding='utf-8') as in_fp:
        for line in in_fp:
            try:
                obj = json.loads(line)
                data_str = obj.get("data", "")
                if any(sub in data_str for sub in substrings):
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
                    if max_duration is not None and delta > max_duration:
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
    parser.add_argument('--max_duration', type=float, default=None, help='Maximum duration in seconds to include in output')
    args = parser.parse_args()

    filter_relevant_messages(input_file=args.input_file, output_file=args.output_file, max_duration=args.max_duration)

if __name__ == '__main__':
    main()
