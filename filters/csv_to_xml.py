import pandas as pd
import ast
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from tqdm import tqdm


class CsvToXmlConverter:
    def __init__(self, json_data):
        self.csv_path = Path(json_data.get("csv_path", "annotations.csv"))
        self.image_folder = Path(json_data.get("image_folder", "images"))
        self.output_folder = Path(json_data.get("output_folder", "."))
        self.output_xml_folder = self.output_folder / "annotations"
        self.database_name = json_data.get("database_name", "Unknown")
        
        # Ensure output directory exists
        self.output_xml_folder.mkdir(parents=True, exist_ok=True)

    def create_xml_annotation(self, image_name, image_width, image_height, objects):
        """Create Pascal VOC format XML annotation."""
        annotation = ET.Element("annotation")
        
        # Add folder element
        folder = ET.SubElement(annotation, "folder")
        folder.text = str(self.image_folder.name)
        
        # Add filename element
        filename = ET.SubElement(annotation, "filename")
        filename.text = image_name
        
        # Add path element
        path = ET.SubElement(annotation, "path")
        path.text = str(self.image_folder / image_name)
        
        # Add source element
        source = ET.SubElement(annotation, "source")
        database = ET.SubElement(source, "database")
        database.text = self.database_name
        
        # Add size element
        size = ET.SubElement(annotation, "size")
        width = ET.SubElement(size, "width")
        width.text = str(image_width)
        height = ET.SubElement(size, "height")
        height.text = str(image_height)
        depth = ET.SubElement(size, "depth")
        depth.text = "3"  # Assuming RGB images
        
        # Add segmented element
        segmented = ET.SubElement(annotation, "segmented")
        segmented.text = "0"
        
        # Add object elements
        for obj in objects:
            object_elem = ET.SubElement(annotation, "object")
            
            # Object name
            name = ET.SubElement(object_elem, "name")
            name.text = obj['label']
            
            # Pose (unknown)
            pose = ET.SubElement(object_elem, "pose")
            pose.text = "Unspecified"
            
            # Truncated
            truncated = ET.SubElement(object_elem, "truncated")
            truncated.text = "0"
            
            # Difficult
            difficult = ET.SubElement(object_elem, "difficult")
            difficult.text = "0"
            
            # Bounding box
            bndbox = ET.SubElement(object_elem, "bndbox")
            
            points = obj.get('points', [])
            if (
                isinstance(points, (list, tuple))
                and len(points) == 2
                and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points)
            ):
                (x1, y1), (x2, y2) = points
                
                # Ensure coordinates are in correct order (top-left, bottom-right)
                xmin = min(x1, x2)
                ymin = min(y1, y2)
                xmax = max(x1, x2)
                ymax = max(y1, y2)
                
                xmin_elem = ET.SubElement(bndbox, "xmin")
                xmin_elem.text = str(int(xmin))
                ymin_elem = ET.SubElement(bndbox, "ymin")
                ymin_elem.text = str(int(ymin))
                xmax_elem = ET.SubElement(bndbox, "xmax")
                xmax_elem.text = str(int(xmax))
                ymax_elem = ET.SubElement(bndbox, "ymax")
                ymax_elem.text = str(int(ymax))
        
        return annotation

    def format_xml(self, element):
        """Format XML with proper indentation."""
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(element)
        return element

    def convert_all(self):
        """Convert all annotations in CSV to XML format."""
        df = pd.read_csv(self.csv_path)
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Converting to XML"):
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
            
            # Filter out invalid objects
            valid_objects = []
            for obj in objects:
                label = obj.get('label')
                points = obj.get('points', [])
                
                if (
                    label and
                    isinstance(points, (list, tuple)) and
                    len(points) == 2 and
                    all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points)
                ):
                    valid_objects.append(obj)
                else:
                    print(f"[Warning] Invalid object format in {image_name}: {obj}")
            
            if valid_objects:
                # Create XML annotation
                xml_annotation = self.create_xml_annotation(image_name, img_w, img_h, valid_objects)
                
                # Format and save XML
                formatted_xml = self.format_xml(xml_annotation)
                xml_file = self.output_xml_folder / f"{Path(image_name).stem}.xml"
                
                tree = ET.ElementTree(formatted_xml)
                tree.write(xml_file, encoding='utf-8', xml_declaration=True)

    def run(self):
        """Run the full CSV to XML conversion pipeline."""
        print("[Start] Converting annotations to XML format...")
        self.convert_all()
        print("[Done] CSV to XML conversion complete.")
        print(f"[Info] XML annotations saved to: {self.output_xml_folder}")


