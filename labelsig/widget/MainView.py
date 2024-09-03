import logging
import os
import shutil
import stat
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from multiprocessing import cpu_count

from PyQt5.QtCore import *
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QIntValidator
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTreeWidgetItem, QTableWidget,QDesktopWidget,
    QPushButton, QLineEdit, QLabel, QCheckBox, QRadioButton, QWidget,
    QHBoxLayout, QSizePolicy, QToolTip, QMessageBox, QHeaderView
)

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

from labelsig.ui_generated.ui_main_view import Ui_MainWindow
from labelsig.utils.utils_annotation import write_annotation, load_annotation, get_annotation_info
from labelsig.utils.utils_comtrade import get_info_comtrade, update_comtrade, delete_specific_channels
from labelsig.utils.utils_general import get_sorted_unique_file_basenames, get_parent_directory
from labelsig.widget.ChannelSelectionView import ChannelSelectionDialog
from labelsig.widget.FaultDetectionView import FaultDetectionPage
from labelsig.widget.FaultIdentificationView import FaultIdentificationPage
from labelsig.widget.FaultLocalizationView import FaultLocalizationPage
from labelsig.widget.HelpView import HelpDialog


style_enable = "color: rgb(255, 255, 255);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(48, 105, 176);border-radius: 16px;"
style_disable = "color: rgb(0, 0, 0);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(169, 169, 197);border-radius: 16px;"


def process_file(file_name, path_raw, path_ann):
    """Process a single file, intended to be run in a separate process."""
    file_start_time = time.time()
    annotation_file_base_path = os.path.join(path_ann, file_name)

    annotation = load_annotation(annotation_file_base_path)
    if annotation["sampling_rate"] is None:
        selected_comtrade_info = get_info_comtrade(path_raw, path_ann, file_name)
        annotation = get_annotation_info(selected_comtrade_info, annotation)
        write_annotation(os.path.join(path_ann, file_name), annotation)
    full_load_time = time.time() - file_start_time
    return file_name, annotation, full_load_time


