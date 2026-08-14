import os
from xml.dom import minidom

class XMLFormatter:
    def __init__(self, xml_folder):
        self.xml_folder = xml_folder

    def prettify_xml_file(self, xml_path):
        try:
            with open(xml_path, 'r', encoding='utf-8') as file:
                xml_string = file.read()
            parsed_xml = minidom.parseString(xml_string)
            pretty_xml = parsed_xml.toprettyxml(indent="  ")
            pretty_xml = "\n".join([line for line in pretty_xml.split("\n") if line.strip() != ""])
            with open(xml_path, 'w', encoding='utf-8') as file:
                file.write(pretty_xml)
            print(f"[✔] Formatted: {os.path.basename(xml_path)}")
        except Exception as e:
            print(f"[✘] Error formatting {xml_path}: {e}")

    def prettify_all_xmls(self):
        if not os.path.exists(self.xml_folder):
            print(f"Folder not found: {self.xml_folder}")
            return

        xml_files = [f for f in os.listdir(self.xml_folder) if f.endswith('.xml')]
        if not xml_files:
            print("No XML files found to format.")
            return

        print(f"Formatting {len(xml_files)} XML files in '{self.xml_folder}'...")
        for file in xml_files:
            full_path = os.path.join(self.xml_folder, file)
            self.prettify_xml_file(full_path)
        print("✅ All XML files formatted successfully.")

