from PyQt5.QtGui import (
    QPaintEvent,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPolygonF,
    QCursor,
    QPainterPath,
    QTransform,
)
from PyQt5.QtWidgets import QWidget
from taurus.qt.qtgui.base import TaurusBaseComponent
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, pyqtSlot, QRect
from PyQt5.QtCore import QTimer, QObject
import numpy as np
import copy
import math
from functools import partial
import time
import yaml
from dataclasses import dataclass
from .callback_container import *
from .customized_callbacks import *
from ....util.util import findMainWindow
from smart.util.geometry_transformation import rotate_multiple_points, angle_between

DECORATION_UPON_CURSOR_ON = {
    "pen": {"color": (255, 255, 0), "width": 1, "ls": "DotLine"},
    "brush": {"color": (0, 0, 255, 255)},
}
DECORATION_UPON_CURSOR_OFF = {
    "pen": {"color": (255, 0, 0), "width": 1, "ls": "SolidLine"},
    "brush": {"color": (0, 0, 255, 255)},
}

DECORATION_TEXT_DEFAULT = {
    "font_size": 10,
    "text_color": (255, 255, 255),
    "alignment": "AlignCenter",
    "padding": 0,
}


def make_decoration_from_text(
    dec={
        "pen": {"color": (255, 255, 0), "width": 3, "ls": "DotLine"},
        "brush": {"color": (0, 0, 255)},
    }
):

    pen_color = QColor(*dec["pen"]["color"])
    pen_width = dec["pen"]["width"]
    pen_style = getattr(Qt, dec["pen"]["ls"])
    qpen = QPen(pen_color, pen_width, pen_style)
    brush_color = QColor(*dec["brush"]["color"])
    qbrush = QBrush(brush_color)
    return {"pen": qpen, "brush": qbrush}


