import xml.etree.ElementTree as ET
from filters.base import BaseModel
import os
from glob import glob
from pathlib import Path
import numpy as np
import multiprocessing as mp
import cv2 
import xlsxwriter
import pandas as pd
import shutil 
from filters.general import read_txt
from termcolor import colored
import shutil
from collections import defaultdict, Counter
from multiprocessing import Pool, cpu_count
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter


class LabelFile(BaseModel):

    def __init__(self, json_data):
        super().__init__(json_data)

    
    
    def replace_label_name(self, replace, path):
        for p in path:
            p = Path(p)
            dest = p.parents[1] / replace 
            dest.mkdir(parents = True, exist_ok = True)
            dest_img = dest / p.name
            xm_name, id = p.stem.split('-')
            xmfile = p.parents[2] / self.annotation / f'{xm_name}.xml'
            xmlTree = ET.parse(xmfile)
            rootElement = xmlTree.getroot()
            for element in rootElement.findall("object"):
                if element.find('id').text == id:
                    if p.exists():
                        element.find('name').text = f'{replace}'
                        self.move_data(str(p), str(dest_img))
                    else:
                        print('path not found, check file already moved or not')
            xmlTree.write(xmfile)
    
    def delete_label_object(self, path):
        for p in path:
            p = Path(p)
            xm_name, id = p.stem.split('-')
            xmfile = p.parents[2] / self.annotation / f'{xm_name}.xml'
            xmlTree = ET.parse(xmfile)
            rootElement = xmlTree.getroot()
            for element in rootElement.findall("object"):
                if element.find('id').text == id:
                    if p.exists():
                        rootElement.remove(element)
                        os.remove(p)
                        print("file deleted")
                    else:
                        print("path not found or alread deleted")                
            xmlTree.write(xmfile)

    def move_folder_name(self, move_name, path):
        for p in path:
            p = Path(p)
            dest = p.parents[1] / move_name 
            dest.mkdir(parents = True, exist_ok = True)
            dest_img = dest / p.name
            if p.exists():
                self.move_data(str(p), str(dest_img))
            else:
                print('path not found')

    def run(self):
        path_lst = []
        label_path = self.data['label_txt']
        lines = read_txt(label_path)
        for line in lines:
            
            line1 = line.split('=')
            if line1[0] == 'replace':
                replace = line1[1]
                self.replace_label_name(replace, path_lst)
                path_lst, replace = [], ''
            
            elif line1[0] == 'del':
                self.delete_label_object(path_lst)
                path_lst = []

            elif line1[0] == 'move':
                move_name = line1[1]
                self.move_folder_name(move_name, path_lst)
                path_lst = []
            else:
                path_lst.append(line)


class LabelId:
    def __init__(self, json_data):
        self.data = json_data
        self.id = 1

    def reset_id(self):
        """Remove old id and add new id for all XML files"""
        
        for k, v in self.data['input'].items():
            path = Path(v['dir']) / self.data['annotation']
            assert path.exists(), f'{path} path not found'

            print(f'\n 📁 Processing folder: {path}')

            for file in path.glob('**/*.xml'):
                try:
                    xmlTree = ET.parse(file)
                    rootElement = xmlTree.getroot()
                    modified = False

                    for member in rootElement.findall('object'):
                        # Remove old <id> if exists
                        old_id = member.find('id')
                        if old_id is not None:
                            member.remove(old_id)

                        # Add new <id>
                        new_id = ET.SubElement(member, 'id')
                        new_id.text = f'S{self.id}'
                        print(f'Added id: S{self.id} in {file.name}')
                        self.id += 1
                        modified = True

                    if modified:
                        xmlTree.write(file)
                except Exception as e:
                    print(f'{file} could not be processed: {e}')

    def remove_id(self):
        """Remove all <id> tags from each <object> in all XML files"""
        for k, v in self.data['input'].items():
            path = Path(v['dir']) / self.data['annotation']
            assert path.exists(), f'{path} path not found'

            print(f'\n 📁 Processing folder: {path}')

            for file in path.glob('**/*.xml'):
                try:
                    xmlTree = ET.parse(file)
                    rootElement = xmlTree.getroot()
                    modified = False

                    for member in rootElement.findall('object'):
                        id_tag = member.find('id')
                        if id_tag is not None:
                            print(f'Removed id: {id_tag.text} from {file.name}')
                            member.remove(id_tag)
                            modified = True

                    if modified:
                        xmlTree.write(file)
                except Exception as e:
                    print(f'{file} could not be processed: {e}')


    def rename(self):
        "Rename class name using json"
        class_name = self.data['class_names']
        for k, v in self.data['input'].items():
            path = Path(v['dir']) / self.data['annotation']
            assert path.exists(), f'{path} path not found'
            for file in path.glob('**/*.xml'):
                if os.path.exists(file):
                    print(file)
                    xmlTree = ET.parse(file)
                    rootElement = xmlTree.getroot()
                    for member in rootElement.findall('object'):
                        name = member.find('name').text
                        for nm in class_name.keys():
                            if name in class_name[nm]:
                                member.find('name').text = nm
                    xmlTree.write(file)
                else:
                    print(file ,'path is not found')
 


