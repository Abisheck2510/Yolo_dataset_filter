import cv2
import os
import shutil
import numpy as np
from pathlib import Path
import multiprocessing as mp
import xml.etree.ElementTree as ET
from termcolor import colored


class CropImages:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def chunk(lst, n):
        return [list(a) for a in np.array_split(lst, n)]

    @staticmethod
    def success_alert(msg):
        print('[', colored('ok', 'green'), ']', msg)

    def get_matched_pairs(self, path, img_folder, xml_folder):
        img_dir = path / img_folder
        xml_dir = path / xml_folder
        img_files = sorted(img_dir.glob('*.jpg'))
        xml_files = sorted(xml_dir.glob('*.xml'))

        img_basenames = {f.stem: f for f in img_files}
        xml_basenames = {f.stem: f for f in xml_files}
        matched_keys = img_basenames.keys() & xml_basenames.keys()
        return [(img_basenames[k], xml_basenames[k]) for k in sorted(matched_keys)]

    def crop_img(self, x, path, path_list):
        for img_file, xml_file in path_list:
            print(f'Processing [{x}]: {img_file.name}')
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                img = cv2.imread(str(img_file))
                if img is None:
                    print(f"❌ Failed to read image: {img_file}")
                    continue

                img_height, img_width = img.shape[:2]
                size_tag = root.find('size')
                updated = False

                if size_tag is not None:
                    width_tag = size_tag.find('width')
                    height_tag = size_tag.find('height')

                    if width_tag is not None and int(width_tag.text) != img_width:
                        width_tag.text = str(img_width)
                        updated = True
                    if height_tag is not None and int(height_tag.text) != img_height:
                        height_tag.text = str(img_height)
                        updated = True

                if updated:
                    tree.write(xml_file)
                    self.success_alert(f"Corrected XML size: {xml_file.name}")

                for obj in root.findall('object'):
                    bndbox = obj.find('bndbox')
                    xmin = int(float(bndbox.find('xmin').text))
                    ymin = int(float(bndbox.find('ymin').text))
                    xmax = int(float(bndbox.find('xmax').text))
                    ymax = int(float(bndbox.find('ymax').text))

                    label = obj.find('name').text
                    obj_id = obj.find('id').text if obj.find('id') is not None else 'noid'

                    crop_dir = path / 'Cropped_Images' / label
                    crop_dir.mkdir(parents=True, exist_ok=True)
                    save_path = crop_dir / f'{img_file.stem}-{obj_id}.jpg'

                    cropped = img[ymin:ymax, xmin:xmax]
                    cv2.imwrite(str(save_path), cropped)

            except Exception as e:
                print(f"❌ Error in {img_file.name}: {e}")

    def start(self):
        for k, v in self.data['input'].items():
            path = Path(v['dir'])
            crop_dir = path / 'Cropped_Images'
            if crop_dir.exists():
                shutil.rmtree(crop_dir)
                self.success_alert(f"Deleted: {crop_dir}")

            pairs = self.get_matched_pairs(path, self.data['images'], self.data['annotation'])
            num_proc = min(12, len(pairs))
            chunks = self.chunk(pairs, num_proc)

            processes = [
                mp.Process(target=self.crop_img, args=(i, path, chunks[i]))
                for i in range(num_proc)
            ]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
