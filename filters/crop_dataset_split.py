import random
import shutil
from pathlib import Path

from filters.base import BaseModel
from filters.general import write_yaml


class CropDatasetSplit(BaseModel):
    def __init__(self, json_data, split_ratio=0.8):
        super().__init__(json_data)
        self.split_ratio = split_ratio
        self.lut = {}
        for canonical, aliases in self.class_names.items():
            self.lut[canonical] = canonical
            for alias in aliases:
                self.lut[alias] = canonical

    def resolve_class(self, folder_name):
        return self.lut.get(folder_name)

    def collect_items(self):
        items = []
        for key, v in self.data['input'].items():
            dataset_dir = Path(v['dir'])
            crop_dir = dataset_dir / 'Cropped_Images'
            if not crop_dir.exists():
                print(f"[skip] No Cropped_Images folder in {dataset_dir}")
                continue

            prefix = dataset_dir.name
            for label_dir in crop_dir.iterdir():
                if not label_dir.is_dir():
                    continue
                class_name = self.resolve_class(label_dir.name)
                if class_name is None:
                    print(f"[skip] Folder '{label_dir.name}' does not match any class_names in config.json")
                    continue
                for img_path in label_dir.glob('*.jpg'):
                    items.append((img_path, class_name, prefix))
        return items

    def run(self):
        items = self.collect_items()
        if not items:
            print("No cropped images found. Run Crop Images first.")
            return

        random.shuffle(items)
        split_idx = int(len(items) * self.split_ratio)
        train_items = items[:split_idx]
        val_items = items[split_idx:]

        workspace_dir = Path(__file__).parents[1]
        output_dir = workspace_dir / "crop_dataset"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        present = {class_name for _, class_name, _ in items}
        classes = [c for c in self.class_names.keys() if c in present]
        extra = sorted(present - set(classes))
        if extra:
            print(f"[warn] classes not in config.json class_names order, appending alphabetically: {extra}")
            classes.extend(extra)

        print(f"Splitting cropped dataset: {len(train_items)} train, {len(val_items)} val across {len(classes)} classes.")

        for split_name, split_items in (("train", train_items), ("val", val_items)):
            for img_path, class_name, prefix in split_items:
                dest_dir = output_dir / split_name / class_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_name = f"{prefix}_{img_path.name}"
                shutil.copy(str(img_path), str(dest_dir / dest_name))

        yaml_data = {
            "path": str(output_dir.absolute()),
            "train": "train",
            "val": "val",
            "nc": len(classes),
            "names": classes,
        }
        yaml_path = output_dir / "custom.yaml"
        write_yaml(str(yaml_path), yaml_data)
        print(f"Cropped dataset split complete! Output saved to: {output_dir}")
        print(f"Generated {yaml_path}")
