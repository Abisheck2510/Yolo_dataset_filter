import os
import random
import shutil
from pathlib import Path

# Input dataset folder
SOURCE_DIR = "/datavolume/files/dataset/cosai_dataset/namakal/namakal_5/Cropped_Images"

# Output folder
OUTPUT_DIR = "/datavolume/files/dataset/cosai_dataset/namakal/namakal_5/cls_training"

# Split ratio
TRAIN_RATIO = 0.8

random.seed(42)

source_path = Path(SOURCE_DIR)
output_path = Path(OUTPUT_DIR)

train_path = output_path / "train"
val_path = output_path / "val"

# Create output directories
train_path.mkdir(parents=True, exist_ok=True)
val_path.mkdir(parents=True, exist_ok=True)

# Process each class folder
for class_dir in source_path.iterdir():
    if not class_dir.is_dir():
        continue

    class_name = class_dir.name

    # Create class folders
    (train_path / class_name).mkdir(parents=True, exist_ok=True)
    (val_path / class_name).mkdir(parents=True, exist_ok=True)

    # Get all images
    images = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]:
        images.extend(list(class_dir.glob(ext)))

    random.shuffle(images)

    split_idx = int(len(images) * TRAIN_RATIO)

    train_images = images[:split_idx]
    val_images = images[split_idx:]

    # Copy train images
    for img in train_images:
        shutil.copy2(
            img,
            train_path / class_name / img.name
        )

    # Copy val images
    for img in val_images:
        shutil.copy2(
            img,
            val_path / class_name / img.name
        )

    print(
        f"{class_name}: "
        f"Train={len(train_images)}, "
        f"Val={len(val_images)}"
    )

print("\nDataset split completed!")
