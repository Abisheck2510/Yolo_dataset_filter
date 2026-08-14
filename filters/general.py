import json
import re
import yaml

def read_json():
    with open('config.json') as json_file:
        data = json.load(json_file)
    return data

def write_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def read_txt(label_path):
    
    with open(label_path) as f:
        lines = [x.strip() for x in f.read().strip().splitlines() if len(x.strip())]
    return lines

def write_txt(filename, lists):
    with open(filename, 'w') as f:
        for item in lists:
            f.write("%s\n" % item)

def write_yaml(filename, data):
    with open(filename, 'w') as outfile:
        yaml.dump(data, outfile, sort_keys=False, default_flow_style=False)

