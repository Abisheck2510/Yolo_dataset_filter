import json

PATHS_TXT = "/datavolume/files/dataset/aRun_Label/2025_DatasetFilter/0genrate_config/xpath.txt"       # input: one directory path per line
CONFIG_OUT = "config.json"    # output json config
DEFAULT_SAMPLE = 100

CLASS_NAMES = {
    "license_plate": ["object","number","plate"],
    "helmet": ["n"],
    "no_helmet": ["n"],
    "seat_belt": ["n"],
    "no_seat_belt": ["n"],
    "triple_riding": ["n"]
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
