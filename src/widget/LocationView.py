import os.path
from PyQt5.QtGui import QImage, QPixmap
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QDialog,
    QVBoxLayout, QRadioButton, QDialogButtonBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from src.widget.ImageAnnotationView_Location import AdaptableLabel
from src.widget.CountdownWarningView import WarningDialog
from src.ui_generated.ui_location_view import Ui_main
from src.utils.utils_general import get_parent_directory
from src.utils.utils_comtrade import get_channels_comtrade,get_info_comtrade
from src.utils.utils_annotation import get_annotation_info,update_annotation_label
from src.utils.utils_visualize import get_image_from_comtrade_location

style_enable = "color: rgb(255, 255, 255);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(48, 105, 176);border-radius: 16px;"
style_disable = "color: rgb(0, 0, 0);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(169, 169, 197);border-radius: 16px;"


class LocationPage(QMainWindow, Ui_main):
    VERSION='0.0.1'
    def __init__(self,parent=None):
        super(LocationPage, self).__init__()
        self.setupUi(self)
        if parent is not None:
            self.parent=parent
        self.init_ui_elements()
        self.refresh_lw_comtrade()
        self.is_zoomed_in = False  # 添加属性来跟踪是否已放大


    def init_ui_elements(self):
        self.scale_rate=0.4
        self.root_project = get_parent_directory(levels_up=2)
        self.path_dict = self.get_temp_path()
        self.path_raw = self.path_dict['path_raw']
        self.path_annotation = self.path_dict['path_annotation']
        self.path_tmp = self.path_dict['path_tmp']
        self.path_config=os.path.join(self.root_project,'config')
        self.info_targets = []
        self.set_window_properties()
        self.configure_list_widgets()
        self.configure_buttons()

    def set_window_properties(self):
        path_icon = self.construct_path(self.root_project, 'resource', 'WindowIcon.png')
        self.setWindowIcon(QIcon(path_icon))
        version_label = QLabel()
        version_label.setText(f"Version: {self.VERSION}")
        self.statusBar.addWidget(version_label)
        self.status_label = QLabel()
        self.statusBar.addWidget(self.status_label)
        self.status_label.setText(" " * 10)

    def configure_list_widgets(self):
        self.lw_comtrade.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_comtrade.itemClicked.connect(self.refresh_lw_channel)
        self.lw_channel.itemClicked.connect(self.show_waveform)

    def configure_buttons(self):
        self.button_scale_up.clicked.connect(self.scale_up)
        self.button_scale_down.clicked.connect(self.scale_down)
        self.button_confirm.clicked.connect(self.confirm)
        # self.button_scrutinize.clicked.connect(self.scrutinize)
        self.button_return.clicked.connect(self.return_to_main)
        self.button_clear.clicked.connect(self.clear)
        self.button_mark.clicked.connect(self.mark_channel)
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_clear, True)
        self.set_button_style(self.button_return, True)
        self.set_button_style(self.button_mark, False)


    def mark_channel(self):
        self.set_button_style(self.button_confirm, True)
        self.lw_comtrade.setDisabled(True)
        current_item = self.lw_channel.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "Warning", "No channel selected.")
            return
        current_channel_name = current_item.text()
        choice = self.prompt_channel_marking(current_channel_name)
        if choice == 'unmark':
            self.unmark_channel(current_channel_name)
        elif choice == 'reference':
            self.set_reference_signal(current_channel_name)
        elif choice == 'fault':
            self.mark_fault_line(current_channel_name)
        elif choice == 'sound':
            self.mark_sound_line(current_channel_name)
        elif choice == 'ambiguous':
            self.mark_ambiguous_line(current_channel_name)
        # 更新UI或其他必要的状态
        self.refresh_listwidget_channels(listwidget=self.lw_channel,
                                         item_list=self.analog_channel_ids,
                                         reference_signal=self.reference_signal,
                                         fault_lines=self.fault_lines,
                                         sound_lines=self.sound_lines,
                                         ambiguous_lines=self.ambiguous_lines)
        # print('fault lines:',self.fault_lines)
        # print('sound lines:',self.sound_lines)
        # print('ambiguous lines:',self.ambiguous_lines)
        # print('reference signal:',self.reference_signal)
        # print('_'*50)


    def prompt_channel_marking(self, channel_name):
        dlg = QDialog(self)
        dlg.setWindowTitle("Mark Channel")
        layout = QVBoxLayout()
        rb_reference = QRadioButton("Reference Signal")
        rb_fault = QRadioButton("Fault Line")
        rb_sound = QRadioButton("Sound Line")
        rb_ambiguous = QRadioButton("Ambiguous Line")
        rb_unmark = QRadioButton("Unmark Selection")
        # 如果当前信道已经是参考信号，则禁用其他两个选项
        if channel_name in self.reference_signal:
            rb_fault.setDisabled(True)
            rb_sound.setDisabled(True)
            rb_ambiguous.setDisabled(True)

        else:
            rb_fault.setDisabled(False)
            rb_sound.setDisabled(False)
            rb_ambiguous.setDisabled(False)

        layout.addWidget(rb_reference)
        layout.addWidget(rb_fault)
        layout.addWidget(rb_sound)
        layout.addWidget(rb_unmark)
        layout.addWidget(rb_ambiguous)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)
        layout.addWidget(button_box)
        dlg.setLayout(layout)
        # 默认选中当前的标记状态
        if channel_name in self.reference_signal:
            rb_reference.setChecked(True)
        elif channel_name in self.fault_lines:
            rb_fault.setChecked(True)
        elif channel_name in self.sound_lines:
            rb_sound.setChecked(True)
        else:
            rb_unmark.setChecked(True)
        if dlg.exec_() == QDialog.Accepted:
            if rb_unmark.isChecked():
                return 'unmark'
            elif rb_reference.isChecked():
                return 'reference'
            elif rb_fault.isChecked():
                return 'fault'
            elif rb_sound.isChecked():
                return 'sound'
            elif rb_ambiguous.isChecked() :
                return 'ambiguous'
        return None

    def unmark_channel(self, channel_name):
        # 从所有标记列表中移除信道
        if channel_name in self.reference_signal:
            self.reference_signal.remove(channel_name)
        if channel_name in self.fault_lines:
            self.fault_lines.remove(channel_name)
        if channel_name in self.sound_lines:
            self.sound_lines.remove(channel_name)
        if channel_name in self.ambiguous_lines:
            self.ambiguous_lines.remove(channel_name)
        self.status_label.setText(f"Selection for '{channel_name}' has been cleared.")

    def set_reference_signal(self, channel_name):
        # 在设置为参考信号前，先从其他列表中移除
        if channel_name in self.fault_lines:
            self.fault_lines.remove(channel_name)
        if channel_name in self.sound_lines:
            self.sound_lines.remove(channel_name)
        if channel_name in self.ambiguous_lines:
            self.ambiguous_lines.remove(channel_name)
        self.reference_signal = [channel_name]
        self.status_label.setText(f"Reference signal set to '{channel_name}'")

    def mark_fault_line(self, channel_name):
        # 在标记为故障线前，从参考信号和非故障信号列表中移除
        if channel_name in self.reference_signal:
            self.reference_signal.remove(channel_name)
        if channel_name in self.sound_lines:
            self.sound_lines.remove(channel_name)
        if channel_name in self.ambiguous_lines:
            self.ambiguous_lines.remove(channel_name)
        if channel_name not in self.fault_lines:
            self.fault_lines.append(channel_name)
        self.status_label.setText(f"Fault line marked as '{channel_name}'")

    def mark_sound_line(self, channel_name):
        # 在标记为非故障线前，从参考信号和故障信号列表中移除
        if channel_name in self.reference_signal:
            self.reference_signal.remove(channel_name)
        if channel_name in self.fault_lines:
            self.fault_lines.remove(channel_name)
        if channel_name in self.ambiguous_lines:
            self.ambiguous_lines.remove(channel_name)
        if channel_name not in self.sound_lines:
            self.sound_lines.append(channel_name)
        self.status_label.setText(f"Sound line marked as '{channel_name}'")

    def mark_ambiguous_line(self, channel_name):
        # 在标记为不清楚的信号前，从所有其他标记列表中移除
        if channel_name in self.reference_signal:
            self.reference_signal.remove(channel_name)
        if channel_name in self.fault_lines:
            self.fault_lines.remove(channel_name)
        if channel_name in self.sound_lines:
            self.sound_lines.remove(channel_name)
        if channel_name not in self.ambiguous_lines:
            self.ambiguous_lines.append(channel_name)
        self.status_label.setText(f"Ambiguous signal marked as '{channel_name}'")

    def scale_up(self):
        self.scale_rate=self.scale_rate*1.5
        self.show_waveform_scrutinized()

    def scale_down(self):
        self.scale_rate=self.scale_rate*0.5
        self.show_waveform_scrutinized()

    def return_to_main(self):
        self.close()
        self.parent.show()

    def set_button_style(self, button, enable=True):
        if enable:
            button.setStyleSheet(style_enable)
        else:
            button.setStyleSheet(style_disable)
        button.setDisabled(not enable)

    def get_temp_path(self):
        root_project = get_parent_directory(levels_up=2)
        path_tmp = self.construct_path(root_project, 'tmp')
        path_tmp_raw = self.construct_path(root_project, 'tmp', 'raw')
        path_tmp_annotation = self.construct_path(root_project, 'tmp', 'annotation')
        os.makedirs(path_tmp_raw, exist_ok=True)
        os.makedirs(path_tmp_annotation, exist_ok=True)
        path_dict = {'path_raw': path_tmp_raw, 'path_annotation': path_tmp_annotation, 'path_tmp': path_tmp}
        return path_dict

    def construct_path(self, *args):
        return os.path.join(*args)

    def clear(self):
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_return, False)
        self.set_button_style(self.button_mark, False)

        warning_dialog = WarningDialog(self)
        self.status_label.setText('Warning: All Annotation Files Would Be Cleared')
        if warning_dialog.exec_() == QDialog.Accepted:
            self.files_from_annotation = {os.path.splitext(f)[0] for f in os.listdir(self.path_annotation)}

            for filename in self.files_from_annotation:
                path_raw_base = os.path.join(self.path_raw, filename)
                path_annotation_base = os.path.join(self.path_annotation,filename)
                path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
                annotation = get_annotation_info(path_base_dict)
                annotation['location']={}
                _ = update_annotation_label(path_base_dict=path_base_dict,
                                                               annotation_dict=annotation)
            self.status_label.setText('Clear All Annotation Files Successfully')
            self.refresh_lw_comtrade()
            if hasattr(self, 'comtrade_selected'):
                self.refresh_lw_channel_annotation()
            if hasattr(self, 'label_Adap'):
                self.label_Adap.close()
        else:
            self.status_label.setText('Operation Canceled')
        self.set_button_style(self.button_return, True)

    # def scrutinize(self):
    #     if not self.is_zoomed_in:
    #         self.is_zoomed_in = True  # 更新放大状态
    #         # 如果当前未放大，则放大波形
    #         self.show_waveform_scrutinized()
    #         self.lw_comtrade.setDisabled(True)
    #         self.set_button_style(self.button_scale_up, True)
    #         self.set_button_style(self.button_scale_down, True)
    #     else:
    #         self.is_zoomed_in = False  # 更新放大状态
    #         self.lw_comtrade.setDisabled(False)
    #         self.set_button_style(self.button_scale_up, False)
    #         self.set_button_style(self.button_scale_down, False)
    #         self.refresh_lw_channel_annotation()
    #         self.show_waveform_scrutinized_confirm()


    def confirm(self):
        self.lw_comtrade.setDisabled(False)
        self.lw_channel.setDisabled(False)
        # self.set_button_style(self.button_scrutinize, True)
        self.set_button_style(self.button_clear, True)
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_mark, False)
        self.set_button_style(self.button_return, True)
        self.set_button_style(self.button_scale_up, False)
        self.set_button_style(self.button_scale_down, False)
        self.refresh_lw_channel_annotation()
        self.show_waveform_scrutinized_confirm()
        self.confirm_and_write_file()
        self.lw_comtrade.setDisabled(False)

    def show_waveform(self):
        self.set_button_style(self.button_scale_up,True)
        self.set_button_style(self.button_scale_down,True)
        self.set_button_style(self.button_mark, True)
        self.set_button_style(self.button_confirm, False)

        self.channel_selected = self.lw_channel.currentItem().text()

        self.info_img = {'top_bottom_left_right': (0.9, 0.1, 0.1, 0.95)}
        buf=get_image_from_comtrade_location(channel_selected=self.channel_selected,
                                    comtrade_selected=self.comtrade_selected,
                                    info_comtrade=self.info_comtrade,
                                    channels_info=self.channels_info,
                                    scale_rate=self.scale_rate,
                                    reference_signal=self.reference_signal)
        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_scrutinize= False
        self.show_label_Adap(pixmap=pixmap)

    def show_waveform_scrutinized(self):
        data_pixel=int(self.annotation['total_samples']*self.scale_rate)
        size_pixel=data_pixel+150
        if size_pixel>=65536:
            QMessageBox.warning(self, "Warning", "The size of the image is too large, please scale down the image.")
            self.set_button_style(self.button_scale_up, False)
            return
        else:
            self.set_button_style(self.button_scale_up, True)
        left_ratio=100/(100+50+data_pixel)
        right_ratio=(100+data_pixel)/(150+data_pixel)
        if left_ratio>=right_ratio:
            QMessageBox.warning(self, "Warning", "The size of the image is too small, please scale up the image.")
            self.set_button_style(self.button_scale_down, False)
            return
        else:
            self.set_button_style(self.button_scale_down, True)


        self.info_img={'top_bottom_left_right':(0.9,0.1,left_ratio,right_ratio)}
        buf=get_image_from_comtrade_location(channel_selected=self.channel_selected,
                                    comtrade_selected=self.comtrade_selected,
                                    info_comtrade=self.info_comtrade,
                                    channels_info=self.channels_info,
                                    scale_rate=self.scale_rate,mode = 'Annotation',
                                    reference_signal=self.reference_signal)
        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_scrutinize = True
        self.show_label_Adap(pixmap=pixmap)

    def show_waveform_scrutinized_confirm(self):
        self.info_img = {'top_bottom_left_right': (0.9, 0.1, 0.1, 0.95)}
        buf=get_image_from_comtrade_location(channel_selected=self.channel_selected,
                                    comtrade_selected=self.comtrade_selected,
                                    info_comtrade=self.info_comtrade,
                                    channels_info=self.channels_info,
                                    scale_rate=self.scale_rate,
                                    reference_signal=self.reference_signal)
        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_scrutinize=False
        self.show_label_Adap(pixmap=pixmap)

    def show_label_Adap(self, pixmap):
        if hasattr(self, 'label_Adap'):
            self.label_Adap.close()
        self.label_Adap = AdaptableLabel(parent=self.label_located,operation=self,pixmap=pixmap)  # 重定义的label
        self.label_Adap.show()

    def refresh_lw_comtrade(self):
        self.files_from_raw = {os.path.splitext(f)[0] for f in os.listdir(self.path_raw)}
        self.files_from_annotation = {os.path.splitext(f)[0] for f in os.listdir(self.path_annotation)}
        unique_base_files = sorted(self.files_from_raw)
        annotation_valid_list = [file_name for file_name in unique_base_files
                                 if self.get_annotation_info(file_name)['location']]
        blue_items = [item for item in annotation_valid_list if item in self.files_from_annotation]
        self.refresh_listwidget(listwidget=self.lw_comtrade, item_list=self.files_from_raw, blue_items=blue_items)

    def get_annotation_info(self, file_name):
        path_raw_base = os.path.join(self.path_raw, file_name)
        path_annotation_base = os.path.join(self.path_annotation, file_name)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        return get_annotation_info(path_base_dict)

    def refresh_listwidget(self, listwidget, item_list, blue_items=[]):
        listwidget.clear()
        for item in item_list:
            item_widget = QtWidgets.QListWidgetItem(item)
            if item in blue_items:
                item_widget.setBackground(QtGui.QColor("#cfd8e3"))
            listwidget.addItem(item_widget)
        listwidget.sortItems()
    def refresh_listwidget_channels(self, listwidget, item_list,
                                    reference_signal=[],
                                    fault_lines=[],
                                    sound_lines=[],
                                    ambiguous_lines=[]):
        listwidget.clear()
        for item in item_list:
            item_widget = QtWidgets.QListWidgetItem(item)
            if item in reference_signal:
                item_widget.setBackground(QtGui.QColor("#DDDDBB"))
            if item in fault_lines:
                item_widget.setBackground(QtGui.QColor("#CD5C5C"))
            if item in sound_lines:
                item_widget.setBackground(QtGui.QColor("#8FBC8F"))
            if item in ambiguous_lines:
                item_widget.setBackground(QtGui.QColor("#A9A9A9"))
            listwidget.addItem(item_widget)
        listwidget.sortItems()

    def closeEvent(self, event):
        self.deleteLater()
    def refresh_lw_channel(self):
        if hasattr(self, 'label_Adap'):
            self.label_Adap.close()
        # self.set_button_style(self.button_scrutinize,False)
        self.set_button_style(self.button_mark,False)
        self.comtrade_selected = self.lw_comtrade.currentItem().text()
        path_raw_base=os.path.join(self.path_raw,self.comtrade_selected)
        path_annotation_base=os.path.join(self.path_annotation,self.comtrade_selected)

        self.channels_info = get_channels_comtrade(path_file_base=path_raw_base)
        self.info_comtrade=get_info_comtrade(path_file_base=path_raw_base)
        self.analog_channel_ids = self.channels_info['analog_channel_ids']
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        self.annotation=get_annotation_info(path_base_dict)
        self.loca_annotation=self.annotation['location']

        self.reference_signal = self.loca_annotation.setdefault('reference_signal', [])
        self.fault_lines = self.loca_annotation.setdefault('fault_lines', [])
        self.sound_lines = self.loca_annotation.setdefault('sound_lines', [])
        self.ambiguous_lines = self.loca_annotation.setdefault('ambiguous_lines', [])

        self.refresh_listwidget_channels(listwidget=self.lw_channel,
                                         item_list=self.analog_channel_ids,
                                         reference_signal=self.reference_signal,
                                         fault_lines=self.fault_lines,
                                         sound_lines=self.sound_lines,
                                         ambiguous_lines=self.ambiguous_lines)

    def refresh_lw_channel_annotation(self):
        path_raw_base = os.path.join(self.path_raw, self.comtrade_selected)
        path_annotation_base = os.path.join(self.path_annotation, self.comtrade_selected)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        annotation = get_annotation_info(path_base_dict)
        self.refresh_listwidget_channels(listwidget=self.lw_channel,
                                         item_list=self.analog_channel_ids,
                                         reference_signal=self.reference_signal,
                                         fault_lines=self.fault_lines,
                                         sound_lines=self.sound_lines,
                                         ambiguous_lines=self.ambiguous_lines)
    def confirm_and_write_file(self):
        self.loca_annotation['reference_signal']=self.reference_signal
        self.loca_annotation['fault_lines']=self.fault_lines
        self.loca_annotation['sound_lines']=self.sound_lines
        self.annotation['location']=self.loca_annotation
        path_raw_base=os.path.join(self.path_raw,self.comtrade_selected)
        path_annotation_base=os.path.join(self.path_annotation,self.comtrade_selected)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        flag_save_annotation = update_annotation_label(path_base_dict=path_base_dict, annotation_dict=self.annotation)
        if flag_save_annotation:
            self.status_label.setText('Annotation saved successfully!')

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    MainWindow = LocationPage()
    MainWindow.show()
    app.exec_()
