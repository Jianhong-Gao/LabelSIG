
import matplotlib.pyplot as plt
from src.utils.utils_general import differentiate_voltage
from src.utils.utils_comtrade import get_channels_comtrade, get_info_comtrade, process_analog_data, find_id_of_U0_I0
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import shutil
import matplotlib
from src.utils.utils_general import get_parent_directory
matplotlib.use('Agg')

matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 用黑体显示中文
matplotlib.rcParams['axes.unicode_minus'] = False  # 正常显示负号
plt.rcParams.update({'font.size': 12})
from matplotlib.ticker import MaxNLocator



def create_folders(tree, root):
    for key, value in tree.items():
        current_path = os.path.join(root, key)
        os.makedirs(current_path, exist_ok=True)
        if isinstance(value, dict):
            create_folders(value, current_path)


def plot_channel_data(voltage, current, index, sampling_rate, trigger_moment=None, filename=None):
    fig, ax1 = plt.subplots(figsize=(6, 3))
    ax1.set_title(f"file name: {filename}")
    time_values_ms = [(i / sampling_rate) * 1 for i in index]
    ax1.plot(time_values_ms, voltage, color='r', label='Zero-sequence Voltage Derivative')
    ax1.set_ylabel('Voltage Derivative(kV/s)')
    ax1.set_xlim(time_values_ms[0], time_values_ms[-1])
    ax1.set_xlabel('Time (s)')
    ax1.yaxis.set_label_coords(-0.055, 0.5)
    ax2 = ax1.twinx()
    ax2.plot(time_values_ms, current, color='b', label='Zero-sequence Current')
    ax2.set_ylabel('Current(A)')
    ax2.set_xlim(time_values_ms[0], time_values_ms[-1])
    if trigger_moment is not None and trigger_moment in index:
        start_time_ms = (trigger_moment / sampling_rate) * 1
        ax1.axvline(x=start_time_ms, color='g', linestyle='--', label='Trigger Moment')
        ax2.axvline(x=start_time_ms, color='g', linestyle='--')
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc=0)
    plt.subplots_adjust(left=0.08, right=0.9, top=0.9, bottom=0.15)
    return fig, (ax1, ax2)


def single_visualize(filename, path_output, path_source, annotation):
    statistics_tree = {
        'NE': {'total': 0},
        'PE': {
            'total': 0,
            'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
            'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
        },
        'TE': {
            'total': 0,
            'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
            'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
        },
        'UNK': {'total': 0}
    }
    create_folders(tree=statistics_tree, root=path_output)
    path_file_base = os.path.join(path_source, filename)
    channels_info = get_channels_comtrade(path_file_base=path_file_base)
    info_comtrade = get_info_comtrade(path_file_base=path_file_base)
    sampling_rate = info_comtrade['sampling_rate']
    trigger_moment = info_comtrade['trigger_moment']
    analog_channel_ids = channels_info['analog_channel_ids']
    analog_values = channels_info['analog_channel_values']
    length_one_cycle = int(sampling_rate * 0.02)
    id_U0_I0 = find_id_of_U0_I0(analog_channel_ids)
    if id_U0_I0:
        id_U0, id_I0 = id_U0_I0
        U0 = analog_values[id_U0]
        I0 = analog_values[id_I0]
        diff_U0 = differentiate_voltage(voltage=U0)

        if len(diff_U0) < trigger_moment:
            fig, ax1 = plt.subplots(figsize=(6, 3))
            ax1.set_title(f"File name: {filename}")
        else:
            channel_voltage, channel_current, channel_index = process_analog_data(diff_U0, I0, trigger_moment,
                                                                                  length_one_cycle)
            fig, _ = plot_channel_data(channel_voltage, channel_current, channel_index, sampling_rate,
                                       trigger_moment=trigger_moment, filename=filename)
    else:
        fig, ax1 = plt.subplots(figsize=(6, 3))
        ax1.set_title(f"File name: {filename}")

    label_detection = annotation['detection_label']
    label_location = annotation['location_label']
    label_type = annotation['type_label']

    if label_detection == None:
        label_detection = 'UNK'
    path_output = os.path.join(path_output, label_detection, 'total')
    path_save = os.path.join(path_output, filename + '.png')
    fig.savefig(path_save, dpi=300)
    plt.close(fig)
    if label_detection == 'NE':
        return
    if label_detection == 'PE' or label_detection == 'TE':
        path_location = os.path.join(path_output, '..', 'location', label_location, filename + '.png')
        path_type = os.path.join(path_output, '..', 'type', label_type, filename + '.png')
        shutil.copy2(path_save, path_location)
        shutil.copy2(path_save, path_type)


def batch_visualize(filename_list, path_output, path_source):
    for filename in filename_list:
        single_visualize(filename, path_output, path_source)