class baseShape(object):

    def __init__(
        self,
        dim,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        rotation_center=None,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        lables={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):
        # super().__init__(parent = parent)
        self._dim_pars = dim
        self._dim_pars_origin = dim
        self.ref_geometry = transformation["translate"]

        # self.cen = self.compute_center_from_dim()
        self.anchor_kwargs = None
        self._rotcenter = rotation_center
        self._decoration = copy.deepcopy(decoration_cursor_off)
        self._decoration_cursor_on = copy.deepcopy(decoration_cursor_on)
        self._decoration_cursor_off = copy.deepcopy(decoration_cursor_off)
        self.anchors = {}
        self._transformation = transformation
        self._text_decoration = copy.deepcopy(text_decoration)
        self._labels = copy.deepcopy(lables)
        self.clickable = False
        self.show = True

    def set_clickable(self, clickable=True):
        self.clickable = clickable

    def reset_ref_geometry(self):
        self.ref_geometry = copy.deepcopy(self.transformation["translate"])

    def show_shape(self):
        self.show = True

    def hide_shape(self):
        self.show = False

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        assert type(labels) == dict, "Need dictionary for labels"
        assert "text" in labels, "need text at least"
        # assert type(labels['text'])==list and type(labels['anchor'])==list, 'the value of text and anchor must be a list'
        # assert len(labels['text'])==len(labels['anchor']), 'The dim of text and anchor must be equal'
        if len(labels["text"]) != 0:
            self._labels.update(labels)

    @property
    def text_decoration(self):
        return self._text_decoration

    @text_decoration.setter
    def text_decoration(self, decoration):
        self._text_decoration.update(decoration)

    @property
    def dim_pars(self):
        return self._dim_pars

    @dim_pars.setter
    def dim_pars(self, new_dim):
        self._dim_pars = new_dim
        self._dim_pars_origin = new_dim

    @property
    def rot_center(self):
        if self._rotcenter == None:
            self._rotcenter = [
                int(each) for each in self.compute_center_from_dim(False)
            ]
        return self._rotcenter

    @rot_center.setter
    def rot_center(self, rot_center):
        if (
            type(rot_center) == tuple
            or type(rot_center) == list
            or type(rot_center) == np.ndarray
        ):
            self._rotcenter = [int(each) for each in rot_center]
        elif rot_center == None:
            self._rotcenter = [
                int(each) for each in self.compute_center_from_dim(False)
            ]

    @property
    def decoration(self):
        return self._decoration

    @decoration.setter
    def decoration(self, decoration):
        self._decoration.update(decoration)

    @property
    def decoration_cursor_on(self):
        return self._decoration_cursor_on

    @decoration_cursor_on.setter
    def decoration_cursor_on(self, decoration):
        self._decoration_cursor_on.update(decoration)

    @property
    def decoration_cursor_off(self):
        return self._decoration_cursor_off

    @decoration_cursor_off.setter
    def decoration_cursor_off(self, decoration):
        self._decoration_cursor_off.update(decoration)

    @property
    def transformation(self):
        return self._transformation

    @transformation.setter
    def transformation(self, transformation):
        assert isinstance(transformation, dict), "wrong format of transformation"
        self._transformation.update(transformation)
        # self.calculate_shape()

    def compute_center_from_dim(self, apply_translate=True):
        raise NotImplementedError

    def make_anchors(self, **kwargs):
        self.anchor_kwargs = kwargs
        # raise NotImplementedError

    def update_anchors(self):
        self.make_anchors(**self.anchor_kwargs)

    def calculate_shape(self):
        raise NotImplementedError

    def calculate_anchor_orientation(self):
        raise NotImplementedError

    def calculate_shape_boundary(self):
        raise NotImplementedError

    def check_pos(self, x, y):
        raise NotImplementedError

    def text_label(self, qp):
        raise NotImplementedError

    def _draw_text(
        self,
        qp,
        alignment,
        text,
        anchor,
        x,
        y,
        width,
        height,
        width_txt,
        height_txt,
        padding,
        txt_orientation="horizontal",
    ):
        # qp: qpainter
        # alignment: Qt alignment enum
        # text: text label
        # (x, y) original anchor position
        # width, height: the width and height of shape
        # width_txt, height_txt: the width and height of text
        # padding: additinal padding to applied
        # net effect: the text will be displayed at the anchor position after considering the final size of text area and orientation sense
        padding = 0
        if anchor == "left":
            x = x - width_txt - padding
            y = y + int((height - height_txt) / 2)
        elif anchor == "right":
            x = x + width + padding
            y = y + int((height - height_txt) / 2)
        elif anchor == "top":
            y = y - height_txt - padding
            x = x + int((width - width_txt) / 2)
        elif anchor == "bottom":
            y = y + height + padding
            x = x + int((width - width_txt) / 2)
        elif anchor == "center":
            x = x + int((width - width_txt) / 2) + padding
            y = y + int((height - height_txt) / 2) + padding
        else:
            if anchor in self.anchors:
                x, y = self.anchors[anchor]
                if "left" in anchor:
                    x = x - width_txt - padding
                    y = y + int((0 - height_txt) / 2)
                elif "right" in anchor:
                    x = x + 0 + padding
                    y = y + int((0 - height_txt) / 2)
                elif "top" in anchor:
                    y = y - height_txt - padding
                    x = x + int((0 - width_txt) / 2)
                elif "bottom" in anchor:
                    y = y + 0 + padding
                    x = x + int((0 - width_txt) / 2)
                # y = y - int(height_txt/2)
            else:
                raise KeyError("Invalid anchor key for text labeling!")
        if txt_orientation == "horizontal":
            if "top" in anchor:
                qp.drawText(
                    int(x),
                    int(y - height_txt / 2),
                    int(width_txt),
                    int(height_txt),
                    getattr(Qt, alignment),
                    text,
                )
            elif "bottom" in anchor:
                qp.drawText(
                    int(x),
                    int(y + height_txt / 2),
                    int(width_txt),
                    int(height_txt),
                    getattr(Qt, alignment),
                    text,
                )
            elif "center" in anchor:
                qp.drawText(
                    int(x),
                    int(y),
                    int(width_txt),
                    int(height_txt),
                    getattr(Qt, alignment),
                    text,
                )
            elif "left" in anchor:
                qp.drawText(
                    int(x - height_txt / 2),
                    int(y),
                    int(width_txt),
                    int(height_txt),
                    getattr(Qt, alignment),
                    text,
                )
            elif "right" in anchor:
                qp.drawText(
                    int(x + height_txt / 2),
                    int(y),
                    int(width_txt),
                    int(height_txt),
                    getattr(Qt, alignment),
                    text,
                )
            else:
                raise KeyError("Invalid anchor key for text labeling!")
        elif txt_orientation == "vertical":
            if "right" in anchor:
                qp.translate(
                    int(x + height_txt / 2), int(y + width_txt / 2 + height_txt / 2)
                )
            elif "left" in anchor:
                qp.translate(
                    int(x + width_txt - height_txt * 1.5),
                    int(y + width_txt / 2 + height_txt / 2),
                )
            elif "top" in anchor:
                qp.translate(
                    int(x + width_txt / 2 - height_txt / 2), int(y + height_txt / 2)
                )
            elif "bottom" in anchor:
                qp.translate(
                    int(x + width_txt / 2 - height_txt / 2),
                    int(y + width_txt + height_txt / 2),
                )
            elif "center" in anchor:
                qp.translate(
                    int(x + width_txt / 2 - height_txt / 2),
                    int(y + width_txt / 2 + height_txt / 2),
                )
            qp.rotate(270)
            qp.drawText(
                int(0),
                int(0),
                int(width_txt),
                int(height_txt),
                getattr(Qt, alignment),
                text,
            )

    def get_proper_extention_dir_for_one_anchor(self, key):
        possible_dirs = []
        possible_dirs_offset = []
        anchor_pos, cen, _ = self.compute_anchor_pos_after_transformation(
            key, return_pos_only=False
        )
        orientations = {
            "left": np.array([-1, 0]),
            "right": np.array([1, 0]),
            "top": np.array([0, -1]),
            "bottom": np.array([0, 1]),
        }
        for each, value in orientations.items():
            if not self.check_pos(*(np.array(anchor_pos) + value)):
                possible_dirs.append(each)
                possible_dirs_offset.append(value)
        if len(possible_dirs) == 0:
            return None
        else:
            ix_shortest = np.argmin(
                np.linalg.norm(
                    cen - (np.array(anchor_pos) + np.array(possible_dirs_offset))
                )
            )
            return possible_dirs[ix_shortest]

    def compute_anchor_pos_after_transformation(
        self, key, return_pos_only=False, ref_anchor=None
    ):
        # calculate anchor pos for key after transformation
        # ref_anchor in [None, 'left', 'right', 'top', 'bottom']
        if ref_anchor == "None":
            ref_anchor = None
        ref_anchor_offset = {
            "left": np.array([-1, 0]),
            "right": np.array([1, 0]),
            "top": np.array([0, -1]),
            "bottom": np.array([0, 1]),
        }
        ref_anchor_dir = None
        if ref_anchor != None:
            ref_anchor_dir = ref_anchor_offset[ref_anchor]

        orientation = key
        or_len = self.calculate_orientation_length(orientation, ref_anchor=ref_anchor)
        cen = self.compute_center_from_dim(apply_translate=True)
        rotate_angle = (
            self.transformation["rotate"] if "rotate" in self.transformation else 0
        )
        anchor = None
        if orientation == "top":
            anchor = np.array(cen) + [0, -or_len]
            ref_anchor = cen
        elif orientation == "bottom":
            anchor = np.array(cen) + [0, or_len]
            ref_anchor = cen
        elif orientation == "left":
            anchor = np.array(cen) + [-or_len, 0]
            ref_anchor = cen
        elif orientation == "right":
            anchor = np.array(cen) + [or_len, 0]
            ref_anchor = cen
        elif orientation == "cen":
            anchor = np.array(cen)
            if ref_anchor != None:
                # ref_anchor = anchor - ref_anchor_offset[ref_anchor_dir]
                ref_anchor = anchor - ref_anchor_dir
            else:
                ref_anchor = anchor - ref_anchor_offset["left"]  # by default
        else:
            if orientation in self.anchors:
                anchor = np.array(self.anchors[orientation]) + np.array(
                    self.transformation["translate"]
                )
                if ref_anchor != None:
                    # ref_anchor = anchor - ref_anchor_offset[ref_anchor_dir]
                    ref_anchor = anchor - ref_anchor_dir
                else:
                    ref_anchor = cen
            else:
                raise KeyError("Not the right key for orientation")
        rot_center = np.array(self.rot_center) + np.array(
            self.transformation["translate"]
        )
        cen_, anchor_, ref_anchor_ = rotate_multiple_points(
            [cen, anchor, ref_anchor], rot_center, rotate_angle
        )
        # return cen and anchor pos and or_len after transformation
        if return_pos_only:
            return anchor_
        else:
            # return anchor_, cen_, or_len
            return anchor_, ref_anchor_, or_len

    def cursor_pos_checker(self, x, y):
        if not self.clickable:
            return False
        cursor_inside_shape = self.check_pos(x, y)
        if cursor_inside_shape:
            self.decoration = copy.deepcopy(self.decoration_cursor_on)
            return True
        else:
            self.decoration = copy.deepcopy(self.decoration_cursor_off)
            return False

    def apply_transform(self, qp):
        # translate_values = self.transformation['translate'] if 'translate' in self.transformation else (0,0)
        rotate_angle = (
            self.transformation["rotate"] if "rotate" in self.transformation else 0
        )
        rot_center = self.rot_center
        qp.translate(*rot_center)
        qp.translate(*self.transformation["translate"])
        qp.rotate(rotate_angle)
        qp.translate(*[-each for each in rot_center])
        return qp

    def paint(self, qp) -> None:

        decoration = make_decoration_from_text(self.decoration)
        qp.setPen(decoration["pen"])
        qp.setBrush(decoration["brush"])
        self.draw_shape(qp)

    def draw_shape(self, qp):
        raise NotImplementedError

    def calculate_orientation_vector(self, orientation="top", ref_anchor=None):
        anchor_, cen_, or_len = self.compute_anchor_pos_after_transformation(
            orientation, return_pos_only=False, ref_anchor=ref_anchor
        )
        return cen_, (anchor_ - cen_) / or_len

    def translate(self, v):
        self.transformation = {"translate": v}

    def rotate(self, angle):
        self.transformation = {"rotate": angle}

    def scale(self, sf):
        raise NotImplementedError

    def reset(self):
        self.transformation.update({"rotate": 0, "translate": [0, 0]})


class rectangle(baseShape):
    def __init__(
        self,
        dim=[700, 100, 40, 80],
        rotation_center=None,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        labels={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):

        super().__init__(
            dim=dim,
            rotation_center=rotation_center,
            decoration_cursor_off=decoration_cursor_off,
            decoration_cursor_on=decoration_cursor_on,
            transformation=transformation,
            text_decoration=text_decoration,
            lables=labels,
        )

    def scale(self, sf):
        self.dim_pars = (
            np.array(self.dim_pars)
            * [
                1,
                1,
                sf / self.transformation["scale"],
                sf / self.transformation["scale"],
            ]
        ).astype(int)
        self.transformation = {"scale": sf}
        if self.anchor_kwargs != None:
            self.update_anchors()

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        if self.anchor_kwargs != None:
            self.update_anchors()
        if self.show:
            qp.drawRect(*np.array(self.dim_pars).astype(int))
        self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration
        qp.save()
        for i, text in enumerate(labels["text"]):
            # x, y = cen
            x, y, w, h = self.dim_pars
            anchor = labels["anchor"][i]
            if labels["decoration"] == None:
                decoration = self.text_decoration
            else:
                if type(labels["decoration"]) == list and len(
                    labels["decoration"]
                ) == len(labels["text"]):
                    decoration = labels["decoration"][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration["alignment"]
            padding = decoration["padding"]
            text_color = decoration["text_color"]
            font_size = decoration["font_size"]
            qp.setPen(QColor(*text_color))
            qp.setFont(QFont("Decorative", font_size))
            text_bound_rect = qp.fontMetrics().boundingRect(
                QRect(), Qt.AlignCenter, text
            )
            w_txt, h_txt = text_bound_rect.width(), text_bound_rect.height()
            self._draw_text(
                qp,
                alignment,
                text,
                anchor,
                x,
                y,
                w,
                h,
                w_txt,
                h_txt,
                padding,
                labels["orientation"][i],
            )
            qp.restore()
            qp.save()

    def calculate_shape_boundary(self):
        x, y, w, h = self.dim_pars
        four_corners = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]
        four_corners = [
            np.array(each) + np.array(self.transformation["translate"])
            for each in four_corners
        ]
        rot_center = np.array(self.rot_center) + np.array(
            self.transformation["translate"]
        )
        four_corners = rotate_multiple_points(
            four_corners, rot_center, self.transformation["rotate"]
        )
        # return x_min, x_max, y_min, y_max
        return (
            int(four_corners[:, 0].min()),
            int(four_corners[:, 0].max()),
            int(four_corners[:, 1].min()),
            int(four_corners[:, 1].max()),
        )

    def compute_center_from_dim(self, apply_translate=True):
        x, y, w, h = self.dim_pars
        if apply_translate:
            return (
                x + w / 2 + self.transformation["translate"][0],
                y + h / 2 + self.transformation["translate"][1],
            )
        else:
            return x + w / 2, y + h / 2

    def make_anchors(
        self, num_of_anchors_on_each_side=4, include_corner=True, grid=False
    ):
        # num_of_anchors_on_each_side: exclude corners
        # two possible signature for num_of_achors_one_each_side
        # either a single int meaning same number of anchor points on top/bottom and left/right side
        # or a tuple of two int values meaning different number of anchor points
        # (10, 5): means 10 anchor points top/bottom side and 5 on left/right side
        # if grid is True, anchors will be not only on four edges but also inside the rectangle in a grid net
        super().make_anchors(
            num_of_anchors_on_each_side=num_of_anchors_on_each_side,
            include_corner=include_corner,
            grid=grid,
        )
        if type(num_of_anchors_on_each_side) == str:
            try:
                num_of_anchors_on_each_side = [int(num_of_anchors_on_each_side)] * 2
            except:
                num_of_anchors_on_each_side = eval(num_of_anchors_on_each_side)
        else:
            try:
                num_of_anchors_on_each_side = [int(num_of_anchors_on_each_side)] * 2
            except:
                num_of_anchors_on_each_side = num_of_anchors_on_each_side
        assert (
            len(num_of_anchors_on_each_side) == 2
        ), "You need two integer number to represent anchor number on all sides"

        w, h = self.dim_pars[2:]
        if not include_corner:
            w_step, h_step = w / (num_of_anchors_on_each_side[0] + 1), h / (
                num_of_anchors_on_each_side[1] + 1
            )
        else:
            assert (
                num_of_anchors_on_each_side[0] > 2
                and num_of_anchors_on_each_side[1] > 2
            ), "At least two achors at each edge"
            w_step, h_step = w / (num_of_anchors_on_each_side[0] - 1), h / (
                num_of_anchors_on_each_side[1] - 1
            )

        top_left_coord = np.array(self.dim_pars[0:2])
        bottom_right_coord = top_left_coord + np.array([w, h])
        anchors = {}
        if not grid:
            for i in range(num_of_anchors_on_each_side[0]):
                if not include_corner:
                    anchors[f"anchor_top_{i}"] = top_left_coord + [(i + 1) * w_step, 0]
                    anchors[f"anchor_bottom_{i}"] = bottom_right_coord + [
                        -(i + 1) * w_step,
                        0,
                    ]
                else:
                    anchors[f"anchor_top_{i}"] = top_left_coord + [i * w_step, 0]
                    anchors[f"anchor_bottom_{i}"] = bottom_right_coord + [
                        -i * w_step,
                        0,
                    ]
            for i in range(num_of_anchors_on_each_side[1]):
                if not include_corner:
                    anchors[f"anchor_left_{i}"] = top_left_coord + [0, (i + 1) * h_step]
                    anchors[f"anchor_right_{i}"] = bottom_right_coord + [
                        0,
                        -(i + 1) * h_step,
                    ]
                else:
                    anchors[f"anchor_left_{i}"] = top_left_coord + [0, i * h_step]
                    anchors[f"anchor_right_{i}"] = bottom_right_coord + [0, -i * h_step]
        else:
            for i in range(num_of_anchors_on_each_side[0]):  # num of columns
                for j in range(num_of_anchors_on_each_side[1]):  # num of rows
                    if not include_corner:
                        anchors[f"anchor_grid_{j}_{i}"] = top_left_coord + [
                            (i + 1) * w_step,
                            (j + 1) * h_step,
                        ]
                    else:
                        anchors[f"anchor_grid_{j}_{i}"] = top_left_coord + [
                            i * w_step,
                            j * h_step,
                        ]
        # for each in anchors:
        # anchors[each] = anchors[each] + np.array(self.transformation['translate'])
        self.anchors = anchors

    def calculate_orientation_length(self, orientation="top", ref_anchor=None):
        if orientation == "cen":
            return 1
        w, h = np.array(self.dim_pars[2:])
        if orientation in ["top", "bottom"]:
            return h / 2
        elif orientation in ["left", "right"]:
            return w / 2
        else:
            if orientation in self.anchors:
                if ref_anchor == None:
                    return np.linalg.norm(
                        np.array(self.anchors[orientation])
                        - np.array(self.compute_center_from_dim(apply_translate=False))
                    )
                else:
                    return 1
            else:
                raise KeyError(
                    f"No such orientation key:{orientation}!Possible ones are {self.anchors}"
                )

    def check_pos(self, x, y):
        ox, oy, w, h = np.array(self.dim_pars)
        pos_ = rotate_multiple_points(
            [(x, y)],
            np.array(self.rot_center) + np.array(self.transformation["translate"]),
            -self.transformation["rotate"],
        )
        pos_ = np.array(pos_) - np.array(self.transformation["translate"])
        x_, y_ = pos_
        if (ox <= x_ <= ox + w) and (oy <= y_ <= oy + h):
            return True
        else:
            return False


class roundedRectangle(rectangle):
    def __init__(
        self,
        dim=[700, 100, 40, 80, 10, 10],
        rotation_center=None,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        labels={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):
        super().__init__(
            dim[0:4],
            rotation_center,
            decoration_cursor_off,
            decoration_cursor_on,
            transformation,
            text_decoration,
            labels,
        )
        self.xy_radius = dim[4:]

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        if self.anchor_kwargs != None:
            self.update_anchors()
        if self.show:
            qp.drawRoundedRect(
                *np.array(list(self.dim_pars) + list(self.xy_radius)).astype(int)
            )
        self.text_label(qp)


class circle(baseShape):
    def __init__(
        self,
        dim=[100, 100, 40],
        rotation_center=None,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        labels={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):

        super().__init__(
            dim=dim,
            rotation_center=rotation_center,
            decoration_cursor_off=decoration_cursor_off,
            decoration_cursor_on=decoration_cursor_on,
            transformation=transformation,
            text_decoration=text_decoration,
            lables=labels,
        )

    def scale(self, sf):
        self.dim_pars = list(
            (
                np.array(self.dim_pars)
                * np.array([1, 1, sf / self.transformation["scale"]])
            ).astype(int)
        )
        self.transformation["scale"] = sf
        if self.anchor_kwargs != None:
            self.update_anchors()

    def draw_shape(self, qp):
        if self.anchor_kwargs != None:
            self.update_anchors()
        qp = self.apply_transform(qp)
        if self.show:
            qp.drawEllipse(*(self.dim_pars + [self.dim_pars[-1]]))
        self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration
        cen = self.compute_center_from_dim(False)
        r = self.dim_pars[-1] / 2
        qp.save()
        for i, text in enumerate(labels["text"]):
            x, y = cen
            x, y = x - r, y - r
            anchor = labels["anchor"][i]
            if labels["decoration"] == None:
                decoration = self.text_decoration
            else:
                if type(labels["decoration"]) == list and len(
                    labels["decoration"]
                ) == len(labels["text"]):
                    decoration = labels["decoration"][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration["alignment"]
            padding = decoration["padding"]
            text_color = decoration["text_color"]
            font_size = decoration["font_size"]
            qp.setPen(QColor(*text_color))
            qp.setFont(QFont("Decorative", font_size))
            text_bound_rect = qp.fontMetrics().boundingRect(
                QRect(), Qt.AlignCenter, text
            )
            w_txt, h_txt = text_bound_rect.width(), text_bound_rect.height()
            self._draw_text(
                qp,
                alignment,
                text,
                anchor,
                x,
                y,
                2 * r,
                2 * r,
                w_txt,
                h_txt,
                padding,
                labels["orientation"][i],
            )
            qp.restore()
            qp.save()
            # x, y = self._cal_text_anchor_point(anchor, x, y, r, r, w_txt, h_txt, padding)
            # qp.drawText(int(x), int(y), int(w_txt), int(h_txt), getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        cen = np.array(self.compute_center_from_dim(False))
        r = self.dim_pars[-1] / 2
        four_corners = [cen + each for each in [[r, 0], [-r, 0], [0, r], [0, -r]]]
        four_corners = [
            np.array(each) + np.array(self.transformation["translate"])
            for each in four_corners
        ]
        rot_center = np.array(self.rot_center) + np.array(
            self.transformation["translate"]
        )
        four_corners = rotate_multiple_points(
            four_corners, rot_center, self.transformation["rotate"]
        )
        # return x_min, x_max, y_min, y_max
        return (
            int(four_corners[:, 0].min()),
            int(four_corners[:, 0].max()),
            int(four_corners[:, 1].min()),
            int(four_corners[:, 1].max()),
        )

    def compute_center_from_dim(self, apply_translate=True):
        x, y, R = self.dim_pars
        x, y = x + R / 2, y + R / 2
        if apply_translate:
            return (
                x + self.transformation["translate"][0],
                y + self.transformation["translate"][1],
            )
        else:
            return x, y

    def make_anchors(self, num_of_anchors=4):
        # num_of_anchors_on_each_side: exclude corners
        *_, R = self.dim_pars
        r = R / 2
        super().make_anchors(num_of_anchors=num_of_anchors)
        cen = np.array(self.compute_center_from_dim(False))
        ang_step = math.radians(360 / num_of_anchors)
        anchors = {}
        for i in range(num_of_anchors):
            dx, dy = r * math.cos(ang_step * i), -r * math.sin(ang_step * i)
            # print(i, dx, dy)
            # dir = 'left' if i>=(num_of_anchors/2) else 'right'
            # anchors[f'anchor_{dir}_{i}'] = cen + [dx, dy] + np.array(self.transformation['translate'])
            # anchors[f'anchor_{i}'] = cen + [dx, dy] + np.array(self.transformation['translate'])
            anchors[f"anchor_{i}"] = cen + [dx, dy]
        self.anchors = anchors

    def calculate_orientation_length(self, orientation="top", ref_anchor=None):
        if orientation == "cen":
            return 1
        else:
            return self.dim_pars[-1] / 2

    def check_pos(self, x, y):
        cen = np.array(self.compute_center_from_dim(False))
        r = self.dim_pars[-1] / 2
        p1, p2, p3, p4 = [cen + each for each in [[r, 0], [-r, 0], [0, r], [0, -r]]]
        pos_ = rotate_multiple_points(
            [(x, y)],
            np.array(self.rot_center) + np.array(self.transformation["translate"]),
            -self.transformation["rotate"],
        )
        pos_ = np.array(pos_) - np.array(self.transformation["translate"])
        x_, y_ = pos_
        if (p2[0] <= x_ <= p1[0]) and (p4[1] <= y_ <= p3[1]):
            return True
        else:
            return False


class isocelesTriangle(baseShape):
    def __init__(
        self,
        dim=[100, 100, 40, 60],
        rotation_center=None,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        labels={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):

        super().__init__(
            dim=dim,
            rotation_center=rotation_center,
            decoration_cursor_off=decoration_cursor_off,
            decoration_cursor_on=decoration_cursor_on,
            transformation=transformation,
            text_decoration=text_decoration,
            lables=labels,
        )

    def scale(self, sf):
        self.dim_pars = (
            np.array(self.dim_pars) * [1, 1, sf / self.transformation["scale"], 1]
        ).astype(int)
        self.transformation["scale"] = sf
        if self.anchor_kwargs != None:
            self.update_anchors()

    def _cal_corner_point_coordinates(self, return_type_is_qpointF=True):
        ang = math.radians(self.dim_pars[-1]) / 2
        edge_lenth = self.dim_pars[-2]
        dx = edge_lenth * math.sin(ang)
        dy = edge_lenth * math.cos(ang)
        point1 = (np.array(self.dim_pars[0:2])).astype(int)
        point2 = (np.array(self.dim_pars[0:2]) + np.array([-dx, dy])).astype(int)
        point3 = (np.array(self.dim_pars[0:2]) + np.array([dx, dy])).astype(int)
        if return_type_is_qpointF:
            return QPointF(*point1), QPointF(*point2), QPointF(*point3)
        else:
            return point1, point2, point3

    def draw_shape(self, qp):
        if self.anchor_kwargs != None:
            self.update_anchors()
        qp = self.apply_transform(qp)
        if self.show:
            point1, point2, point3 = self._cal_corner_point_coordinates()
            polygon = QPolygonF()
            polygon.append(point1)
            polygon.append(point2)
            polygon.append(point3)
            qp.drawPolygon(polygon)
        else:
            self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration
        point1, point2, point3 = self._cal_corner_point_coordinates(False)
        qp.save()
        for i, text in enumerate(labels["text"]):
            anchor = labels["anchor"][i]
            if labels["decoration"] == None:
                decoration = self.text_decoration
            else:
                if type(labels["decoration"]) == list and len(
                    labels["decoration"]
                ) == len(labels["text"]):
                    decoration = labels["decoration"][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration["alignment"]
            padding = decoration["padding"]
            text_color = decoration["text_color"]
            font_size = decoration["font_size"]

            qp.setPen(QColor(*text_color))
            qp.setFont(QFont("Decorative", font_size))
            text_bound_rect = qp.fontMetrics().boundingRect(
                QRect(), Qt.AlignCenter, text
            )
            w_txt, h_txt = text_bound_rect.width(), text_bound_rect.height()
            if anchor == "left":
                x, y = point2
            elif anchor == "right":
                x, y = point3
            elif anchor == "top":
                x, y = point1
            elif anchor == "bottom":
                x, y = (point2 + point3) / 2
            elif anchor == "center":
                x, y = (point2 + point3) / 2
                y = y - abs(point1[1] - y) / 2
            else:
                if anchor in self.anchors:
                    x, y = self.anchors[anchor]

            self._draw_text(
                qp,
                alignment,
                text,
                anchor,
                x,
                y,
                0,
                0,
                w_txt,
                h_txt,
                padding,
                labels["orientation"][i],
            )
            qp.restore()
            qp.save()
            # x, y = self._cal_text_anchor_point(anchor, x, y, 0, 0, w_txt, h_txt, padding)
            # qp.setPen(QColor(*text_color))
            # qp.setFont(QFont('Decorative', font_size))
            # qp.drawText(int(x), int(y), int(w_txt), int(h_txt), getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        three_corners = self._cal_corner_point_coordinates(False)
        three_corners = [
            np.array(each) + np.array(self.transformation["translate"])
            for each in three_corners
        ]
        rot_center = np.array(self.rot_center) + np.array(
            self.transformation["translate"]
        )
        three_corners = rotate_multiple_points(
            three_corners, rot_center, self.transformation["rotate"]
        )
        # return x_min, x_max, y_min, y_max
        return (
            int(three_corners[:, 0].min()),
            int(three_corners[:, 0].max()),
            int(three_corners[:, 1].min()),
            int(three_corners[:, 1].max()),
        )

    def compute_center_from_dim(self, apply_translate=True):
        x, y, edge, ang = self.dim_pars
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        r = edge**2 / 2 / abs(p3[1] - p1[1])
        # geometry rot center
        x, y = np.array(p1) + [0, r]
        if apply_translate:
            return (
                x + self.transformation["translate"][0],
                y + self.transformation["translate"][1],
            )
        else:
            return x, y

    def make_anchors(self, num_of_anchors_on_each_side=4, include_corner=True):
        # num_of_anchors_on_each_side: exclude corners
        super().make_anchors(
            num_of_anchors_on_each_side=num_of_anchors_on_each_side,
            include_corner=include_corner,
        )
        edge, ang = self.dim_pars[2:]
        ang = math.radians(ang / 2)
        bottom_edge = edge * math.sin(ang) * 2
        height = edge * math.cos(ang)
        if not include_corner:
            w_step, h_step = bottom_edge / (num_of_anchors_on_each_side + 1), height / (
                num_of_anchors_on_each_side + 1
            )
        else:
            assert num_of_anchors_on_each_side > 2, "At least two achors at each edge"
            w_step, h_step = bottom_edge / (num_of_anchors_on_each_side - 1), height / (
                num_of_anchors_on_each_side - 1
            )

        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        anchors = {}
        for i in range(num_of_anchors_on_each_side):
            if not include_corner:
                anchors[f"anchor_left_{i}"] = np.array(p1) + [
                    -(i + 1) * h_step * math.tan(ang),
                    (i + 1) * h_step,
                ]
                anchors[f"anchor_bottom_{i}"] = np.array(p2) + [(i + 1) * w_step, 0]
                anchors[f"anchor_right_{i}"] = np.array(p1) + [
                    (i + 1) * h_step * math.tan(ang),
                    (i + 1) * h_step,
                ]
            else:
                anchors[f"anchor_left_{i}"] = np.array(p1) + [
                    -i * h_step * math.tan(ang),
                    i * h_step,
                ]
                anchors[f"anchor_bottom_{i}"] = np.array(p2) + [i * w_step, 0]
                anchors[f"anchor_right_{i}"] = np.array(p1) + [
                    i * h_step * math.tan(ang),
                    i * h_step,
                ]
        for each in anchors:
            anchors[each] = anchors[each] + np.array(self.transformation["translate"])
        self.anchors = anchors

    def calculate_orientation_length(self, orientation="top", ref_anchor=None):
        if orientation == "cen":
            return 1
        cen = self.compute_center_from_dim(False)
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        w, h = np.array(self.dim_pars[2:])
        if orientation == "top":
            return abs(cen[1] - p1[1])
        elif orientation == "bottom":
            return abs(cen[1] - p2[1])
        elif orientation in ["left", "right"]:
            return abs(cen[0] - p1[0])
        else:
            if orientation in self.anchors:
                if ref_anchor == None:
                    return np.linalg.norm(
                        np.array(self.anchors[orientation])
                        - np.array(self.compute_center_from_dim(apply_translate=False))
                    )
                else:
                    return 1
            else:
                raise KeyError("No such orientation key!")

    def check_pos(self, x, y):
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        pos_ = rotate_multiple_points(
            [(x, y)],
            np.array(self.rot_center) + np.array(self.transformation["translate"]),
            -self.transformation["rotate"],
        )
        pos_ = np.array(pos_) - np.array(self.transformation["translate"])
        x_, y_ = pos_
        if (p2[0] <= x_ <= p3[0]) and (p1[1] <= y_ <= p2[1]):
            return True
        else:
            return False


class trapezoid(baseShape):
    def __init__(
        self,
        dim=[100, 100, 40, 60, 50],
        rotation_center=None,
        decoration_cursor_off=DECORATION_UPON_CURSOR_OFF,
        decoration_cursor_on=DECORATION_UPON_CURSOR_ON,
        transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
        text_decoration=DECORATION_TEXT_DEFAULT,
        labels={"text": [], "anchor": [], "orientation": [], "decoration": None},
    ):
        # dim = [cen_x, cen_y, len_top, len_bottom, height]
        super().__init__(
            dim=dim,
            rotation_center=rotation_center,
            decoration_cursor_off=decoration_cursor_off,
            decoration_cursor_on=decoration_cursor_on,
            transformation=transformation,
            text_decoration=text_decoration,
            lables=labels,
        )

    def scale(self, sf):
        sf_norm = sf / self.transformation["scale"]
        self.dim_pars = (
            np.array(self.dim_pars) * [1, 1, sf_norm, sf_norm, sf_norm]
        ).astype(int)
        self.transformation["scale"] = sf
        if self.anchor_kwargs != None:
            self.update_anchors()

    def _cal_corner_point_coordinates(self, return_type_is_qpointF=True):
        edge_lenth_top = self.dim_pars[-3]
        edge_lenth_bottom = self.dim_pars[-2]
        height = self.dim_pars[-2]
        dx_top = edge_lenth_top / 2
        dx_bottom = edge_lenth_bottom / 2
        dy = height / 2
        point1 = (np.array(self.dim_pars[0:2]) + np.array([-dx_top, -dy])).astype(int)
        point2 = (np.array(self.dim_pars[0:2]) + np.array([dx_top, -dy])).astype(int)
        point3 = (np.array(self.dim_pars[0:2]) + np.array([-dx_bottom, dy])).astype(int)
        point4 = (np.array(self.dim_pars[0:2]) + np.array([dx_bottom, dy])).astype(int)
        if return_type_is_qpointF:
            return (
                QPointF(*point1),
                QPointF(*point2),
                QPointF(*point3),
                QPointF(*point4),
            )
        else:
            return point1, point2, point3, point4

    def draw_shape(self, qp):
        if self.anchor_kwargs != None:
            self.update_anchors()
        qp = self.apply_transform(qp)
        if self.show:
            point1, point2, point3, point4 = self._cal_corner_point_coordinates()
            polygon = QPolygonF()
            polygon.append(point1)
            polygon.append(point2)
            polygon.append(point4)
            polygon.append(point3)
            qp.drawPolygon(polygon)
        self.text_label(qp)

    def _get_width_height(self):
        # (length_top + length_bottom)/2, height
        return max([self.dim_pars[2], self.dim_pars[3]]), self.dim_pars[-1]

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration
        point1, point2, point3, point4 = self._cal_corner_point_coordinates(False)
        qp.save()
        for i, text in enumerate(labels["text"]):
            anchor = labels["anchor"][i]
            if labels["decoration"] == None:
                decoration = self.text_decoration
            else:
                if type(labels["decoration"]) == list and len(
                    labels["decoration"]
                ) == len(labels["text"]):
                    decoration = labels["decoration"][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration["alignment"]
            padding = decoration["padding"]
            text_color = decoration["text_color"]
            font_size = decoration["font_size"]

            qp.setPen(QColor(*text_color))
            qp.setFont(QFont("Decorative", font_size))
            text_bound_rect = qp.fontMetrics().boundingRect(
                QRect(), Qt.AlignCenter, text
            )
            w_txt, h_txt = text_bound_rect.width(), text_bound_rect.height()
            if anchor == "left":
                x, y = (point1 + point3) / 2
            elif anchor == "right":
                x, y = (point2 + point4) / 2
            elif anchor == "top":
                # x, y = (point1 + point2)/2
                x, y = self.dim_pars[0:2]
            elif anchor == "bottom":
                x, y = (point3 + point4) / 2
            elif anchor == "center":
                x, y = self.dim_pars[0:2]
            else:
                if anchor in self.anchors:
                    x, y = self.anchors[anchor]
            x, y = self.dim_pars[0:2]
            y = y - self.dim_pars[-1] / 2
            x = x - max(self.dim_pars[2:4]) / 2
            w, h = self._get_width_height()
            self._draw_text(
                qp,
                alignment,
                text,
                anchor,
                x,
                y,
                w,
                h,
                w_txt,
                h_txt,
                padding,
                labels["orientation"][i],
            )
            # print(x, y, h, w, self.dim_pars)
            qp.restore()
            qp.save()
            # x, y = self._cal_text_anchor_point(anchor, x, y, 0, 0, w_txt, h_txt, padding)
            # qp.setPen(QColor(*text_color))
            # qp.setFont(QFont('Decorative', font_size))
            # qp.drawText(int(x), int(y), int(w_txt), int(h_txt), getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        four_corners = self._cal_corner_point_coordinates(False)
        four_corners = [
            np.array(each) + np.array(self.transformation["translate"])
            for each in four_corners
        ]
        rot_center = np.array(self.rot_center) + np.array(
            self.transformation["translate"]
        )
        four_corners = rotate_multiple_points(
            four_corners, rot_center, self.transformation["rotate"]
        )
        # return x_min, x_max, y_min, y_max
        return (
            int(four_corners[:, 0].min()),
            int(four_corners[:, 0].max()),
            int(four_corners[:, 1].min()),
            int(four_corners[:, 1].max()),
        )

    def compute_center_from_dim(self, apply_translate=True):
        x, y, *_ = self.dim_pars
        if apply_translate:
            return (
                x + self.transformation["translate"][0],
                y + self.transformation["translate"][1],
            )
        else:
            return x, y

    def make_anchors(self, num_of_anchors_on_each_side=4, include_corner=True):
        # num_of_anchors_on_each_side: exclude corners
        super().make_anchors(
            num_of_anchors_on_each_side=num_of_anchors_on_each_side,
            include_corner=include_corner,
        )
        bottom_edge = self.dim_pars[-2]
        top_edge = self.dim_pars[-3]
        height = self.dim_pars[-1]
        ang = math.atan(height / ((top_edge - bottom_edge) / 2))
        if not include_corner:
            w_step_bottom, w_step_top, h_step = (
                bottom_edge / (num_of_anchors_on_each_side + 1),
                top_edge / (num_of_anchors_on_each_side + 1),
                height / (num_of_anchors_on_each_side + 1),
            )
        else:
            assert num_of_anchors_on_each_side > 2, "At least two achors at each edge"
            w_step_bottom, w_step_top, h_step = (
                bottom_edge / (num_of_anchors_on_each_side - 1),
                top_edge / (num_of_anchors_on_each_side - 1),
                height / (num_of_anchors_on_each_side - 1),
            )

        p1, p2, p3, p4 = self._cal_corner_point_coordinates(False)
        anchors = {}
        for i in range(num_of_anchors_on_each_side):
            if not include_corner:
                anchors[f"anchor_left_{i}"] = np.array(p1) + [
                    -(i + 1) * h_step * math.tan(ang),
                    (i + 1) * h_step,
                ]
                anchors[f"anchor_bottom_{i}"] = np.array(p3) + [
                    (i + 1) * w_step_bottom,
                    0,
                ]
                anchors[f"anchor_top_{i}"] = np.array(p1) + [(i + 1) * w_step_top, 0]
                anchors[f"anchor_right_{i}"] = np.array(p2) + [
                    (i + 1) * h_step * math.tan(ang),
                    (i + 1) * h_step,
                ]
            else:
                anchors[f"anchor_left_{i}"] = np.array(p1) + [
                    -i * h_step * math.tan(ang),
                    i * h_step,
                ]
                anchors[f"anchor_bottom_{i}"] = np.array(p3) + [i * w_step_bottom, 0]
                anchors[f"anchor_top_{i}"] = np.array(p1) + [i * w_step_top, 0]
                anchors[f"anchor_right_{i}"] = np.array(p2) + [
                    i * h_step * math.tan(ang),
                    i * h_step,
                ]
        for each in anchors:
            anchors[each] = anchors[each]
        self.anchors = anchors

    def calculate_orientation_length(self, orientation="top", ref_anchor=None):
        if orientation == "cen":
            return 1
        w_top, w_bottom, h = np.array(self.dim_pars[2:])
        if orientation in ["top", "bottom"]:
            return h / 2
        elif orientation in ["left", "right"]:
            return (w_top + w_bottom) / 2
        else:
            if orientation in self.anchors:
                if ref_anchor == None:
                    return np.linalg.norm(
                        np.array(self.anchors[orientation])
                        - np.array(self.compute_center_from_dim(apply_translate=False))
                    )
                else:
                    return 1
            else:
                raise KeyError("No such orientation key!")

    def check_pos(self, x, y):
        p1, p2, p3, p4 = self._cal_corner_point_coordinates(False)
        pos_ = rotate_multiple_points(
            [(x, y)],
            np.array(self.rot_center) + np.array(self.transformation["translate"]),
            -self.transformation["rotate"],
        )
        pos_ = np.array(pos_) - np.array(self.transformation["translate"])
        x_, y_ = pos_
        if (p3[0] <= x_ <= p4[0]) and (p1[1] <= y_ <= p3[1]):
            return True
        else:
            return False


class line(baseShape):
    pass


class ellipse(baseShape):
    pass


class pie(baseShape):
    pass


class buildObject(object):

    def __init__(self, shape_config, qpainter):
        self.shape_config = shape_config
        self.shape_info = {}
        self.qpainer = qpainter
        self.unpack_shape_info()

    def unpack_shape_info(self):
        pass

    def paint_all_shapes(self):
        self.build_shapes()
        self.qpainter.begin(self)
        for each in self.shape_info:
            paint_api, paint_pars, paint_decoration = self.shape_info[each]
            self.qpainer.setPen(paint_decoration["pen"])
            self.qpainer.setBrush(paint_decoration["brush"])
            getattr(self.qpainer, paint_api)(*paint_pars)
        self.qpainter.end(self)

    def build_shapes(self):
        pass


class shapeComposite(TaurusBaseComponent, QObject):
    # class shapeComposite(TaurusBaseComponent):

    modelKeys = [TaurusBaseComponent.MLIST]
    model_str_list = []
    # modelKeys = []
    updateSignal = pyqtSignal()

    def __init__(
        self,
        shapes,
        parent=None,
        anchor_args=None,
        alignment_pattern=None,
        connection_pattern=None,
        ref_shape_index=None,
        model_index_list=[],
        callbacks_upon_model_change=[],
        callbacks_upon_mouseclick=[],
        callbacks_upon_rightmouseclick=[],
        static_labels=[],
    ):
        # connection_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        # alignment_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        super(QObject, shapeComposite).__init__(self)
        TaurusBaseComponent.__init__(self)
        self.model_ix_start = len(self.model_str_list)
        self._shapes = copy.deepcopy(shapes)
        self._model_shape_index_list = model_index_list
        self._callbacks_upon_model_change = callbacks_upon_model_change
        self._callbacks_upon_left_mouseclick = callbacks_upon_mouseclick
        self._callbacks_upon_right_mouseclick = callbacks_upon_rightmouseclick
        self.ref_shape = (
            self.shapes[ref_shape_index] if ref_shape_index != None else self.shapes[0]
        )
        self.anchor_args = anchor_args
        # self.make_anchors()
        self.alignment = alignment_pattern
        self.connection = connection_pattern
        self.static_labels = static_labels
        self.lines = None
        self.build_composite()
        self.callbacks = {}
        self._models = {}
        self.parent = findMainWindow()

    def copy_object_meta(self):
        return (
            {
                "shapes": self._shapes,
                "anchor_args": self.anchor_args,
                "alignment_pattern": self.alignment,
                "connection_pattern": self.connection,
                "ref_shape_index": self._shapes.index(self.ref_shape),
                "model_index_list": self._model_shape_index_list,
            },
            self.callbacks,
            self._models,
        )

    def unpack_callbacks_and_models(self):
        if len(self._models) == 0:
            return
        # models = list(set(list(self._models.values())))
        models = list(self._models.values())
        # self._models_unique = models
        self.__class__.model_str_list = self.__class__.model_str_list + list(models)
        self.setModel(self.__class__.model_str_list)
        inx_shape = [int(each) for each in self._models.keys()]
        self.model_shape_index_list = inx_shape
        for ix in inx_shape:
            self.shapes[ix].set_clickable(True)
        self.callbacks_upon_model_change = [
            self._make_callback(each, False)
            for each in self.callbacks["callbacks_upon_model_change"].values()
        ]
        self.callbacks_upon_left_mouseclick = [
            self._make_callback(each, True)
            for each in self.callbacks["callbacks_upon_leftmouse_click"].values()
        ]
        self.callbacks_upon_right_mouseclick = [
            self._make_callback(each, True)
            for each in self.callbacks["callbacks_upon_rightmouse_click"].values()
        ]

    def _make_callback(self, callback_info_list, mouseclick_callback=True):
        if callback_info_list == None or callback_info_list == "None":
            return lambda *kwargs: None
        # if there are multiple callbacks linking to one model
        if type(callback_info_list[0]) == list:

            def call_back_chain(parent, shape, model_value):
                cbs = []
                for callback_info in callback_info_list:
                    cb_str = callback_info[0]
                    cb_args = callback_info[1:]
                    cbs.append(
                        partial(
                            eval(cb_str),
                            **{
                                cb_args[i]: cb_args[i + 1]
                                for i in range(0, len(cb_args), 2)
                            },
                        )
                    )
                for cb in cbs:
                    cb(parent, shape, model_value)

            def call_back_chain_mouseclick(parent):
                cbs = []
                for callback_info in callback_info_list:
                    cb_str = callback_info[0]
                    cb_args = callback_info[1:]
                    cbs.append(
                        partial(
                            eval(cb_str),
                            **{
                                cb_args[i]: cb_args[i + 1]
                                for i in range(0, len(cb_args), 2)
                            },
                        )
                    )
                for cb in cbs:
                    cb(parent)

            if mouseclick_callback:
                return call_back_chain_mouseclick
            else:
                return call_back_chain
        # if there is only single callback func
        else:
            cb_str = callback_info_list[0]
            cb_args = callback_info_list[1:]
            return partial(
                eval(cb_str),
                **{cb_args[i]: cb_args[i + 1] for i in range(0, len(cb_args), 2)},
            )

    @property
    def shapes(self):
        return self._shapes

    @property
    def model_shape_index_list(self):
        return self._model_shape_index_list

    @model_shape_index_list.setter
    def model_shape_index_list(self, model_shape_index_list):
        shapes_num = len(self.shapes)
        assert (
            type(model_shape_index_list) == list
        ), "please give a list of model shape index"
        for each in model_shape_index_list:
            assert (
                type(each) == int and each < shapes_num
            ), "index must be integer and smaller than the num of total shape in the composite obj"
        self._model_shape_index_list = model_shape_index_list

    @property
    def callbacks_upon_model_change(self):
        return self._callbacks_upon_model_change

    @callbacks_upon_model_change.setter
    def callbacks_upon_model_change(self, cbs):
        assert len(cbs) == len(
            self.model_shape_index_list
        ), "Length of callbacks must equal to that of model shape index"
        self._callbacks_upon_model_change = {
            ix: cb for ix, cb in zip(self.model_shape_index_list, cbs)
        }

    @property
    def callbacks_upon_left_mouseclick(self):
        return self._callbacks_upon_left_mouseclick

    @callbacks_upon_left_mouseclick.setter
    def callbacks_upon_left_mouseclick(self, cbs):
        assert len(cbs) == len(
            self.model_shape_index_list
        ), "Length of callbacks must equal to that of model shape index"
        self._callbacks_upon_left_mouseclick = {
            ix: cb for ix, cb in zip(self.model_shape_index_list, cbs)
        }

    @property
    def callbacks_upon_right_mouseclick(self):
        return self._callbacks_upon_right_mouseclick

    @callbacks_upon_right_mouseclick.setter
    def callbacks_upon_right_mouseclick(self, cbs):
        assert len(cbs) == len(
            self.model_shape_index_list
        ), "Length of callbacks must equal to that of model shape index"
        self._callbacks_upon_right_mouseclick = {
            ix: cb for ix, cb in zip(self.model_shape_index_list, cbs)
        }

    def build_composite(self):
        self.align_shapes()
        self.make_line_connection()
        self.set_static_labels()

    def set_static_labels(self):
        if len(self.static_labels) == 0:
            return
        else:
            assert len(self.shapes) == len(
                self.static_labels
            ), "num of shapes must match the num of static labels"
            for i, each in enumerate(self.static_labels):
                self.shapes[i].labels = {"text": [each]}

    def align_shapes(self):
        if self.alignment == None:
            return
        shape_index = self.alignment["shapes"]
        anchors = self.alignment["anchors"]
        gaps = self.alignment["gaps"]
        ref_anchors = self.alignment["ref_anchors"]
        assert len(shape_index) == len(
            anchors
        ), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_, gap_, ref_anchors_ in zip(
            shape_index, anchors, gaps, ref_anchors
        ):
            ref_shape, target_shape, *_ = [self.shapes[each] for each in shapes_]
            buildTools.align_two_shapes(
                ref_shape, target_shape, anchors_, gap_, ref_anchors_
            )
        for shape in self.shapes:
            shape.reset_ref_geometry()

    def make_line_connection(self):
        self.lines = []
        if self.connection == None:
            return
        shape_index = self.connection["shapes"]
        anchors = self.connection["anchors"]
        connect_types = self.connection.get("connect_types", [False] * len(anchors))
        assert len(shape_index) == len(
            anchors
        ), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_, connect_ in zip(shape_index, anchors, connect_types):
            shapes = [self.shapes[each] for each in shapes_]
            lines = buildTools.make_line_connection_btw_two_anchors(
                shapes, anchors_, direct_connection=connect_
            )
            self.lines.append(lines)

    def translate(self, vec):
        self.ref_shape.translate(vec)
        self.build_composite()

    def rotate(self, ang):
        self.ref_shape.rotate(ang)
        self.build_composite()

    def scale(self, sf):
        for i, shape in enumerate(self.shapes):
            shape.scale(sf)
        self.build_composite()

    def uponLeftMouseClicked(self, shape_index):
        self.callbacks_upon_left_mouseclick[shape_index](self.parent)

    def uponRightMouseClicked(self, shape_index):
        return self.callbacks_upon_right_mouseclick[shape_index](self.parent)

    def handleEvent(self, evt_src, evt_type, evt_value):
        """reimplemented from TaurusBaseComponent"""
        try:
            for i, _ix in enumerate(self.model_shape_index_list):
                key = (TaurusBaseComponent.MLIST, i + self.model_ix_start)
                if (
                    key not in self.modelKeys
                ):  # this could happen when the setModel step is slower than the event polling
                    return
                if evt_src is self.getModelObj(key=key):
                    self._callbacks_upon_model_change[_ix](
                        self.parent, self.shapes[_ix], evt_value
                    )
                    self.updateSignal.emit()
        except Exception as e:
            # if i>(len(self.modelKeys)-2):
            #    return
            self.info("Skipping event. Reason: %s", e)


class buildTools(object):

    @classmethod
    def build_basic_shape_from_yaml(cls, yaml_file_path):
        with open(yaml_file_path, "r", encoding="utf8") as f:
            config = yaml.safe_load(f.read())
        shape_container = {}
        basic_shapes = config["basic_shapes"]
        for shape, shape_info in basic_shapes.items():
            for shape_type, shape_type_info in shape_info.items():
                anchor_pars = shape_type_info.pop("anchor_pars")
                shape_obj = eval(shape)(**shape_type_info)
                # print(shape_type_info, shape_obj.transformation)
                shape_container[f"{shape}.{shape_type}"] = shape_obj
                if anchor_pars != None:
                    shape_obj.make_anchors(*anchor_pars)
                else:
                    shape_obj.make_anchors()
        return shape_container

    @staticmethod
    def formate_callbacks(callbacks_info):
        # callbacks could be already a dict or a compact form that needs to be unpacked to make dict
        # case 1: {0: ['callback_1', 'common_arg', 'arg1']; 1: ['callback_1','common_arg', 'arg2']}
        # case 2: {'index': [0,1], 'callback': ['callback_1', 'common_arg'], 'args': ['arg1','arg2']}
        if ("index" in callbacks_info) and ("callback" in callbacks_info):
            callback = callbacks_info["callback"]
            if "args" in callbacks_info:
                callbacks = [callback + [arg] for arg in callbacks_info["args"]]
            else:
                callbacks = [callback] * len(callbacks_info["index"])
            return dict(zip(callbacks_info["index"], callbacks))
        else:
            return callbacks_info

    @classmethod
    def build_composite_shape_from_yaml(cls, yaml_file_path, **kwargs):
        with open(yaml_file_path, "r", encoding="utf8") as f:
            config = yaml.safe_load(f.read())
        shape_container = cls.build_basic_shape_from_yaml(yaml_file_path)
        composite_container = config["composite_shapes"]
        composite_obj_container = {}
        for i, (composite, composite_info) in enumerate(composite_container.items()):
            inherited = composite_info.pop("inherit", None)
            if inherited != None:
                inherited_composite_info = composite_container[inherited]
                composite_info = {**inherited_composite_info, **composite_info}
            _models = composite_info["models"]
            # _models could be a dict already or a compact way that will need to unpack to form a dict
            if ("model" in _models) and ("index" in _models):
                _models = dict(
                    zip(_models["index"], [_models["model"]] * len(_models["index"]))
                )
            hide_shape_ix = composite_info.pop("hide", [])
            callbacks_upon_model_change = buildTools.formate_callbacks(
                composite_info["callbacks_upon_model_change"]
            )
            callbacks_upon_leftmouse_click = buildTools.formate_callbacks(
                composite_info["callbacks_upon_leftmouse_click"]
            )
            callbacks_upon_rightmouse_click = buildTools.formate_callbacks(
                composite_info["callbacks_upon_rightmouse_click"]
            )
            callbacks = {
                "callbacks_upon_model_change": callbacks_upon_model_change,
                "callbacks_upon_leftmouse_click": callbacks_upon_leftmouse_click,
                "callbacks_upon_rightmouse_click": callbacks_upon_rightmouse_click,
            }
            shapes_tag = composite_info["shapes"]
            shapes = []
            for each in shapes_tag:
                if "*" not in each:
                    each = each + "*1"
                shape_key, num_shape = each.rsplit("*")
                num_shape = int(num_shape)
                for i in range(num_shape):
                    shapes.append(copy.deepcopy(shape_container[shape_key]))
            ref_shape = composite_info["ref_shape"]
            alignment_pattern = composite_info["alignment"]
            if "connection" in composite_info:
                connection_pattern = composite_info["connection"]
            else:
                connection_pattern = None
            static_labels = composite_info.pop("static_labels", [])
            composite_obj_container[composite] = shapeComposite(
                shapes=shapes,
                alignment_pattern=alignment_pattern,
                connection_pattern=connection_pattern,
                static_labels=static_labels,
            )
            composite_obj_container[composite].callbacks = callbacks
            composite_obj_container[composite]._models = _models
            if composite_info["transformation"] != "None":
                translate = composite_info["transformation"].pop("translate", (0, 0))
                if "translate" in kwargs:
                    assert (
                        type(kwargs["translate"][0]) == list
                        and len(kwargs["translate"]) > i
                    ), "You should provide a list of translate vector for all composite!"
                    translate = kwargs["translate"][i]
                rotation = composite_info["transformation"].pop("rotate", 0)
                sf = composite_info["transformation"].pop("scale", 1)
                composite_obj_container[composite].translate(translate)
                composite_obj_container[composite].rotate(rotation)
                composite_obj_container[composite].scale(sf)
            for i in hide_shape_ix:
                composite_obj_container[composite].shapes[i].hide_shape()
            composite_obj_container[composite].unpack_callbacks_and_models()

        return composite_obj_container

    @classmethod
    def build_view_from_yaml(cls, yaml_file_path, canvas_width):
        composite_obj_container = cls.build_composite_shape_from_yaml(yaml_file_path)
        with open(yaml_file_path, "r", encoding="utf8") as f:
            viewer_config = yaml.safe_load(f.read())["viewers"]
        viewer_container = {}
        connection_container = {}
        for viewer, viewer_info in viewer_config.items():
            if viewer_info["transformation"]["translate"]["type"] == "absolute":
                max_width = 0
                max_width = max(
                    [
                        each[0]
                        for each in viewer_info["transformation"]["translate"]["values"]
                    ]
                )
                sf = canvas_width / max_width
            else:
                sf = 1
            composite_obj_container_subset = {}
            acc_boundary_offset = 0
            for i, each in enumerate(viewer_info["composites"]):
                init_kwargs, cbs, models = composite_obj_container[
                    each
                ].copy_object_meta()
                composite = shapeComposite(**init_kwargs)
                composite.callbacks = cbs
                composite._models = models
                composite.unpack_callbacks_and_models()
                # composite = copy.deepcopy(composite_obj_container[each])
                if i == 0:
                    translate = viewer_info["transformation"]["translate"][
                        "first_composite"
                    ]
                    translate = [int(translate[0] * sf), translate[1]]
                else:
                    if viewer_info["transformation"]["translate"]["type"] == "absolute":
                        translate = viewer_info["transformation"]["translate"][
                            "values"
                        ][i - 1]
                        translate = [int(translate[0] * sf), translate[1]]
                    elif (
                        viewer_info["transformation"]["translate"]["type"] == "relative"
                    ):
                        translate = (
                            viewer_info["transformation"]["translate"][
                                "first_composite"
                            ]
                            + np.array(
                                viewer_info["transformation"]["translate"]["values"][0]
                            )
                            * i
                        ) + [acc_boundary_offset,0]
                x_min, x_max, *_ = buildTools.calculate_boundary_for_combined_shapes(composite.shapes)
                acc_boundary_offset = acc_boundary_offset + abs(x_max - x_min)
                composite.translate(translate)
                if each in composite_obj_container_subset:
                    j = 2
                    while True:
                        if each + f"{j}" in composite_obj_container_subset:
                            j = j + 1
                            continue
                        else:
                            composite_obj_container_subset[each + f"{j}"] = composite
                            break
                else:
                    composite_obj_container_subset[each] = composite
            viewer_container[viewer] = composite_obj_container_subset
            if "connection" in viewer_info:
                connection_container[viewer] = viewer_info["connection"]
            else:
                connection_container[viewer] = {}
        return viewer_container, connection_container

    @classmethod
    def calculate_boundary_for_combined_shapes(cls, shapes):
        x_min, x_max, y_min, y_max = None, None, None, None
        for i, shape in enumerate(shapes):
            if i == 0:
                x_min, x_max, y_min, y_max = shape.calculate_shape_boundary()
            else:
                _x_min, _x_max, _y_min, _y_max = shape.calculate_shape_boundary()
                x_min = min([x_min, _x_min])
                x_max = max([x_max, _x_max])
                y_min = min([y_min, _y_min])
                y_max = max([y_max, _y_max])
        return x_min, x_max, y_min, y_max

    @classmethod
    def align_multiple_shapes(cls, shapes, orientations):
        def _align_shapes(_shapes, orientations_):
            # _shapes = [ref1, tag1, ref2, tag2, ...], orientations_ = [ref_or1, tag_or1, ref_or2, tag_or2, ...]
            assert len(_shapes) == len(
                orientations_
            ), "The length of shapes and orientation must be equal!"
            for i in range(len(_shapes) - 1):
                ref_shape, target_shape = _shapes[i], _shapes[i + 1]
                orientations_temp = orientations_[i : i + 2]
                buildTools.align_two_shapes(ref_shape, target_shape, orientations_temp)

        if type(shapes[0]) == list:
            # shapes is a list of _shapes, orientations is a list of orientations_
            assert (
                type(orientations[0]) == list
            ), "Format mismatch. Should be list of list."
            for shape_segment, orientaion_seg in zip(shapes, orientations):
                _align_shapes(shape_segment, orientaion_seg)
        else:
            _align_shapes(shapes, orientations)

    @classmethod
    def align_two_shapes(
        cls,
        ref_shape,
        target_shape,
        orientations=["bottom", "top"],
        gap=0.0,
        ref_anchors=[None, None],
    ):
        cen_, v_unit = ref_shape.calculate_orientation_vector(
            orientations[0], ref_anchors[0]
        )
        v_mag = ref_shape.calculate_orientation_length(
            orientations[0], ref_anchors[0]
        ) + target_shape.calculate_orientation_length(orientations[1], ref_anchors[1])
        # if orientations[0] == orientations[1]:
        #    v_mag = -ref_shape.calculate_orientation_length(orientations[0], ref_anchors[0]) + target_shape.calculate_orientation_length(orientations[1], ref_anchors[1])
        # else:
        #    v_mag = ref_shape.calculate_orientation_length(orientations[0], ref_anchors[0]) + target_shape.calculate_orientation_length(orientations[1], ref_anchors[1])
        v = v_unit * v_mag * (1 + gap)
        # set rot ang to 0 and translate to 0
        target_shape.reset()
        # this center is the geometry center if ref_anchor is None, and become offseted anchor otherwise
        if orientations[1] in ["left", "right", "top", "bottom"]:
            origin_cen_target = target_shape.compute_center_from_dim()
        else:
            if ref_anchors[1] == None:
                origin_cen_target = target_shape.compute_center_from_dim()
            else:
                if orientations[1] == "cen":
                    anchor = target_shape.compute_center_from_dim()
                else:
                    anchor = target_shape.anchors[orientations[1]]
                ref_anchor_offset = {
                    "left": np.array([-1, 0]),
                    "right": np.array([1, 0]),
                    "top": np.array([0, -1]),
                    "bottom": np.array([0, 1]),
                }
                assert ref_anchors[1] in ref_anchor_offset, "Wrong key for ref anchor"
                origin_cen_target = anchor - ref_anchor_offset[ref_anchors[1]]
        new_cen_target = v + cen_
        v_diff = new_cen_target - origin_cen_target
        target_shape.rot_center = origin_cen_target
        # let's calculate the angle between the original target shape and the orientated one
        target_cen_, target_v_unit = target_shape.calculate_orientation_vector(
            orientations[1], ref_anchors[1]
        )
        target_v_new = -v
        angle_offset = -angle_between(target_v_unit, target_v_new)
        target_shape.transformation.update(
            {"rotate": angle_offset, "translate": v_diff}
        )
        return target_shape

    @classmethod
    def make_line_connection_btw_two_anchors(
        cls, shapes, anchors, short_head_line_len=10, direct_connection=False
    ):
        line_nodes = []
        if direct_connection:
            short_head_line_len = 0

        def _apply_offset(pos, dir):
            offset = {
                "left": np.array([-short_head_line_len, 0]),
                "right": np.array([short_head_line_len, 0]),
                "top": np.array([0, -short_head_line_len]),
                "bottom": np.array([0, short_head_line_len]),
            }
            return np.array(pos) + offset[dir]

        def _extend_to_beyond_boundary(pos, dir, pair_pos, overshot_pix_ct=20):
            x_min, x_max, y_min, y_max = (
                buildTools.calculate_boundary_for_combined_shapes(shapes)
            )
            x_pair, y_pair = pair_pos
            if dir == "left":
                if x_pair > pos[0]:
                    x = min([x_min, pos[0]]) - overshot_pix_ct
                    y = pos[1]
                else:
                    x, y = pos
            elif dir == "right":
                if x_pair < pos[0]:
                    x = max([x_max, pos[0]]) + overshot_pix_ct
                    y = pos[1]
                else:
                    x, y = pos
            elif dir == "top":
                if y_pair < pos[1]:
                    x = pos[0]
                    y = min([y_min, pos[1]]) - overshot_pix_ct
                else:
                    x, y = pos[0], min([pos[1], 100])
            elif dir == "bottom":
                if y_pair > pos[1]:
                    x = pos[0]
                    y = max([y_max, pos[1]]) + overshot_pix_ct
                else:
                    x, y = pos
            return [int(x), int(y)]

        def _get_sign_from_dir(dir):
            if dir in ["left", "top"]:
                return ">="
            elif dir in ["right", "bottom"]:
                return "<="

        assert (
            len(shapes) == 2 and len(anchors) == 2
        ), "shapes and anchors must be list of two items"
        dirs = []
        anchor_pos = []
        for shape, anchor in zip(shapes, anchors):
            dirs.append(shape.get_proper_extention_dir_for_one_anchor(anchor))
            anchor_pos.append(
                shape.compute_anchor_pos_after_transformation(
                    anchor, return_pos_only=True
                )
            )

        if direct_connection:
            line_pos = []
            for _pos, _dir in zip(anchor_pos, dirs):
                pos_offset = _apply_offset(_pos, _dir)
                if (_pos == anchor_pos[0]).all():
                    line_pos = line_pos + [_pos, pos_offset]
                else:
                    line_pos = line_pos + [pos_offset, _pos]
            return np.array(line_pos).astype(int)

            # return np.array(anchor_pos).astype(int)

        dir0, dir1 = dirs
        anchor_pos_offset = [
            _apply_offset(_pos, _dir) for _pos, _dir in zip(anchor_pos, dirs)
        ]

        # if direct_connection:
        # return np.array(anchor_pos_offset).astype(int)

        if ("left" not in dirs) and ("right" not in dirs):
            if (dirs == ["top", "top"]) or (dirs == ["bottom", "bottom"]):
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                    anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                )
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                    anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                )
                if dirs == ["top", "top"]:
                    y_min = min(
                        [
                            first_anchor_pos_after_extend[1],
                            second_anchor_pos_after_extend[1],
                        ]
                    )
                else:
                    y_min = max(
                        [
                            first_anchor_pos_after_extend[1],
                            second_anchor_pos_after_extend[1],
                        ]
                    )
                first_anchor_pos_after_extend = [
                    first_anchor_pos_after_extend[0],
                    y_min,
                ]
                second_anchor_pos_after_extend = [
                    second_anchor_pos_after_extend[0],
                    y_min,
                ]
                line_nodes = [
                    anchor_pos[0],
                    anchor_pos_offset[0],
                    first_anchor_pos_after_extend,
                    second_anchor_pos_after_extend,
                    anchor_pos_offset[1],
                    anchor_pos[1],
                ]
            else:
                if (
                    (dir0 == "top")
                    and (anchor_pos_offset[0][1] < anchor_pos_offset[1][1])
                ) or (
                    (dir0 == "bottom")
                    and (anchor_pos_offset[0][1] > anchor_pos_offset[1][1])
                ):
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                    )
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                    )
                    x_cen = (anchor_pos_offset[0][0] + anchor_pos_offset[1][0]) / 2
                    first_anchor_pos_after_extend_cen = [
                        x_cen,
                        first_anchor_pos_after_extend[1],
                    ]
                    second_anchor_pos_after_extend_cen = [
                        x_cen,
                        second_anchor_pos_after_extend[1],
                    ]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        first_anchor_pos_after_extend,
                        first_anchor_pos_after_extend_cen,
                        second_anchor_pos_after_extend_cen,
                        second_anchor_pos_after_extend,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
                else:
                    if anchor_pos_offset[0][1] < anchor_pos_offset[1][1]:
                        cross_pt = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]]
                    else:
                        cross_pt = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        cross_pt,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
        elif ("top" not in dirs) and ("bottom" not in dirs):
            if (dirs == ["left", "left"]) or (dirs == ["right", "right"]):
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                    anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                )
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                    anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                )
                if dirs == ["left", "left"]:
                    x_min = min(
                        [
                            first_anchor_pos_after_extend[0],
                            second_anchor_pos_after_extend[0],
                        ]
                    )
                else:
                    x_min = max(
                        [
                            first_anchor_pos_after_extend[0],
                            second_anchor_pos_after_extend[0],
                        ]
                    )
                first_anchor_pos_after_extend = [
                    x_min,
                    first_anchor_pos_after_extend[1],
                ]
                second_anchor_pos_after_extend = [
                    x_min,
                    second_anchor_pos_after_extend[1],
                ]
                line_nodes = [
                    anchor_pos[0],
                    anchor_pos_offset[0],
                    first_anchor_pos_after_extend,
                    second_anchor_pos_after_extend,
                    anchor_pos_offset[1],
                    anchor_pos[1],
                ]
            else:
                if (
                    (dir0 == "left")
                    and (anchor_pos_offset[0][0] < anchor_pos_offset[1][0])
                ) or (
                    (dir0 == "right")
                    and (anchor_pos_offset[0][0] > anchor_pos_offset[1][0])
                ):
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                    )
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                    )
                    y_cen = (anchor_pos_offset[0][1] + anchor_pos_offset[1][1]) / 2
                    first_anchor_pos_after_extend_cen = [
                        first_anchor_pos_after_extend[0],
                        y_cen,
                    ]
                    second_anchor_pos_after_extend_cen = [
                        second_anchor_pos_after_extend[0],
                        y_cen,
                    ]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        first_anchor_pos_after_extend,
                        first_anchor_pos_after_extend_cen,
                        second_anchor_pos_after_extend_cen,
                        second_anchor_pos_after_extend,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
                else:
                    if anchor_pos_offset[0][1] < anchor_pos_offset[1][1]:
                        cross_pt = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]]
                    else:
                        cross_pt = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        cross_pt,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
        else:  # mixture of top/bottom and left/right
            if dir0 in ["top", "bottom"]:
                ref_x, ref_y = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]]
                check_x, check_y = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]]
                check_result_x = eval(f"{check_x}{_get_sign_from_dir(dir1)}{ref_x}")
                check_result_y = eval(f"{check_y}{_get_sign_from_dir(dir0)}{ref_y}")
                if check_result_x and check_result_y:
                    cross_pt = [ref_x, ref_y]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        cross_pt,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
                else:
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                    )
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                    )
                    cross_pt = [
                        second_anchor_pos_after_extend[0],
                        first_anchor_pos_after_extend[1],
                    ]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        first_anchor_pos_after_extend,
                        cross_pt,
                        second_anchor_pos_after_extend,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
            else:
                ref_x, ref_y = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]]
                check_x, check_y = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]]
                check_result_x = eval(f"{check_x}{_get_sign_from_dir(dir0)}{ref_x}")
                check_result_y = eval(f"{check_y}{_get_sign_from_dir(dir1)}{ref_y}")
                if check_result_x and check_result_y:
                    cross_pt = [ref_x, ref_y]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        cross_pt,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
                else:
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[0], dir0, anchor_pos_offset[1]
                    )
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(
                        anchor_pos_offset[1], dir1, anchor_pos_offset[0]
                    )
                    cross_pt = [
                        first_anchor_pos_after_extend[0],
                        second_anchor_pos_after_extend[1],
                    ]
                    line_nodes = [
                        anchor_pos[0],
                        anchor_pos_offset[0],
                        first_anchor_pos_after_extend,
                        cross_pt,
                        second_anchor_pos_after_extend,
                        anchor_pos_offset[1],
                        anchor_pos[1],
                    ]
        return np.array(line_nodes).astype(int)


