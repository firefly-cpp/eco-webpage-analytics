import argparse
import json
import sys
from pathlib import Path

# SWDM v4 operational network energy intensity
# Unit: kWh/GB
core_network_ann_per_gb = 0.059

# SWDM v4 embodied network energy intensity
# Unit: kWh/GB
core_network_dcn_per_gb = 0.013

# total network energy intensity
# Unit: kWh/GB
core_network_total = core_network_ann_per_gb + core_network_dcn_per_gb

# SWDM v4 total data-centre energy intensity:
# operational data-centre energy: 0.055 kWh/GB
# embodied data-centre energy:    0.012 kWh/GB
# Unit: kWh/GB
dc_kwh_per_gb = 0.055 + 0.012

# SWDM v4 total user-device energy intensity:
# operational user-device energy: 0.080 kWh/GB
# embodied user-device energy:    0.081 kWh/GB
# Unit: kWh/GB
user_device_kwh_per_gb = 0.080 + 0.081

# byte-to-gigabyte conversion used by SWDM v4:
# Unit: bytes/GB
bytes_per_gb = 1000000000

# grams of CO2e emitted to produce 1 kWh
# SWDM v4 default global average grid intensity
# Unit: gCO2e/kWh
carbon_intensity = 494


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

#rate website on a scale of A+ to F, using the Digital Carbon Rating scale
def get_rating(co2_per_visit):
    if co2_per_visit <= 0.040:
        return "A+"
    elif co2_per_visit <= 0.079:
        return "A"
    elif co2_per_visit <= 0.145:
        return "B"
    elif co2_per_visit <= 0.209:
        return "C"
    elif co2_per_visit <= 0.278:
        return "D"
    elif co2_per_visit <= 0.359:
        return "E"
    else:
        return "F"

def calculate_co2_from_bytes(total_bytes):
    if total_bytes < 0:
        raise ValueError("total_bytes must be a non-negative number.")

    total_bytes_in_gb = total_bytes / bytes_per_gb

    total_energy = total_bytes_in_gb * (
        dc_kwh_per_gb +
        core_network_total +
        user_device_kwh_per_gb
    )

    return total_energy * carbon_intensity

def calculate_co2(entry):
    total_bytes = entry["total_bytes"]

    co2_per_visit = calculate_co2_from_bytes(total_bytes)
    co2_per_1000_visits = co2_per_visit * 1000
    rating = get_rating(co2_per_visit)

    result = {
        "url": entry["url"],
        "co2_per_visit": round(co2_per_visit, 4),
        "co2_per_1000_visits": round(co2_per_1000_visits, 1),
        "rating": rating
    }

    return result

def add_carbon_data(entry):
    result = {**entry, **calculate_co2(entry)}
    image_transcoding = entry.get("image_transcoding")

    if image_transcoding:
        saved_co2_per_visit = calculate_co2_from_bytes(image_transcoding["saved_bytes"])

        result["image_transcoding"] = {
            **image_transcoding,
            "saved_co2_per_visit": round(saved_co2_per_visit, 4),
            "saved_co2_per_1000_visits": round(saved_co2_per_visit * 1000, 1)
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