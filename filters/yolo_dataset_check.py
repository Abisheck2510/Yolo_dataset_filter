import os
from pathlib import Path
import shutil

class CorruptYoloFilter:
    def __init__(self, json_data):
        self.data = json_data
        self.image_dir_name = self.data['images']
        self.annotation_dir_name = self.data['annotation']
        self.class_names = self.data.get('class_names', {})
        # Flatten class_names dict to get allowed class ids as strings
        # Assuming your labels use class ids as integers starting from 0 in order
        # If your classes are strings instead of numbers, adjust accordingly
        self.allowed_class_ids = set(str(i) for i in range(len(self.class_names)))

    def is_label_valid(self, label_path: Path) -> bool:
        """
        Validate label file:
        - Non-empty
        - Each line exactly 5 values
        - First value: integer class id in allowed range
        - Next 4 values floats in [0, 1]
        """
        try:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                if not lines:
                    print(f"❌ Empty label file: {label_path.name}")
                    return False
                for idx, line in enumerate(lines, 1):
                    parts = line.strip().split()
                    if len(parts) != 5:
                        print(f"❌ Line {idx} in {label_path.name} does not have 5 values: {parts}")
                        return False
                    cls_id, x, y, w, h = parts
                    if cls_id not in self.allowed_class_ids:
                        print(f"❌ Invalid class id '{cls_id}' at line {idx} in {label_path.name}")
                        return False
                    try:
                        x, y, w, h = map(float, (x, y, w, h))
                    except ValueError:
                        print(f"❌ Non-float bbox values at line {idx} in {label_path.name}")
                        return False
                    if not all(0 <= v <= 1 for v in [x, y, w, h]):
                        print(f"❌ Out-of-range bbox values at line {idx} in {label_path.name}: {x}, {y}, {w}, {h}")
                        return False
            return True
        except Exception as e:
            print(f"❌ Error reading label {label_path.name}: {e}")
            return False

    def move_corrupt_image_labels(self, base_path: Path):
        """
        Scan images and labels. Move corrupt pairs to corrupt folder.
        """
        image_dir = base_path / self.image_dir_name
        label_dir = base_path / self.annotation_dir_name
        corrupt_dir = base_path / "corrupt"
        corrupt_dir.mkdir(exist_ok=True, parents=True)

        image_exts = {'.jpg', '.jpeg', '.png'}
        moved_count = 0

        for img_path in image_dir.rglob("*"):
            if img_path.suffix.lower() not in image_exts:
                continue
            label_path = label_dir / img_path.with_suffix('.txt').name
            if not label_path.exists():
                continue  # No label, skip (or treat as corrupt if you want)
            if not self.is_label_valid(label_path):
                # Move both image and label to corrupt folder
                shutil.move(str(img_path), corrupt_dir / img_path.name)
                shutil.move(str(label_path), corrupt_dir / label_path.name)
                print(f"❌ Moved corrupt pair: {img_path.name} + {label_path.name}")
                moved_count += 1

        print(f"\n✅ Completed: Moved {moved_count} corrupt image-label pairs to '{corrupt_dir}'")

    def run_filter(self):
        print(f"🔍 Checking dataset for corrupted labels...")
        for key, val in self.data.get('input', {}).items():
            base_path = Path(val['dir'])
            print(f"\n📁 Dataset '{key}' at: {base_path}")
            self.move_corrupt_image_labels(base_path)