class LoadFolderThread(QThread):
    signal_finished = pyqtSignal(str, dict)
    signal_duplicate_files = pyqtSignal(list)  # Signal to inform the main thread about duplicate files.
    signal_update_label = pyqtSignal(str)

    def __init__(self, mainwindow, external_folder_path):
        super().__init__()
        self.main_window = mainwindow
        self.root_project_path = get_parent_directory(levels_up=1)
        self.internal_raw_path = os.path.join(self.root_project_path, 'tmp', 'raw')
        self.internal_ann_path = os.path.join(self.root_project_path, 'tmp', 'ann')
        self.external_folder_path = external_folder_path

    def run(self):
        raw_folder_path = os.path.join(self.external_folder_path, 'raw')
        ann_folder_path = os.path.join(self.external_folder_path, 'ann')

        if os.path.exists(raw_folder_path) and os.path.exists(ann_folder_path):
            duplicate_files = self.import_files(raw_folder_path, self.internal_raw_path) + \
                              self.import_files(ann_folder_path, self.internal_ann_path)
            if duplicate_files:
                self.signal_duplicate_files.emit(duplicate_files)
        elif os.path.exists(raw_folder_path):
            # Only raw folder exists
            self.import_files(raw_folder_path, self.internal_raw_path)
        else:
            self.import_other_files()
        start_time = time.time()
        dict_info = self.get_dict()
        self.signal_finished.emit(self.external_folder_path, dict_info)

    def import_files(self, external_folder_path, internal_folder_path):
        if not os.path.exists(internal_folder_path):
            os.makedirs(internal_folder_path)

        duplicates = []
        for file_name in os.listdir(external_folder_path):
            external_file_path = os.path.join(external_folder_path, file_name)
            internal_file_path = os.path.join(internal_folder_path, file_name)
            if os.path.exists(internal_file_path):
                duplicates.append(file_name)
            else:
                shutil.copy(external_file_path, internal_folder_path)
        return duplicates

    def import_other_files(self):
        if not os.path.exists(self.internal_raw_path):
            os.makedirs(self.internal_raw_path)

        existing_files_base_names = {os.path.splitext(file_name)[0] for file_name in os.listdir(self.internal_raw_path)
                                     if os.path.isfile(os.path.join(self.internal_raw_path, file_name))}
        all_files = os.listdir(self.external_folder_path)
        total_files = len(all_files)
        progress_bar_length = 30  # Length of the progress bar

        for index, file_name in enumerate(all_files):
            progress_ratio = (index + 1) / total_files
            filled_length = int(progress_bar_length * progress_ratio)

            progress_bar = '█' * filled_length + '-' * (progress_bar_length - filled_length)
            progress_text = f"{index + 1}/{total_files}"
            update_info = f"[{progress_bar}] {progress_text} 正在导入: {file_name}"
            self.signal_update_label.emit(update_info)

            external_file_path = os.path.join(self.external_folder_path, file_name)
            if os.path.isfile(external_file_path):
                base_name = os.path.splitext(file_name)[0]
                if base_name not in existing_files_base_names:
                    shutil.copy(external_file_path, self.internal_raw_path)
        self.signal_update_label.emit(f"[{'█' * progress_bar_length}] All files imported,waiting for processing!")

    def get_dict(self, bar_length=30):
        dict_info = {}
        total_files = len(get_sorted_unique_file_basenames(self.internal_raw_path))
        if total_files == 0:
            self.signal_update_label.emit("[{}] No files found!".format('█' * bar_length))
            return dict_info

        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            future_to_file = {
                executor.submit(process_file, file_name, self.internal_raw_path, self.internal_ann_path): file_name
                for file_name in get_sorted_unique_file_basenames(self.internal_raw_path)}
            processing_times = []

            for future in as_completed(future_to_file):
                file_name = future_to_file[future]
                try:
                    file_name, annotation, full_load_time = future.result()
                    dict_info[file_name] = annotation
                    processing_times.append(full_load_time)

                    if self.signal_update_label:
                        max_time_per_file = max(processing_times)
                        idx = len(dict_info)
                        estimated_remaining_time = max_time_per_file * (total_files - idx)
                        progress_ratio = idx / total_files
                        bar_length = 30
                        filled_length = int(bar_length * progress_ratio)
                        bar = '█' * filled_length + '-' * (bar_length - filled_length)
                        mins, secs = divmod(estimated_remaining_time, 60)
                        progress_text = (f"[{bar}] ({idx}/{total_files}) \n"
                                         f"Processing file: {file_name} \n"
                                         f"Estimated remaining time: {int(mins)} minutes {int(secs)} seconds")
                        self.signal_update_label.emit(progress_text)
                except Exception as e:
                    logger.error(f"File processing failed for {file_name}: {e}")

        self.signal_update_label.emit("[{}] All files processed!".format('█' * bar_length))
        return dict_info


class FileOpenThread(QThread):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        root_project = get_parent_directory(levels_up=1)
        exe_path = os.path.join(root_project, 'CAAP2008X', 'CAAP2008X.exe')  # 构建CAAP2008X.exe的绝对路径
        cfg_file_path = os.path.join(root_project, self.file_path + '.cfg')  # 构建配置文件的绝对路径
        command = f'start "{exe_path}" "{cfg_file_path}"'
        os.system(command)


