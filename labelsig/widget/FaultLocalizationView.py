import os
import numpy as np
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QLineF
from PyQt5.QtGui import QPen, QColor, QPainter,QTransform,QIcon, QImage, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsLineItem,QMessageBox,QDialog,
    QGraphicsRectItem, QApplication, QGraphicsSimpleTextItem, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton,QLabel, QScrollArea, QListWidgetItem
)
from qtpy.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QDialog,
    QVBoxLayout, QRadioButton, QDialogButtonBox
)
from labelsig.widget.LabelManagementView import LabelManagementDialog

from labelsig.widget.CountdownWarningView import WarningDialog
from labelsig.ui_generated.ui_fault_localization_view import Ui_main

from labelsig.utils.utils_general import get_annotation_ranges,get_sorted_unique_file_basenames,get_parent_directory,differentiate_voltage
from labelsig.utils.utils_annotation import write_annotation,load_annotation
from labelsig.utils.utils_comtrade import get_info_comtrade
import threading

class SignalAnnotationView(QGraphicsView):

    def __init__(self, parent=None, selected_comtrade_info=None, reference_signal=[]):
        super(SignalAnnotationView, self).__init__(parent)
        self.scale_factor = 1 / 1.2  # Initial scale factor
        self.margin_side = 50  # Space for both left and right margins
        self.margin_top = 20  # Space for x-axis
        self.margin_bottom = 50  # Space for x-axis
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

        if reference_signal:
            self.signal_data_reference = np.array(self.channels_info['analog_channel_values'][
                                                      self.channels_info['analog_channel_ids'].index(
                                                          reference_signal[0])
                                                  ]) * 1000
            self.signal_data_reference = differentiate_voltage(voltage=self.signal_data_reference)
            self.min_dU = np.min(self.signal_data_reference)
            self.max_dU = np.max(self.signal_data_reference)
        else:
            self.signal_data_reference = None
            self.min_dU = self.max_dU = 0  # Initialize to zero or some default

        self.sampling_rate = selected_comtrade_info['sampling_rate']

        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        self.selected_annotation = annotation["fault_localization"]
        self.rect_item = None

        self.min_y = np.min(self.signal_data)
        self.max_y = np.max(self.signal_data)

        self._draw_background_grid()
        self._draw_axes()
        self._draw_signal()


        self._initialize_scene()

    def _initialize_scene(self):
        """Initializes the background grid, axes, and signal."""
        self._draw_background_grid()
        self._draw_axes()
        self._draw_signal()
        if self.signal_data_reference is not None:
            self._draw_reference_signal()  # Reference signal



    def update_annotation(self, start_idx, end_idx, semantic_category, value_semantic_category, color_semantic_category):
        length_signal = len(self.signal_data)
        self.selected_annotation.setdefault("Semantic-Category", {})[value_semantic_category] = {
            "label": semantic_category,
            "color": color_semantic_category
        }
        self.selected_annotation[semantic_category] = self._create_sequence(length_signal, start_idx, end_idx)
        self.selected_annotation.setdefault("Comprehensive-Category", [0] * length_signal)
        for i in range(start_idx, end_idx + 1):
            self.selected_annotation["Comprehensive-Category"][i] = value_semantic_category

    def _create_sequence(self, length_signal, start_idx, end_idx):
        sequence = [0] * length_signal
        for i in range(start_idx, end_idx + 1):
            sequence[i] = 1
        return sequence

    def _update_view(self):
        self.scene.clear()
        self._initialize_scene()
        self.centerOn(self.mapToScene(self.viewport().rect().center()))

        self.viewport().update()

    def resizeEvent(self, event):
        self._update_view()
        super(SignalAnnotationView, self).resizeEvent(event)

    def _draw_background_grid(self):
        grid_pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        grid_spacing = 100 * self.scale_factor

        scaled_width = (self.width() - 2 * self.margin_side) * self.scale_factor
        scaled_height = self.height() - self.margin_bottom - self.margin_top

        for x in range(self.margin_side, int(self.margin_side + scaled_width), int(grid_spacing)):
            line = QGraphicsLineItem(QLineF(x, self.margin_top, x, self.margin_top + scaled_height))
            line.setPen(grid_pen)
            self.scene.addItem(line)

        for y in range(self.margin_top, int(scaled_height + self.margin_top), int(grid_spacing)):
            line = QGraphicsLineItem(QLineF(self.margin_side, y, self.margin_side + scaled_width, y))
            line.setPen(grid_pen)
            self.scene.addItem(line)

    def _draw_axes(self):
        axis_pen = QPen(Qt.black, 2)
        tick_pen = QPen(Qt.black, 1)
        tick_length = 5

        scaled_width = (self.width() - 2 * self.margin_side) * self.scale_factor
        scaled_height = self.height() - self.margin_bottom - self.margin_top

        # 绘制原始信号的 x 和 y 轴
        self._draw_line(QLineF(self.margin_side, self.margin_top, self.margin_side, self.margin_top + scaled_height),
                        axis_pen)
        self._draw_line(QLineF(self.margin_side, self.margin_top + scaled_height, self.margin_side + scaled_width,
                               self.margin_top + scaled_height), axis_pen)

        # 绘制参考信号的第二个 y 轴
        right_y_axis = QLineF(self.margin_side + scaled_width, self.margin_top, self.margin_side + scaled_width,
                              self.margin_top + scaled_height)
        self._draw_line(right_y_axis, axis_pen)

        # 绘制原始信号的标签和刻度
        self._draw_text("Amplitude", QPointF(10, self.margin_top + scaled_height / 2 - 20), -90)
        self._draw_text("Time (s)", QPointF(self.margin_side + scaled_width / 2 - 30, self.height() - 30))

        y_ticks = np.linspace(self.min_y, self.max_y, 5)
        for y in y_ticks:
            scene_y = self._to_scene_y_coords(y, self.min_y, self.max_y)
            self._draw_line(QLineF(self.margin_side - tick_length, scene_y, self.margin_side, scene_y), tick_pen)
            self._draw_text(f"{y:.1f}", QPointF(self.margin_side - 40, scene_y - 10))

        # 绘制参考信号的标签和刻度
        self._draw_text("dU", QPointF(self.margin_side + scaled_width + 20, self.margin_top + scaled_height / 2 - 20),
                        -90)
        dU_ticks = np.linspace(self.min_dU, self.max_dU, 5)
        for dU in dU_ticks:
            scene_y = self._to_scene_y_coords(dU, self.min_dU, self.max_dU)
            self._draw_line(
                QLineF(self.margin_side + scaled_width, scene_y, self.margin_side + scaled_width + tick_length,
                       scene_y), tick_pen)
            self._draw_text(f"{dU:.1f}", QPointF(self.margin_side + scaled_width + 10, scene_y - 10))

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
        """Draws the original signal on the scene."""
        pen = QPen(Qt.blue, 2)
        previous_point = None

        total_width = (self.width() - self.margin_side * 2) * self.scale_factor + self.margin_side * 2
        self.time_values = np.linspace(self.margin_side, total_width - self.margin_side, len(self.signal_data))

        for i, y in enumerate(self.signal_data):
            current_point = QPointF(self.time_values[i], self._to_scene_y_coords(y, self.min_y, self.max_y))
            if previous_point is not None:
                self._draw_line(QLineF(previous_point, current_point), pen)
            previous_point = current_point

    def _draw_reference_signal(self):
        """Draws the reference signal on the scene if it exists."""
        if self.signal_data_reference is None:
            return

        pen = QPen(Qt.red, 2)  # Use a different color for the reference signal
        previous_point = None

        for i, dU in enumerate(self.signal_data_reference):
            current_point = QPointF(self.time_values[i], self._to_scene_y_coords(dU, self.min_dU, self.max_dU))
            if previous_point is not None:
                self._draw_line(QLineF(previous_point, current_point), pen)
            previous_point = current_point

    def _to_scene_y_coords(self, y, min_val, max_val):
        """Converts a y value to scene coordinates based on the given min and max values."""
        if max_val == min_val:
            return self.margin_top + (self.height() - self.margin_bottom - self.margin_top) / 2  # Center it vertically
        return self.margin_top + ((y - min_val) / (max_val - min_val)) * (
                    self.height() - self.margin_bottom - self.margin_top)

    def _get_clamped_x(self, x):
        total_width = (self.width() - self.margin_side * 2) * self.scale_factor + self.margin_side * 2
        return max(self.margin_side, min(x, total_width - self.margin_side))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_annotation:
            self.start_point = self.mapToScene(event.pos())
            clamped_x = self._get_clamped_x(self.start_point.x())
            top_left = QPointF(clamped_x, 0)
            bottom_right = QPointF(clamped_x, self.height() - self.margin_bottom)
            self.rect_item = QGraphicsRectItem(QRectF(top_left, bottom_right))
            self.rect_item.setPen(QPen(Qt.red, 2))
            self.rect_item.setBrush(QColor(255, 0, 0, 50))
            self.scene.addItem(self.rect_item)

    def mouseMoveEvent(self, event):
        if self.rect_item and self.is_annotation:
            clamped_x = self._get_clamped_x(self.mapToScene(event.pos()).x())
            left_x = max(self.margin_side, self.start_point.x())
            total_width = (self.width() - self.margin_side * 2) * self.scale_factor + self.margin_side * 2
            right_x = min(total_width - self.margin_side, clamped_x)
            if left_x < right_x:
                self.rect_item.setRect(QRectF(QPointF(left_x, self.margin_top), QPointF(right_x, self.height() - self.margin_bottom)))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect_item and self.is_annotation:
            rect = self.rect_item.rect()
            if rect.width() < 2:
                self.scene.removeItem(self.rect_item)
                self.rect_item = None
                return



    def open_label_selection_dialog(self):
        annotationDialog = LabelManagementDialog()
        annotationDialog.mySignal.connect(self._get_annotation_label)
        annotationDialog.exec_()

    def _get_annotation_label(self, semantic_category=None, value_semantic_category=None, color_semantic_category=None):
        self.current_semantic_category = semantic_category
        self.current_value_semantic_category = value_semantic_category
        self.current_color_semantic_category = color_semantic_category

    def zoom_in(self):
        self.scale_factor *= 1.2
        self._update_view()

    def zoom_out(self):
        self.scale_factor /= 1.2
        self._update_view()

    def _redraw_scene(self):
        self.scene.clear()
        self._initialize_scene()
        self.viewport().update()  # 强制刷新视图



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


