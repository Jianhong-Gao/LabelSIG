import os
import subprocess
import numpy as np
import json

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


def read_or_create_file(file_path, file_name):
    full_path = os.path.join(file_path, file_name)
    if os.path.isfile(full_path):
        with open(full_path, "r") as file:
            return json.load(file)
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