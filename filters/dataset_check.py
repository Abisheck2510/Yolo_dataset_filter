import os
import json
import cv2
import xml.etree.ElementTree as ET
from pathlib import Path
from termcolor import colored
from collections import defaultdict
import numpy as np
import multiprocessing as mp


def check_image_chunk(chunk):
    errors = []
    for file in chunk:
        try:
            img = cv2.imread(str(file))
            if img is None:
                errors.append(file.name)
        except:
            errors.append(file.name)
    return errors


def check_class_chunk(chunk, class_names):
    result = {}
    for file in chunk:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            errors = []
            for obj in root.findall("object"):
                name = obj.find("name").text
                if name not in class_names:
                    errors.append(name)
            if errors:
                result[file.name] = errors
        except:
            result[file.name] = ["ParseError"]
    return result


class DatasetValidator:
    def __init__(self, json_data):
        self.data = json_data
        self.class_names = self.data['class_names']

    @staticmethod
    def success_alert(msg):
        print('[', colored('ok', 'green'), ']', msg)

    @staticmethod
    def danger_alert(msg):
        print(colored('not found:', 'red'), colored(msg, 'red'))

    def check_folder_exists(self, path):
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        self.success_alert("image folders") if img_dir.exists() else self.danger_alert("image folder")
        self.success_alert("annotation folders") if anno_dir.exists() else self.danger_alert("annotation folder")

    def check_extensions(self, path):
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        image_exts = {'.jpg', '.jpeg', '.png'}
        anno_exts = {'.xml'}

        wrong_images = [f for f in img_dir.iterdir() if f.suffix.lower() not in image_exts]
        wrong_annos = [f for f in anno_dir.iterdir() if f.suffix.lower() not in anno_exts]

        if wrong_images:
            self.danger_alert(f"Invalid image extensions: {[f.name for f in wrong_images]}")
        else:
            self.success_alert("No other extensions in image folders")

        if wrong_annos:
            self.danger_alert(f"Invalid annotation extensions: {[f.name for f in wrong_annos]}")
        else:
            self.success_alert("No other extensions in annotation folders")

    def check_file_pairs(self, path):
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        image_stems = {f.stem for f in img_dir.iterdir() if f.is_file()}
        xml_stems = {f.stem for f in anno_dir.iterdir() if f.is_file()}

        missing_annos = image_stems - xml_stems
        missing_images = xml_stems - image_stems

        for m in missing_annos:
            self.danger_alert(f"Missing annotation for image: {m}")
        for m in missing_images:
            self.danger_alert(f"Missing image for annotation: {m}")

        if not missing_annos and not missing_images:
            self.success_alert("all images and XML files are matched")

    def check_unreadable_images(self, path):
        img_dir = path / self.data['images']
        all_files = list(img_dir.iterdir())
        chunked = np.array_split(all_files, mp.cpu_count())

        with mp.Pool() as pool:
            results = pool.map(check_image_chunk, chunked)

        errors = [file for sublist in results for file in sublist]

        if errors:
            self.danger_alert(f"Corrupted or unreadable images: {errors}")
        else:
            self.success_alert("no corrupted images")

    def check_class_names(self, path):
        anno_dir = path / self.data['annotation']
        all_files = list(anno_dir.iterdir())
        chunked = np.array_split(all_files, mp.cpu_count())

        with mp.Pool() as pool:
            results = pool.starmap(check_class_chunk, [(list(chunk), self.class_names) for chunk in chunked])

        output_txt = path / "error_class_names.txt"
        error_tree = defaultdict(dict)
        for result in results:
            for file, classes in result.items():
                error_tree['annotation'][file] = classes

        if error_tree:
            with open(output_txt, "w") as f:
                for folder, files in error_tree.items():
                    folder_header = f"📁 {folder}"
                    print(colored(folder_header, "yellow"))
                    f.write(folder_header + "\n")
                    for file, classes in files.items():
                        print(f" └── {file}")
                        f.write(f" └── {file}\n")
                        for cls in classes:
                            class_line = f"     └─ ❌ Invalid class: '{cls}'"
                            print(colored(class_line, "red"))
                            f.write(class_line + "\n")
            self.danger_alert(f"Invalid class names found. See {output_txt}")
        else:
            self.success_alert("correct class names")

    def run_all_checks(self):
        for k, v in self.data['input'].items():
            path = Path(v['dir'])
            print(f"\n📁 Checking dataset: {k}")
            self.check_folder_exists(path)
            self.check_extensions(path)
            self.check_file_pairs(path)
            self.check_unreadable_images(path)
            self.check_class_names(path)
