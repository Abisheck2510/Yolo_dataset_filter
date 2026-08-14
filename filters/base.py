from pathlib import Path
import shutil

class BaseModel:

    def __init__(self, json_data):
        self.data = json_data
        self.images = self.data['images']
        self.annotation = self.data['annotation']
        self.class_names = self.data['class_names']
    
    def read_folder(self, path, img_dir, xml_dir):
        path_list = []
        imfpath = path / img_dir
        for e in imfpath.rglob('*.jpg'):
            xmlfile = path / xml_dir / f'{e.stem}.xml'
            if e.exists() and xmlfile.exists():
                path_list.append((str(e), str(xmlfile)))
        return path_list
    
    def get_paths(self, path_dir): 
        path_dir = Path(path_dir)
        im = path_dir / self.images
        xm = path_dir / self.annotation
        return path_dir, im, xm

    def move_data(self, src, dest):
        try:
            shutil.move(src, dest)
            print("File moved successfully.")
    
        # If source and destination are same
        except shutil.SameFileError:
            print("Source and destination represents the same file.")
        
        # If there is any permission issue
        except PermissionError:
            print("Permission denied.")
        
        # For other errors
        except:
            print("Error occurred while moving file.")