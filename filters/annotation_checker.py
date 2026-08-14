import os
from pathlib import Path
import xml.etree.ElementTree as ET
from termcolor import colored


class AnnotationChecker:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def success_alert(msg):
        print('[', colored('ok', 'green'), ']', msg)

    @staticmethod
    def danger_alert(msg):
        print('[', colored('error', 'red'), ']', colored(msg, 'red'))

    def check_mismatches(self):
        for k, v in self.data['input'].items():
            base_path = Path(v['dir'])
            img_dir = base_path / self.data['images']
            xml_dir = base_path / self.data['annotation']
            mismatch_dir = base_path / 'corrupted_images' / 'mismatch'
            mismatch_dir.mkdir(parents=True, exist_ok=True)

            img_files = sorted(img_dir.glob('*.jpg'))
            xml_files = sorted(xml_dir.glob('*.xml'))

            img_basenames = {f.stem: f for f in img_files}
            xml_basenames = {f.stem: f for f in xml_files}

            img_only = img_basenames.keys() - xml_basenames.keys()
            xml_only = xml_basenames.keys() - img_basenames.keys()

            for name in img_only:
                img_basenames[name].rename(mismatch_dir / img_basenames[name].name)
                self.danger_alert(f"Moved unmatched image: {img_basenames[name]}")

            for name in xml_only:
                xml_basenames[name].rename(mismatch_dir / xml_basenames[name].name)
                self.danger_alert(f"Moved unmatched XML: {xml_basenames[name]}")

            matched = img_basenames.keys() & xml_basenames.keys()
            self.success_alert(f"Matched Pairs Found: {len(matched)}")

    def check_annotation_validity(self):
        for k, v in self.data['input'].items():
            base_path = Path(v['dir'])
            img_dir = base_path / self.data['images']
            xml_dir = base_path / self.data['annotation']

            empty_img_dir = base_path / 'corrupted_images' / 'empty_annotations'
            empty_xml_dir = base_path / 'corrupted_images' / 'empty_annotations'
            empty_img_dir.mkdir(parents=True, exist_ok=True)
            empty_xml_dir.mkdir(parents=True, exist_ok=True)

            img_files = sorted(img_dir.glob('*.jpg'))
            xml_files = sorted(xml_dir.glob('*.xml'))

            for xml_file in xml_files:
                try:
                    if os.path.getsize(xml_file) == 0:
                        raise ValueError("Empty XML file")

                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    objects = root.findall('object')

                    if not objects:
                        raise ValueError("No <object> found")

                    for obj in objects:
                        bndbox = obj.find('bndbox')
                        if bndbox is None:
                            raise ValueError("Missing <bndbox>")
                        for tag in ['xmin', 'ymin', 'xmax', 'ymax']:
                            val = bndbox.find(tag)
                            if val is None or not val.text or not val.text.strip().isdigit():
                                raise ValueError(f"Invalid <{tag}>")

                except Exception as e:
                    stem = xml_file.stem
                    img_file = img_dir / f"{stem}.jpg"
                    if img_file.exists():
                        img_file.rename(empty_img_dir / img_file.name)
                    xml_file.rename(empty_xml_dir / xml_file.name)
                    self.danger_alert(f"{e} — moved: {xml_file.name}")
