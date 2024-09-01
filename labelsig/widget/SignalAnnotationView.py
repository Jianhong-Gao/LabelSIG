import sys
import numpy as np
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QLineF
from PyQt5.QtGui import QPen, QColor, QPainter,QTransform
from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsLineItem,
    QGraphicsRectItem, QApplication, QGraphicsSimpleTextItem, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
)


class SignalAnnotationView(QGraphicsView):
    annotationAdded = pyqtSignal(int, int, str)  # Signal emitted when a new annotation is added with start and end indices

    def __init__(self, signal_data, sampling_rate, parent=None):
        super(SignalAnnotationView, self).__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Disable view caching
        self.setCacheMode(QGraphicsView.CacheNone)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.signal_data = signal_data
        self.sampling_rate = sampling_rate
        self.start_point = None
        self.rect_item = None

        self.scale_factor = 1.0  # Initial scale factor
        self.setSizePolicy(900, 500)  # Fixed view size

        self.margin_side = 50  # Space for both left and right margins
        self.margin_bottom = 30  # Space for x-axis

        # Calculate min and max values for y-axis scaling
        self.min_y = np.min(self.signal_data)
        self.max_y = np.max(self.signal_data)

        self._draw_background_grid()
        self._draw_axes()
        self._draw_signal()



    def _draw_background_grid(self):
        """Draws the background grid on the scene."""
        grid_pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)

        # Adjust grid spacing based on scale factor
        grid_spacing = 100 * self.scale_factor

        # Scaled dimensions
        scaled_width = (self.width() - 2 * self.margin_side) * self.scale_factor
        scaled_height = self.height() - self.margin_bottom

        # Draw vertical grid lines
        for x in range(self.margin_side, int(self.margin_side + scaled_width), int(grid_spacing)):
            line = QGraphicsLineItem(QLineF(x, 0, x, scaled_height))
            line.setPen(grid_pen)
            self.scene.addItem(line)

        # Draw horizontal grid lines
        for y in range(0, int(scaled_height), int(grid_spacing)):
            line = QGraphicsLineItem(QLineF(self.margin_side, y, self.margin_side + scaled_width, y))
            line.setPen(grid_pen)
            self.scene.addItem(line)

    def _draw_axes(self):
        """Draws the x and y axes with ticks."""
        axis_pen = QPen(Qt.black, 2)
        tick_length = 5  # Length of the tick marks
        tick_pen = QPen(Qt.black, 1)

        # Calculate scaled dimensions
        scaled_width = (self.width() - 2 * self.margin_side) * self.scale_factor
        scaled_height = self.height() - self.margin_bottom

        # Draw y-axis
        y_axis = QGraphicsLineItem(QLineF(self.margin_side, 0, self.margin_side, scaled_height))
        y_axis.setPen(axis_pen)
        self.scene.addItem(y_axis)

        # Draw x-axis
        x_axis = QGraphicsLineItem(
            QLineF(self.margin_side, scaled_height, self.margin_side + scaled_width, scaled_height))
        x_axis.setPen(axis_pen)
        self.scene.addItem(x_axis)

        # Draw top border (right above the signal area)
        top_border = QGraphicsLineItem(QLineF(self.margin_side, 0, self.margin_side + scaled_width, 0))
        top_border.setPen(axis_pen)
        self.scene.addItem(top_border)

        # Draw right border (right edge of the signal area)
        right_border = QGraphicsLineItem(
            QLineF(self.margin_side + scaled_width, 0, self.margin_side + scaled_width, scaled_height))
        right_border.setPen(axis_pen)
        self.scene.addItem(right_border)

        # Add labels to the axes
        y_label = QGraphicsSimpleTextItem("Amplitude")
        y_label.setRotation(-90)
        y_label.setPos(10, scaled_height / 2 - 20)
        self.scene.addItem(y_label)

        x_label = QGraphicsSimpleTextItem("Time (s)")
        x_label.setPos(self.margin_side + scaled_width / 2 - 30, self.height() - 20)
        self.scene.addItem(x_label)

        # Add y-axis ticks and labels
        y_ticks = np.linspace(self.min_y, self.max_y, 5)  # Define tick positions based on signal amplitude range
        for y in y_ticks:
            scene_y = self._to_scene_y_coords(y)
            tick = QGraphicsLineItem(QLineF(self.margin_side - tick_length, scene_y, self.margin_side, scene_y))
            tick.setPen(tick_pen)
            self.scene.addItem(tick)

            tick_label = QGraphicsSimpleTextItem(f"{y:.1f}")
            tick_label.setPos(self.margin_side - 40, scene_y - 10)
            self.scene.addItem(tick_label)

        # Add x-axis ticks and labels, considering the right margin and scale factor
        num_ticks = 6  # Number of ticks to display
        tick_positions = np.linspace(self.margin_side, self.margin_side + scaled_width, num_ticks)

        for i, pos in enumerate(tick_positions):
            tick = QGraphicsLineItem(QLineF(pos, scaled_height, pos, scaled_height + tick_length))
            tick.setPen(tick_pen)
            self.scene.addItem(tick)

            tick_label = QGraphicsSimpleTextItem(f"{i / (num_ticks - 1):.1f}")
            tick_label.setPos(pos - 10, scaled_height + 5)
            self.scene.addItem(tick_label)

    def _draw_signal(self):
        """Draws the signal on the scene."""
        pen = QPen(Qt.blue, 2)
        previous_point = None

        # Map the time values to the full width of the view including the right margin, adjusted by scale_factor
        total_width = (self.width() - self.margin_side * 2) * self.scale_factor+self.margin_side * 2

        self.time_values = np.linspace(self.margin_side, total_width - self.margin_side, len(self.signal_data))

        for i, y in enumerate(self.signal_data):
            x = self.time_values[i]
            current_point = QPointF(x, self._to_scene_y_coords(y))
            if previous_point is not None:
                line = QGraphicsLineItem(QLineF(previous_point, current_point))
                line.setPen(pen)
                self.scene.addItem(line)
            previous_point = current_point

    def _to_scene_y_coords(self, y):
        """Converts y data coordinates to scene y coordinates."""
        # Map the signal amplitude to the height of the view
        return ((y - self.min_y) / (self.max_y - self.min_y)) * (self.height() - self.margin_bottom)

    def _get_clamped_x(self, x):
        """Ensure the x-coordinate stays within the signal range."""
        total_width = (self.width() - self.margin_side * 2) * self.scale_factor + self.margin_side * 2

        return max(self.margin_side, min(x, total_width - self.margin_side))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = self.mapToScene(event.pos())
            clamped_x = self._get_clamped_x(self.start_point.x())
            # Create the rectangle regardless of initial position, but clamp to signal bounds
            top_left = QPointF(clamped_x, 0)  # Fix top edge at the top of the signal area
            bottom_right = QPointF(clamped_x, self.height() - self.margin_bottom)  # Fix bottom edge at the bottom of the signal area

            self.rect_item = QGraphicsRectItem(QRectF(top_left, bottom_right))
            self.rect_item.setPen(QPen(Qt.red, 2))
            self.rect_item.setBrush(QColor(255, 0, 0, 50))
            self.scene.addItem(self.rect_item)

    def mouseMoveEvent(self, event):
        if self.rect_item:
            end_point = self.mapToScene(event.pos())
            clamped_x = self._get_clamped_x(end_point.x())

            # Update the rectangle to be within signal bounds, regardless of initial point
            left_x = max(self.margin_side, self.start_point.x())
            total_width = (self.width() - self.margin_side * 2) * self.scale_factor + self.margin_side * 2
            right_x = min(total_width-self.margin_side * 1, clamped_x)

            if left_x<right_x:
                self.rect_item.setRect(QRectF(QPointF(left_x, 0), QPointF(right_x, self.height() - self.margin_bottom)))
                self.rect_item.setVisible(True)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect_item:
            rect = self.rect_item.rect()

            # Check if the user actually dragged to create a rectangle with a non-zero width

            if abs(rect.width()) < 2:  # Adjust this threshold as needed

                self.scene.removeItem(self.rect_item)
                self.rect_item = None
                return

            self._finalize_annotation()

    def _finalize_annotation(self):
        rect = self.rect_item.rect()

        # Calculate the start and end indices based on the selected range
        start_idx = int(np.interp(rect.left(), self.time_values, np.arange(len(self.signal_data))))
        end_idx = int(np.interp(rect.right(), self.time_values, np.arange(len(self.signal_data))))

        if end_idx > start_idx:

            label_text = self._get_annotation_label()
            text_item = QGraphicsSimpleTextItem(label_text)
            text_item.setBrush(Qt.black)
            text_item.setPos(rect.topLeft())
            self.scene.addItem(text_item)

            # Emit the annotationAdded signal with the start and end indices
            self.annotationAdded.emit(start_idx, end_idx, label_text)
            # self.scene.removeItem(self.rect_item)
            self.rect_item = None



    def _get_annotation_label(self):
        # In a real application, this could open a dialog to get user input
        # For simplicity, let's just return a fixed label for this example
        return "Fault"

    def zoom_in(self):
        self.scale_factor *= 1.2
        self._redraw_scene()

    def zoom_out(self):
        self.scale_factor /= 1.2
        self._redraw_scene()

    def _redraw_scene(self):
        self.scene.clear()
        self._draw_background_grid()
        self._draw_axes()
        self._draw_signal()
        self.viewport().update()  # 强制刷新视图







class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Signal Annotation Tool")

        # Generate a sinusoidal signal
        self.sampling_rate = 1000  # Hz
        t = np.linspace(0, 1, self.sampling_rate, endpoint=False)
        signal = np.sin(2 * np.pi * 20 * t)

        self.view = SignalAnnotationView(signal, self.sampling_rate)
        self.view.annotationAdded.connect(self.on_annotation_added)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.view)

        # Add zoom in and zoom out buttons
        button_layout = QHBoxLayout()
        zoom_in_button = QPushButton("Zoom In")
        zoom_out_button = QPushButton("Zoom Out")

        zoom_in_button.clicked.connect(self.view.zoom_in)
        zoom_out_button.clicked.connect(self.view.zoom_out)

        button_layout.addWidget(zoom_in_button)
        button_layout.addWidget(zoom_out_button)

        layout.addLayout(button_layout)
        self.setCentralWidget(central_widget)

    def on_annotation_added(self, start_idx, end_idx, label):
        print(f"Annotation added: {label} from index {start_idx} to {end_idx}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
