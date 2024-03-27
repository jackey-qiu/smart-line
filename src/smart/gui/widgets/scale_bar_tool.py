# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

if os.name == "nt":
    pass
"""
Module manages the advanced settings, and various other settings GUI
"""

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class scaleAnchor(object):
    def __init__(self):
        self.__parent = None
        self.__parentAnchor = None
        self.__itemAnchor = None
        self.__offset = (0, 0)
        if hasattr(self, 'geometryChanged'):
            self.geometryChanged.connect(self.__geometryChanged)

    def anchor(self, itemPos, parentPos, offset=(0, 0)):
        """
        Anchors the item at its local itemPos to the item's parent at parentPos.
        Both positions are expressed in values relative to the size of the item or parent;
        a value of 0 indicates left or top edge, while 1 indicates right or bottom edge.

        Optionally, offset may be specified to introduce an absolute offset.

        Example: anchor a box such that its upper-right corner is fixed 10px left
        and 10px down from its parent's upper-right corner::

            box.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-10,10))
        """
        parent = self.parentItem()
        if parent is None:
            if self.__parent is not None:
                self.__parent.geometryChanged.connect(self.__geometryChanged)
            else:
                raise Exception("Cannot anchor; parent is not set.")

        if (self.__parent is not parent) and (parent is not None):
            if self.__parent is not None:
                self.__parent.geometryChanged.disconnect(self.__geometryChanged)

            self.__parent = parent
            parent.geometryChanged.connect(self.__geometryChanged)

        self.__itemAnchor = itemPos
        self.__parentAnchor = parentPos
        self.__offset = offset
        self.__geometryChanged()

    def _update_anchor(self, itemPos, parentPos, offset):
        self.__itemAnchor = itemPos
        self.__parentAnchor = parentPos
        self.__offset = offset
        self.__geometryChanged()

    def __geometryChanged(self):
        if self.__parent is None:
            return
        if self.__itemAnchor is None:
            return
        o = self.mapToParent(pg.Point(0, 0))
        a = self.boundingRect().bottomRight() * pg.Point(self.__itemAnchor)
        a = self.mapToParent(a)
        p = self.__parent.boundingRect().bottomRight() * pg.Point(self.__parentAnchor)
        off = pg.Point(self.__offset)
        pos = p + (o - a) + off
        self.setPos(pos)


