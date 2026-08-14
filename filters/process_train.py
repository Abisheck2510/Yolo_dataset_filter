# -*- coding: utf-8 -*-

import pathlib
from xml.dom import minidom
import os
import glob
from filters.base import BaseModel
from filters.general import read_json, write_txt, write_yaml
import numpy as np
import random
from pathlib import Path
import shutil


class FinalProcess(BaseModel):

    def __init__(self, json_data):
        super().__init__(json_data)
    
    def split_data(self, path_list):
        """split train and val data
        Args:
            path_list: list
        Return:
            train(list): train data as list
            val(list): val data as list
        """
        train, validate, test = np.split(path_list, [int(len(path_list)*0.8), int(len(path_list)*0.9)])
        train, validate, test = list(train), list(validate), list(test)
        train.extend(test)
        return train, validate
    
    def read_images(self):
        """Read image path from folder"""
        path_list = []
        for idx, (k, v) in enumerate(self.data['input'].items()):
            path, im_path, xm_path = self.get_paths(v['dir'])
            for im in im_path.glob('**/*.jpg'):
                path_list.append(str(im.absolute()))
        return path_list
    
    def write_date(self, path_list, dir_name):
        """write train and val as txt
        Args:
            path_list: path as list
            dir_name: directory name
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = Path(dir_path).parents[0] / dir_name
        dir_path.mkdir(parents=True, exist_ok= True)
        print(dir_path)
        random.shuffle(path_list)
        train, validate = self.split_data(path_list)
        train_path = str(dir_path / 'train.txt')
        val_path = str(dir_path / 'val.txt')
        write_txt(train_path, train)
        write_txt(val_path, validate)
        yaml_data = {}
        yaml_data['train'] = train_path
        yaml_data['val'] = val_path
        yaml_data['nc'] = len(self.class_names.keys())
        yaml_data['names'] = list(self.class_names.keys())
        write_yaml(str(dir_path / 'custom.yaml'), yaml_data)

    def create_txt(self):
        path_list = self.read_images()
        self.write_date(path_list, 'final')
   
        
class RandomTrain(FinalProcess):

    def __init__(self, json_data):
        super().__init__(json_data)

    def create_txt(self):
        random_list = []
        for idx, (k, v) in enumerate(self.data['input'].items()):
            path_list = []
            path, im_path, xm_path = self.get_paths(v['dir'])
            for im in im_path.glob('**/*.jpg'):
                path_list.append(str(im.absolute()))
            value = int((v['sample'] / 100) * len(path_list))
            select_data = random.choices(path_list, k = value)
            random_list.extend(select_data)
        self.write_date(random_list, 'random_select')
       

class ConvertYolo(BaseModel):

    def __init__(self, json_data):
        super().__init__(json_data)
        self.lut, val = {}, 0
        for k in json_data['class_names'].keys():
            self.lut[k] = val
            val += 1
   
    @staticmethod
    def convert_coordinates(size, box):
        dw = 1.0/size[0]
        dh = 1.0/size[1]
        x = (box[0]+box[1])/2.0
        y = (box[2]+box[3])/2.0
        w = box[1]-box[0]
        h = box[3]-box[2]
        x = x*dw
        w = w*dw
        y = y*dh
        h = h*dh
        return (x,y,w,h)

    def convert_xml2yolo(self):
        for k, v in self.data['input'].items():
            path, im_path, xm_path = self.get_paths(v['dir'])
            label_path = path / 'yolo_labels'
            label_path.mkdir(parents=True, exist_ok= True)
            for fname in xm_path.glob('**/*.xml'):
                fname = str(fname)
                try:
                    xmldoc = minidom.parse(str(fname))
                    fname_out = (fname[:-4]+'.txt')
                    fout = os.path.basename(fname_out)
                    dest_out = label_path / fout
                    print(dest_out)
                    with open(str(dest_out), "w") as f:

                        itemlist = xmldoc.getElementsByTagName('object')
                        size = xmldoc.getElementsByTagName('size')[0]
                        width = int((size.getElementsByTagName('width')[0]).firstChild.data)
                        height = int((size.getElementsByTagName('height')[0]).firstChild.data)

                        for item in itemlist:
                            # get class label
                            classid =  (item.getElementsByTagName('name')[0]).firstChild.data
                            if classid in self.lut:
                                label_str = str(self.lut[classid])
                            else:
                                label_str = "-1"
                                print ("warning: label '%s' not in look-up table" % classid)

                            # get bbox coordinates
                            xmin = ((item.getElementsByTagName('bndbox')[0]).getElementsByTagName('xmin')[0]).firstChild.data
                            ymin = ((item.getElementsByTagName('bndbox')[0]).getElementsByTagName('ymin')[0]).firstChild.data
                            xmax = ((item.getElementsByTagName('bndbox')[0]).getElementsByTagName('xmax')[0]).firstChild.data
                            ymax = ((item.getElementsByTagName('bndbox')[0]).getElementsByTagName('ymax')[0]).firstChild.data
                            b = (float(xmin), float(xmax), float(ymin), float(ymax))
                            bb = self.convert_coordinates((width,height), b)
                            #print(bb)

                            f.write(label_str + " " + " ".join([("%.6f" % a) for a in bb]) + '\n')
                except Exception as e:
                    print(e)
               

            print ("wrote %s" % fname_out)


