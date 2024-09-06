import logging
import os
filename = os.path.splitext(os.path.basename(__file__))[0]
if not logging.getLogger().hasHandlers():  # 检查是否已配置
    logging.basicConfig(
        level=logging.INFO,  # 辅助程序可以设置不同的日志级别
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(f"{filename}.log"),
            logging.StreamHandler()
        ]
    )
logger = logging.getLogger(filename)

import weakref

import numpy as np
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QColor, QPainter, QIcon, QFont
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsLineItem, QDialog,QDesktopWidget,
                             QGraphicsRectItem, QApplication, QGraphicsSimpleTextItem, QMainWindow, QLabel,
                             QListWidgetItem
                             )

from labelsig.ui_generated.ui_fault_detection_view import Ui_main
from labelsig.utils.utils_annotation import write_annotation, load_annotation
from labelsig.utils.utils_comtrade import get_info_comtrade
from labelsig.utils.utils_general import get_annotation_ranges, get_sorted_unique_file_basenames, get_parent_directory
from labelsig.widget.CountdownWarningView import WarningDialog
from labelsig.widget.LabelManagementView import LabelManagementDialog




class SignalAnnotationView(QGraphicsView):

    def __init__(self, parent=None, selected_comtrade_info=None):
        super(SignalAnnotationView, self).__init__(parent)
        self.horizontal_scale_factor = 1/1.1  # Initial scale factor
        self.margin_side = 50  # Space for both left and right margins
        self.margin_top = 10  # Space for x-axis
        self.margin_bottom = 50  # Space for x-axis

        self.setStyleSheet("QGraphicsView { padding: 10px; margin: 0px; }")

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())

        self.setCacheMode(QGraphicsView.CacheNone)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.root_project = get_parent_directory(levels_up=1)
        self.path_raw = os.path.join(self.root_project, 'tmp', 'raw')
        self.path_ann = os.path.join(self.root_project, 'tmp', 'ann')

        self.is_annotation = False

        self.channels_info = selected_comtrade_info['channels_info']
        self.selected_comtrade_filename = selected_comtrade_info['selected_comtrade_filename']
        self.selected_channel = selected_comtrade_info['selected_channel']
        self.signal_data = np.array(self.channels_info['analog_channel_values'][
                                        self.channels_info['analog_channel_ids'].index(self.selected_channel)
                                    ]) * 1000
        self.sampling_rate = selected_comtrade_info['sampling_rate']

        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        self.selected_annotation = annotation["fault_detection"].get(self.selected_channel, {})
        self.rect_item = None

        self.min_y = np.min(self.signal_data) * 1.2
        self.max_y = np.max(self.signal_data) * 1.2
        self.annotation_items = []  # 用于存储所有注释图形对象的列表
        self._initialize_scene()

    def _initialize_scene(self):
        """Initializes the background grid, axes, and signal."""
        scene_width = self.width() * self.horizontal_scale_factor  # 增加额外空间
        scene_height = self.height()  # 增加额外空间
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

        self._draw_background_grid()
        self._draw_axes()
        self._draw_signal()

        self.resetTransform()  # 重置之前的缩放，防止累积缩放
        self.scale(1, 0.90)  # 仅在垂直方向上缩放

    def show_selected_annotation(self):
        # 清除现有的注释
        self._clear_existing_annotations()

        if "Comprehensive-Category" in self.selected_annotation:
            annotation_ranges = get_annotation_ranges(self.selected_annotation["Comprehensive-Category"])
            # print(f"show_selected_annotation:{annotation_ranges}")

            for value, ranges in annotation_ranges.items():
                if value == 0:
                    continue
                for start_idx, end_idx in ranges:
                    self._draw_annotation_segment(start_idx, end_idx, value)

    def _clear_existing_annotations(self):
        """清除现有的注释图形对象。"""
        for item_ref in self.annotation_items:
            item = item_ref()  # 获取弱引用对象
            if item is not None and item.scene() is not None:  # 确保item仍然存在于场景中
                self.scene.removeItem(item)
        self.annotation_items.clear()  # 清空列表

    def _draw_annotation_segment(self, start_idx, end_idx, value):
        start_x = self.time_values[start_idx]
        end_x = self.time_values[end_idx]
        rect = QRectF(start_x, self.margin_top, end_x - start_x, self.height() - self.margin_bottom - self.margin_top)
        if value != 0:
            color = self.selected_annotation["Semantic-Category"][value]["color"]
            label = self.selected_annotation["Semantic-Category"][value]["label"]
            self._draw_rect_and_label(rect, color, label)

    def _draw_rect_and_label(self, rect, color, label):
        """Draws a rectangle and label for the annotation."""
        border_color = QColor(color)
        border_color.setAlpha(255)
        fill_color = QColor(color)
        fill_color.setAlpha(100)

        rect_item = QGraphicsRectItem(rect)
        rect_item.setPen(QPen(border_color, 2))
        rect_item.setBrush(fill_color)
        self.scene.addItem(rect_item)
        self.annotation_items.append(weakref.ref(rect_item))  # 使用弱引用保存到注释对象列表中

        text_item = QGraphicsSimpleTextItem(label)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        text_item.setFont(font)
        text_item.setBrush(Qt.black)
        text_item.setPos(rect.left(), rect.top())

        self.scene.addItem(text_item)
        self.annotation_items.append(weakref.ref(text_item))

    def update_annotation(self, start_idx, end_idx, semantic_category, value_semantic_category,
                          color_semantic_category):
        # print(start_idx, end_idx, semantic_category, value_semantic_category, color_semantic_category)
        if semantic_category and color_semantic_category is not None:
            length_signal = len(self.signal_data)
            self.selected_annotation.setdefault("Semantic-Category", {})[value_semantic_category] = {
                "label": semantic_category,
                "color": color_semantic_category
            }
            self.selected_annotation[semantic_category] = self._create_sequence(length_signal, start_idx, end_idx)
            self.selected_annotation.setdefault("Comprehensive-Category", [0] * length_signal)
            for i in range(start_idx, end_idx + 1):
                self.selected_annotation["Comprehensive-Category"][i] = value_semantic_category

            # annotation_ranges = get_annotation_ranges(self.selected_annotation["Comprehensive-Category"])
            # print(f"update_annotation:{annotation_ranges}")

    def _create_sequence(self, length_signal, start_idx, end_idx):
        sequence = [0] * length_signal
        for i in range(start_idx, end_idx + 1):
            sequence[i] = 1
        return sequence

    def _update_view(self):
        self.scene.clear()
        self._initialize_scene()
        self.centerOn(self.mapToScene(self.viewport().rect().center()))
        self.show_selected_annotation()
        self.viewport().update()

    def resizeEvent(self, event):
        self._update_view()
        super(SignalAnnotationView, self).resizeEvent(event)

    def _draw_background_grid(self):
        grid_pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)


        grid_spacing_horizontal = 100 * self.horizontal_scale_factor  # 水平缩放
        grid_spacing_vertical = 100  # 垂直方向保持不变

        scaled_width = (self.width() - 2 * self.margin_side) * self.horizontal_scale_factor
        scaled_height = self.height() - self.margin_bottom - self.margin_top

        for x in range(self.margin_side, int(self.margin_side + scaled_width), int(grid_spacing_horizontal)):
            line = QGraphicsLineItem(QLineF(x, self.margin_top, x, self.margin_top + scaled_height))
            line.setPen(grid_pen)
            self.scene.addItem(line)

        for y in range(self.margin_top, int(scaled_height + self.margin_top), int(grid_spacing_vertical)):
            line = QGraphicsLineItem(QLineF(self.margin_side, y, self.margin_side + scaled_width, y))
            line.setPen(grid_pen)
            self.scene.addItem(line)

    def _draw_time_ticks(self):
        """Draw time ticks on the X-axis based on the signal length and sampling rate."""
        tick_pen = QPen(Qt.black, 1)
        tick_length = 5

        # Calculate the total width based on horizontal scale factor
        scaled_width = (self.width() - 2 * self.margin_side) * self.horizontal_scale_factor

        # Determine the number of ticks based on the scaled width
        num_ticks = int(scaled_width / 100)  # Adjust the number of ticks; change 100 for finer/coarser ticks

        # Calculate the total duration of the signal in seconds
        time_duration = len(self.signal_data) / self.sampling_rate

        # Determine the time interval between ticks
        tick_interval = time_duration / num_ticks

        # Calculate tick positions along the X-axis
        tick_positions = np.linspace(self.margin_side, self.margin_side + scaled_width, num_ticks)

        for i, pos in enumerate(tick_positions):
            # Calculate the time value for each tick
            tick_time = i * tick_interval*1000
            # Draw the tick line
            self._draw_line(
                QLineF(pos, self.height() - self.margin_bottom, pos, self.height() - self.margin_bottom + tick_length),
                tick_pen)
            # Draw the time label
            self._draw_text(f"{int(tick_time)}", QPointF(pos - 10, self.height() - self.margin_bottom + 5))

    def _draw_axes(self):
        axis_pen = QPen(Qt.black, 2)
        tick_pen = QPen(Qt.black, 1)
        tick_length = 5

        scaled_width = (self.width() - 2 * self.margin_side) * self.horizontal_scale_factor
        scaled_height = self.height() - self.margin_bottom - self.margin_top

        # Draw Y axis and its labels
        self._draw_line(QLineF(self.margin_side, self.margin_top, self.margin_side, self.margin_top + scaled_height),
                        axis_pen)
        self._draw_line(QLineF(self.margin_side, self.margin_top + scaled_height, self.margin_side + scaled_width,
                               self.margin_top + scaled_height), axis_pen)

        # Draw labels for Y-axis
        self._draw_text("Amplitude", QPointF(10, self.margin_top + scaled_height / 2 - 20), -90)
        self._draw_text("Time (ms)", QPointF(self.margin_side + scaled_width / 2 - 30, self.height() - 30))

        # Draw Y-axis ticks and labels
        y_ticks = np.linspace(self.min_y, self.max_y, 5)
        for y in y_ticks:
            scene_y = self._to_scene_y_coords(y)
            self._draw_line(QLineF(self.margin_side - tick_length, scene_y, self.margin_side, scene_y), tick_pen)
            self._draw_text(f"{int(y):.1f}", QPointF(self.margin_side - 40, scene_y - 10))

        # Draw time ticks on the X-axis
        self._draw_time_ticks()  # 添加这一行来绘制时间刻度

    def _draw_line(self, line, pen):
        line_item = QGraphicsLineItem(line)
        line_item.setPen(pen)
        self.scene.addItem(line_item)

    def _draw_text(self, text, position, rotation=0):
        text_item = QGraphicsSimpleTextItem(text)
        text_item.setBrush(Qt.black)
        text_item.setPos(position)
        text_item.setRotation(rotation)
        self.scene.addItem(text_item)

    def _draw_signal(self):
        pen = QPen(Qt.blue, 2)
        previous_point = None

        total_width = (self.width() - self.margin_side * 2) * self.horizontal_scale_factor + self.margin_side * 2
        self.time_values = np.linspace(self.margin_side, total_width - self.margin_side, len(self.signal_data))

        for i, y in enumerate(self.signal_data):
            current_point = QPointF(self.time_values[i], self._to_scene_y_coords(y))
            if previous_point is not None:
                self._draw_line(QLineF(previous_point, current_point), pen)
            previous_point = current_point

    def _to_scene_y_coords(self, y):
        return self.margin_top + (1 - (y - self.min_y) / (self.max_y - self.min_y)) * (
                    self.height() - self.margin_bottom - self.margin_top)

    def _get_clamped_x(self, x):
        total_width = (self.width() - self.margin_side * 2) * self.horizontal_scale_factor + self.margin_side * 2
        return max(self.margin_side, min(x, total_width - self.margin_side))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_annotation:
            self.start_point = self.mapToScene(event.pos())
            clamped_x = self._get_clamped_x(self.start_point.x())
            top_left = QPointF(clamped_x, self.margin_top)
            bottom_right = QPointF(clamped_x, self.height() - self.margin_bottom)
            self.rect_item = QGraphicsRectItem(QRectF(top_left, bottom_right))
            self.rect_item.setPen(QPen(Qt.red, 2))
            self.rect_item.setBrush(QColor(255, 0, 0, 50))
            self.scene.addItem(self.rect_item)
            # 立即保存强引用，避免被垃圾回收
            self.annotation_items.append(weakref.ref(self.rect_item))

    def mouseMoveEvent(self, event):
        if self.rect_item and self.is_annotation:
            # 保证rect_item存在且在场景中
            if self.rect_item.scene() is None:
                return
            clamped_x = self._get_clamped_x(self.mapToScene(event.pos()).x())
            left_x = max(self.margin_side, self.start_point.x())
            total_width = (self.width() - self.margin_side * 2) * self.horizontal_scale_factor + self.margin_side * 2
            right_x = min(total_width - self.margin_side, clamped_x)
            if left_x < right_x:
                self.rect_item.setRect(
                    QRectF(QPointF(left_x, self.margin_top), QPointF(right_x, self.height() - self.margin_bottom)))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect_item and self.is_annotation:
            rect = self.rect_item.rect()
            if rect.width() < 2:
                self.scene.removeItem(self.rect_item)
                self.rect_item = None
                return
            self._finalize_annotation()
            # 删除后清理引用，避免使用已删除对象
            self.rect_item = None

    def _finalize_annotation(self):
        rect = self.rect_item.rect()
        start_idx = int(np.interp(rect.left(), self.time_values, np.arange(len(self.signal_data))))
        end_idx = int(np.interp(rect.right(), self.time_values, np.arange(len(self.signal_data))))
        if end_idx > start_idx:
            self.open_label_selection_dialog()
            self.scene.removeItem(self.rect_item)
            self.update_annotation(start_idx, end_idx, self.current_semantic_category,
                                   self.current_value_semantic_category, self.current_color_semantic_category)
            self.show_selected_annotation()

    def open_label_selection_dialog(self):
        annotationDialog = LabelManagementDialog()
        annotationDialog.mySignal.connect(self._get_annotation_label)
        annotationDialog.exec_()

    def _get_annotation_label(self, semantic_category=None, value_semantic_category=None, color_semantic_category=None):
        self.current_semantic_category = semantic_category
        self.current_value_semantic_category = value_semantic_category
        self.current_color_semantic_category = color_semantic_category

    def zoom_in(self):
        self.horizontal_scale_factor *= 2
        self._update_view()

    def zoom_out(self):
        self.horizontal_scale_factor /= 2
        self._update_view()


