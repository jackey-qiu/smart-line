from PyQt5.QtGui import QPaintEvent, QPainter, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
import numpy as np
import time
from ...widgets.shapes.shape_container import (
    rectangle,
    shapeComposite,
    isocelesTriangle,
    buildTools,
)
from ....util.util import findMainWindow

data={'shape': ['REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC', 'REC'], 'alignment_shapes': [[0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [17, 18], [18, 19], [19, 20], [20, 21], [21, 22], [22, 23], [23, 24], [24, 25], [25, 26], [26, 27]], 'alignment': [['right', 'left'], ['right', 'left'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top'], ['bottom', 'top']], 'connection': [[0, 1], [1, 2], [1, 3], [1, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [0, 26], [0, 27]], 'gap': [40, 40, 10, 10, 90, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]}
data['names'] = [each+str(i) for i, each in enumerate(data['shape'])]
data['states'] = ['ready'] * len(data['shape'])

class chainSynopticView(QWidget):
    FILL_READY = {"brush": {"color": (0, 0, 255)}}
    FILL_PREPARED = {"brush": {"color": (250, 255, 0)}}
    FILL_STARTED = {"brush": {"color": (0, 255, 0)}}
    FILL_TRIGGER = {"brush": {"color": (50, 50, 50)}}
    FILL_TRIGGER_2 = {"brush": {"color": (90, 90, 90)}}
    FILL_FAILED = {"brush": {"color": (255, 50, 0)}}
    FILL_PAUSED = {"brush": {"color": (255, 0, 255)}}
    CLICKED_SHAPE = {"pen": {"color": (255, 255, 0), "width": 3, "ls": "SolidLine"}}
    NONCLICKED_SHAPE = {"pen": {"color": (255, 0, 0), "width": 3, "ls": "SolidLine"}}

    def __init__(
        self,
        parent=None,
        padding_vertical=20,
        padding_hor=60,
        block_width=180,
        block_height=20,
    ) -> None:
        super().__init__(parent=parent)
        self.set_parent()
        self.padding_vertical = padding_vertical
        self.padding_hor = padding_hor
        self.block_width = block_width
        self.block_height = block_height
        self._data = []
        self.composite_chain = None
        self.composite_shapes = []
        self.legend_shapes = []
        self.last_clicked_shape = None
        self.name_list = []
        self.set_data()
        self.set_parent()
        self.trigger_style_used = self.FILL_TRIGGER

    def set_data(self, data = data):
        self._data = data
        self.build_legend_shapes()
        self.build_shapes()
        self.update()

    def update_state(self, state_data):
        name = state_data['name']
        state = state_data['state']
        which = self._data['names'].index(name)
        self._data['states'][which] = state
        self.build_legend_shapes()
        self.build_shapes()
        self.update()

    def build_legend_shapes(self):
        height = 20
        width = int(self.padding_hor * 0.8)
        x = int(self.padding_hor * 0.1)
        shape_ready = rectangle(dim=[x, self.padding_vertical, width, height])
        shape_ready.decoration = self.FILL_READY
        shape_ready.labels = {
            "text": ["ready"],
            "anchor": ["center"],
            "orientation": ["horizontal"],
        }
        shape_prepared = rectangle(
            dim=[
                x,
                (self.padding_vertical + self.block_height) * 1 + self.padding_vertical,
                width,
                height,
            ]
        )
        shape_prepared.decoration = self.FILL_PREPARED
        shape_prepared.labels = {
            "text": ["prepare"],
            "anchor": ["center"],
            "orientation": ["horizontal"],
        }
        shape_prepared.text_decoration = {"text_color": (0, 0, 0)}
        shape_started = rectangle(
            dim=[
                x,
                (self.padding_vertical + self.block_height) * 2 + self.padding_vertical,
                width,
                height,
            ]
        )
        shape_started.decoration = self.FILL_STARTED
        shape_started.labels = {
            "text": ["start"],
            "anchor": ["center"],
            "orientation": ["horizontal"],
        }
        shape_started.text_decoration = {"text_color": (0, 0, 0)}
        shape_trigger = rectangle(
            dim=[
                x,
                (self.padding_vertical + self.block_height) * 3 + self.padding_vertical,
                width,
                height,
            ]
        )
        shape_trigger.decoration = self.FILL_TRIGGER
        shape_trigger.labels = {
            "text": ["trigger"],
            "anchor": ["center"],
            "orientation": ["horizontal"],
        }
        self.legend_shapes = [
            shape_ready,
            shape_prepared,
            shape_started,
            shape_trigger,
        ]

    def build_shapes(self):
        self.composite_shapes = []
        if len(self._data) == 0:
            self.shapes = []
            return
        for i in range(len(self._data['names'])):
            unique_id = self._data['names'][i]
            state = self._data['states'][i]

            shape = rectangle(
                dim=[
                    self.padding_hor,
                    self.padding_vertical,
                    self.block_width,
                    self.block_height,
                ],
                rotation_center=None,
                transformation={
                    "rotate": 0,
                    "translate": np.array([0, 0]),
                    "scale": 1,
                    "translate_offset": np.array([0, 0]),
                },
            )
            shape.set_clickable(True)

            if state == "ready":
                shape.decoration = self.FILL_READY
                shape.decoration_cursor_off = self.FILL_READY
                shape.decoration_cursor_on = self.FILL_READY
            elif state == "prepared":
                shape.decoration = self.FILL_PREPARED
                shape.decoration_cursor_off = self.FILL_PREPARED
                shape.decoration_cursor_on = self.FILL_PREPARED
                shape.text_decoration = {"text_color": (0, 0, 0)}
            elif state == "started":
                shape.decoration = self.FILL_STARTED
                shape.decoration_cursor_off = self.FILL_STARTED
                shape.decoration_cursor_on = self.FILL_STARTED
                shape.text_decoration = {"text_color": (0, 0, 0)}
            elif state == "trigger":
                if self.trigger_style_used == self.FILL_TRIGGER:
                    shape.decoration = self.FILL_TRIGGER
                    shape.decoration_cursor_off = self.FILL_TRIGGER
                    shape.decoration_cursor_on = self.FILL_TRIGGER
                    self.trigger_style_used = self.FILL_TRIGGER_2
                elif self.trigger_style_used == self.FILL_TRIGGER_2:
                    shape.decoration = self.FILL_TRIGGER_2
                    shape.decoration_cursor_off = self.FILL_TRIGGER_2
                    shape.decoration_cursor_on = self.FILL_TRIGGER_2
                    self.trigger_style_used = self.FILL_TRIGGER
            shape.labels = {
                "text": [f"{unique_id}"],
                "anchor": ["center"],
                "orientation": ["horizontal"],
            }
            setattr(shape, "unique_id", unique_id)
            self.composite_shapes.append(shape)
        self.build_composite_object()
        self.update()

    def build_composite_object(self):
        self.lines_bw_composite = []
        #ix_with_line_conn = [i for i in range(len(self._data['alignment'])) if self._data['alignment'][i]==['right','left']]
        self.composite_chain = shapeComposite(
            shapes=self.composite_shapes,
            anchor_args=[4 for i in range(len(self.composite_shapes))],
            alignment_pattern={
                "shapes": self._data['alignment_shapes'],
                "anchors": self._data['alignment'],
                "gaps": self._data['gap'],
                "ref_anchors": [[None, None]]*len(self._data['gap']),
                'gaps_absolute': True,
            },

            connection_pattern={
                "shapes": self._data['connection'],
                "anchors": [['right', 'left']]*len(self._data['connection']),
                "connect_types": [True]*len(self._data['connection']) 
            },
        )

    def set_parent(self):
        self.parent = findMainWindow()

    def paintEvent(self, a0) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing, True)
        qp.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # for each in self.shapes:
        for each in [self.composite_chain]:
            for line in each.lines:
                qp.setPen(QPen(Qt.green, 2, Qt.SolidLine))
                for i in range(len(line) - 1):
                    pts = list(line[i]) + list(line[i + 1])
                    qp.drawLine(*pts)

        for each in [self.composite_chain]:
            for each_shape in each.shapes:
                qp.resetTransform()
                each_shape.paint(qp)
        for each_shape in self.legend_shapes:
            qp.resetTransform()
            each_shape.paint(qp)
        qp.end()

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        # if self.parent !=None:
        self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each in [self.composite_chain]:
            for each_shape in each.shapes:
                each_shape.cursor_pos_checker(event.x(), event.y())
        self.update()

    def mousePressEvent(self, event):
        return
        x, y = event.x(), event.y()
        shapes_under_cursor = []
        for each in [self.composite_chain]:
            for each_shape in each.shapes:
                if each_shape.check_pos(x, y) and event.button() == Qt.LeftButton:
                    # queue_id = each_shape.labels['text'][0].rsplit(':')[0]
                    unique_id = each_shape.unique_id
                    self.parent.update_task_from_server(unique_id)
                    if self.parent != None:
                        self.parent.statusbar.showMessage(
                            f"Clicked job id is: {unique_id}"
                        )
                    if self.last_clicked_shape == None:
                        # self.last_clicked_shape.decoration_cursor_off = self.NONCLICKED_SHAPE
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = (
                            self.CLICKED_SHAPE
                        )
                    else:
                        self.last_clicked_shape.decoration_cursor_off = (
                            self.NONCLICKED_SHAPE
                        )
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = (
                            self.CLICKED_SHAPE
                        )
                    return
