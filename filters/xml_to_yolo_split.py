import os
import random
import zipfile
import yaml
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from filters.base import BaseModel

class XmlToYoloSplit(BaseModel):
    def __init__(self, json_data):
        super().__init__(json_data)
        self.lut = {}
        for idx, (key, aliases) in enumerate(self.class_names.items()):
            self.lut[key] = idx
            for alias in aliases:
                self.lut[alias] = idx

    @staticmethod
    def convert_coordinates(size, box):
        dw = 1.0 / size[0]
        dh = 1.0 / size[1]
        x = (box[0] + box[1]) / 2.0
        y = (box[2] + box[3]) / 2.0
        w = box[1] - box[0]
        h = box[3] - box[2]
        x = x * dw
        w = w * dw
        y = y * dh
        h = h * dh
        return (x, y, w, h)

    def convert_xml_to_label_text(self, xml_path):
        try:
            root = ET.parse(str(xml_path)).getroot()
            size = root.find('size')
            width = int(size.find('width').text)
            height = int(size.find('height').text)

            lines = []
            for item in root.iter('object'):
                classid = item.find('name').text
                if classid in self.lut:
                    label_str = str(self.lut[classid])
                else:
                    label_str = "-1"
                    print(f"warning: label '{classid}' not in look-up table")

                bndbox = item.find('bndbox')
                xmin = bndbox.find('xmin').text
                ymin = bndbox.find('ymin').text
                xmax = bndbox.find('xmax').text
                ymax = bndbox.find('ymax').text
                b = (float(xmin), float(xmax), float(ymin), float(ymax))
                bb = self.convert_coordinates((width, height), b)
                lines.append(f"{label_str} " + " ".join([("%.6f" % a) for a in bb]))

            return "\n".join(lines) + "\n"
        except Exception as e:
            print(f"Error converting {xml_path}: {e}")
            return None

    def _build_entry(self, img_path, xml_path, split):
        img_path = Path(img_path)
        xml_path = Path(xml_path)
        img_bytes = img_path.read_bytes()
        label_text = self.convert_xml_to_label_text(xml_path)
        return split, img_path.stem, img_path.suffix, img_bytes, label_text

    def run(self):
        # We will collect all image-xml pairs
        all_pairs = []
        for k, v in self.data['input'].items():
            path, im_path, xm_path = self.get_paths(v['dir'])
            # Read pairs using BaseModel's read_folder
            pairs = self.read_folder(path, self.images, self.annotation)
            all_pairs.extend(pairs)

        if not all_pairs:
            print("No image-xml pairs found in the input directories.")
            return

        # Shuffle the pairs
        random.shuffle(all_pairs)

        # Split into train (80%) and val (20%)
        split_idx = int(len(all_pairs) * 0.8)
        train_pairs = all_pairs[:split_idx]
        val_pairs = all_pairs[split_idx:]

        # Build directly into a zip archive: source files are read once and written
        # straight into the zip, with no intermediate "yolo_dataset" folder on disk
        # (avoids the copy-to-folder + re-read-to-zip double I/O pass).
        workspace_dir = Path(__file__).parents[1]
        zip_path = workspace_dir / "yolo_dataset.zip"

        print(f"Splitting dataset: {len(train_pairs)} train items, {len(val_pairs)} val items.")

        jobs = [(img_path, xml_path, "train") for img_path, xml_path in train_pairs]
        jobs += [(img_path, xml_path, "val") for img_path, xml_path in val_pairs]

        # Reads + xml parsing happen concurrently across threads (I/O-bound); the
        # zip itself is written from the main thread since ZipFile isn't thread-safe.
        # Different input source directories can contain same-named files (e.g. two
        # cameras both producing "anpr_plate5482.jpg"); dedupe by suffixing repeats
        # so nothing gets silently dropped or collides in the archive.
        seen_counts = {}
        max_workers = min(32, (os.cpu_count() or 4) * 4)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf, \
                ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._build_entry, img_path, xml_path, split)
                for img_path, xml_path, split in jobs
            ]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Building zip"):
                split, stem, ext, img_bytes, label_text = future.result()
                key = (split, stem)
                occurrence = seen_counts.get(key, 0)
                seen_counts[key] = occurrence + 1
                name = stem if occurrence == 0 else f"{stem}_{occurrence}"
                if occurrence > 0:
                    print(f"note: duplicate filename '{stem}{ext}' in '{split}' split, renamed to '{name}{ext}'")
                zf.writestr(f"{split}/images/{name}{ext}", img_bytes)
                if label_text is not None:
                    zf.writestr(f"{split}/labels/{name}.txt", label_text)

            yaml_data = {
                "path": ".",
                "train": "train/images",
                "val": "val/images",
                "nc": len(self.class_names.keys()),
                "names": list(self.class_names.keys())
            }
            zf.writestr("custom.yaml", yaml.dump(yaml_data, sort_keys=False, default_flow_style=False))

        print(f"Zipped dataset saved to: {zip_path}")