class StatusWidget(QWidget):
    statusChanged = pyqtSignal(str)  # 增加此信号

    def __init__(self, status_labels=None, parent=None):
        super(StatusWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.radio_buttons = {}
        for label in status_labels:
            rb = QRadioButton(label, self)
            rb.toggled.connect(self._emit_status_changed)
            self.layout.addWidget(rb)
            self.radio_buttons[label] = rb

    def _emit_status_changed(self, checked):
        if checked:
            sender = self.sender()
            self.statusChanged.emit(sender.text())

    def set_status(self, status):
        if status in self.radio_buttons:
            self.radio_buttons[status].setChecked(True)
        else:
            self.clear_status()

    def clear_status(self):
        for rb in self.radio_buttons.values():
            rb.setChecked(False)

    def current_status(self):
        """Retrieve the currently selected status."""
        for label, rb in self.radio_buttons.items():
            if rb.isChecked():
                return label
        return None


class CustomTableWidget(QTableWidget):
    signal_update_label = pyqtSignal(str)
    HEADERS = ["Filename", "Sampling rate(Hz)", "Total Sample Points", "Total Duration(ms)", "Trigger Index",
               "Function"]

    def __init__(self, parent=None):
        super(CustomTableWidget, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)  # 移除边距
        self.verticalHeader().setDefaultSectionSize(20)  # 设置行高
        self.horizontalHeader().setStretchLastSection(True)  # 让最后一列自动拉伸填充剩余空间
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # 让列宽根据内容自动调整
        self.root_project = get_parent_directory(levels_up=1)
        self.path_raw = os.path.join(self.root_project, "tmp", 'raw')
        self.path_ann = os.path.join(self.root_project, "tmp", 'ann')
        self.setFont(QFont('Arial', 10))  # 调整字体大小
        self.button_mappers = {
            "open": QSignalMapper(self),
            "clip": QSignalMapper(self),
            "unlock": QSignalMapper(self),
            "confirm": QSignalMapper(self)
        }
        self.connect_button_signals()

    def connect_button_signals(self):
        """Connect signals for button mappers."""
        self.button_mappers["open"].mapped[int].connect(self.open_file)
        self.button_mappers["clip"].mapped[int].connect(self.clip_channel)
        self.button_mappers["unlock"].mapped[int].connect(self.unlock_row)
        self.button_mappers["confirm"].mapped[int].connect(self.confirm_edit)

    def create_button(self, label, row, mapper):
        """Create a button and connect it to a signal mapper."""
        button = QPushButton(label)
        mapper.setMapping(button, row)
        button.clicked.connect(mapper.map)
        return button

    def _create_filename_cell(self, file_name):
        """Create a widget containing a checkbox and label for the filename."""
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox(self)
        label = QLabel(file_name, self)
        layout.addWidget(checkbox)
        layout.addWidget(label)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget

    def _add_line_edit(self, trigger_index):
        """Create a line edit for trigger index with validation."""
        line_edit = QLineEdit(str(trigger_index))
        line_edit.setValidator(QIntValidator(1, 99999))
        line_edit.setAlignment(Qt.AlignCenter)
        return line_edit

    def _add_buttons_to_function_column(self, row):
        """Add function buttons to a row."""
        container_widget = QWidget()
        layout = QHBoxLayout(container_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.create_button('Open File', row, self.button_mappers["open"]))
        layout.addWidget(self.create_button('Clip Channel', row, self.button_mappers["clip"]))
        layout.addWidget(self.create_button('Unlock', row, self.button_mappers["unlock"]))
        layout.addWidget(self.create_button('Confirm', row, self.button_mappers["confirm"]))

        container_widget.setLayout(layout)
        return container_widget

    def populate_table_from_dict(self, dict_info):
        """Populate the table with data from dict_info."""
        self.clearContents()
        self.setRowCount(len(dict_info))
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)

        for row, (file_name, annotation) in enumerate(dict_info.items()):
            self._populate_row_with_data(row, file_name, annotation)

    def _populate_row_with_data(self, row, file_name, annotation):
        """Populate a single row with the provided data."""

        sampling_rate = int(annotation["sampling_rate"])
        total_sample_points = annotation["total_samples"]
        total_duration = int((total_sample_points / sampling_rate) * 1000)
        trigger_index = int(annotation['trigger_index'])

        # Filename cell
        self.setCellWidget(row, 0, self._create_filename_cell(file_name))

        # Center-align for columns 2, 3, 4
        sampling_rate_label = QLabel(str(sampling_rate))
        sampling_rate_label.setAlignment(Qt.AlignCenter)
        self.setCellWidget(row, 1, sampling_rate_label)

        total_sample_points_label = QLabel(f"{total_sample_points}")
        total_sample_points_label.setAlignment(Qt.AlignCenter)
        self.setCellWidget(row, 2, total_sample_points_label)

        total_duration_label = QLabel(f"{total_duration}")
        total_duration_label.setAlignment(Qt.AlignCenter)
        self.setCellWidget(row, 3, total_duration_label)

        # Trigger Index column
        self.setCellWidget(row, 4, self._add_line_edit(trigger_index))

        # Function buttons
        self.setCellWidget(row, 5, self._add_buttons_to_function_column(row))

    def _get_sender_row(self):
        """Get the row of the widget that triggered the current slot."""
        sender_widget = self.sender()
        if sender_widget:
            for row in range(self.rowCount()):
                for col in range(self.columnCount()):
                    widget = self.cellWidget(row, col)
                    if widget and sender_widget.isAncestorOf(widget):
                        return row
        return None

    def open_file(self, row):
        """Open the file associated with the specified row."""
        self._execute_file_action(row, "open")

    def clip_channel(self, row):
        """Clip channels for the file associated with the specified row."""
        self._execute_file_action(row, "clip")

    def unlock_row(self, row):
        """Unlock the specified row for editing."""
        self._set_row_widget_enabled(row, True)

    def confirm_edit(self, row):
        trigger_index_widget = self.cellWidget(row, 4)
        trigger_index = trigger_index_widget.text()
        trigger_index = str(int(trigger_index))
        trigger_index_widget.setEnabled(False)

        def run():
            orig_name = self._get_filename_from_row(row)
            annotation = load_annotation(os.path.join(self.path_ann, orig_name))
            annotation['trigger_index'] = trigger_index
            write_annotation(os.path.join(self.path_ann, orig_name), annotation)
            update_comtrade(trigger_index=int(trigger_index), path_raw=self.path_raw, orig_name=orig_name)

        # 创建并启动线程
        edit_thread = threading.Thread(target=run)
        edit_thread.start()

    def _execute_file_action(self, row, action):
        """Helper method to execute a file-related action."""
        orig_name = self._get_filename_from_row(row)
        file_path = os.path.join(self.path_raw, orig_name)
        if action == "open":
            self.file_open_thread = FileOpenThread(file_path)
            self.file_open_thread.start()
            self.signal_update_label.emit(f'File {orig_name} opened')

        elif action == "clip":
            dialog = ChannelSelectionDialog(self, file_name=orig_name, mode='Clip')
            if dialog.exec_():
                channels_info = dialog.selected_channels
                delete_specific_channels(path_raw=self.path_raw, orig_name=orig_name,
                                         analog_channel_ids=channels_info['analog_channel_ids'],
                                         status_channel_ids=channels_info['status_channel_ids'])

    def _get_filename_from_row(self, row):
        """Helper method to retrieve the filename from a given row."""
        widget = self.cellWidget(row, 0)
        label = widget.findChild(QLabel)
        return label.text() if label else ""

    def _set_row_widget_enabled(self, row, enabled=True):
        """Enable or disable editing for widgets in the specified row."""
        for col in range(self.columnCount()):
            widget = self.cellWidget(row, col)
            if widget:
                widget.setEnabled(enabled)

    def _delete_file(self, file_path):
        """Delete the specified file."""
        try:
            if not os.access(file_path, os.W_OK):
                os.chmod(file_path, stat.S_IWRITE)
            os.remove(file_path)

        except PermissionError:
            logger.error(f"Permission denied: {file_path}")

    def get_checked_files_with_rows(self):
        """Return a list of tuples containing the checked filenames and their row numbers."""
        checked_files_with_rows = []
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 0)  # 获取第一列的widget
            checkbox = widget.findChild(QCheckBox)
            label = widget.findChild(QLabel)
            if checkbox and checkbox.isChecked():  # 如果复选框被选中
                checked_files_with_rows.append((label.text(), row))  # 将文件名和行号添加到结果列表中
        return checked_files_with_rows

    def delete_row(self, row):
        if row is None:
            return
        widget = self.cellWidget(row, 0)  # 获取第 0 列的组件
        if widget is None:
            logger.info(f"第 {row} 行的组件为空。")
            return
        label = widget.findChild(QLabel)  # 从组件中查找QLabel
        if label is None:
            logger.info(f"无法在第 {row} 行的组件中找到标签。")
            return
        file_name = label.text()
        for ext in ['.cfg', '.dat']:
            file_path = os.path.join(self.parent().path_raw, file_name + ext)
            self._delete_file(file_path)
        for ext in ['.ann']:
            file_path = os.path.join(self.parent().path_ann, file_name + ext)
            self._delete_file(file_path)

        self.removeRow(row)
        self.signal_update_label.emit(f'文件 {file_name} 及其标注文件已被删除')


