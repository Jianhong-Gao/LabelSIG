import pickle
import os
from labelsig.utils.utils_comtrade import get_info_comtrade

def load_annotation(path_file_ann):
    with open(path_file_ann, 'rb') as f:
        return pickle.load(f)


def write_annotation(path_annotation_base,annotation):
    path_file_ann=path_annotation_base+'.ann'
    path_dir_ann = os.path.dirname(path_file_ann)
    if not os.path.exists(path_dir_ann):
        os.makedirs(path_dir_ann)
    with open(path_file_ann, 'wb') as f:
        pickle.dump(annotation, f)
        return True
    return False


def update_annotation_label(path_base_dict=None,annotation_dict=None):
    path_annotation_base=path_base_dict['path_annotation_base']
    annotation=get_annotation_info(path_base_dict)
    for key in annotation_dict:
        annotation[key]=annotation_dict[key]
    flag_save_annotation=write_annotation(path_annotation_base,annotation)
    return flag_save_annotation

def upgrade_annotation_info(path_base_dict, annotation):
    path_raw_base = path_base_dict['path_raw_base']
    info_comtrade = get_info_comtrade(path_file_base=path_raw_base)
    annotation['sampling_rate']=info_comtrade['sampling_rate']
    annotation['fault_trigger']=info_comtrade['trigger_moment']
    annotation['total_samples']=info_comtrade['total_samples']
    return annotation


def get_annotation_info(path_base_dict):
    path_annotation_base=path_base_dict['path_annotation_base']
    path_file_ann=path_annotation_base+'.ann'
    if not os.path.exists(path_file_ann):
        annotation=initialize_annotation()
        annotation=upgrade_annotation_info(path_base_dict,annotation)
        flag_save_annotation=write_annotation(path_annotation_base,annotation)
        return annotation
    else:
        annotation = load_annotation(path_file_ann)
        # 查看annotation是否有segmentation字段，如果没有则添加为空字典
        if 'location' not in annotation:
            annotation['location']={}
        if 'segmentation' not in annotation:
            annotation['segmentation']={}
        if 'total_samples' not in annotation:
            info_comtrade = get_info_comtrade(path_file_base=path_base_dict['path_raw_base'])
            annotation['total_samples'] = info_comtrade['total_samples']
        flag_save_annotation = write_annotation(path_annotation_base, annotation)
        return annotation


def initialize_annotation():
    annotation = {
        "sampling_rate": None,
        "total_samples": None,
        "fault_trigger": None,
        "detection_label": None,
        "type_label": None,
        "location_label": None,
        "description_info": None,
        "natural_language_description": "",
        "location":{},
        "segmentation": {},
    }
    return annotation
