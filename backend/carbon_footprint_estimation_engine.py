import argparse
import json
import sys
from pathlib import Path

#customer premise equipment (modem, router, ...)
cpe_kwh_per_h = 0.007
#access network that connects users and ISP
an_kwh_per_h = 0.0028
#electricity consumed transmitting 1 gigabyte  of data through the core network at the access network node
core_network_ann_per_gb = 0.01771684761728*0.5
#electricity consumed transmitting 1 gigabyte  of data through the core network at the data centers node
#values are split up into regions but summed up here to get the total
core_network_dcn_per_gb = 0.00885842380864
core_network_total = core_network_ann_per_gb + core_network_dcn_per_gb
#data center electricity usage trasmitting 1 gigabyte of data
#data is again split up but summed up to get the total
dc_kwh_per_gb = 0.04107

#user device energy consumption, here the value is from a laptop
device_kwh_per_h = 0.0242

#grams of co2 emitted to produce 1 kwh
#depends on region and energy sources, for now we just use this as a placeholder, maybe make it chooseable in the GUI
carbon_intensity = 400

def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not data:
        raise ValueError("The JSON file is empty.")

    entries = []

    if isinstance(data, list):
        for item in data:
            entries.append(item)

    elif isinstance(data, dict):
        entries.append(data)

    else:
        raise ValueError("The JSON file must contain a JSON object or a list of JSON objects.")

    if len(entries) == 0:
        raise ValueError("The JSON file contains no valid entries.")

    return entries

def get_arguments():
    if len(sys.argv) != 2:
        print("Error: Please provide exactly one argument: the path to the JSON file.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Estimate carbon emissions from website data JSON."
    )

    parser.add_argument(
        "file_path",
        help="Path to the JSON file from the website data collection engine."
    )

    return parser.parse_args()

#rate website on a scale of A-F, the values need some tweaking
def get_rating(co2_per_visit):
    if co2_per_visit <= 0.05:
        return "A"
    elif co2_per_visit <= 0.10:
        return "B"
    elif co2_per_visit <= 0.20:
        return "C"
    elif co2_per_visit <= 0.30:
        return "D"
    elif co2_per_visit <= 0.40:
        return "E"
    else:
        return "F"
    
def calculate_co2(entry):
    total_bytes = entry["total_bytes"]
    load_time = entry["load_time"]

    total_bytes_in_gb = total_bytes / 1000000000
    load_time_in_hours = load_time / 3600

    data_energy = total_bytes_in_gb * (dc_kwh_per_gb + core_network_total)

    time_energy = load_time_in_hours * (cpe_kwh_per_h + an_kwh_per_h + device_kwh_per_h)

    energy_total = data_energy + time_energy

    co2_per_visit = round(energy_total * carbon_intensity, 4)
    co2_per_1000_visits = co2_per_visit * 1000
    rating = get_rating(co2_per_visit)

    result = {
        "url": entry["url"],
        "co2_per_visit": co2_per_visit,
        "co2_per_1000_visits": co2_per_1000_visits,
        "rating": rating
    }

    return result

def write_json_file(results):
    with open(Path(__file__).parent / "co2_results.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

def main():
    try:
        args = get_arguments()

        entries = read_json_file(args.file_path)

        results = []

        for entry in entries:
            result = calculate_co2(entry)
            results.append(result)

        write_json_file(results)

    except ValueError as error:
        print("Error:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()   