class FileProcessorThread(QThread):
    flag_enable_button = pyqtSignal(bool)
    update_progress = pyqtSignal(str)  # Signal to update progress
    finished = pyqtSignal(dict)  # Signal to indicate completion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_project = get_parent_directory(levels_up=1)
        self.path_raw = os.path.join(self.root_project, "tmp", "raw")
        self.path_ann = os.path.join(self.root_project, "tmp", "ann")

    def get_sorted_unique_file_basenames(self, path):
        return get_sorted_unique_file_basenames(path)

    def run(self):
        self.flag_enable_button.emit(False)
        dict_info = {}
        total_files = len(self.get_sorted_unique_file_basenames(self.path_raw))
        processing_times = []

        if total_files == 0:
            self.update_progress.emit("[{}] No files found!".format('█' * 50))
            self.finished.emit(dict_info)
            self.flag_enable_button.emit(True)
            return

        for idx, file_name in enumerate(self.get_sorted_unique_file_basenames(self.path_raw)):
            file_start_time = time.time()
            start_time = time.time()
            file_name, annotation, full_load_time = process_file(file_name, self.path_raw, self.path_ann, )
            dict_info[file_name] = annotation
            file_end_time = time.time()
            processing_times.append(file_end_time - file_start_time)
            if self.update_progress:
                max_time_per_file = max(processing_times)
                estimated_remaining_time = max_time_per_file * (total_files - idx - 1)
                progress_ratio = (idx + 1) / total_files
                bar_length = 30
                filled_length = int(bar_length * progress_ratio)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                mins, secs = divmod(estimated_remaining_time, 60)
                progress_text = (f"[{bar}] ({idx + 1}/{total_files}) \n"
                                 f"Processing file: {file_name} \n"
                                 f"Estimated remaining time: {int(mins)} minutes {int(secs)} seconds")
                self.update_progress.emit(progress_text)
        self.update_progress.emit("[{}] All files processed!".format('█' * bar_length))


        self.finished.emit(dict_info)
        self.flag_enable_button.emit(True)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.version = '2.0.4'
        self.center()
        self.init_ui_elements()
        self.connect_signals()

    def center(self):
        # 获取主窗口的矩形几何信息
        qr = self.frameGeometry()

        # 获取屏幕中心点
        cp = QDesktopWidget().availableGeometry().center()

        # 将主窗口的矩形几何信息移动到屏幕中心
        qr.moveCenter(cp)

        # 移动窗口的位置到矩形的左上角，这样窗口就居中显示了
        self.move(qr.topLeft())

    def init_ui_elements(self):

        self.reconfigure_table_files()
        self.setWindowTitle("LabelSIG")
        self.statusBar().showMessage(f"Version: {self.version}")
        self.root_project = get_parent_directory(levels_up=1)

        self.path_raw = os.path.join(self.root_project, "tmp", "raw")
        self.path_ann = os.path.join(self.root_project, "tmp", "ann")
        os.makedirs(self.path_raw, exist_ok=True)
        os.makedirs(self.path_ann, exist_ok=True)
        self.setup_label_info()

        path_icon = os.path.join(self.root_project, 'resource', 'WindowIcon.png')
        self.setWindowIcon(QIcon(path_icon))

        self.file_Processor_thread = FileProcessorThread()
        self.file_Processor_thread.flag_enable_button.connect(self.call_enable_buttons)
        self.file_Processor_thread.update_progress.connect(self.update_label_info)
        self.file_Processor_thread.finished.connect(self.display_files_in_table)
        self.file_Processor_thread.start()

    def call_enable_buttons(self, flag_enable_button):
        if flag_enable_button:
            self.enable_buttons()
        else:
            self.disable_buttons()

    def set_button_style(self, button, enable=True):
        if enable:
            button.setStyleSheet(style_enable)
        else:
            button.setStyleSheet(style_disable)
        button.setDisabled(not enable)

    def disable_buttons(self):
        self.set_button_style(self.button_load_folder, enable=False)
        self.set_button_style(self.button_output, enable=False)
        self.set_button_style(self.button_delete, enable=False)
        self.set_button_style(self.button_help, enable=False)
        self.set_button_style(self.button_clear_cache, enable=False)
        self.set_button_style(self.button_fault_detection, enable=False)
        self.set_button_style(self.button_fault_identification, enable=False)
        self.set_button_style(self.button_fault_localization, enable=False)

    def enable_buttons(self):
        self.set_button_style(self.button_load_folder, enable=True)
        self.set_button_style(self.button_output, enable=True)
        self.set_button_style(self.button_delete, enable=True)
        self.set_button_style(self.button_help, enable=True)
        self.set_button_style(self.button_clear_cache, enable=True)
        self.set_button_style(self.button_fault_detection, enable=True)
        self.set_button_style(self.button_fault_identification, enable=True)
        self.set_button_style(self.button_fault_localization, enable=True)

    def add_items(self, parent, elements):
        for key, value in elements.items():
            item = QTreeWidgetItem(parent)
            if isinstance(value, dict):
                item.setText(0, key)
                item.setText(1, str(value.get('total', '')))
                self.add_items(item, value)
            else:
                item.setText(0, key)
                item.setText(1, str(value))

    def setup_label_info(self):
        self.label_info.setWordWrap(True)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_info.setSizePolicy(size_policy)

    def connect_signals(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        # 设置 QToolTip 的样式
        self.button_load_folder.clicked.connect(self.load_folder)
        self.button_load_folder.setToolTip('Load a folder containing raw data files')
        self.button_output.clicked.connect(self.output_files)
        self.button_output.setToolTip('Output raw data files and corresponding annotation files')
        self.button_delete.clicked.connect(self.delete_checked_files)
        self.button_delete.setToolTip('Delete selected files and corresponding annotation files')
        self.button_help.clicked.connect(self.show_help)
        self.button_help.setToolTip('Show help')
        self.button_fault_detection.clicked.connect(self.task_fault_detection)
        self.button_fault_detection.setToolTip('Single-category Point-wise Semantic Annotation')
        self.button_fault_identification.clicked.connect(self.task_fault_identification)
        self.button_fault_identification.setToolTip('Multi-category Point-wise Semantic Annotation')
        self.button_fault_localization.clicked.connect(self.task_fault_localization)
        self.button_fault_localization.setToolTip('Channel-wise Annotation')
        self.button_clear_cache.clicked.connect(self.clear_cache)
        self.button_clear_cache.setToolTip('Clear cache')

    def task_fault_detection(self):
        self.hide()
        self.widget_fault_detection = FaultDetectionPage(parent=self)
        self.widget_fault_detection.show()

    def task_fault_identification(self):
        self.hide()
        self.widget_fault_identification = FaultIdentificationPage(parent=self)
        self.widget_fault_identification.show()

    def task_fault_localization(self):
        self.hide()
        self.widget_fault_localization = FaultLocalizationPage(parent=self)
        self.widget_fault_localization.show()

    # 使用线程执行文件clear_cache操作
    def clear_cache(self):
        shutil.rmtree(self.path_raw)
        shutil.rmtree(self.path_ann)
        os.makedirs(self.path_raw, exist_ok=True)
        os.makedirs(self.path_ann, exist_ok=True)
        self.file_Processor_thread.start()

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def output_files(self):
        self.disable_buttons()
        checked_files_with_rows = self.table_files.get_checked_files_with_rows()
        files_to_output = [filename for filename, _ in checked_files_with_rows]
        if len(files_to_output) == 0:
            reply = QMessageBox.question(self, '批量导出', '没有选中的文件. 是否要进行批量导出?', QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.No:
                self.enable_buttons()
                return
            files_to_output = {os.path.splitext(f)[0] for f in os.listdir(self.path_raw)}
        files_to_output_ann = {os.path.splitext(f)[0] + '.ann' for f in files_to_output}
        # 检查每个文件是否有对应的标注文件
        for file_name in files_to_output_ann:
            corresponding_annotation = os.path.join(self.path_ann, file_name)
            if not os.path.exists(corresponding_annotation):
                warning_message = QMessageBox(self)
                warning_message.setIcon(QMessageBox.Warning)
                warning_message.setText(f"文件 {file_name} 没有对应的标注文件，无法导出。")
                warning_message.setWindowTitle("警告")
                warning_message.setStandardButtons(QMessageBox.Ok)
                warning_message.exec_()
                return
        destination_dir = QFileDialog.getExistingDirectory(self, '选择存储文件夹', get_parent_directory(levels_up=3))
        if not destination_dir:
            self.enable_buttons()
            return  # 用户取消了选择

        current_datetime = datetime.now().strftime('%y%m%d%H%M')
        new_folder_name = f'LabelSIG_{current_datetime}'
        new_folder_path = os.path.join(destination_dir, new_folder_name)
        os.makedirs(new_folder_path, exist_ok=True)  # 创建新文件夹

        # 创建raw和annotation子文件夹
        raw_folder_path = os.path.join(new_folder_path, 'raw')
        annotation_folder_path = os.path.join(new_folder_path, 'ann')
        os.makedirs(raw_folder_path, exist_ok=True)
        os.makedirs(annotation_folder_path, exist_ok=True)
        processing_times = []  # 记录每个文件的处理时间
        total_files = len(files_to_output)
        bar_length = 50
        for idx, file_name in enumerate(files_to_output):
            file_start_time = time.time()
            src_file_raw = os.path.join(self.path_raw, file_name + '.cfg')
            dst_file_raw = os.path.join(raw_folder_path, file_name + '.cfg')
            shutil.copy(src_file_raw, dst_file_raw)  # 复制数据文件到raw子文件夹
            src_file_raw = os.path.join(self.path_raw, file_name + '.dat')
            dst_file_raw = os.path.join(raw_folder_path, file_name + '.dat')
            shutil.copy(src_file_raw, dst_file_raw)  # 复制数据文件到raw子文件夹
            # 复制标注文件到annotation子文件夹
            file_name_ann = os.path.splitext(file_name)[0] + '.ann'
            src_file_annotation = os.path.join(self.path_ann, file_name_ann)
            dst_file_annotation = os.path.join(annotation_folder_path, file_name_ann)
            shutil.copy(src_file_annotation, dst_file_annotation)
            file_end_time = time.time()
            processing_times.append(file_end_time - file_start_time)
            if self.label_info is not None:
                max_time_per_file = max(processing_times)
                # 这里我们考虑最大处理时间来预估剩余时间
                estimated_remaining_time = max_time_per_file * (total_files - idx - 1)
                progress_ratio = (idx + 1) / total_files
                filled_length = int(bar_length * progress_ratio)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                mins, secs = divmod(estimated_remaining_time, 60)
                self.label_info.setText(
                    f"[{bar}] ({idx + 1}/{total_files}) \n正在处理文件: {file_name} \n预计剩余等待时间: {int(mins)}分{int(secs)}秒")
        self.label_info.setText(f'文件已输出到 {new_folder_path}')  # 显示文件输出信息
        self.enable_buttons()

    def reconfigure_table_files(self):
        pos = self.table_files.pos()
        size = self.table_files.size()
        self.table_files.setParent(None)

        self.table_files = CustomTableWidget(self)
        self.table_files.signal_update_label.connect(self.update_label_info)
        self.table_files.move(pos)
        self.table_files.resize(size)

    def load_folder(self):
        script_dir = os.path.dirname(__file__)
        relative_path = '../../../'
        initial_path = os.path.abspath(os.path.join(script_dir, relative_path))
        external_folder_path = QFileDialog.getExistingDirectory(self, 'Open file', initial_path)

        if external_folder_path:
            self.label_info.setText(f'外部文件夹 {external_folder_path} 正在加载')
            self.disable_buttons()
            self.load_thread = LoadFolderThread(mainwindow=self, external_folder_path=external_folder_path)
            self.load_thread.signal_finished.connect(self.on_load_folder_finished)
            self.load_thread.signal_update_label.connect(self.update_label_info)
            self.load_thread.start()

    def update_label_info(self, update_info):
        self.label_info.setText(update_info)

    def on_load_folder_finished(self, external_folder_path, dict_info):
        self.display_files_in_table(dict_info)
        self.enable_buttons()

    def display_files_in_table(self, dict_info):
        self.table_files.populate_table_from_dict(dict_info)

    def delete_checked_files(self):
        checked_files_with_rows = self.table_files.get_checked_files_with_rows()

        if not checked_files_with_rows:
            QMessageBox.information(self, "Info", "没有选中的文件.")
            return
        # 提取文件名用于确认删除操作
        filenames_to_delete = [filename for filename, _ in checked_files_with_rows]
        msg_content = "\n".join(filenames_to_delete)
        reply = QMessageBox.question(self, 'Confirm Delete',
                                     f"确定要删除以下文件吗?\n{msg_content}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for _, row in reversed(checked_files_with_rows):
                self.table_files.delete_row(row)
            self.label_info.setText(f'选中的文件已被删除')


if __name__ == '__main__':


    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    MainWindow = MainWindow()
    MainWindow.show()
    app.exec_()
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # app = QApplication(sys.argv)
    # login = MainWindow()
    # login.show()
    # sys.exit(app.exec_())