class ScaleBar(pg.GraphicsObject, scaleAnchor):
    """
    Displays a rectangular bar to indicate the relative scale of objects on the view.
    """

    def __init__(self, size, magnification_factor=1, height=5, fs=11, brush=None, pen=None, position="Bottom Right",
                 suffix='m'):
        pg.GraphicsObject.__init__(self)
        self.setFlag(self.ItemHasNoContents)
        # self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.axisOrder = 'row-major'
        # // fontsize fs
        self.fs = fs
        if brush is None:
            brush = pg.getConfigOption('foreground')
        self.brush = pg.functions.mkBrush(brush)
        self.pen = pg.functions.mkPen(color=pen)
        self.height = height
        self.size = size
        self.magnification_factor = magnification_factor
        if suffix == "um":
            suffix = "μm"
        self.suffix = suffix
        self.position = position
        self.calculate_position()
        self.si_format = False

        self.scale_background = QtWidgets.QGraphicsRectItem()
        # self.scale_background.setPen(QtCore.Qt.NoPen)
        self.scale_background.setBrush(QtGui.QColor(38, 38, 38, 100))
        self.scale_background.setParentItem(self)

        self.bar = QtWidgets.QGraphicsRectItem()
        self.bar.setPen(self.pen)
        self.bar.setBrush(self.brush)
        self.bar.setParentItem(self)

        self.scale_text = pg.TextItem(anchor=(0.5, 1), color=pen)
        self.zoom_text = pg.TextItem(anchor=(0.5, 1), color=pen)
        self.update_text()

        self.scale_text.setParentItem(self)
        self.zoom_text.setParentItem(self)
        self._scaleAnchor__parent = None

    def update_size(self, size):
        self.size = size
        self.update_text()
        self.updateBar()

    def update_fontsize(self, fs):
        self.fs = fs
        self.update_text()

    def update_text(self):
        if self.si_format:
            self.scale_text.setHtml("<p style='font-size:{}px'>{}</p>".format(self.fs,
                                                                              pg.functions.siFormat(self.size,
                                                                                                    suffix=self.suffix)))

        else:
            # // conversion to mm
            if self.size >= 1000 and self.suffix == "μm":
                size = "{:.3f}".format(self.size / 1000.)
                suffix = "mm"
            else:
                size = self.size
                suffix = self.suffix
            self.scale_text.setHtml("<p style='font-size:{}px'>{} {}</p>".format(self.fs,
                                                                                 size,
                                                                                 suffix))
        self.zoom_text.setHtml("<p style='font-size:{}px'>{:d}x</p>".format(self.fs, int(self.magnification_factor)))

    def update_height(self, heigth):
        self.height = heigth
        self.updateBar()

    def update_position(self, position):
        self.position = position
        self.calculate_position()
        # // forward settings to anchor
        self._update_anchor(itemPos=self.anchor_pos, parentPos=self.anchor_pos, offset=self.offset)
        self.updateBar()

    def calculate_position(self):
        """
        Calculates the position of the bar relative to the screen.

        :return:
        """

        position_list = ["Bottom Right", "Bottom Left", "Top Left", "Top Right"]
        if self.position in position_list:
            if self.position == "Bottom Right":
                self.anchor_pos = (1, 1)
                self.offset = (-30, -10)
            elif self.position == "Top Right":
                self.anchor_pos = (1, 0)
                self.offset = (-30, self.fs * 3.2 + self.height)
            elif self.position == "Top Left":
                self.anchor_pos = (0, 0)
                self.offset = (30, self.fs * 3.2 + self.height)
            elif self.position == "Bottom Left":
                self.anchor_pos = (0, 1)
                self.offset = (30, -10)
            else:
                raise AssertionError
        else:
            self.anchor_pos = (1, 1)
            self.offset = (-30, -30)

    def parentChanged(self):
        if self.parentItem() is None:
            return
        # view = self.parentItem().getViewBox()
        view = self.parentItem()
        if view is None:
            return
        # view.sigRangeChanged.connect(self.updateDelay)
        self.updateDelay()

    def update_color(self, color):
        self.scale_text.setColor(color)
        self.zoom_text.setColor(color)
        self.brush.setColor(color)
        self.pen.setColor(color)
        self.bar.setPen(self.pen)
        self.bar.setBrush(self.brush)

    def updateBar(self):
        if self._scaleAnchor__parent is None:
            print("don't update bar")
            return
        view = self._scaleAnchor__parent
        if view is None:
            return
        p1 = view.mapFromViewToItem(self, QtCore.QPointF(0, 0))
        p2 = view.mapFromViewToItem(self, QtCore.QPointF(self.size, 0))
        w = (p2 - p1).x()

        # // correction when the bar is algined on the left or right
        if "right" in self.position.lower():
            box_alignment_correction = w
            text_alignment_correction = -w / 2.
        else:
            box_alignment_correction = 0
            text_alignment_correction = w / 2.
        self.bar.setRect(QtCore.QRectF(-box_alignment_correction, -self.height, w, self.height))
        self.scale_text.setPos(text_alignment_correction, -self.height)
        self.zoom_text.setPos(text_alignment_correction, -self.height - self.fs * 1.2)

        # // expand the background for very small scales. Otherwise scaling problems occur
        size_limit = 3 * self.fs
        if w < size_limit:
            w = size_limit
            if "right" in self.position.lower():
                box_alignment_correction = 30

        self.scale_background.setRect(
            QtCore.QRectF(-box_alignment_correction - 20, -(self.fs * 2.7) - self.height, w + 40,
                          self.height + self.fs * 2.9))
        self.update()

    def updateDelay(self):
        QtCore.QTimer.singleShot(100, self.updateBar)
        # QtCore.QCoreApplication.instance().processEvents()

    def boundingRect(self):
        return self.bar.rect()#QtCore.QRectF()

    def setParentItem(self, p):
        ret = pg.GraphicsObject.setParentItem(self, p)
        self._scaleAnchor__parent = p
        # ret=self._qtBaseClass.setParentItem(self, p)
        if self.offset is not None:
            offset = pg.Point(self.offset)
            # anchorx = 1 if offset[0] <= 0 else 0
            # anchory = 1 if offset[1] <= 0 else 0
            # anchor = (anchorx, anchory)
            self.anchor(
                itemPos=self.anchor_pos,
                parentPos=self.anchor_pos,
                offset=offset
            )
        return ret

    def paint(self, p, *args):
        # p.setRenderHint(p.Antialiasing)
        # p.drawRect(self.bar.rect())
        self.bar.paint(p, *args)
        self.scale_background.paint(p, *args)
        self.scale_text.paint(p, *args)
        self.zoom_text.paint(p, *args)
        '''
        p.drawRec(0, 0, self.pixmap)
        if self.border is not None:
            p.setPen(self.border)
            p.drawRect(self.boundingRect())
        '''
    def mapToData(self, obj):
        tr = self.inverseDataTransform()
        return tr.map(obj)

    def inverseDataTransform(self):
        """Return the transform that maps from this image's local coordinate
        system to its input array.

        See dataTransform() for more information.
        """
        tr = QtGui.QTransform()
        if self.axisOrder == 'row-major':
            # transpose
            tr.scale(1, -1)
            tr.rotate(-90)
        return tr