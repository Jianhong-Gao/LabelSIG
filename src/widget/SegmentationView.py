import os.path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow,QDialog,QLabel,QMessageBox,QApplication
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
from src.widget.ImageAnnotationView_Segmentation import AdaptableLabel
from src.widget.CountdownWarningView import WarningDialog
from src.ui_generated.ui_segmentation_view import Ui_main
from src.utils.utils_general import get_parent_directory
from src.utils.utils_comtrade import get_channels_comtrade,get_info_comtrade
from src.utils.utils_annotation import get_annotation_info,update_annotation_label
from src.utils.utils_visualize import get_image_from_comtrade

style_enable = "color: rgb(255, 255, 255);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(48, 105, 176);border-radius: 16px;"
style_disable = "color: rgb(0, 0, 0);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(169, 169, 197);border-radius: 16px;"


class SegmentationPage(QMainWindow, Ui_main):
    VERSION='2.2.1'
    def __init__(self,parent=None):
        super(SegmentationPage, self).__init__()
        self.setupUi(self)
        if parent is not None:
            self.parent=parent
        self.init_ui_elements()
        self.refresh_lw_comtrade()

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
        self.button_annotate.clicked.connect(self.annotate)
        self.button_return.clicked.connect(self.return_to_main)
        self.button_clear.clicked.connect(self.clear)
        self.set_button_style(self.button_annotate, False)
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_clear, True)
        self.set_button_style(self.button_return, True)
    def scale_up(self):
        self.scale_rate=self.scale_rate*2
        if self.flag_annotate:
            self.show_waveform_annotated()

    def scale_down(self):
        self.scale_rate=self.scale_rate*0.5
        if self.flag_annotate:
            self.show_waveform_annotated()


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
        self.set_button_style(self.button_annotate, False)
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_return, False)
        warning_dialog = WarningDialog(self)
        self.status_label.setText('Warning: All Annotation Files Would Be Cleared')
        if warning_dialog.exec_() == QDialog.Accepted:
            self.files_from_annotation = {os.path.splitext(f)[0] for f in os.listdir(self.path_annotation)}

            for filename in self.files_from_annotation:
                path_raw_base = os.path.join(self.path_raw, filename)
                path_annotation_base = os.path.join(self.path_annotation,filename)
                path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
                annotation = get_annotation_info(path_base_dict)
                annotation['segmentation']={}
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

    def annotate(self):
        self.show_waveform_annotated()
        self.lw_comtrade.setDisabled(True)
        self.lw_channel.setDisabled(True)
        self.set_button_style(self.button_clear, False)
        self.set_button_style(self.button_annotate, False)
        self.set_button_style(self.button_confirm, True)
        self.set_button_style(self.button_return, False)
        self.set_button_style(self.button_scale_up, True)
        self.set_button_style(self.button_scale_down, True)


    def confirm(self):
        if hasattr(self, 'label_Adap'):
            self.label_Adap.inner_label.confirm_and_write_file()
        self.flag_annotate = False
        self.lw_comtrade.setDisabled(False)
        self.lw_channel.setDisabled(False)
        self.set_button_style(self.button_annotate, True)
        self.set_button_style(self.button_clear, True)
        self.set_button_style(self.button_confirm, False)
        self.set_button_style(self.button_return, True)
        self.set_button_style(self.button_scale_up, False)
        self.set_button_style(self.button_scale_down, False)
        self.refresh_lw_channel_annotation()
        self.show_waveform_annotated_confirm()

    def show_waveform(self):
        self.set_button_style(self.button_annotate, True)
        self.channel_selected = self.lw_channel.currentItem().text()
        self.info_img = {'top_bottom_left_right': (0.9, 0.1, 0.1, 0.95)}
        buf=get_image_from_comtrade(channel_selected=self.channel_selected,
                                    comtrade_selected=self.comtrade_selected,
                                    info_comtrade=self.info_comtrade,
                                    channels_info=self.channels_info,
                                    scale_rate=self.scale_rate)
        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_annotate= False
        self.show_label_Adap(pixmap=pixmap)

    def show_waveform_annotated(self):
        data_pixel=int(self.annotation['total_samples']*self.scale_rate)
        size_pixel=data_pixel+150
        if size_pixel>=65536:
            # 跳出信息框，说明图片尺寸过大，不适用WarningDialog
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
        buf = get_image_from_comtrade(channel_selected=self.channel_selected,
                                      comtrade_selected=self.comtrade_selected,
                                      mode='Annotation',
                                      info_comtrade=self.info_comtrade,
                                      channels_info=self.channels_info,
                                      scale_rate=self.scale_rate)


        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_annotate = True
        self.show_label_Adap(pixmap=pixmap)

    def show_waveform_annotated_confirm(self):
        self.info_img = {'top_bottom_left_right': (0.9, 0.1, 0.1, 0.95)}
        buf=get_image_from_comtrade(channel_selected=self.channel_selected,comtrade_selected=self.comtrade_selected,
                                    info_comtrade=self.info_comtrade,
                                    channels_info=self.channels_info,
                                    scale_rate=self.scale_rate)
        qimage = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.flag_annotate=False
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
                                 if self.get_annotation_info(file_name)['segmentation']]
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
    def closeEvent(self, event):
        self.deleteLater()
    def refresh_lw_channel(self):
        if hasattr(self, 'label_Adap'):
            self.label_Adap.close()
        self.comtrade_selected = self.lw_comtrade.currentItem().text()
        path_raw_base=os.path.join(self.path_raw,self.comtrade_selected)
        path_annotation_base=os.path.join(self.path_annotation,self.comtrade_selected)

        self.channels_info = get_channels_comtrade(path_file_base=path_raw_base)
        self.info_comtrade=get_info_comtrade(path_file_base=path_raw_base)
        self.analog_channel_ids = self.channels_info['analog_channel_ids']
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        self.annotation=get_annotation_info(path_base_dict)
        channels_labeled=list(self.annotation['segmentation'].keys())
        self.refresh_listwidget(listwidget=self.lw_channel, item_list=self.analog_channel_ids, blue_items=channels_labeled)

    def refresh_lw_channel_annotation(self):
        path_raw_base = os.path.join(self.path_raw, self.comtrade_selected)
        path_annotation_base = os.path.join(self.path_annotation, self.comtrade_selected)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        annotation = get_annotation_info(path_base_dict)
        segm_annotation = annotation['segmentation']
        channels_labeled = list(segm_annotation.keys())
        self.refresh_listwidget(listwidget=self.lw_channel, item_list=self.analog_channel_ids, blue_items=channels_labeled)

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    MainWindow = SegmentationPage()
    MainWindow.show()
    app.exec_()