class FaultLocalizationPage(QMainWindow, Ui_main):
    VERSION='2.0.0'
    def __init__(self,parent=None):
        super(FaultLocalizationPage, self).__init__()
        self.setupUi(self)
        if parent is not None:
            self.parent=parent
        self.init_ui_elements()
        self.refresh_comtrade_list()

    def refresh_list(self, listwidget, base_path, highlight_func):
        filenames = get_sorted_unique_file_basenames(base_path)
        highlighted_items = [filename for filename in filenames if highlight_func(filename)]
        self.update_list_widget(listwidget=listwidget, item_list=filenames, highlighted_items=highlighted_items)

    def refresh_comtrade_list(self):
        self.ann_files = get_sorted_unique_file_basenames(self.path_ann)
        self.refresh_list(self.comtrade_list_widget, self.path_raw,
                          lambda f: f in self.ann_files and load_annotation(os.path.join(self.path_ann, f)).get(
                              'fault_localization'))


    def init_ui_elements(self):
        self.root_project = get_parent_directory(levels_up=1)
        self.path_raw = os.path.join(self.root_project,'tmp', 'raw')
        self.path_ann = os.path.join(self.root_project, 'tmp','ann')

        for path in [self.path_raw, self.path_ann]:
            os.makedirs(path, exist_ok=True)

        self.set_window_properties()
        self.comtrade_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.comtrade_list_widget.itemClicked.connect(self.refresh_channel_list)
        self.channel_list_widget.itemClicked.connect(self.display_selected_channel_waveform)
        self._connect_button_signals()
        self._set_buttons_enabled(False, [self.button_confirm])
        self._set_buttons_enabled(True, [self.button_clear, self.button_return,self.button_zoom_in,self.button_zoom_out])


    def set_window_properties(self):
        self.setWindowIcon(QIcon(os.path.join(self.root_project, 'resource', 'WindowIcon.png')))
        version_label = QLabel(f"Version: {self.VERSION}")
        self.statusBar.addWidget(version_label)
        self.status_label = QLabel("")
        self.statusBar.addWidget(self.status_label)



    def _connect_button_signals(self):
        buttons_and_actions = {
            self.button_zoom_in:self.zoom_in,
            self.button_zoom_out:self.zoom_out,
            self.button_confirm: self.confirm,
            self.button_mark: self.mark_channel,
            self.button_return: self.return_to_main,
            self.button_clear: self.clear
        }
        for button, action in buttons_and_actions.items():
            button.clicked.connect(action)

    def mark_channel(self):
        self._set_buttons_enabled(True, [self.button_confirm])
        current_item = self.channel_list_widget.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "Warning", "No channel selected.")
            return

        current_channel_name = current_item.text()
        choice = self.prompt_channel_marking(current_channel_name)


        actions = {
            'unmark': self.unmark_channel,
            'reference': self.set_reference_signal,
            'fault': self.mark_fault_line,
            'sound': self.mark_sound_line,
            'ambiguous': self.mark_ambiguous_line,
        }

        if choice in actions:
            actions[choice](current_channel_name)

        self.refresh_listwidget_channels(
            listwidget=self.channel_list_widget,
            item_list=self.signal_view.channels_info['analog_channel_ids'],
            reference_signal=self.reference_signal,
            fault_lines=self.fault_lines,
            sound_lines=self.sound_lines,
            ambiguous_lines=self.ambiguous_lines
        )

    def refresh_listwidget_channels(self, listwidget, item_list,
                                    reference_signal=[],
                                    fault_lines=[],
                                    sound_lines=[],
                                    ambiguous_lines=[]):
        listwidget.clear()

        # Define a color map
        color_map = {
            'reference_signal': QColor("#DDDDBB"),
            'fault_lines': QColor("#CD5C5C"),
            'sound_lines': QColor("#8FBC8F"),
            'ambiguous_lines': QColor("#A9A9A9")
        }

        for item in item_list:
            item_widget = QListWidgetItem(item)
            # Set background color based on item list
            if item in reference_signal:
                item_widget.setBackground(color_map['reference_signal'])
            elif item in fault_lines:
                item_widget.setBackground(color_map['fault_lines'])
            elif item in sound_lines:
                item_widget.setBackground(color_map['sound_lines'])
            elif item in ambiguous_lines:
                item_widget.setBackground(color_map['ambiguous_lines'])
            listwidget.addItem(item_widget)

        listwidget.sortItems()

    def prompt_channel_marking(self, channel_name):
        dlg = QDialog(self)
        dlg.setWindowTitle("Mark Channel")

        layout = QVBoxLayout()

        # 使用字典来管理按钮
        radio_buttons = {
            'reference': QRadioButton("Reference Signal"),
            'fault': QRadioButton("Fault Line"),
            'sound': QRadioButton("Sound Line"),
            'ambiguous': QRadioButton("Ambiguous Line"),
            'unmark': QRadioButton("Unmark Selection"),
        }

        # 添加按钮到布局
        for button in radio_buttons.values():
            layout.addWidget(button)

        # 设置按钮状态和默认选中状态
        self._initialize_channel_marking(channel_name, radio_buttons)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)
        layout.addWidget(button_box)

        dlg.setLayout(layout)

        if dlg.exec_() == QDialog.Accepted:
            for key, button in radio_buttons.items():
                if button.isChecked():
                    return key
        return None

    def _initialize_channel_marking(self, channel_name, radio_buttons):
        """初始化信道标记的按钮状态和默认选中状态"""
        button_states = {
            'reference': channel_name in self.reference_signal,
            'fault': channel_name in self.fault_lines,
            'sound': channel_name in self.sound_lines,
            'ambiguous': channel_name in self.ambiguous_lines,
        }

        # 设置默认选中状态
        for key, selected in button_states.items():
            if selected:
                radio_buttons[key].setChecked(True)
                # 禁用其他选项
                for other_key in radio_buttons:
                    if other_key != key and other_key != 'unmark':
                        radio_buttons[other_key].setDisabled(True)
                return

        # 如果没有选中的，则默认选择 unmark
        radio_buttons['unmark'].setChecked(True)

    def update_channel_marking(self, channel_name, action):
        """通用的信道标记和更新逻辑"""
        # 定义一个映射，指明每种标记对应的列表
        categories = {
            'reference': self.reference_signal,
            'fault': self.fault_lines,
            'sound': self.sound_lines,
            'ambiguous': self.ambiguous_lines,
        }

        # 先从所有列表中移除该信道
        for key, lst in categories.items():
            if channel_name in lst:
                lst.remove(channel_name)

        # 如果不是取消标记操作，则添加到对应的列表中
        if action != 'unmark':
            categories[action].append(channel_name)

        # 更新状态标签
        self.status_label.setText(f"{action.capitalize()} signal marked as '{channel_name}'")

    def unmark_channel(self, channel_name):
        self.update_channel_marking(channel_name, 'unmark')

    def set_reference_signal(self, channel_name):
        self.update_channel_marking(channel_name, 'reference')

    def mark_fault_line(self, channel_name):
        self.update_channel_marking(channel_name, 'fault')

    def mark_sound_line(self, channel_name):
        self.update_channel_marking(channel_name, 'sound')

    def mark_ambiguous_line(self, channel_name):
        self.update_channel_marking(channel_name, 'ambiguous')

    def set_button_style(self, button, enable=True):
        button.setStyleSheet(enabled_button_style if enable else disabled_button_style)
        button.setDisabled(not enable)

    def confirm(self):
        self._set_widgets_enabled(True, [self.comtrade_list_widget, self.channel_list_widget])
        self._set_buttons_enabled(True, [ self.button_clear, self.button_return])
        self._set_buttons_enabled(False, [ self.button_confirm])
        # 更新注释信息
        self.signal_view.is_annotation = False
        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        annotation["fault_localization"] = self.signal_view.selected_annotation
        write_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename), annotation)
        self.confirm_and_write_file()


    def zoom_in(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.zoom_in()
            self.button_zoom_out.clicked.connect(self.signal_view.zoom_out)

    def zoom_out(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.zoom_out()


    def clear(self):
        self._set_buttons_enabled(False, [  self.button_confirm, self.button_return])
        warning_dialog = WarningDialog(self)
        self.status_label.setText('Warning: All Annotation Files Would Be Cleared')
        if warning_dialog.exec_() == QDialog.Accepted:
            self._clear_all_annotations()
            self.status_label.setText('Clear All Annotation Files Successfully')
            self.refresh_comtrade_list()
        else:
            self.status_label.setText('Operation Canceled')
        self.set_button_style(self.button_return, True)
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.close()
            self.signal_view = None
        self.refresh_channel_annotations()
        self.refresh_channel_list()


    def display_selected_channel_waveform(self):
        if hasattr(self, 'signal_view') and self.signal_view is not None:
            self.signal_view.close()
            self.signal_view=None
        self.selected_channel = self.channel_list_widget.currentItem().text()
        self.selected_comtrade_info["selected_channel"]=self.selected_channel
        self.selected_comtrade_info["selected_comtrade_filename"]=self.selected_comtrade_filename

        self.signal_view = SignalAnnotationView(parent=self.label_container,selected_comtrade_info=self.selected_comtrade_info,reference_signal=self.reference_signal)

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
        self.selected_comtrade_filename = self.comtrade_list_widget.currentItem().text()
        self.selected_comtrade_info = get_info_comtrade(
            path_raw=self.path_raw,
            path_ann=self.path_ann,
            selected_comtrade_filename=self.selected_comtrade_filename
        )

        annotation_whole = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        self.annotation=annotation_whole["fault_localization"]
        self.reference_signal = self.annotation.setdefault('reference_signal', [])
        self.fault_lines = self.annotation.setdefault('fault_lines', [])
        self.sound_lines = self.annotation.setdefault('sound_lines', [])
        self.ambiguous_lines = self.annotation.setdefault('ambiguous_lines', [])

        self.refresh_listwidget_channels(
            listwidget=self.channel_list_widget,
            item_list=self.selected_comtrade_info["channels_info"]['analog_channel_ids'],
            reference_signal=self.reference_signal,
            fault_lines=self.fault_lines,
            sound_lines=self.sound_lines,
            ambiguous_lines=self.ambiguous_lines
        )


    def refresh_channel_annotations(self):
        annotation_whole = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))

        analog_channel_ids=self.selected_comtrade_info["channels_info"]["analog_channel_ids"]
        annotated_channels = list(annotation_whole['fault_localization'].keys())
        self.update_list_widget(listwidget=self.channel_list_widget, item_list=analog_channel_ids, highlighted_items=annotated_channels)

    def _set_buttons_enabled(self, enable, buttons):
        for button in buttons:
            self.set_button_style(button, enable)

    def _set_widgets_enabled(self, enabled, widgets):
        for widget in widgets:
            widget.setEnabled(enabled)

    def _clear_all_annotations(self):
        """清空所有注释文件的 'fault_localization' 字段"""
        ann_files = get_sorted_unique_file_basenames(self.path_ann)
        for filename in ann_files:
            annotation = load_annotation(os.path.join(self.path_ann, filename))
            annotation['fault_localization'] = {}
            write_annotation(os.path.join(self.path_ann, filename), annotation)

    def confirm_and_write_file(self):
        self.annotation['reference_signal']=self.reference_signal
        self.annotation['fault_lines']=self.fault_lines
        self.annotation['sound_lines']=self.sound_lines
        self.annotation['ambiguous_lines']=self.ambiguous_lines
        annotation = load_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename))
        annotation["fault_localization"] = self.annotation
        flag_save_annotation=write_annotation(os.path.join(self.path_ann, self.selected_comtrade_filename), annotation)
        self.refresh_channel_list()
        if flag_save_annotation:
            self.status_label.setText('Annotation saved successfully!')

    def return_to_main(self):
        self.close()
        self.parent.show()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    MainWindow = FaultLocalizationPage()
    MainWindow.show()
    app.exec_()
