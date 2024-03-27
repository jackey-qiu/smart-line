# -*- coding: utf-8 -*-
import os

from smart.gui.widgets.table_tree_widgets import CopyTable

from smart.util.geometry_transformation import rotatePoint
import numpy as np
# from numpy import (array, dot, arccos, clip)
from numpy.linalg import norm
import math
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from pathlib import Path
ui_file_folder = Path(__file__).parent.parent / 'ui'

def test_FiducialMarkerWidget(self):
    """

    :param self:
    :return:
    """
    image = self.mdi_field_widget.field_img[-1]
    dset =  self.mdi_field_widget.field_list[-1]
    if isinstance(dset, dict):
        attrs = dset
    else:
        print(type(dset))
    dialog = FiducialMarkerWidget(self, image, attrs=attrs)
    self.mdi_field_widget.field.fiducialMarkerAdded_sig.connect(dialog.add_field_tool)
    dialog.show()

class MarkerTable(CopyTable):
    """
    Class for statistical details on the fit
    """
    removeTool_sig = Signal(object)
    def __init__(self, parent=None):
        super(CopyTable, self).__init__(parent)
        self._parent=parent
        self._reset()
        self.remove_buttons = []
        self.field_tool_list = []
        self.positions = []
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        # self.setMaximumHeight(QtWidgets.QDesktopWidget().screenGeometry(QtWidgets.QDesktopWidget().primaryScreen()).height() // 3)

    def _reset(self):
        """
        Reset the table to the empty contents
        """
        self.clear()
        self.setRowCount(0)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Original Image Feature Position", "Sample Feature Position", "Action"])

    def add_field_tool(self, tool):
        pattern = tool.getLocalHandlePositions()
        # for i, p in enumerate(pattern):
        self.add_position(pattern[0][1], pattern[1][1])
        self.field_tool_list.insert(0,tool)

    def add_position(self, start_loc, end_loc):
        """
        Append an entry to the table. an average of all transformations is computed
        :param start_loc:
        :param end_loc:
        :return:
        """
        self.hide()
        rowCount = self.rowCount()
        if rowCount>=2:
            self.remove_row(1)
        self.insertRow(0)

        item = QtWidgets.QTableWidgetItem()
        item.setText("x = {:.4f}; y = {:.4f}".format(start_loc.x()/1000, start_loc.y()/1000))
        self.setItem(0, 0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setText("x = {:.4f}; y = {:.4f}".format(end_loc.x()/1000, end_loc.y()/1000))
        self.setItem(0, 1, item)
        remove_btn = QtWidgets.QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_button_clicked)
        self.remove_buttons.insert(0,remove_btn)
        self.setCellWidget(0, 2, remove_btn)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.show()

    def remove_row(self, idx):
        """
        Remove this row from the table
        :return:
        """
        self.removeRow(idx)
        del self.remove_buttons[idx]

        tool = self.field_tool_list[idx]
        # // remove the corresponding item from the field
        self.removeTool_sig.emit(tool)
        del self.field_tool_list[idx]

    def remove_button_clicked(self):
        if self.sender() in self.remove_buttons:
            idx = self.remove_buttons.index(self.sender())
            self.remove_row(idx)

    def reset_all(self):
        """
        Resets the position, and removes the tools
        :return:
        """
        self.remove_row(1)
        self.remove_row(0)

    def get_positions(self):
        """
        return the positions of all active tools in the workspace
        :return:
        """
        positions = []
        for tool in self.field_tool_list:
            pattern = tool.getLocalHandlePositions()
            point1 = pattern[0][1]
            point2 = pattern[1][1]
            positions.insert(0,[point1, point2])
        return positions