def get_image_from_comtrade(channel_selected=None, comtrade_selected=None,
                            info_comtrade=None, channels_info=None,mode=None,scale_rate=0.4):
    total_samples = info_comtrade['total_samples']
    trigger_moment = info_comtrade['trigger_moment']
    sampling_rate = info_comtrade['sampling_rate']
    if mode == 'Annotation':
        data_pixel = int(total_samples * scale_rate)
        size_pixel, left_margin, right_margin = data_pixel + 150, 100 / (data_pixel + 150), \
                                                (100+data_pixel) / (data_pixel + 150)
    else:
        size_pixel, left_margin, right_margin = 1300, 0.1, 0.95

    dpi = 100

    fig = plt.figure(figsize=(size_pixel / dpi, 5.8), dpi=dpi)
    plt.subplots_adjust(left=left_margin, right=right_margin, top=0.9, bottom=0.1)
    channel_values = [value * 1000 for value in
                      channels_info['analog_channel_values'][channels_info['analog_channel_ids'].index(channel_selected)]]
    time_values_ms = [i / sampling_rate for i in range(total_samples)]
    plt.plot(time_values_ms,channel_values)

    name_image = os.path.basename(comtrade_selected) + '_' + channel_selected
    plt.title(name_image)
    plt.ylabel('Amplitude(kV)' if channel_selected.startswith('U') else 'Amplitude(kA)' if channel_selected.startswith(
        'I') else 'Amplitude')
    plt.xlabel('Time(s)')
    ax = plt.gca()  # Get current axes
    if trigger_moment is not None:
        start_time_ms = (trigger_moment / sampling_rate) * 1
        ax.axvline(x=start_time_ms, color='g', linestyle='--', label='Trigger Moment')
    plt.legend()
    max_ticks = size_pixel // 50
    ax.xaxis.set_major_locator(MaxNLocator(max_ticks))
    plt.xlim(time_values_ms[0], time_values_ms[-1])
    # plt.xlim(0, total_samples-1)
    plt.close()
    canvas = FigureCanvas(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    return buf

def get_image_from_comtrade_location(channel_selected=None, comtrade_selected=None,
                            info_comtrade=None, channels_info=None,
                            mode='Annotation',scale_rate=0.6,reference_signal=[]):
    total_samples = info_comtrade['total_samples']
    trigger_moment = info_comtrade['trigger_moment']
    sampling_rate = info_comtrade['sampling_rate']
    if mode == 'Annotation':
        data_pixel = int(total_samples * scale_rate)
        size_pixel, left_margin, right_margin = data_pixel + 150, 100 / (data_pixel + 150), \
                                                (100+data_pixel) / (data_pixel + 150)
    else:
        size_pixel, left_margin, right_margin = 1300, 0.1, 0.95
    dpi = 100
    fig = plt.figure(figsize=(size_pixel / dpi, 5.8), dpi=dpi)
    plt.subplots_adjust(left=left_margin, right=right_margin, top=0.9, bottom=0.1)


    channel_values = [value * 1000 for value in
                      channels_info['analog_channel_values'][channels_info['analog_channel_ids'].index(channel_selected)]]
    time_values_ms = [i / sampling_rate for i in range(total_samples)]
    ax1 = plt.gca()
    ax1.plot(time_values_ms, channel_values)
    ax1.set_zorder(2)  # 设置ax1的z-order为更高的值
    if len(reference_signal)!=0:
        ax2 = ax1.twinx()
        channel_reference = [
            value * 1000 for value in channels_info['analog_channel_values'][channels_info['analog_channel_ids'].index(reference_signal[0])]
        ]
        channel_reference = differentiate_voltage(voltage=channel_reference)
        ax2.plot(time_values_ms, channel_reference,color='r', label='Voltage Derivative')
        ax2.set_ylabel('Voltage Derivative',color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        ax2.set_zorder(1)  # 设置ax1的z-order为更高的值
    ax1.patch.set_visible(False)  # 设置ax1的背景为透明

    name_image = os.path.basename(comtrade_selected) + '_' + channel_selected
    ax1.set_title(name_image)
    ax1.set_ylabel('Amplitude(kV)' if channel_selected.startswith('U') else 'Amplitude(kA)' if channel_selected.startswith('I') else 'Amplitude')
    ax1.set_xlabel('Time(s)')

    if trigger_moment is not None:
        start_time_ms = (trigger_moment / sampling_rate) * 1
        ax1.axvline(x=start_time_ms, color='g', linestyle='--', label='Trigger Moment')
    # Configure ticks
    max_ticks = size_pixel // 50
    ax1.xaxis.set_major_locator(MaxNLocator(max_ticks))
    ax1.set_xlim(time_values_ms[0], time_values_ms[-1])
    # Handle legends for both y-axes
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    if reference_signal:
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
    else:
        ax1.legend()
    # Finish up the plot
    plt.close(fig)
    canvas = FigureCanvas(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    # Return the RGBA buffer for further processing if needed
    return buf



if __name__ == '__main__':
    STATISTICS_TREE = {
        'NE': {'total': 0},
        'PE': {
            'total': 0,
            'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
            'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
        },
        'TE': {
            'total': 0,
            'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
            'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
        },
        'UNK': {'total': 0}
    }
    root_path = os.path.join(get_parent_directory(levels_up=2), 'testnew')  # 将此路径替换为你希望创建文件夹的目录
    create_folders(tree=STATISTICS_TREE, root=root_path)
