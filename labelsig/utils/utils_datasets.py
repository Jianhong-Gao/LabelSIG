from typing import List
import numpy as np
import os
import os.path as osp



class CustomError(Exception):
    pass

def find_id_of_U0_I0(analog_channel_ids):
    nickname_U0=['UZ','Uz','U0']
    nickname_I0=['IZ','Iz','I0']
    id_U0,id_I0=None,None
    for i,channel_name in enumerate(analog_channel_ids):
            for name_U0 in nickname_U0:
                if name_U0 in channel_name:
                    id_U0 = i
            for name_I0 in nickname_I0:
                if name_I0 in channel_name:
                    id_I0 = i
    if id_U0 and id_I0:
        return id_U0,id_I0
    else:
        raise CustomError('未找到零序电压或零序电流通道')

def differentiate_voltage(voltage: list) -> list:
    voltage_array = np.array(voltage)
    derivative = np.diff(voltage_array)
    # 使用中点法
    derivative = (np.roll(derivative, -1) + derivative) / 2.0
    derivative = np.append(derivative, derivative[-1])
    # 将结果转换为list并返回
    return derivative.tolist()

def list_unique_base_files(directory_path: str) -> List[str]:
    try:
        files = [item for item in os.listdir(directory_path) if os.path.isfile(osp.join(directory_path, item))]
        return list({osp.splitext(file)[0] for file in files})
    except Exception as e:
        print(f"Error: {e}")
        return []


def process_analog_data(diff_U0, I0, index_difference, length_one_cycle):
    channel_voltage = []
    channel_current = []
    index_difference = index_difference - 1
    for i in range(5):
        index_start = index_difference + (i - 1) * length_one_cycle
        index_end = index_difference + (i) * length_one_cycle
        node_temp = diff_U0[index_start:index_end]
        channel_voltage.extend(node_temp)
        node_temp = I0[index_start:index_end]
        channel_current.extend(node_temp)
    return channel_voltage,channel_current