class FiducialMarkerWidget_wrapper(object):

    def __init__(self):
        self._parent=self
        self.tbl_markers_fiducial = MarkerTable(self._parent)
        self.tbl_markers_fiducial.removeTool_sig.connect(self.removeTool_sig.emit)
        self.grid_alignment_mark.addWidget(self.tbl_markers_fiducial)
        self.scale_factor = 1

    def update_fiducial(self):
        if self.update_field_current == None:
            return
        self.image_fiducial = self.update_field_current
        self.attrs_fiducial = self.update_field_current.loc
        self.attrs_fiducial['Outline_r'] = self.attrs_fiducial['Outline'].copy()
        self.attrs_fiducial['Rotation_r'] = self.attrs_fiducial['Rotation']

    def connect_slots_fiducial(self):
        self.bt_align_fiducial.clicked.connect(self.compute_transformation)
        self.bt_reset_fiducial.clicked.connect(self.reset_transformation)
        self.updateFieldMode_sig.connect(self.field.set_mode)
        self.removeTool_sig.connect(self.field.remove_item)
        self.saveimagedb_sig.connect(self.imageBuffer.writeImgBackup)
        self.field.fiducialMarkerAdded_sig.connect(self.add_field_tool)

    def add_field_tool(self, tool):
        self.tbl_markers_fiducial.add_field_tool(tool)

    def reset_transformation(self):
        """
        :return:
        """

        s = list(self.image_fiducial._scale)
        tr = QtGui.QTransform()
        tr.scale(1 / s[0], 1 / s[1])
        self.image_fiducial.setTransform(tr)
        #self.image.scale(1 / s[0], 1 / s[1])

        # // restore orientation
        if 'Rotation_r' in self.attrs_fiducial.keys():
            self.image_fiducial.setRotation(-self.attrs_fiducial["Rotation"])
            self.image_fiducial.setRotation(self.attrs_fiducial["Rotation_r"])
            self.attrs_fiducial["Rotation"] = self.attrs_fiducial["Rotation_r"]
        else:
            self.image_fiducial.setRotation(-self.attrs_fiducial["Rotation"])
            self.attrs_fiducial['Rotation'] = 0

        self.outl_r = self.attrs_fiducial['Outline_r']
        a = (abs(self.outl_r[1] - self.outl_r[0]),
             abs(self.outl_r[3] - self.outl_r[2]))

        x_aspect = self.image_fiducial.pixmap.width() / a[0]
        y_aspect = self.image_fiducial.pixmap.height() / a[1]
        s = (1 / x_aspect, 1 / y_aspect)
        tr = QtGui.QTransform()
        tr.scale(s[0], s[1])
        self.image_fiducial.setTransform(tr)
        self.image_fiducial._scale = (s[0], s[1])

        # self.move_box.blockSignals(False)
        self.image_fiducial.setPos(QtCore.QPointF(self.outl_r[0], self.outl_r[2]))
        self.attrs_fiducial['Outline'] = self.attrs_fiducial['Outline_r']
        self.tbl_markers_fiducial.reset_all()
        # self.bt_align.setEnabled(True)
        # self.bt_reset.setEnabled(False)
        self.saveimagedb_sig.emit()

    def _angle_bw_vectors(self, v1, v2):
        #v1 is supposed to be the ref vector on the sample
        #v2 is supposed to be the ref vector on the image
        #return the angle in degree between v1 and v2, sign awared
        #if mess up, the sign of calculated angle will be opposite
        #according to the rotation sense, the following is ture
        #rotating the v1 by the calcualted angle in counterwise direction, it will be in parallel with v2

        v1, v2 = np.array(v1), np.array(v2)
        v1_u, v2_u = v1/np.linalg.norm(v1), v2/np.linalg.norm(v2)
        minor = np.linalg.det(
        np.stack((v1_u[-2:], v2_u[-2:]))
        )
        if minor == 0:
            sign = 1
        else:
            sign = -np.sign(minor)
        dot_p = np.dot(v1_u, v2_u)
        dot_p = min(max(dot_p, -1.0), 1.0)
        return np.rad2deg(sign * np.arccos(dot_p))

    def compute_transformation(self):
        """
        Compute the transform based on the position list.
        :return:
        """
        # // get the scale transform by comparing the difference between the endpoints of the scan
        # point_list = [[point1_img, point1_sample],[point2_img, point2_sample]]
        #each point store a [x, y] coordinates, to get it just using list(point)
        # img has features to be aligned with the sample
        point_list = self.tbl_markers_fiducial.get_positions()
        #reference vector on image and sample
        v_image = np.array(point_list[0][0]-point_list[1][0])
        v_sample = np.array(point_list[0][1]-point_list[1][1])
        #vector pointing from the origin of the image to the first ref point on the image
        v_og_p1_image = np.array(point_list[0][0]-self.image_fiducial.pos())

        #cal the scaling factor
        dis_image = np.linalg.norm(v_image)
        dis_sample = np.linalg.norm(v_sample)
        self.scale_factor = dis_sample / dis_image

        #scale this vector v_og_p1_image
        v_og_p1_image_scaled = v_og_p1_image * self.scale_factor

        #cal the net rotation angle in degree bw vector v_image and v_sample
        net_rotation = self._angle_bw_vectors(v_sample, v_image)

        # // get the current rotation
        current_rotation_degrees = self.attrs_fiducial["Rotation"]
        full_rotation_degrees = current_rotation_degrees + net_rotation

        #rotate the image
        #this rotation is not based on the relative rotation angle but based on the absolute angle
        self.image_fiducial.setRotation(full_rotation_degrees)
        self.attrs_fiducial["Rotation"] = full_rotation_degrees
        # self.image_fiducial.scale(self.scale_factor*s[0], self.scale_factor*s[1])

        #scale the image
        s = list(self.image_fiducial._scale)
        tr = QtGui.QTransform()
        #scale it back according to the original scale
        tr.scale(1/s[0], 1/s[1])
        self.image_fiducial.setTransform(tr)
        #now apply the real scaling factor
        tr = QtGui.QTransform()
        tr.scale(self.scale_factor*(s[0]), self.scale_factor*(s[1]))
        self.image_fiducial.setTransform(tr)
        #store the new scaling factor
        self.image_fiducial._scale = (self.scale_factor*s[0], self.scale_factor*s[1])

        #up to here two feature object should be identical in size and orientation, but still shifted by some translation vector

        #cal the first ref point after scaling and rotation
        p1_image_final = rotatePoint(centerPoint=np.array([0,0]), point = v_og_p1_image_scaled,
                                                  angle=net_rotation) + self.image_fiducial.pos()
        # this p1 final point need to tranlate to the correspoinding p1 on sample
        v_diff_p1 = point_list[0][1] - p1_image_final
        #now move the whole image by this vector
        self.image_fiducial.setPos(self.image_fiducial.pos() + v_diff_p1)

        # // recalculate_all the outline position
        new_outline = self.cal_outl()
        self.attrs_fiducial["Outline"] = new_outline
        # self.bt_align.setEnabled(False)
        # self.bt_reset.setEnabled(True)
        # // save the imageMap in order to save the new position
        self.saveimagedb_sig.emit()

    def cal_outl(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x + width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area
        #roi position
        pos = np.array(self.image_fiducial.pos())
        #width and height
        outl = self.attrs_fiducial['Outline']
        wd, ht = [abs(outl[1] - outl[0])*self.scale_factor,abs(outl[3] - outl[2])*self.scale_factor]
        #rotation angle (0-360)
        ang = math.radians(self.attrs_fiducial['Rotation']%360)
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, outl[-2], outl[-1]]
        return outl

