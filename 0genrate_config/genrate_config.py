import json

PATHS_TXT = "/datavolume/files/dataset/aRun_Label/2025_DatasetFilter/0genrate_config/xpath.txt"       # input: one directory path per line
CONFIG_OUT = "config.json"    # output json config
DEFAULT_SAMPLE = 100

CLASS_NAMES = {
    "person": ["person"],
    "two_Wheeler": ["Two Wheeler"],
    "auto_rickshaw": ["auto_rickshaw"],
    "car": ["car"],
    "lcv": ["lcv"],
    "Eicher": ["Eicher", "Echier", "e"],
    "van": ["van"],
    "mini_bus": ["mini bus"],
    "bus": ["bus"],
    "Truck_2Axle": ["Truck_2Axle", "2"],
    "Truck_3Axle": ["Truck_3Axle", "3"],
    "Truck_4Axle": ["Truck_4Axle", "4"],
    "Truck_6Axle": ["Truck_6Axle", "6"],
    "multi_axle": ["multi axle"],
    "others_earth_mover": ["others(earth mover)"],
    "tracktor": ["tracktor"],
    "tracktor_trailer": ["tracktor_trailer"],
    "cycle": ["cycle"],
}


def read_paths(path):
    with open(path, "r") as f:
        return [ln.strip() for ln in f if ln.strip()]


def main():
    paths = read_paths(PATHS_TXT)
    inputs = {}
    for i, p in enumerate(paths, start=1):
        inputs[f"key{i}"] = {"dir": p, "sample": DEFAULT_SAMPLE}

    config = {
        "output": "workspace",
        "label_txt": "label.txt",
        "images": "images",
        "annotation": "annotation",
        "input": inputs,
        "class_names": CLASS_NAMES,
    }

    with open(CONFIG_OUT, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[done] {len(inputs)} dirs -> {CONFIG_OUT}")


if __name__ == "__main__":
    main()
