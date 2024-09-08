import os
import subprocess
import numpy as np
import json


def get_sorted_unique_file_basenames(directory_path):
    """
    Returns a sorted list of unique basenames (without extensions) for all files in the given directory.

    Parameters:
        directory_path (str): The path to the directory from which to list files.

    Returns:
        list: A sorted list containing the unique basenames of files in the directory.
    """
    return sorted({os.path.splitext(f)[0] for f in os.listdir(directory_path)})


def get_annotation_ranges(comprehensive_category_seq):
    """
    根据 comprehensive_category_seq 返回每个标注值的范围索引列表。

    Args:
        comprehensive_category_seq (list): 包含标注值的序列。

    Returns:
        dict: 以标注值为键，范围索引 (start_idx, end_idx) 的列表为值的字典。
    """
    if not comprehensive_category_seq:
        return {}

    annotation_ranges = {}
    start_idx = 0

    for i in range(1, len(comprehensive_category_seq)):
        # 当元素发生变化时，或到了序列的最后一个元素时
        if comprehensive_category_seq[i] != comprehensive_category_seq[start_idx]:
            # 获取当前元素的值
            current_value = comprehensive_category_seq[start_idx]

            # 保存当前元素的范围 (start_idx, i - 1)
            if current_value not in annotation_ranges:
                annotation_ranges[current_value] = []
            annotation_ranges[current_value].append((start_idx, i - 1))

            # 更新 start_idx 为当前元素的位置
            start_idx = i

    # 处理最后一段
    current_value = comprehensive_category_seq[start_idx]
    if current_value not in annotation_ranges:
        annotation_ranges[current_value] = []
    annotation_ranges[current_value].append((start_idx, len(comprehensive_category_seq) - 1))

    return annotation_ranges



def find_subsequences(lst, value=1):
    output = []
    start = None
    for i, x in enumerate(lst):
        if x == value:
            if start is None:
                start = i
        elif start is not None:
            output.append((start, i - 1))
            start = None
    if start is not None:
        output.append((start, len(lst) - 1))
    return [item for item in output if item[0] != item[1]]


import os
import json


def read_or_create_file(file_path, file_name):
    full_path = os.path.join(file_path, file_name)

    # 如果文件存在，尝试读取
    if os.path.isfile(full_path):
        try:
            with open(full_path, "r") as file:
                content = file.read().strip()  # 去掉多余的空格和换行符
                if content:  # 检查文件是否为空
                    return json.loads(content)  # 尝试解析 JSON
                else:
                    return {}  # 如果文件是空的，返回空字典
        except json.JSONDecodeError:
            print(f"Warning: {file_name} 不是有效的 JSON 文件。")
            return {}  # 如果文件内容无效，返回空字典

    # 如果文件不存在，创建一个新的空文件
    else:
        with open(full_path, "w") as file:
            json.dump({}, file)
        return {}

def get_parent_directory(levels_up=1):
    dir_path = os.path.abspath(os.path.dirname(__file__))

    for _ in range(levels_up):
        dir_path = os.path.abspath(os.path.dirname(dir_path))

    return dir_path

def write_dict_to_file(dictionary, file_path):
    with open(file_path, "w") as file:
        json.dump(dictionary, file)

def differentiate_voltage(voltage: list) -> list:
    voltage_array = np.array(voltage)
    derivative = np.diff(voltage_array)
    derivative = (np.roll(derivative, -1) + derivative) / 2.0
    derivative = np.append(derivative, derivative[-1])
    return derivative.tolist()

def check_and_terminate_process(process_name):
    try:
        process_output = subprocess.check_output('tasklist', shell=True).decode('utf-8', errors='ignore')
        if process_name in process_output:
            command = f'taskkill /f /im {process_name}'
            os.system(command)
            print(f'{process_name} has been terminated.')
        else:
            pass
    except Exception as e:
        print(f"Error: {e}")