class FiducialMarkerWidget(QtWidgets.QDialog):
    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)
    updateFieldMode_sig = Signal(str)
    removeTool_sig = Signal(object)
    saveimagedb_sig = Signal()
    close_sig = Signal()
    def __init__(self, parent, image, attrs):
        assert isinstance(attrs, dict)
        super(FiducialMarkerWidget,self).__init__(parent)
        
        parent.widget_terminal.update_name_space('fiducial_obj', self)
        uic.loadUi(str(ui_file_folder/'fiducial_markers.ui'), self)
        self._parent=parent
        self.image = image
        self.attrs = attrs
        self.attrs['Outline_r'] = self.attrs['Outline'].copy()
        self.attrs['Rotation_r'] = self.attrs['Rotation']
        self.tbl_markers = MarkerTable(self._parent)
        self.tbl_markers.removeTool_sig.connect(self.removeTool_sig.emit)
        self.grid_alignment_mark.addWidget(self.tbl_markers)
        self.scale_factor = 1
        self.net_rotation = 0
        self.translation = (0,0)
        self.bt_reset.setEnabled(False)
        self.connect_slots()

    def connect_slots(self):
        self.bt_align.clicked.connect(self.compute_transformation)
        self.bt_reset.clicked.connect(self.reset_transformation)
        self.bt_close.clicked.connect(self.close_dialog)

    def initialize_field(self):
        """
        Initialize the pointer mode in the field
        :return:
        """
        self.updateFieldMode_sig.emit("fiducial_marker")

    def close_dialog(self):
        """
        Run on close event
        :return:
        """
        # // remove the fiducial tools
        for tool in self.tbl_markers.field_tool_list:
            self.removeTool_sig.emit(tool)
        # // switch to navigate mode (check the main which one is selected)
        self.updateFieldMode_sig.emit("select")
        self.close_sig.emit()
        # // remove the two alginment tools from the workspace
        
        self._parent.widget_terminal.update_name_space('fiducial_obj', None)
        self.close()

    def add_field_tool(self, tool):
        self.tbl_markers.add_field_tool(tool)




    def reset_transformation(self):
        """
        :return:
        """

        s = list(self.image._scale)
        tr = QtGui.QTransform()
        tr.scale(1 / s[0], 1 / s[1])
        self.image.setTransform(tr)
        #self.image.scale(1 / s[0], 1 / s[1])

        # // restore orientation
        if 'Rotation_r' in self.attrs.keys():
            self.image.setRotation(-self.attrs["Rotation"])
            self.image.setRotation(self.attrs["Rotation_r"])
            self.attrs["Rotation"] = self.attrs["Rotation_r"]
        else:
            self.image.setRotation(-self.attrs["Rotation"])
            self.attrs['Rotation'] = 0

        self.outl_r = self.attrs['Outline_r']
        a = (abs(self.outl_r[1] - self.outl_r[0]),
             abs(self.outl_r[3] - self.outl_r[2]))

        x_aspect = self.image.pixmap.width() / a[0]
        y_aspect = self.image.pixmap.height() / a[1]
        s = (1 / x_aspect, 1 / y_aspect)
        tr = QtGui.QTransform()
        tr.scale(s[0], s[1])
        self.image.setTransform(tr)
        self.image._scale = (s[0], s[1])

        # self.move_box.blockSignals(False)
        self.image.setPos(QtCore.QPointF(self.outl_r[0], self.outl_r[2]))
        self.attrs['Outline'] = self.attrs['Outline_r']
        self.tbl_markers.reset_all()
        self.bt_align.setEnabled(True)
        self.bt_reset.setEnabled(False)
        self.saveimagedb_sig.emit()

    def _angle_bw_vectors(self, v1, v2):
        #v1 is supposed to be the ref vector on the sample
        #v2 is supposed to be the ref vector on the image
        #return the angle in degree between v1 and v2, sign awared
        #if mess up, the sign of calculated angle will be opposite
        #according to the rotation sense, the following is ture
        #rotating the v1 by the calcualted angle in counterwise direction, it will be in parallel with v2

        v1, v2 = np.array(v1), np.array(v2)
        v1_u, v2_u = v1/np.linalg.norm(v1), v2/np.linalg.norm(v2)
        minor = np.linalg.det(
        np.stack((v1_u[-2:], v2_u[-2:]))
        )
        if minor == 0:
            sign = 1
        else:
            sign = -np.sign(minor)
        dot_p = np.dot(v1_u, v2_u)
        dot_p = min(max(dot_p, -1.0), 1.0)
        return np.rad2deg(sign * np.arccos(dot_p))

    def compute_transformation(self):
        """
        Compute the transform based on the position list.
        :return:
        """
        # // get the scale transform by comparing the difference between the endpoints of the scan
        # point_list = [[point1_img, point1_sample],[point2_img, point2_sample]]
        #each point store a [x, y] coordinates, to get it just using list(point)
        # img has features to be aligned with the sample
        point_list = self.tbl_markers.get_positions()
        #reference vector on image and sample
        v_image = np.array(point_list[0][0]-point_list[1][0])
        v_sample = np.array(point_list[0][1]-point_list[1][1])
        #vector pointing from the origin of the image to the first ref point on the image
        v_og_p1_image = np.array(point_list[0][0]-self.image.pos())

        #cal the scaling factor
        dis_image = np.linalg.norm(v_image)
        dis_sample = np.linalg.norm(v_sample)
        self.scale_factor = dis_sample / dis_image

        #scale this vector v_og_p1_image
        v_og_p1_image_scaled = v_og_p1_image * self.scale_factor

        #cal the net rotation angle in degree bw vector v_image and v_sample
        self.net_rotation = self._angle_bw_vectors(v_sample, v_image)

        # // get the current rotation
        current_rotation_degrees = self.attrs["Rotation"]
        full_rotation_degrees = current_rotation_degrees + self.net_rotation

        #rotate the image
        #this rotation is not based on the relative rotation angle but based on the absolute angle
        self.image.setRotation(full_rotation_degrees)
        self.attrs["Rotation"] = full_rotation_degrees
        # self.image.scale(self.scale_factor*s[0], self.scale_factor*s[1])

        #scale the image
        s = list(self.image._scale)
        tr = QtGui.QTransform()
        #scale it back according to the original scale
        tr.scale(1/s[0], 1/s[1])
        self.image.setTransform(tr)
        #now apply the real scaling factor
        tr = QtGui.QTransform()
        tr.scale(self.scale_factor*(s[0]), self.scale_factor*(s[1]))
        self.image.setTransform(tr)
        #store the new scaling factor
        self.image._scale = (self.scale_factor*s[0], self.scale_factor*s[1])

        #up to here two feature object should be identical in size and orientation, but still shifted by some translation vector

        #cal the first ref point after scaling and rotation
        p1_image_final = rotatePoint(centerPoint=np.array([0,0]), point = v_og_p1_image_scaled,
                                                  angle=self.net_rotation) + self.image.pos()
        # this p1 final point need to tranlate to the correspoinding p1 on sample
        v_diff_p1 = point_list[0][1] - p1_image_final
        #now move the whole image by this vector
        self.image.setPos(self.image.pos() + v_diff_p1)

        # // recalculate_all the outline position
        new_outline = self.cal_outl()
        self.attrs["Outline"] = new_outline
        '''
        new_outline = self.attrs["Outline"]
        # // calculate the position of the left top corner through a rotation of the coordinate system
        left_top_x = (new_outline[1]-new_outline[0])*self.scale_factor/2.0
        left_top_y = (new_outline[3] - new_outline[2]) * self.scale_factor/2.0
        shift = rotatePoint(centerPoint=[left_top_x,left_top_y], point=[0, 0],
                                                        angle=self.net_rotation)
        new_outline[0] = self.image.pos().x() - shift[0]
        new_outline[1] =  left_top_x*2.0 + new_outline[0]
        new_outline[2] = self.image.pos().y() - shift[1]
        new_outline[3] = new_outline[2] + left_top_y*2.0
        '''
        self.bt_align.setEnabled(False)
        self.bt_reset.setEnabled(True)
        # // save the imageMap in order to save the new position
        self.saveimagedb_sig.emit()

    def cal_outl(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x + width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area
        #roi position
        pos = np.array(self.image.pos())
        #width and height
        outl = self.attrs['Outline']
        wd, ht = [abs(outl[1] - outl[0])*self.scale_factor,abs(outl[3] - outl[2])*self.scale_factor]
        #rotation angle (0-360)
        ang = math.radians(self.attrs['Rotation']%360)
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, outl[-2], outl[-1]]
        return outl

    def compute_transformation_old(self):
        """
        Compute the transform based on the position list.
        :return:
        """
        import math
        # // get the scale transform by comparing the difference between the endpoints of the scan
        # point_list = [[point1_img, point1_sample],[point2_img, point2_sample]]
        #each point store a [x, y] coordinates, to get it just using list(point)
        # img has features to be aligned with the sample
        point_list = self.tbl_markers.get_positions()

        # // distance of the points on the image
        dX =(point_list[0][0].x() - point_list[1][0].x())
        dY =(point_list[0][0].y() - point_list[1][0].y())
        dis_image = math.sqrt(dX ** 2 + dY ** 2)

        # // calculate the rotation
        rot_image = math.atan2(dX , dY)

        # // distance of the points on the sample
        dX =(point_list[0][1].x() - point_list[1][1].x())
        dY =(point_list[0][1].y() - point_list[1][1].y())
        dis_sample = math.sqrt(dX ** 2 + dY ** 2)

        self.scale_factor = dis_sample / dis_image

        # // calculate the rotation
        rot_sample = math.atan2(dX , dY)

        # // distance between the origin of the image and the first point on the image
        origin = self.image.pos()
        distance_origin_x = origin.x() - point_list[0][0].x()
        distance_origin_y = origin.y() - point_list[0][0].y()
        dis_orgin = math.sqrt(distance_origin_x ** 2 + distance_origin_y ** 2)

        # // scale the distance to the origin
        new_distance_origin_x = distance_origin_x*self.scale_factor
        new_distance_origin_y = distance_origin_y * self.scale_factor

        # // calculate translation of the left corner
        shift_x = point_list[0][1].x() - point_list[0][0].x()
        shift_y = point_list[0][1].y() - point_list[0][0].y()
        shift_x += new_distance_origin_x - distance_origin_x
        shift_y += new_distance_origin_y - distance_origin_y

        self.net_rotation = rot_image-rot_sample
        # // report in degrees
        net_rotation_degrees = (self.net_rotation/(2*math.pi))*360

        # // get the current rotation
        current_rotation_degrees = self.attrs["Rotation"]
        current_rotation = (current_rotation_degrees/360.0)*2*math.pi
        full_rotation_degrees = current_rotation_degrees + net_rotation_degrees
        full_rotation = (full_rotation_degrees/360.0)*2*math.pi

        # % reset the scaling to 1/1 prior to rotation
        s = list(self.image._scale)

        # self.image.scale(1 / s[0], 1 / s[1])
        tr = QtGui.QTransform()
        tr.scale(1 / s[0], 1 / s[1])
        self.image.setTransform(tr)

        # self.image.rotate(net_rotation_degrees)
        # self.image.setRotation(net_rotation_degrees)
        #this rotation is not based on the relative rotation angle but based on the absolute angle
        self.image.setRotation(full_rotation_degrees)
        self.attrs["Rotation"] = full_rotation_degrees
        # self.image.scale(self.scale_factor*s[0], self.scale_factor*s[1])

        tr = QtGui.QTransform()
        tr.scale(self.scale_factor*s[0], self.scale_factor*s[1])
        self.image.setTransform(tr)

        self.image._scale = (self.scale_factor*s[0], self.scale_factor*s[1])

        # // get the pure translation component by applying the coordinate transformation for rotation in the XY plane
        # if self.net_rotation - current_rotation != 0:
        translation_component = QtCore.QPointF(shift_x, shift_y)
        self.image.setPos(self.image.pos() + translation_component)
        rotation_shift = point_list[0][1] - rotatePoint(centerPoint=self.image.pos(), point=point_list[0][1],
                                                  angle=net_rotation_degrees)
        self.image.setPos(self.image.pos() + rotation_shift)

        # // recalculate_all the outline position
        new_outline = self.attrs["Outline"]
        # // calculate the position of the left top corner through a rotation of the coordinate system
        left_top_x = (new_outline[1]-new_outline[0])*self.scale_factor/2.0
        left_top_y = (new_outline[3] - new_outline[2]) * self.scale_factor/2.0
        shift = rotatePoint(centerPoint=[left_top_x,left_top_y], point=[0, 0],
                                                        angle=net_rotation_degrees)
        new_outline[0] = self.image.pos().x() - shift[0]
        new_outline[1] =  left_top_x*2.0 + new_outline[0]
        new_outline[2] = self.image.pos().y() - shift[1]
        new_outline[3] = new_outline[2] + left_top_y*2.0
        self.bt_align.setEnabled(False)
        self.bt_reset.setEnabled(True)
        self.attrs["Outline"] = new_outline
        print('vjin',net_rotation_degrees, dis_sample, dis_image, dis_sample / dis_image)
        # // save the imageMap in order to save the new position
        self.saveimagedb_sig.emit()