enabled_button_style = (
    "color: rgb(255, 255, 255);"
    "font: 25pt 'Bahnschrift Condensed';"
    "background-color: rgb(48, 105, 176);"
    "border-radius: 16px;"
)

disabled_button_style = (
    "color: rgb(0, 0, 0);"
    "font: 25pt 'Bahnschrift Condensed';"
    "background-color: rgb(169, 169, 197);"
    "border-radius: 16px;"
)


class FaultDetectionPage(QMainWindow, Ui_main):
    VERSION = '2.0.4'

    def __init__(self, parent=None):
        super(FaultDetectionPage, self).__init__()
        self.setupUi(self)
        if parent is not None:
            self.parent = parent
        self.center()
        self.init_ui_elements()
        self.refresh_comtrade_list()

    def center(self):
        # 获取主窗口的矩形几何信息
        qr = self.frameGeometry()

        # 获取屏幕中心点
        cp = QDesktopWidget().availableGeometry().center()

        # 将主窗口的矩形几何信息移动到屏幕中心
        qr.moveCenter(cp)

        # 移动窗口的位置到矩形的左上角，这样窗口就居中显示了
        self.move(qr.topLeft())

    def refresh_comtrade_list(self):

        # 获取原始文件和注释文件的唯一基本名称列表
        self.raw_files = get_sorted_unique_file_basenames(self.path_raw)
        self.ann_files = get_sorted_unique_file_basenames(self.path_ann)
        # 找到有效的注释文件并过滤出 fault_detection 不为空的文件
        highlighted_items = [
            filename for filename in self.raw_files
            if filename in self.ann_files
               and load_annotation(os.path.join(self.path_ann, filename)).get('fault_detection')
        ]
        # 更新列表小部件
        self.update_list_widget(listwidget=self.comtrade_list_widget, item_list=self.raw_files,
                                highlighted_items=highlighted_items)

    def init_ui_elements(self):
        self.root_project = get_parent_directory(levels_up=1)
        self.path_config = os.path.join(self.root_project, 'config')
        self.path_raw = os.path.join(self.root_project, 'tmp', 'raw')
        self.path_ann = os.path.join(self.root_project, 'tmp', 'ann')

        for path in [self.path_raw, self.path_ann]:
            os.makedirs(path, exist_ok=True)

        self.set_window_properties()
        self.comtrade_list_widget.itemClicked.connect(self.refresh_channel_list)
        self.channel_list_widget.itemClicked.connect(self.display_selected_channel_waveform)
        self._connect_button_signals()
        self._set_buttons_enabled(False, [self.button_annotate, self.button_confirm])
        self._set_buttons_enabled(True, [self.button_clear, self.button_return])

    def set_window_properties(self):
        self.setWindowIcon(QIcon(os.path.join(self.root_project, 'resource', 'WindowIcon.png')))
        version_label = QLabel(f"Version: {self.VERSION}")
        self.statusBar.addWidget(version_label)
        self.status_label = QLabel("")
        self.statusBar.addWidget(self.status_label)

    def _connect_button_signals(self):
        buttons_and_actions = {
            self.button_zoom_in: self.zoom_in,
            self.button_zoom_out: self.zoom_out,
            self.button_confirm: self.confirm,
            self.button_annotate: self.annotate,
            self.button_return: self.return_to_main,
            self.button_clear: self.clear
        }
        for button, action in buttons_and_actions.items():
            button.clicked.connect(action)

    def set_button_style(self, button, enable=True):
        button.setStyleSheet(enabled_button_style if enable else disabled_button_style)
        button.setDisabled(not enable)

    def annotate(self):
        # 禁用相关小部件
        self._set_widgets_enabled(False, [self.comtrade_list_widget, self.channel_list_widget])
        # 设置按钮状态
        self._set_buttons_enabled(False, [self.button_clear, self.button_annotate, self.button_return])
        self._set_buttons_enabled(True, [self.button_confirm, self.button_zoom_in, self.button_zoom_out])
        # 显示选中的注释
        self.signal_view.is_annotation = True

    def confirm(self):
        self._set_widgets_enabled(True, [self.comtrade_list_widget, self.channel_list_widget])
        self._set_buttons_enabled(True, [self.button_annotate, self.button_clear, self.button_return])
        self._set_buttons_enabled(False, [self.button_confirm, self.button_zoom_in, self.button_zoom_out])
        # 更新注释信息
        self.signal_view.is_annotation = False
        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        annotation["fault_detection"][self.selected_channel] = self.signal_view.selected_annotation
        write_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename), annotation)

        # 刷新频道注释
        self.refresh_channel_annotations()

    def zoom_in(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.zoom_in()


    def zoom_out(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.zoom_out()

    def clear(self):
        self._set_buttons_enabled(False, [self.button_annotate, self.button_confirm, self.button_return])
        warning_dialog = WarningDialog(self)
        self.status_label.setText('Warning: All Annotation Files Would Be Cleared')
        if warning_dialog.exec_() == QDialog.Accepted:
            self._clear_all_annotations()
            self.status_label.setText('Clear All Annotation Files Successfully')
            self.refresh_comtrade_list()
            self.channel_list_widget.clear()
        else:
            self.status_label.setText('Operation Canceled')
        self.set_button_style(self.button_return, True)
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.close()
            self.signal_view = None

    def display_selected_channel_waveform(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.close()
            self.signal_view = None
        self.selected_channel = self.channel_list_widget.currentItem().text()
        self.selected_comtrade_info["selected_channel"] = self.selected_channel
        self.selected_comtrade_info["selected_comtrade_filename"] = self.selected_comtrade_filename

        self.signal_view = SignalAnnotationView(parent=self.label_container,
                                                selected_comtrade_info=self.selected_comtrade_info)
        self.set_button_style(self.button_annotate, True)
        self.signal_view.show()

    def update_list_widget(self, listwidget, item_list, highlighted_items=[]):
        # 清空列表小部件
        listwidget.clear()
        # 将高亮项转换为集合以提高查找速度
        highlighted_set = set(highlighted_items)
        # 遍历项目列表，添加到小部件中
        for item in item_list:
            item_widget = QListWidgetItem(item)
            # 如果该项在高亮项集合中，则设置背景颜色
            if item in highlighted_set:
                item_widget.setBackground(QColor("#cfd8e3"))
            listwidget.addItem(item_widget)
        # 对小部件中的项目进行排序
        listwidget.sortItems()

    def closeEvent(self, event):
        self.deleteLater()

    def refresh_channel_list(self):
        self.set_button_style(self.button_annotate, False)
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.close()
            self.signal_view = None
        self.selected_comtrade_filename = self.comtrade_list_widget.currentItem().text()
        self.selected_comtrade_info = get_info_comtrade(path_raw=self.path_raw, path_ann=self.path_ann,
                                                        selected_comtrade_filename=self.selected_comtrade_filename)

        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        annotated_channels = list(annotation['fault_detection'].keys())
        self.analog_channel_ids = self.selected_comtrade_info["channels_info"]['analog_channel_ids']
        self.update_list_widget(listwidget=self.channel_list_widget, item_list=self.analog_channel_ids,
                                highlighted_items=annotated_channels)

    def refresh_channel_annotations(self):
        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))

        analog_channel_ids = self.selected_comtrade_info["channels_info"]["analog_channel_ids"]
        annotated_channels = list(annotation['fault_detection'].keys())
        self.update_list_widget(listwidget=self.channel_list_widget, item_list=analog_channel_ids,
                                highlighted_items=annotated_channels)

    def _set_buttons_enabled(self, enable, buttons):
        for button in buttons:
            self.set_button_style(button, enable)

    def _set_widgets_enabled(self, enabled, widgets):
        for widget in widgets:
            widget.setEnabled(enabled)

    def _clear_all_annotations(self):
        """清空所有注释文件的 'fault_detection' 字段"""
        ann_files = get_sorted_unique_file_basenames(self.path_ann)
        for filename in ann_files:
            annotation = load_annotation(os.path.join(self.path_ann, filename))
            annotation['fault_detection'] = {}
            write_annotation(os.path.join(self.path_ann, filename), annotation)

    def return_to_main(self):
        self.close()
        try:
            self.parent.show()
        except:
            logger.error('缺少父类')


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    MainWindow = FaultDetectionPage()
    MainWindow.show()
    app.exec_()