# class DatasetReport:
#     def __init__(self, config_data):
#         self.data = config_data

#     def generate_report(self, save_path="dataset_report.xlsx"):
#         records = []
#         for name, info in self.data["input"].items():
#             folder = Path(info["dir"])
#             image_dir = folder / self.data["images"]
#             xml_dir = folder / self.data["annotation"]

#             image_count = len([f for f in image_dir.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
#             annotation_count = len([f for f in xml_dir.glob("*.xml")])

#             records.append({
#                 "Folder_path": name,
#                 "image_count": image_count,
#                 "annotation_count": annotation_count
#             })

#         df = pd.DataFrame(records)
#         df.to_excel(save_path, index=False)
#         print(f"✅ Report saved to: {save_path}")
#         return df



# def process_folder(args):
#     name, info, images_key, annotation_key = args
#     folder_name = Path(info['dir']).name  # Actual folder name from path
    
#     image_dir = Path(info['dir']) / images_key
#     xml_dir = Path(info['dir']) / annotation_key

#     image_count = len([f for f in image_dir.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
#     annotation_files = list(xml_dir.glob("*.xml"))
#     class_counter = Counter()

#     for xml_file in annotation_files:
#         try:
#             tree = ET.parse(xml_file)
#             root = tree.getroot()
#             for obj in root.findall("object"):
#                 cls = obj.find("name").text.strip()
#                 class_counter[cls] += 1
#         except Exception as e:
#             print(f"❌ Error reading {xml_file}: {e}")

#     return {
#         "folder_name": folder_name,
#         "image_count": image_count,
#         "annotation_count": len(annotation_files),
#         "class_counter": dict(class_counter)
#     }


# class DatasetReport:
#     def __init__(self, config_data):
#         self.data = config_data

#     def generate_report(self, save_path="dataset_report.xlsx"):
#         pool_args = [
#             (name, info, self.data["images"], self.data["annotation"])
#             for name, info in self.data["input"].items()
#         ]

#         with Pool(processes=cpu_count()) as pool:
#             results = pool.map(process_folder, pool_args)

#         summary_records = []
#         class_dist_rows = []
#         total_class_counter = Counter()

#         for res in results:
#             folder_path = res["folder_name"]
#             folder_name = Path(folder_path).name


#             summary_records.append({
#                 "Folder_path": res["folder_name"],
#                 "image_count": res["image_count"],
#                 "annotation_count": res["annotation_count"]
#             })
#             total_class_counter.update(res["class_counter"])
#             class_row = {"folder": folder_name}
#             class_row.update(res["class_counter"])
#             class_dist_rows.append(class_row)

#         # Add total (dataset row)
#         total_row = {"folder": "Total Class"}
#         total_row.update(total_class_counter)
#         class_dist_rows.append(total_row)

#         df_summary = pd.DataFrame(summary_records)
#         df_class_dist = pd.DataFrame(class_dist_rows).fillna(0).astype({'folder': str})

#         # Ensure consistent column order
#         cols = ['folder'] + sorted(c for c in df_class_dist.columns if c != 'folder')
#         df_class_dist = df_class_dist[cols]

#         # Create workbook
#         wb = Workbook()
#         wb.remove(wb.active)

#         # Write both sheets
#         self._write_and_format_sheet(wb.create_sheet("Summary"), df_summary)
#         self._write_and_format_sheet(wb.create_sheet("Class_Distribution"), df_class_dist)

#         wb.save(save_path)
#         print(f"✅ Excel report saved at: {save_path}")
#         return df_summary, df_class_dist

