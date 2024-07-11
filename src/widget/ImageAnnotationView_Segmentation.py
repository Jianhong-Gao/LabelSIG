from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import numpy as np
import os
from src.widget.LabelManagementView import MyDialog
from src.utils.utils_general import read_or_create_file,find_subsequences
from src.utils.utils_annotation import update_annotation_label


style_enable = "color: rgb(255, 255, 255);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(48, 105, 176);border-radius: 16px;"
style_disable = "color: rgb(0, 0, 0);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(169, 169, 197);border-radius: 16px;"


def Hex_to_Qcolor(hex):
    # 去除颜色代码前的'#'符号，确保它是一个纯粹的十六进制数
    hex = hex.lstrip('#')
    # 提取红、绿、蓝颜色值
    r = int(hex[0:2], 16)
    g = int(hex[2:4], 16)
    b = int(hex[4:6], 16)
    # 格式化为QColor字符串
    Qcolor = f'QColor({r}, {g}, {b}, 255)'
    return Qcolor



class MyLabel(QLabel):
    def __init__(self, parent=None,operation=None):
        super(MyLabel, self).__init__((parent))
        self.parent = parent
        self.operation=operation
        self.init_attributes()
        self.init_UI()

    def init_attributes(self):
        info = self.operation.info_img
        self.flag_annotate=self.operation.flag_annotate
        self.annotation=self.operation.annotation
        self.sampling_rate=self.annotation['sampling_rate']
        self.total_samples=self.annotation['total_samples']
        self.segm_annotation=self.annotation['segmentation']

        self.channel_selected=self.operation.channel_selected
        self.comtrade_selected=self.operation.comtrade_selected
        self.path_raw = self.operation.path_raw
        self.path_annotation = self.operation.path_annotation
        self.path_config=self.operation.path_config
        self.enable_annotation = True
        self.x0, self.y0, self.x1, self.y1 = 0, 0, 0, 0
        self.set_geometry(info['top_bottom_left_right'])
        self.init_annotation()
        if self.operation.flag_annotate:
            self.setCursor(Qt.CrossCursor)
        self.refresh_label_config()

    def init_UI(self):
        self.setStyleSheet('background-color: rgb(48, 105, 176);')
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightMenuShow)

    def set_geometry(self, bounds):
        top, bottom, left, right = bounds
        self.setGeometry(self.parent.geometry())
        self.dist_left, self.dist_right, self.dist_top, self.dist_bottom = left, right, top, bottom

    def refresh_label_config(self):
        self.config_annotation = read_or_create_file(self.path_config, "Annotation.config")
        self.label_config=self.config_annotation.keys()
        return self.label_config

    def init_annotation(self):
        if self.channel_selected not in self.segm_annotation.keys():
            self.segm_annotation[self.channel_selected] = {}
        self.channel_annotation = self.segm_annotation[self.channel_selected]
        if 'temp_annotation' not in self.channel_annotation:
            self.channel_annotation['temp_annotation'] = [0 for i in range(self.total_samples)]
        self.temp_annotation = self.channel_annotation['temp_annotation']
        self.refresh_label_config()

    def confirm_and_write_file(self):
        self.segm_annotation[self.channel_selected] = self.channel_annotation
        self.annotation['segmentation']=self.segm_annotation
        path_raw_base=os.path.join(self.path_raw,self.comtrade_selected)
        path_annotation_base=os.path.join(self.path_annotation,self.comtrade_selected)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        flag_save_annotation = update_annotation_label(path_base_dict=path_base_dict, annotation_dict=self.operation.annotation)
        if flag_save_annotation:
            self.operation.status_label.setText('Annotation saved successfully!')

    def cal_left_right_box(self):
        width_image = self.width()
        height_image = self.height()
        self.width_box = width_image * (self.dist_right - self.dist_left)
        self.height_box = height_image * (self.dist_bottom - self.dist_top)
        self.coordinate_left_box = int(self.dist_left * width_image)
        self.coordinate_right_box = int(self.dist_right * width_image)
        self.coordinate_top_box = int(self.dist_top * height_image)
        self.coordinate_bottom_box = int(self.dist_bottom * height_image)

    # 鼠标点击事件
    def rightMenuShow(self, pos):  # 添加右键菜单
        menu = QMenu(self)
        menu.addAction(QAction('Undo', menu))
        menu.addAction(QAction('Clear', menu))
        menu.triggered.connect(self.menuSlot)
        menu.exec_(QCursor.pos())

    def menuSlot(self, act):
        self.update()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.flag_annotate:
            self.flag_LeftButton = True
            self.x0 = event.x()
            self.y0 = event.y()

    # 鼠标释放事件
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.operation.flag_annotate:
            self.flag_LeftButton = False
            self.x1, self.y1 = event.x(), event.y()
            if self.valid_annotation_area(self.x0, self.y0, self.x1, self.y1):
                self.adjust_coordinates()
                self.save_info(self.x0, self.x1)

    def valid_annotation_area(self, x0, y0, x1, y1):
        # 校验标注区域是否有效
        if (x0 == x1 or
            x1 <= x0 or
            (x0 > self.coordinate_right_box and x1 > self.coordinate_right_box) or
            (y0 > self.coordinate_top_box and y1 > self.coordinate_top_box) or
            (y0 < self.coordinate_bottom_box and y1 < self.coordinate_bottom_box)):
            return False
        return True

    def adjust_coordinates(self):
        # 校正坐标确保不超出边界
        self.x0 = max(self.x0, self.coordinate_left_box)
        self.x1 = max(self.x1, self.coordinate_left_box)
        self.x0 = min(self.x0, self.coordinate_right_box)
        self.x1 = min(self.x1, self.coordinate_right_box)

    # 鼠标移动事件
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.flag_annotate:
            if self.flag_LeftButton:
                self.x1 = event.x()
                self.y1 = event.y()
                self.update()

    def pixel_to_index(self, x0_pixel, x1_pixel):
        x0_pixel = x0_pixel - self.coordinate_left_box
        x1_pixel = x1_pixel - self.coordinate_left_box
        length_pixel = self.coordinate_right_box - self.coordinate_left_box
        length_index = self.total_samples
        x0_index = int(x0_pixel * length_index / length_pixel)
        x1_index = int(x1_pixel * length_index / length_pixel)
        return x0_index, x1_index

    def index_to_pixel(self, x0_index, x1_index):
        length_pixel = self.coordinate_right_box - self.coordinate_left_box
        length_index = self.total_samples
        x0_pixel = int(x0_index * length_pixel / length_index) + self.coordinate_left_box
        x1_pixel = int(x1_index * length_pixel / length_index) + self.coordinate_left_box
        return x0_pixel, x1_pixel

    def save_info(self, x0, x1):
        x0_index, x1_index = self.pixel_to_index(x0, x1)
        self.openMyDialog()
        if self.label_name != '':
            self.refresh_label_config()
            value = self.config_annotation[self.label_name]['value']
            self.temp_annotation = np.array(self.temp_annotation)
            self.temp_annotation[x0_index:x1_index] = value
            print('总采样点数：',self.total_samples)
            print('起始点pixel：',x0,'终止点pixel',x1)
            print('起始点索引：',x0_index,'终止点索引',x1_index)
            print('当前采样率',self.sampling_rate)
            x0_index_time = x0_index / self.sampling_rate
            x1_index_time = x1_index / self.sampling_rate
            print(x0_index_time,x1_index_time)


            self.temp_annotation = self.temp_annotation.tolist()
            self.channel_annotation['temp_annotation'] = self.temp_annotation
            for category_name in self.label_config:
                value_temp = self.config_annotation[category_name]['value']
                result_temp = self.fill_and_replace(self.temp_annotation, target_num=value_temp)
                subsequence_temp = find_subsequences(result_temp)
                dict_annotation_temp = {'annotation_result': result_temp, 'annotation_subsequence': subsequence_temp}
                self.channel_annotation[category_name] = dict_annotation_temp

        self.enable_annotation = False
        self.update()

    def fill_and_replace(self,lst_temp, target_num):
        return [1 if num == target_num else 0 for num in lst_temp]
    def drawRect(self, painter):
        painter.setClipRect(self.coordinate_left_box, self.coordinate_top_box, int(self.width_box),
                            int(self.height_box))
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.setFont(QFont('Bahnschrift Condensed', 15))
        if self.enable_annotation:
            rect_temp = QRect(self.x0, self.coordinate_top_box, abs(self.x1 - self.x0), int(self.height_box))
            painter.drawRect(rect_temp)
        self.update_annotation(painter)

    def update_annotation(self, painter):
        self.enable_annotation = True
        self.config_annotation = read_or_create_file(self.path_config, "Annotation.config")
        for category_name in self.channel_annotation.keys():
            if category_name == 'Background' or category_name == 'temp_annotation':
                continue
            try:
                dict_annotation = self.channel_annotation[category_name]
                subsequence = dict_annotation['annotation_subsequence']
                color_hex = self.config_annotation[category_name]['color']
            except:
                continue
            for x0_index, x1_index in subsequence:
                x0_pixel, x1_pixel = self.index_to_pixel(x0_index, x1_index)
                center_x = round((x0_pixel + x1_pixel) / 2)
                center_y = round((self.coordinate_top_box + self.coordinate_bottom_box) * 0.2)
                color_Qcolor = Hex_to_Qcolor(color_hex)
                code = "painter.setPen(QPen(" + color_Qcolor + ", 2, Qt.SolidLine))"
                exec(code)
                rect = QRect(x0_pixel, self.coordinate_top_box, abs(x1_pixel - x0_pixel), int(self.height_box))
                painter.drawRect(rect)
                painter.translate(center_x, center_y)
                painter.rotate(90)
                painter.drawText(0, 0, category_name)
                painter.rotate(-90)
                painter.translate(-center_x, -center_y)

    def paintEvent(self, event):
        super(MyLabel, self).paintEvent(event)
        painter = QPainter(self)
        self.cal_left_right_box()
        self.drawRect(painter)
        painter.end()
    def openMyDialog(self):
        my = MyDialog(self.operation, self.label_config)
        my.mySignal.connect(self.getDialogSignal)
        my.exec_()

    def getDialogSignal(self, label_name):
        self.label_name = label_name


class AdaptableLabel(QLabel):
    def __init__(self, parent=None,operation=None,pixmap=None):
        super(AdaptableLabel, self).__init__(parent)
        self.operation=operation
        self.parent = parent
        self.init_ui()
        self.setGeometry(0, 0, parent.geometry().width(), parent.geometry().height())
        self.setPixmap(pixmap)

    def init_ui(self):
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.inner_label = MyLabel(parent = self.scroll_area,operation=self.operation)
        self.inner_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.inner_label)
        self.scroll_area.setGeometry(self.geometry())


    def setPixmap(self,pixmap):
        self.inner_label.setPixmap(pixmap)
        self.inner_label.setFixedSize(pixmap.size())
        self.inner_label.adjustSize()
        self.scroll_area.resize(pixmap.size())
        self.scroll_area.move(self.width() // 2 - pixmap.width() // 2,
                              self.height() // 2 - pixmap.height() // 2)
        self.scroll_area.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scroll_area.setGeometry(self.geometry())



