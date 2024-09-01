import pickle
import os
from labelsig.utils.utils_comtrade import get_info_comtrade

def load_annotation(path_file_ann):

    if not os.path.exists(path_file_ann+'.ann'):
        annotation=initialize_annotation()
        write_annotation(path_file_ann, annotation)
        return annotation
    else:
        with open(path_file_ann+".ann", 'rb') as f:
            return pickle.load(f)


def write_annotation(path_file_ann,annotation):
    if not os.path.exists(os.path.dirname(path_file_ann+'.ann')):
        os.makedirs(os.path.dirname(path_file_ann+'.ann'))
    with open(path_file_ann+'.ann', 'wb') as f:
        pickle.dump(annotation, f)
        return True
    return False





def get_annotation_from_info(selected_comtrade_info):
    path_ann=selected_comtrade_info["path_ann"]
    selected_comtrade_info=selected_comtrade_info["selected_comtrade_info"]
    annotation_path_without_extension=os.path.join(path_ann,selected_comtrade_info)
    path_file_ann=annotation_path_without_extension+'.ann'
    if not os.path.exists(path_file_ann):
        annotation=initialize_annotation()
        annotation['sampling_rate']=selected_comtrade_info['sampling_rate']
        annotation['trigger_index']=selected_comtrade_info['trigger_index']
        annotation['total_samples']=selected_comtrade_info['total_samples']
        annotation['start_timestamp']=selected_comtrade_info['start_timestamp']
        annotation['trigger_timestamp']=selected_comtrade_info['trigger_timestamp']

        flag_save_annotation=write_annotation(annotation_path_without_extension,annotation)
        return annotation
    else:
        annotation = load_annotation(path_file_ann)
        # 查看annotation是否有segmentation字段，如果没有则添加为空字典
        flag_save_annotation = write_annotation(annotation_path_without_extension, annotation)
        return annotation

def get_annotation_info(selected_comtrade_info,annotation=None):
    annotation['sampling_rate']=selected_comtrade_info['sampling_rate']
    annotation['trigger_index']=selected_comtrade_info['trigger_index']
    annotation['total_samples']=selected_comtrade_info['total_samples']
    annotation['start_timestamp']=selected_comtrade_info['start_timestamp']
    annotation['trigger_timestamp']=selected_comtrade_info['trigger_timestamp']
    return annotation



def initialize_annotation():
    annotation = {
        "sampling_rate": None,
        "total_samples": None,
        "start_timestamp":None,
        "trigger_timestamp":None,
        "trigger_index": None,
        "fault_detection":{},
        "fault_identification":{},
        "fault_localization":{},
    }
    return annotation