#     def _write_and_format_sheet(self, ws, df):
#         # Formatting
#         header_font = Font(bold=True, color="FFFFFF")
#         header_fill = PatternFill("solid", fgColor="4F81BD")
#         thin_border = Border(
#             left=Side(style="thin"), right=Side(style="thin"),
#             top=Side(style="thin"), bottom=Side(style="thin")
#         )
#         align_center = Alignment(horizontal="center", vertical="center")

#         # Header row
#         for col_idx, col_name in enumerate(df.columns, start=1):
#             cell = ws.cell(row=1, column=col_idx, value=col_name)
#             cell.font = header_font
#             cell.fill = header_fill
#             cell.border = thin_border
#             cell.alignment = align_center
#             ws.column_dimensions[cell.column_letter].width = 20

#         # Data rows
#         for r_idx, row in enumerate(df.itertuples(index=False), start=2):
#             for c_idx, value in enumerate(row, start=1):
#                 cell = ws.cell(row=r_idx, column=c_idx, value=value)
#                 cell.border = thin_border
#                 cell.alignment = Alignment(horizontal="center", vertical="center")


def get_dir_size(path):
    total_size = 0
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def process_folder(args):
    name, info, images_key, annotation_key = args
    folder_name = Path(info['dir']).name

    image_dir = Path(info['dir']) / images_key
    xml_dir = Path(info['dir']) / annotation_key
    label_dir = Path(info['dir']) / 'labels'
    crop_dir = Path(info['dir']) / 'Cropped_Images'

    image_count = len([f for f in image_dir.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
    annotation_files = list(xml_dir.glob("*.xml"))
    class_counter = Counter()

    for xml_file in annotation_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for obj in root.findall("object"):
                cls = obj.find("name").text.strip()
                class_counter[cls] += 1
        except Exception as e:
            print(f"❌ Error reading {xml_file}: {e}")

    # Calculate storage sizes
    image_size_bytes = get_dir_size(image_dir)
    label_size_bytes = get_dir_size(label_dir)
    overall_size_bytes = get_dir_size(Path(info['dir']))

    # Count cropped images
    cropped_class_counter = Counter()
    cropped_count = 0
    if crop_dir.exists():
        for label_subdir in crop_dir.iterdir():
            if label_subdir.is_dir():
                label = label_subdir.name
                count = len([f for f in label_subdir.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
                cropped_class_counter[label] = count
                cropped_count += count

    return {
        "folder_name": folder_name,
        "image_count": image_count,
        "annotation_count": len(annotation_files),
        "class_counter": dict(class_counter),
        "image_size_bytes": image_size_bytes,
        "label_size_bytes": label_size_bytes,
        "overall_size_bytes": overall_size_bytes,
        "cropped_class_counter": dict(cropped_class_counter),
        "cropped_count": cropped_count
    }


class DatasetReport:
    def __init__(self, config_data):
        self.data = config_data

    def generate_report(self, save_path="dataset_report.xlsx"):
        pool_args = [
            (name, info, self.data["images"], self.data["annotation"])
            for name, info in self.data["input"].items()
        ]

        with Pool(processes=cpu_count()) as pool:
            results = pool.map(process_folder, pool_args)

        summary_records = []
        class_dist_rows = []
        storage_records = []
        cropped_rows = []
        total_class_counter = Counter()

        for res in results:
            folder_name = Path(res["folder_name"]).name
            
            summary_records.append({
                "Folder_path": res["folder_name"],
                "image_count": res["image_count"],
                "annotation_count": res["annotation_count"]
            })
		
            total_class_counter.update(res["class_counter"])
            class_row = {"folder": folder_name}
            class_row.update(res["class_counter"])
            class_dist_rows.append(class_row)

            # Storage details
            image_gb = round(res["image_size_bytes"] / (1024 * 1024 * 1024), 3)
            label_gb = round(res["label_size_bytes"] / (1024 * 1024 * 1024), 3)
            overall_gb = round(res["overall_size_bytes"] / (1024 * 1024 * 1024), 3)
            storage_records.append({
                "Folder_path": res["folder_name"],
                "Image_Storage (GB)": image_gb,
                "Label_Storage (GB)": label_gb,
                "Overall_Storage (GB)": overall_gb
            })

            # Cropped images details
            cropped_row = {"folder": folder_name}
            cropped_row.update(res["cropped_class_counter"])
            cropped_rows.append(cropped_row)

        # ---- Prepare Class Distribution ----
        df_class_dist = pd.DataFrame(class_dist_rows).fillna(0).astype({'folder': str})
        
        # Use class order from config if available
        if "class_names" in self.data:
            class_cols = [cls for cls in self.data["class_names"] if cls in df_class_dist.columns]
        else:
            class_cols = sorted([c for c in df_class_dist.columns if c != 'folder'])

        # Add placeholder column for total_annotations (formula will be inserted in Excel)
        df_class_dist['total_annotations'] = ""

        # Add Total Class row
        total_row = {"folder": "Total Class", "total_annotations": ""}
        total_row.update({cls: "" for cls in class_cols})

        # Add Accuracy (%) row
        accuracy_row = {"folder": "Total Class (%)", "total_annotations": ""}
        accuracy_row.update({cls: "" for cls in class_cols})

        df_class_dist = pd.concat([
            df_class_dist,
            pd.DataFrame([total_row]),
            pd.DataFrame([accuracy_row])
        ], ignore_index=True)

        # Reorder columns
        ordered_cols = ['folder'] + class_cols + ['total_annotations']
        df_class_dist = df_class_dist[ordered_cols]

        # ---- Summary Sheet ----
        df_summary = pd.DataFrame(summary_records)

        # Add total row to summary sheet
        total_images = df_summary["image_count"].sum()
        total_annotations = df_summary["annotation_count"].sum()
        df_summary = pd.concat([
            df_summary,
            pd.DataFrame([{
                "Folder_path": "Total",
                "image_count": total_images,
                "annotation_count": total_annotations
            }])
        ], ignore_index=True)

        # ---- Storage Details Sheet ----
        df_storage = pd.DataFrame(storage_records)

        # Add total row to storage sheet
        total_image_storage = df_storage["Image_Storage (GB)"].sum()
        total_label_storage = df_storage["Label_Storage (GB)"].sum()
        total_overall_storage = df_storage["Overall_Storage (GB)"].sum()
        df_storage = pd.concat([
            df_storage,
            pd.DataFrame([{
                "Folder_path": "Total",
                "Image_Storage (GB)": round(total_image_storage, 3),
                "Label_Storage (GB)": round(total_label_storage, 3),
                "Overall_Storage (GB)": round(total_overall_storage, 3)
            }])
        ], ignore_index=True)

        # ---- Cropped Images Count Sheet ----
        df_cropped = pd.DataFrame(cropped_rows).fillna(0).astype({'folder': str})
        
        # Determine class columns for cropped
        if "class_names" in self.data:
            cropped_class_cols = [cls for cls in self.data["class_names"] if cls in df_cropped.columns]
            extra_cropped_cols = sorted([c for c in df_cropped.columns if c != 'folder' and c not in cropped_class_cols])
            cropped_class_cols = cropped_class_cols + extra_cropped_cols
        else:
            cropped_class_cols = sorted([c for c in df_cropped.columns if c != 'folder'])

        # Ensure all config classes are represented in df_cropped
        if "class_names" in self.data:
            for cls in self.data["class_names"]:
                if cls not in df_cropped.columns:
                    df_cropped[cls] = 0
                    if cls not in cropped_class_cols:
                        cropped_class_cols.append(cls)

        # Add placeholder column for total_cropped
        df_cropped['total_cropped'] = ""

        # Add Total Class row for cropped images
        total_cropped_row = {"folder": "Total Class", "total_cropped": ""}
        total_cropped_row.update({cls: "" for cls in cropped_class_cols})

        df_cropped = pd.concat([
            df_cropped,
            pd.DataFrame([total_cropped_row])
        ], ignore_index=True)

        # Reorder columns
        ordered_cropped_cols = ['folder'] + cropped_class_cols + ['total_cropped']
        df_cropped = df_cropped[ordered_cropped_cols]

        # ---- Save Excel Workbook ----
        wb = Workbook()
        wb.remove(wb.active)
        self._write_and_format_sheet(wb.create_sheet("Summary"), df_summary)
        self._write_and_format_sheet(wb.create_sheet("Class_Distribution"), df_class_dist)
        self._write_and_format_sheet(wb.create_sheet("Storage_Details"), df_storage)
        self._write_and_format_sheet(wb.create_sheet("Cropped_Images_Count"), df_cropped)
        wb.save(save_path)

        print(f"✅ Excel report saved at: {save_path}")
        return df_summary, df_class_dist, df_storage, df_cropped

    header_font = Font(bold=True, color="FFFFFF", size=12)
    bold_font = Font(bold=True, size=12)
    normal_font = Font(size=12)

    def _write_and_format_sheet(self, ws, df):
        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="4F81BD")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin")
        )
        align_center = Alignment(horizontal="center", vertical="center")

        # Write header
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = align_center
            if col_name in ["folder", "Folder_path", "total_annotations", "total_cropped", "Image_Storage (GB)", "Label_Storage (GB)", "Overall_Storage (GB)"]:
                ws.column_dimensions[cell.column_letter].width = 30
            else:
                ws.column_dimensions[cell.column_letter].width = 20

        ws.row_dimensions[1].height = 30

        # Detect if it's Class_Distribution or Cropped_Images_Count
        is_class_distribution = "total_annotations" in df.columns and "folder" in df.columns
        is_cropped_distribution = "total_cropped" in df.columns and "folder" in df.columns

        if is_class_distribution or is_cropped_distribution:
            total_key = "total_annotations" if is_class_distribution else "total_cropped"
            class_cols = [c for c in df.columns if c not in ['folder', total_key]]
            total_col_idx = df.columns.get_loc(total_key) + 1
            total_col_letter = get_column_letter(total_col_idx)

        for r_idx, row in enumerate(df.itertuples(index=False), start=2):

            is_total_row = False
            is_accuracy_row = False
            is_total_summary_row = False

            if "folder" in df.columns:
                folder_val = row[df.columns.get_loc("folder")]
                is_total_row = (folder_val == "Total Class")
                is_accuracy_row = (folder_val == "Total Class (%)")

            if "Folder_path" in df.columns:
                folder_path_val = row[df.columns.get_loc("Folder_path")]
                is_total_summary_row = (folder_path_val == "Total")

            if is_total_summary_row or "Folder_path" in df.columns:
                ws.row_dimensions[r_idx].height = 30
            elif is_total_row or is_accuracy_row:
                ws.row_dimensions[r_idx].height = 30
            else:
                ws.row_dimensions[r_idx].height = 25

            for c_idx, col_name in enumerate(df.columns, start=1):
                col_letter = get_column_letter(c_idx)
                cell = ws.cell(row=r_idx, column=c_idx)
                value = row[c_idx - 1]

                if is_class_distribution or is_cropped_distribution:
                    total_key = "total_annotations" if is_class_distribution else "total_cropped"
                    if is_total_row:
                        if col_name in class_cols:
                            cell.value = f"=SUM({col_letter}2:{col_letter}{r_idx - 1})"
                        elif col_name == total_key:
                            cell.value = f"=SUM({total_col_letter}2:{total_col_letter}{r_idx - 1})"
                        else:
                            cell.value = value or ""
                    elif is_accuracy_row:
                        total_row_idx = r_idx - 1
                        if col_name in class_cols:
                            cell.value = f"={col_letter}{total_row_idx}/${total_col_letter}${total_row_idx}"
                            cell.number_format = '0.00%'
                        elif col_name == total_key:
                            first_class_col = get_column_letter(df.columns.get_loc(class_cols[0]) + 1)
                            last_class_col = get_column_letter(df.columns.get_loc(class_cols[-1]) + 1)
                            cell.value = f"=SUM({first_class_col}{r_idx}:{last_class_col}{r_idx})"
                            cell.number_format = '0.00%'
                        else:
                            cell.value = ""
                    else:
                        if col_name == total_key:
                            first_data_col = get_column_letter(df.columns.get_loc(class_cols[0]) + 1)
                            last_data_col = get_column_letter(df.columns.get_loc(class_cols[-1]) + 1)
                            cell.value = f"=SUM({first_data_col}{r_idx}:{last_data_col}{r_idx})"
                        else:
                            cell.value = value
                else:
                    # For Summary sheet, Storage sheet or others
                    cell.value = value

                # --- BOLD FORMATTING RULES ---
                bold_font = Font(bold=True)
                if col_name in ["folder", "Folder_path", "total_annotations", "total_cropped"]:
                    cell.font = bold_font
                if is_total_row or is_accuracy_row or is_total_summary_row:
                    cell.font = bold_font

                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")
