from src.utils.utils_comtrade import read_comtrade, get_index_fault_moment
from typing import List
import numpy as np
import os
import os.path as osp
import torch
from torch.utils.data import Dataset
import matplotlib.pyplot as plt

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


class TimeSeriesDataset_One_to_Five(Dataset):
    def __init__(self, root):
        self.root = root
        self.raw_dir = osp.join(root, 'raw')
        self.processed_dir = osp.join(root, 'processed')
        if not osp.exists(self.processed_dir):
            os.makedirs(self.processed_dir)  # Create the directory if it doesn't exist
        self.processed_file_names = self._processed_file_names()
        # 如果还没有处理过的文件，那么处理数据
        if not self.processed_file_names:
            self.process()


    def _processed_file_names(self):
        list_base_file = list_unique_base_files(self.processed_dir)
        list_dat = []
        for base_file in list_base_file:
            if 'data' in base_file:
                list_dat.append(base_file + '.pt')
        return list_dat

    def process(self):
        idx = 0
        self.raw_paths = [osp.join(self.raw_dir,base_file) for base_file in list_unique_base_files(self.raw_dir)]
        self.labels = []
        for raw_path in self.raw_paths:
            comtrade_reader = read_comtrade(base_filepath=raw_path)
            index_difference = get_index_fault_moment(comtrade_reader) - 1
            analog_values = comtrade_reader.analog
            length_one_cycle = 100
            U0 = analog_values[3]
            diff_U0 = differentiate_voltage(voltage=U0)
            for i in range(len([4, 5, 6, 7, 8])):
                I0 = analog_values[i + 4]
                label=self.get_label_for_data(raw_path, i)
                self.labels.extend([label])
                channel_voltage, channel_current = process_analog_data(diff_U0, I0, index_difference, length_one_cycle)
                ts_data = torch.stack([torch.tensor(channel_voltage), torch.tensor(channel_current)])
                data_with_label = (ts_data, label)
                torch.save(data_with_label, osp.join(self.processed_dir, f'data_{idx}.pt'))
                idx += 1

    def get_label_for_data(self,raw_path: str,id:int) -> int:
        FPOS = raw_path.split('_')[-1]
        id_feeder = int(FPOS[0])
        if id_feeder != id + 1:
            label = 0
        else:
            label = 1
        return label

    def __len__(self):
        return len(self.processed_file_names)

    def __getitem__(self, idx):
        ts_data, label = torch.load(osp.join(self.processed_dir, f'data_{idx}.pt'))
        return ts_data, label


class TimeSeriesDataset_Plain(Dataset):
    def __init__(self, root):
        self.root = root
        self.raw_dir = osp.join(root, 'raw')
        self.processed_dir = osp.join(root, 'processed')
        if not osp.exists(self.processed_dir):
            os.makedirs(self.processed_dir)  # Create the directory if it doesn't exist
        self.processed_file_names = self._processed_file_names()
        # 如果还没有处理过的文件，那么处理数据
        if not self.processed_file_names:
            self.process()


    def _processed_file_names(self):
        list_base_file = list_unique_base_files(self.processed_dir)
        list_dat = []
        for base_file in list_base_file:
            if 'data' in base_file:
                list_dat.append(base_file + '.pt')
        return list_dat

    def process(self):
        idx = 0
        self.raw_paths = [osp.join(self.raw_dir,base_file) for base_file in list_unique_base_files(self.raw_dir)]
        self.labels = []
        for raw_path in self.raw_paths:
            comtrade_reader = read_comtrade(base_filepath=raw_path)
            index_difference = get_index_fault_moment(comtrade_reader) - 1
            analog_values = comtrade_reader.analog
            length_one_cycle = 100
            try:
                id_U0,id_I0=find_id_of_U0_I0(comtrade_reader.analog_channel_ids)
            except CustomError as e:
                print(e)
            U0 = analog_values[id_U0]
            I0 = analog_values[id_I0]
            diff_U0 = differentiate_voltage(voltage=U0)
            label=self.get_label_for_data(raw_path)
            self.labels.extend([label])
            channel_voltage, channel_current = process_analog_data(diff_U0, I0, index_difference, length_one_cycle)
            ts_data = torch.stack([torch.tensor(channel_voltage), torch.tensor(channel_current)])
            data_with_label = (ts_data, label)
            torch.save(data_with_label, osp.join(self.processed_dir, f'data_{idx}.pt'))
            idx += 1

    def get_label_for_data(self,raw_path: str) -> int:
        if 'Non-Fault' in raw_path:
            label = 0
        else:
            label = 1
        return label

    def __len__(self):
        return len(self.processed_file_names)

    def __getitem__(self, idx):
        ts_data, label = torch.load(osp.join(self.processed_dir, f'data_{idx}.pt'))
        return ts_data, label

if __name__ == '__main__':
    dataset = TimeSeriesDataset_One_to_Five(root='../../data/Simulation4TimeSeries')
    channel_data, label = dataset[3]
    print(label)
    voltage=channel_data[0]
    current=channel_data[1]
    fig, ax1 = plt.subplots()
    ax1.plot(voltage, color='r')
    ax1.set_ylabel('Voltage(V)')
    ax2 = ax1.twinx()
    ax2.plot(current, color='b')
    ax2.set_ylabel('Current(A)')
    plt.subplots_adjust(left=0.1,right=0.85,top=0.9,bottom=0.1)
    plt.show()