from taurus.qt.qtgui.container import TaurusWidget


class shapeContainer(TaurusWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.set_parent()
        self.build_shapes()
        self.composite_shape = shapeComposite(
            shapes=self.shapes[0:-2],
            anchor_args=[4, 3, 3, 3, 3],
            alignment_pattern={
                "shapes": [[0, 1], [0, 2], [0, 3], [0, 4]],
                "anchors": [
                    ["cen", "cen"],
                    ["anchor_bottom_0", "anchor_top_1"],
                    ["anchor_bottom_1", "anchor_top_1"],
                    ["anchor_bottom_2", "anchor_top_1"],
                ],
                "gaps": [0.3, 0.3, 0.3, 13],
                "ref_anchors": [
                    ["bottom", "bottom"],
                    ["bottom", "top"],
                    ["bottom", "top"],
                    ["bottom", "top"],
                ],
            },
            connection_pattern={
                "shapes": [[1, 2], [3, 4]],
                "anchors": [
                    ["left", "right"],
                    ["top", "top"],
                ],
            },
        )

        self.composite_shape_2 = shapeComposite(
            shapes=[self.shapes[i] for i in [-1, -3, -4, -5, -6, -2]],
            anchor_args=[4, 3, 3, 3, 3, 3],
            alignment_pattern={
                "shapes": [[0, 1], [0, 2], [0, 3], [0, 4], [0, 5]],
                "anchors": [
                    ["left", "right"],
                    ["top", "bottom"],
                    ["right", "left"],
                    ["bottom", "top"],
                    ["cen", "cen"],
                ],
                "gaps": [0.3, 0.3, 0.3, 0.3, 0.3],
                "ref_anchors": [
                    ["bottom", "bottom"],
                    ["bottom", "top"],
                    ["bottom", "top"],
                    ["bottom", "top"],
                    ["bottom", "top"],
                ],
            },
            connection_pattern={
                "shapes": [[1, 2], [3, 4], [0, 0], [0, 0], [0, 0], [0, 0]],
                "anchors": [
                    ["left", "right"],
                    ["top", "top"],
                    ["top", "left"],
                    ["left", "bottom"],
                    ["bottom", "right"],
                    ["right", "top"],
                ],
                "connect_types": [False, False, True, True, True, True],
            },
        )
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.test_rotate_shape)
        self.test_connection_or = ["bottom", "top"]
        # self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])

    # def set_parent(self, parent):
    # self.parent = parent
    def set_parent(self):
        self.parent = findMainWindow()

    def build_shapes(self):
        self.shapes = [
            rectangle(
                dim=[200, 180, 100 * 1.0, 100 * 1.0],
                rotation_center=None,
                transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
            ),
            rectangle(
                dim=[100, 300, 20 * 1.0, 20 * 1.0],
                rotation_center=[110, 310],
                transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
            ),
            rectangle(
                dim=[100, 300, 20 * 1.0, 20 * 1.0],
                rotation_center=[110, 310],
                transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
            ),
            rectangle(
                dim=[100, 300, 20 * 1.0, 20 * 1.0],
                rotation_center=[110, 310],
                transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
            ),
            rectangle(
                dim=[100, 300, 20 * 1.0, 20 * 1.0],
                rotation_center=[110, 310],
                transformation={"rotate": 0, "translate": (0, 0), "scale": 1},
            ),
            isocelesTriangle(dim=[500, 500, 69.28, 60]),
            circle(dim=[700, 400, 80]),
        ]  # ,\
        #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)}),\
        #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)}),\
        #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)})]# \
        #    rectangle(dim = [300,100,80,40],rotation_center = [300,100], transformation={'rotate':0, 'translate':(50,20)})]
        #    rectangle(dim = [500,100,40,80],transformation={'rotate':0, 'translate':(0,0)}), \
        #    rectangle(dim = [500,100,80,80],transformation={'rotate':0, 'translate':(0,0)})]

    def align_multiple_shapes(self, shapes, orientations):
        buildTools.align_multiple_shapes(shapes, orientations)

    def align_two_shapes(self, ref_shape, target_shape, orientations=["bottom", "top"]):
        buildTools.align_two_shapes(ref_shape, target_shape, orientations)

    def _test_get_rot_center_lines(self, which_shape=0, offset=20):
        cen = np.array(self.shapes[which_shape].rot_center) + np.array(
            self.shapes[which_shape].transformation["translate"]
        )
        line_hor_left = cen - [offset, 0]
        line_hor_right = cen + [offset, 0]
        line_ver_top = cen - [0, offset]
        line_ver_bottom = cen + [0, offset]
        return list(line_hor_left) + list(line_hor_right), list(line_ver_top) + list(
            line_ver_bottom
        )

    def _test_connection(self, qp):
        lines = self.make_line_connection_btw_two_anchors(
            self.shapes, self.test_connection_or
        )
        self.test_draw_connection_lines(qp, lines)

    def _test_composite_shape(self, qp):
        for line in self.composite_shape.lines + self.composite_shape_2.lines:
            self.test_draw_connection_lines(qp, line)

    def paintEvent(self, a0) -> None:
        qp = QPainter()
        qp.begin(self)
        # self._test_connection(qp)
        self._test_composite_shape(qp)
        # for each in self.shapes:
        for each in self.composite_shape.shapes:
            qp.resetTransform()
            each.paint(qp)
        for each in self.composite_shape_2.shapes:
            qp.resetTransform()
            each.paint(qp)
        # qp.resetTransform()
        # self.shapes[-1].paint(qp)
        # qp.resetTransform()
        # self.shapes[-2].paint(qp)
        qp.resetTransform()
        qp.setPen(QPen(Qt.green, 4, Qt.SolidLine))
        hor, ver = self._test_get_rot_center_lines()
        qp.drawLine(*[int(each) for each in hor])
        qp.drawLine(*[int(each) for each in ver])
        qp.end()

    def test_draw_connection_lines(self, qp, line_nodes):
        qp.setPen(QPen(Qt.green, 4, Qt.SolidLine))
        for i in range(len(line_nodes) - 1):
            pts = list(line_nodes[i]) + list(line_nodes[i + 1])
            qp.drawLine(*pts)

    def start_(self):
        self.test_timer.start(200)

    def stop_(self):
        self.test_timer.stop()

    def test_rotate_shape(self):
        self.composite_shape.shapes[0].transformation = {
            "rotate": (self.composite_shape.shapes[0].transformation["rotate"] + 10)
            % 360,
            "translate": self.composite_shape.shapes[0].transformation["translate"],
        }
        self.composite_shape_2.shapes[0].transformation = {
            "rotate": (self.composite_shape_2.shapes[0].transformation["rotate"] + 10)
            % 360,
            "translate": self.composite_shape_2.shapes[0].transformation["translate"],
        }
        # self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])
        # self.align_two_shapes(ref_shape=self.shapes[0], target_shape=self.shapes[1], orientations=  ['bottom', 'top'])
        self.composite_shape.build_composite()
        self.composite_shape_2.build_composite()
        for each in self.composite_shape.shapes + self.composite_shape_2.shapes:
            each.cursor_pos_checker(self.last_x, self.last_y)
        self.update()

    def make_line_connection_btw_two_anchors(
        self, shapes, anchors, short_head_line_len=10
    ):
        return buildTools.make_line_connection_btw_two_anchors(
            shapes, anchors, short_head_line_len
        )

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        if self.parent != None:
            self.parent.statusbar.showMessage(
                "Mouse coords: ( %d : %d )" % (event.x(), event.y())
            )
        for each in (
            self.composite_shape.shapes
            + self.shapes[-2:]
            + self.composite_shape_2.shapes
        ):
            each.cursor_pos_checker(event.x(), event.y())
        self.update()
