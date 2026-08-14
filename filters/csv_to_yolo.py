import pandas as pd
import ast
from pathlib import Path
from PIL import Image
from tqdm import tqdm


class CsvToYoloConverter:
    def __init__(self, json_data):
        self.csv_path = Path(json_data.get("csv_path", "annotations.csv"))
        self.image_folder = Path(json_data.get("image_folder", "images"))
        self.output_folder = Path(json_data.get("output_folder", "."))
        self.output_yolo_folder = self.output_folder / "yolo_labels"
        self.class_mapping_file = self.output_folder / json_data.get("label_txt", "label.txt")
        self.label2id = {}

        # Ensure output directory exists
        self.output_yolo_folder.mkdir(parents=True, exist_ok=True)

    def build_class_mapping(self):
        """Scan the CSV and extract a label-to-class ID mapping, then save to label.txt."""
        df = pd.read_csv(self.csv_path)
        label_set = set()

        for ann in df['annotations']:
            try:
                if not isinstance(ann, str) or ann.strip() == "" or ann.strip().lower() in ["nan", "none"]:
                    continue
                objects = ast.literal_eval(ann)
                for obj in objects:
                    label_set.add(obj['label'])
            except Exception as e:
                print(f"[Warning] Annotation parse error: {e} | Annotation: {ann}")
                continue

        # Create mapping from label to class ID
        self.label2id = {label: idx for idx, label in enumerate(sorted(label_set))}

        # Save to label.txt
        with open(self.class_mapping_file, "w") as f:
            for label in sorted(self.label2id, key=self.label2id.get):
                f.write(f"{label}\n")

        print(f"[Info] Class mapping saved to: {self.class_mapping_file}")

    def convert_all(self):
        """Convert all annotations in CSV to YOLO .txt format."""
        df = pd.read_csv(self.csv_path)

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Converting"):
            image_name = row['image_name']
            image_path = self.image_folder / image_name

            if not image_path.exists():
                print(f"[Warning] Image not found: {image_path}")
                continue

            try:
                with Image.open(image_path) as img:
                    img_w, img_h = img.size
            except Exception as e:
                print(f"[Error] Failed to load image {image_path}: {e}")
                continue

            try:
                ann = row['annotations']
                if not isinstance(ann, str) or ann.strip() == "" or ann.strip().lower() in ["nan", "none"]:
                    continue
                objects = ast.literal_eval(ann)
            except Exception as e:
                print(f"[Error] Annotation parse error for {image_name}: {e} | Annotation: {ann}")
                continue

            yolo_lines = []
            for obj in objects:
                label = obj.get('label')
                if label not in self.label2id:
                    continue

                points = obj.get('points', [])
                if (
                    isinstance(points, (list, tuple))
                    and len(points) == 2
                    and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points)
                ):
                    (x1, y1), (x2, y2) = points
                else:
                    print(f"[Warning] Invalid bbox format in {image_name}: {points}")
                    continue

                x_center = (x1 + x2) / 2.0 / img_w
                y_center = (y1 + y2) / 2.0 / img_h
                width = abs(x2 - x1) / img_w
                height = abs(y2 - y1) / img_h
                class_id = self.label2id[label]

                yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

            if yolo_lines:
                label_file = self.output_yolo_folder / f"{Path(image_name).stem}.txt"
                with open(label_file, "w") as f:
                    f.write("\n".join(yolo_lines))

    def run(self):
        """Run the full CSV to YOLO label conversion pipeline."""
        print("[Start] Building class mapping from CSV...")
        self.build_class_mapping()

        print("[Start] Converting annotations to YOLO format...")
        self.convert_all()

        print("[Done] CSV to YOLO conversion complete.")
        print(f"[Info] YOLO labels saved to: {self.output_yolo_folder}")
