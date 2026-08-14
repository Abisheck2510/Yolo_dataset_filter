class CropImages(BaseModel):

    def __init__(self, json_data):
        super().__init__(json_data)

    @staticmethod
    def chunk(lst, n):
        """Split list into chunks"""
        splits = np.array_split(lst, n)
        chunk_data = [list(a) for a in splits]
        return chunk_data
    
    @staticmethod
    def success_alert(msg):
        print('[', colored('ok', 'green'), ']', msg)

    @staticmethod
    def danger_alert(msg):
        print('[', colored('error', 'red'), ']', colored(msg, 'red'))


    def read_folder(self, base_path, img_folder, xml_folder):
        """Read image and XML files, print mismatched file paths if any, and return only matched pairs."""
        img_dir = base_path / img_folder
        xml_dir = base_path / xml_folder
        mismatch_dir = base_path / 'corrupted_images' / 'mismatch'
        mismatch_dir.mkdir(parents=True, exist_ok=True)

        if not img_dir.exists():
            print(f"❌ Image directory not found: {img_dir}")
            return []
        if not xml_dir.exists():
            print(f"❌ XML directory not found: {xml_dir}")
            return []

        img_files = sorted(img_dir.glob('*.jpg'))  # or *.png
        xml_files = sorted(xml_dir.glob('*.xml'))

        img_basenames = {f.stem: f for f in img_files}
        xml_basenames = {f.stem: f for f in xml_files}

        img_only = img_basenames.keys() - xml_basenames.keys()
        xml_only = xml_basenames.keys() - img_basenames.keys()

        for name in img_only:
            print(f"⚠️ Moving unmatched image: {img_basenames[name]}")
            img_basenames[name].rename(mismatch_dir / img_basenames[name].name)

        for name in xml_only:
            print(f"⚠️ Moving unmatched XML: {xml_basenames[name]}")
            xml_basenames[name].rename(mismatch_dir / xml_basenames[name].name)


        # if img_only or xml_only:
        #     print("⚠️ Mismatched files found (skipping them):")
        #     if img_only:
        #         print(" - Images without XML:")
        #         for name in img_only:
        #             print(f"   {img_basenames[name]}")
        #     if xml_only:
        #         print(" - XMLs without Images:")
        #         for name in xml_only:
        #             print(f"   {xml_basenames[name]}")

        matched_keys = img_basenames.keys() & xml_basenames.keys()
        matched_pairs = [(img_basenames[k], xml_basenames[k]) for k in sorted(matched_keys)]

        print(f"✅ Found {len(matched_pairs)} matched image-XML pairs.")
        return matched_pairs


    def crop_img(self, x, path, path_list):
        """Crop images. If any object has missing/invalid <bndbox>, or XML is empty/malformed, move to corrupted_images/empty_annotations/."""

        # Create required directories
        empty_img_dir = path / 'corrupted_images' / 'empty_annotations' / 'image'
        empty_img_dir.mkdir(parents=True, exist_ok=True)
        empty_xml_dir = path / 'corrupted_images' / 'empty_annotations' / 'xml'
        empty_xml_dir.mkdir(parents=True, exist_ok=True)

        for imfile, xmfile in path_list:
            print(f'Processing [{x}]: {imfile.name}')
            try:
                # Check if XML file is empty (0 bytes)
                if os.path.getsize(xmfile) == 0:
                    raise ValueError("XML file is empty (0 bytes)")

                # Try parsing XML
                xmlTree = ET.parse(xmfile)
                root = xmlTree.getroot()

                # Check if XML has no elements (empty structure)
                if len(root) == 0:
                    raise ValueError("XML contains no elements")

                # Read image
                img = cv2.imread(str(imfile), cv2.IMREAD_COLOR)
                if img is None:
                    print(f'❌ Cannot read image: {imfile}')
                    continue

                img_height, img_width = img.shape[:2]

                # ✅ Fix incorrect <size> if needed
                size_tag = root.find('size')
                if size_tag is not None:
                    width_tag = size_tag.find('width')
                    height_tag = size_tag.find('height')

                    xml_width = int(width_tag.text) if width_tag is not None else -1
                    xml_height = int(height_tag.text) if height_tag is not None else -1

                    updated = False
                    if xml_width != img_width:
                        width_tag.text = str(img_width)
                        updated = True
                    if xml_height != img_height:
                        height_tag.text = str(img_height)
                        updated = True

                    if updated:
                        xmlTree.write(xmfile)
                        self.success_alert(f"Corrected size in XML: {xmfile.name}")

                objects = root.findall('object')
                if not objects:
                    raise ValueError("No <object> tags found")

                # Validate all <bndbox> entries
                for obj in objects:
                    bndbox = obj.find('bndbox')
                    if bndbox is None:
                        raise ValueError("Missing <bndbox> in object")

                    for tag in ['xmin', 'ymin', 'xmax', 'ymax']:
                        val_tag = bndbox.find(tag)
                        if val_tag is None or not val_tag.text or not val_tag.text.strip().isdigit():
                            raise ValueError(f"Invalid or missing <{tag}> in {xmfile.name}")

                # ✅ All validations passed — start cropping
                for obj in objects:
                    bndbox = obj.find('bndbox')
                    xmin = int(float(bndbox.find('xmin').text))
                    ymin = int(float(bndbox.find('ymin').text))
                    xmax = int(float(bndbox.find('xmax').text))
                    ymax = int(float(bndbox.find('ymax').text))

                    label_name = obj.find('name').text
                    crop_path = path / 'Cropped_Images' / label_name
                    crop_path.mkdir(parents=True, exist_ok=True)

                    cropped_img = img[ymin:ymax, xmin:xmax]
                    obj_id = obj.find('id').text if obj.find('id') is not None else 'noid'
                    base_name = imfile.stem
                    save_path = crop_path / f'{base_name}-{obj_id}.jpg'

                    success = cv2.imwrite(str(save_path), cropped_img)
                    if not success:
                        print(f'❌ Failed to save cropped image: {save_path}')

            except Exception as e:
                self.danger_alert(f"{e} — moving to empty_annotations: {xmfile.name}")
                try:
                    imfile.rename(empty_img_dir / imfile.name)
                    xmfile.rename(empty_xml_dir / xmfile.name)
                except Exception as move_err:
                    self.danger_alert(f"❌ Failed to move corrupted files: {imfile.name}, {xmfile.name} — {move_err}")


    def start(self):
        """Start multiprocessing for image cropping"""
        for k, v in self.data['input'].items():
            path = Path(v['dir'])

            # 🔥 Delete existing cropped images
            cropped_dir = path / 'Cropped_Images'
            if cropped_dir.exists() and cropped_dir.is_dir():
                shutil.rmtree(cropped_dir)
                self.success_alert(f"Deleted old cropped images at {cropped_dir}")

            group_paths = self.read_folder(path, self.data['images'], self.data['annotation'])

            num_processes = min(12, len(group_paths))  # don't exceed total tasks
            chunk_list = self.chunk(group_paths, num_processes)

            processes = [
                mp.Process(target=self.crop_img, args=(x, path, chunk_list[x]))
                for x in range(num_processes)
            ]
            for p in processes:
                p.start()
            for p in processes:
                p.join()     