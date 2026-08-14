from filters.label_check import LabelId, LabelFile, DatasetReport
from filters.dataset_check import DatasetValidator
from filters.general import read_json
from filters.process_train1 import ConvertYolo, FinalProcess
from filters.xml_to_yolo_split import XmlToYoloSplit
from filters.yolo_dataset_check import CorruptYoloFilter  
from filters.csv_to_yolo import CsvToYoloConverter
from filters.crop_images import CropImages
from filters.annotation_checker import AnnotationChecker
from filters.csv_to_xml import CsvToXmlConverter
from filters.crop_dataset_split import CropDatasetSplit

data = read_json()
print('(0) Modify names xml \n')
print('(1) Add Id \n')
print('(2) Remove Id \n')
print('(3) Annotation Checker \n')
print('(4) Crop Images \n')
print('(5) Dataset Checker \n')
print('(6) Report \n')
print('(7) Rename\n')
print('(8) Xml to Yolo format \n')
print('(9) Yolo_Dataset_Check \n')
print('(10) Csv to Yolo \n')
print('(11) Csv to Xml \n')
print('(12) Xml to Yolo Split (Train/Val) folders \n')
print('(13) Cropped Images Train/Val Split(Classification model format) \n')



val = int(input("Enter your choice: "))

if val == 0:
    lf = LabelFile(data)
    lf.run()

elif val == 1:
    l1 = LabelId(data)
    l1.reset_id()

elif val == 2:
    l1 = LabelId(data)
    l1.remove_id()

elif val == 3:
    checker = AnnotationChecker(data)
    checker.check_mismatches()
    checker.check_annotation_validity()

elif val == 4:
    l1 = CropImages(data)
    l1.start()

elif val == 5:
    l1 = DatasetValidator(data)
    l1.run_all_checks()

elif val == 6:
    l1 = DatasetReport(data)
    l1.generate_report()

elif val == 7:
    l1 = LabelId(data)
    l1.rename()

elif val == 8:
    cy = ConvertYolo(data)
    cy.convert_xml2yolo()
    f1 = FinalProcess(data)
    f1.create_txt()

elif val == 9:
    cf = CorruptYoloFilter(data)
    cf.run_filter()

elif val == 10:
    csy = CsvToYoloConverter(data)
    csy.run()

elif val == 11:
    csx = CsvToXmlConverter(data)
    csx.run()

elif val == 12:
    xys = XmlToYoloSplit(data)
    xys.run()
    
elif val == 13:
    cds = CropDatasetSplit(data)
    cds.run()


else:
    print('enter the correct choice')



