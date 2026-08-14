import os
import json
import cv2
import xml.etree.ElementTree as ET
from pathlib import Path
from termcolor import colored
from collections import defaultdict
import numpy as np
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import multiprocessing



def check_image_chunk(chunk):
    """Check if images in chunk are readable"""
    errors = []
    for file in chunk:
        try:
            img = cv2.imread(str(file))
            if img is None:
                errors.append(file.name)
        except Exception:
            errors.append(file.name)
    return errors


def check_class_chunk(chunk_data):
    """Check class names in annotation chunk"""
    chunk, class_names = chunk_data
    result = {}
    for file in chunk:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            errors = []
            for obj in root.findall("object"):
                name_elem = obj.find("name")
                if name_elem is not None:
                    name = name_elem.text
                    if name not in class_names:
                        errors.append(name)
            if errors:
                result[file.name] = errors
        except Exception:
            result[file.name] = ["ParseError"]
    return result


def check_extension_chunk(chunk_data):
    """Check file extensions in chunk"""
    chunk, valid_exts = chunk_data
    invalid_files = []
    for file in chunk:
        if file.suffix.lower() not in valid_exts:
            invalid_files.append(file.name)
    return invalid_files


def get_file_stems_chunk(chunk):
    """Get file stems (names without extension) from chunk"""
    return {f.stem for f in chunk if f.is_file()}


