import os.path

from qtpy.QtWidgets import QDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from qtpy.QtWidgets import QMessageBox, QVBoxLayout
from labelsig.widget.ChannelSelectionView import ChannelSelectionDialog
from labelsig.utils import get_channels_comtrade,get_info_comtrade,find_id_of_U0_I0,process_analog_data
from labelsig.utils import get_parent_directory,differentiate_voltage
from labelsig.utils import plot_channel_data

class WaveformVisualizerDialog(QDialog):
    def __init__(self, parent=None,file_name=None, title="Matplotlib image", width=800, height=600):
        super(WaveformVisualizerDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(100, 100, width, height)
        self.filename = file_name
        self.root_labelsig=get_parent_directory(levels_up=1)
        self.path_raw=os.path.join(self.root_labelsig,'tmp','raw')
        canvas = self.plot_image()
        layout = QVBoxLayout()
        layout.addWidget(canvas)
        self.setLayout(layout)

        if canvas :
            self.show()

    def plot_image(self):
        path_file_base=os.path.join(self.path_raw,self.filename)
        channels_info=get_channels_comtrade(path_file_base=path_file_base)
        info_comtrade=get_info_comtrade(path_file_base=path_file_base)
        sampling_rate=info_comtrade['sampling_rate']
        trigger_moment=info_comtrade['trigger_moment']
        analog_channel_ids=channels_info['analog_channel_ids']
        analog_values=channels_info['analog_channel_values']
        length_one_cycle = int(sampling_rate*0.02)
        id_U0_I0 = find_id_of_U0_I0(analog_channel_ids)
        if id_U0_I0:
            id_U0,id_I0=id_U0_I0
        else:
            dialog = ChannelSelectionDialog(self, file_name=self.filename, mode='Visualization')
            if dialog.exec_():
                channels_info = dialog.selected_channels
                if channels_info is None:
                    return None
                id_I0=channels_info['current_channel_index']
                id_U0=channels_info['voltage_channel_index']
                # 检查索引是否为None，并提供警告
                if id_I0 is None or id_U0 is None:
                    QMessageBox.warning(self, "警告", "缺少所需的通道索引。无法继续可视化。")
                    return None
            else:
                return None

        # 打印对应的名字
        print(analog_channel_ids[id_U0],analog_channel_ids[id_I0])
        U0 = analog_values[id_U0]
        I0 = analog_values[id_I0]
        diff_U0 = differentiate_voltage(voltage=U0)
        if len(diff_U0)<trigger_moment:
            QMessageBox.warning(self, "警告", "触发瞬间超出范围。无法继续可视化。")
            return None
        channel_voltage, channel_current, channel_index = process_analog_data(diff_U0, I0, trigger_moment, length_one_cycle)
        fig,(ax1,ax2)=plot_channel_data(channel_voltage, channel_current, channel_index,sampling_rate,
                          trigger_moment=trigger_moment,filename=self.filename)
        canvas = FigureCanvas(fig)
        return canvas


