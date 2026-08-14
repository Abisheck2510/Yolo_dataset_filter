import os
import cv2
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET


def indent(elem, level=0):
    """Pretty-print XML by adding indentation (in-place)."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for subelem in elem:
            indent(subelem, level + 1)
        if not subelem.tail or not subelem.tail.strip():
            subelem.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

class TxtToXmlConverter:
    def __init__(self, config):
        self.data = config
        self.classes = config.get("class_names", [])

        base_dir = list(config["input"].values())[0]["dir"]

        self.label_dir = os.path.join(base_dir, config.get("yolo_txt_dir", "labels"))
        self.image_dir = os.path.join(base_dir, config.get("images", "images"))
        self.output_dir = os.path.join(base_dir, config.get("annotation", "annotations_xml"))
        
        os.makedirs(self.output_dir, exist_ok=True)


    def convert_file(self, txt_path, img_path):
        img = cv2.imread(img_path)
        if img is None:
            print(f"[Warning] Unable to load image: {img_path}")
            return
        h, w, _ = img.shape
        image_name = os.path.basename(img_path)
        xml_name = os.path.splitext(image_name)[0] + ".xml"

        annotation = ET.Element('annotation')
        ET.SubElement(annotation, 'filename').text = image_name

        size = ET.SubElement(annotation, 'size')
        ET.SubElement(size, 'width').text = str(w)
        ET.SubElement(size, 'height').text = str(h)
        ET.SubElement(size, 'depth').text = '3'

        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            class_id, x_c, y_c, box_w, box_h = map(float, parts)
            class_id = int(class_id)
            if class_id >= len(self.classes):
                print(f"[Warning] Invalid class_id {class_id} in {txt_path}")
                continue

            xmin = int((x_c - box_w / 2) * w)
            ymin = int((y_c - box_h / 2) * h)
            xmax = int((x_c + box_w / 2) * w)
            ymax = int((y_c + box_h / 2) * h)

            obj = ET.SubElement(annotation, 'object')
            ET.SubElement(obj, 'name').text = self.classes[class_id]
            bndbox = ET.SubElement(obj, 'bndbox')
            ET.SubElement(bndbox, 'xmin').text = str(xmin)
            ET.SubElement(bndbox, 'ymin').text = str(ymin)
            ET.SubElement(bndbox, 'xmax').text = str(xmax)
            ET.SubElement(bndbox, 'ymax').text = str(ymax)

        # Save XML without declaration
        indent(annotation)
        tree = ET.ElementTree(annotation)
        tree.write(os.path.join(self.output_dir, xml_name), encoding='utf-8', xml_declaration=False)


    def run(self):
        for filename in os.listdir(self.label_dir):
            if not filename.endswith('.txt'):
                continue
            txt_path = os.path.join(self.label_dir, filename)
            img_name = os.path.splitext(filename)[0] + '.jpg'
            img_path = os.path.join(self.image_dir, img_name)
            if os.path.exists(img_path):
                self.convert_file(txt_path, img_path)
            else:
                print(f"[Warning] Image not found for {filename}")