class DatasetValidator:
    print(multiprocessing.cpu_count())
    def __init__(self, json_data, max_workers=None):
        self.data = json_data
        self.class_names = set(self.data['class_names'])  # Use set for faster lookup
        self.max_workers = max_workers or min(mp.cpu_count(), 8)  # Limit max workers
        
    @staticmethod
    def success_alert(msg):
        print('[', colored('ok', 'green'), ']', msg)

    @staticmethod
    def danger_alert(msg):
        print(colored('not found:', 'red'), colored(msg, 'red'))

    def create_optimal_chunks(self, files, chunk_size=None):
        """Create optimal chunks based on file count and available workers"""
        file_list = list(files)
        total_files = len(file_list)
        
        if total_files == 0:
            return []
            
        if chunk_size is None:
            # Calculate optimal chunk size
            chunk_size = max(1, total_files // (self.max_workers * 2))
            chunk_size = min(chunk_size, 100)  # Cap chunk size to avoid memory issues
        
        chunks = []
        for i in range(0, total_files, chunk_size):
            chunks.append(file_list[i:i + chunk_size])
        
        return chunks

    def check_folder_exists(self, path):
        """Check if required folders exist"""
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        
        img_exists = img_dir.exists()
        anno_exists = anno_dir.exists()
        
        self.success_alert("image folders") if img_exists else self.danger_alert("image folder")
        self.success_alert("annotation folders") if anno_exists else self.danger_alert("annotation folder")
        
        return img_exists, anno_exists

    def check_extensions_parallel(self, path):
        """Check file extensions using parallel processing"""
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        
        if not img_dir.exists() or not anno_dir.exists():
            return
            
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        anno_exts = {'.xml'}

        # Get all files
        img_files = list(img_dir.iterdir())
        anno_files = list(anno_dir.iterdir())

        # Create chunks
        img_chunks = self.create_optimal_chunks(img_files)
        anno_chunks = self.create_optimal_chunks(anno_files)

        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit image extension checks
            img_futures = [
                executor.submit(check_extension_chunk, (chunk, image_exts))
                for chunk in img_chunks
            ]
            
            # Submit annotation extension checks
            anno_futures = [
                executor.submit(check_extension_chunk, (chunk, anno_exts))
                for chunk in anno_chunks
            ]
            
            # Collect results
            wrong_images = []
            wrong_annos = []
            
            for future in as_completed(img_futures):
                wrong_images.extend(future.result())
                
            for future in as_completed(anno_futures):
                wrong_annos.extend(future.result())

        # Report results
        if wrong_images:
            self.danger_alert(f"Invalid image extensions: {wrong_images[:10]}{'...' if len(wrong_images) > 10 else ''}")
        else:
            self.success_alert("No invalid extensions in image folders")

        if wrong_annos:
            self.danger_alert(f"Invalid annotation extensions: {wrong_annos[:10]}{'...' if len(wrong_annos) > 10 else ''}")
        else:
            self.success_alert("No invalid extensions in annotation folders")

    def check_file_pairs_parallel(self, path):
        """Check file pairs using parallel processing"""
        img_dir = path / self.data['images']
        anno_dir = path / self.data['annotation']
        
        if not img_dir.exists() or not anno_dir.exists():
            return

        # Get all files
        img_files = list(img_dir.iterdir())
        anno_files = list(anno_dir.iterdir())

        # Create chunks for parallel processing
        img_chunks = self.create_optimal_chunks(img_files)
        anno_chunks = self.create_optimal_chunks(anno_files)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Process image stems
            img_futures = [executor.submit(get_file_stems_chunk, chunk) for chunk in img_chunks]
            anno_futures = [executor.submit(get_file_stems_chunk, chunk) for chunk in anno_chunks]
            
            # Collect stems
            image_stems = set()
            xml_stems = set()
            
            for future in as_completed(img_futures):
                image_stems.update(future.result())
                
            for future in as_completed(anno_futures):
                xml_stems.update(future.result())

        # Find mismatches
        missing_annos = image_stems - xml_stems
        missing_images = xml_stems - image_stems

        # Report results
        for m in list(missing_annos)[:10]:  # Limit output
            self.danger_alert(f"Missing annotation for image: {m}")
        if len(missing_annos) > 10:
            self.danger_alert(f"... and {len(missing_annos) - 10} more missing annotations")
            
        for m in list(missing_images)[:10]:  # Limit output
            self.danger_alert(f"Missing image for annotation: {m}")
        if len(missing_images) > 10:
            self.danger_alert(f"... and {len(missing_images) - 10} more missing images")

        if not missing_annos and not missing_images:
            self.success_alert("all images and XML files are matched")

    def check_unreadable_images_optimized(self, path):
        """Check unreadable images with optimized chunking"""
        img_dir = path / self.data['images']
        
        if not img_dir.exists():
            return
            
        all_files = list(img_dir.iterdir())
        if not all_files:
            self.success_alert("no images to check")
            return

        # Create optimal chunks
        chunks = self.create_optimal_chunks(all_files)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(check_image_chunk, chunk) for chunk in chunks]
            
            errors = []
            for future in as_completed(futures):
                errors.extend(future.result())

        if errors:
            self.danger_alert(f"Corrupted or unreadable images: {errors[:10]}{'...' if len(errors) > 10 else ''}")
        else:
            self.success_alert("no corrupted images")

    def check_class_names_optimized(self, path):
        """Check class names with optimized processing"""
        anno_dir = path / self.data['annotation']
        
        if not anno_dir.exists():
            return
            
        all_files = list(anno_dir.iterdir())
        if not all_files:
            self.success_alert("no annotations to check")
            return

        # Create optimal chunks
        chunks = self.create_optimal_chunks(all_files)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            chunk_data = [(chunk, self.class_names) for chunk in chunks]
            futures = [executor.submit(check_class_chunk, data) for data in chunk_data]
            
            error_tree = defaultdict(dict)
            for future in as_completed(futures):
                result = future.result()
                for file, classes in result.items():
                    error_tree['annotation'][file] = classes

        # Output results
        if error_tree:
            output_txt = path / "error_class_names.txt"
            with open(output_txt, "w") as f:
                for folder, files in error_tree.items():
                    folder_header = f"📁 {folder}"
                    print(colored(folder_header, "yellow"))
                    f.write(folder_header + "\n")
                    
                    # Limit console output but write all to file
                    file_items = list(files.items())
                    for i, (file, classes) in enumerate(file_items):
                        if i < 10:  # Only show first 10 in console
                            print(f" └── {file}")
                            for cls in classes:
                                class_line = f"     └─ ❌ Invalid class: '{cls}'"
                                print(colored(class_line, "red"))
                        
                        # Always write to file
                        f.write(f" └── {file}\n")
                        for cls in classes:
                            f.write(f"     └─ ❌ Invalid class: '{cls}'\n")
                    
                    if len(file_items) > 10:
                        print(f" ... and {len(file_items) - 10} more files with errors")
                        
            self.danger_alert(f"Invalid class names found. See {output_txt}")
        else:
            self.success_alert("correct class names")

    def run_all_checks(self):
        """Run all validation checks with timing"""
        total_start_time = time.time()
        
        for k, v in self.data['input'].items():
            path = Path(v['dir'])
            print(f"\n📁 Checking dataset: {k}")
            
            start_time = time.time()
            
            # Check folder existence first
            img_exists, anno_exists = self.check_folder_exists(path)
            
            if img_exists and anno_exists:
                # Run parallel checks
                self.check_extensions_parallel(path)
                self.check_file_pairs_parallel(path)
                self.check_unreadable_images_optimized(path)
                self.check_class_names_optimized(path)
            
            elapsed = time.time() - start_time
            print(f"⏱️  Dataset '{k}' processed in {elapsed:.2f} seconds")
        
        total_elapsed = time.time() - total_start_time
        print(f"\n🏁 Total validation time: {total_elapsed:.2f} seconds")