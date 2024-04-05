# -*- coding: utf-8 -*-
import os
from pathlib import Path
from PyQt5 import QtGui
from smart.util.util import qt_image_to_array
import pyqtgraph as pg
import numpy as np
import math

class geometry_widget_wrapper(object):
    """
    Module contains tool to change the position and rotation of the image in the workspace.
    """

    def __init__(self):
        self.attrs_geo = None
        self.shape_geo = None
        self.axis_geo = (0,1,2)
        # // disable registration mark tab
        self.tabWidget_2.setTabEnabled(1, False)
        # // enable field view
        self.setEnabled(True)

        self.ent_dimx.setValidator(QtGui.QDoubleValidator(0, 9999999, 3))
        self.ent_dimy.setValidator(QtGui.QDoubleValidator(0, 9999999, 3))
        self.ent_dimz.setValidator(QtGui.QDoubleValidator(0, 9999999, 3))

        self.lineEdit_cx.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))
        self.lineEdit_cy.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))
        self.lineEdit_cz.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))

        self.lineEdit_pxc_x.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))
        self.lineEdit_pxc_y.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))
        self.lineEdit_pxc_z.setValidator(QtGui.QDoubleValidator(0, 9999999, 0))

        self.lineEdit_rot_angle.setValidator(QtGui.QDoubleValidator(0, 9999999, 3))

    #callback whenever switch to a different image, being called once
    def update_geo(self):
        self.attrs_geo = self.update_field_current.loc
        self.img_array_gray = qt_image_to_array(self.update_field_current.pixmap.toImage())
        #array dimension
        self.shape_geo = (self.update_field_current.pixmap.width(), self.update_field_current.pixmap.height(), 1)
        # % get length from outline
        if not 'Outline' in self.attrs_geo.keys():
            self.attrs_geo['Outline'] = [0, self.shape_geo[self.axis_geo[0]], 0, self.shape_geo[self.axis_geo[1]], 0,
                                     self.shape_geo[self.axis_geo[2]]]

        if not "Rotation" in self.attrs_geo.keys():
            self.attrs_geo['Rotation'] = 0

        self._update_input_values()
        self.display_move_box_geo()
        self.save_current_state_geo()
        # // display the selected image in the center
        # self.autoRange(items=[self.update_field_current])

    def connect_slots_geo(self):
        self.pushButton_apply.clicked.connect(self.apply_new_state_geo)
        self.pushButton_reset.clicked.connect(self.reset_move_box_geo)
        self.pushButton_save.clicked.connect(self.save_current_state_geo)
        self.pushButton_tweak_geo.clicked.connect(self.tweak_geo)
        self.pushButton_select_first.clicked.connect(self.highlightFirstImg)
        self.pushButton_select_last.clicked.connect(self.highlightLastImg)
        self.pushButton_next_img.clicked.connect(self.nextImg)
        self.pushButton_pre_img.clicked.connect(self.preImg)
        self.radioButton_select.clicked.connect(lambda: self.switch_mode_from_radio_button_control('select'))
        self.radioButton_fiducial.clicked.connect(lambda: self.switch_mode_from_radio_button_control('fiducial'))
        self.radioButton_dft.clicked.connect(lambda: self.switch_mode_from_radio_button_control('dft'))
        self.radioButton_particle.clicked.connect(lambda: self.switch_mode_from_radio_button_control('particle'))

    def tweak_geo(self):
        which_item = self.comboBox_tweak_item.currentText()
        which_sign = '+' if self.comboBox_tweak_sign.currentText()=='positive' else '-'
        tweak_value = self.doubleSpinBox_tweak_step.value()
        tweak_value_signed = eval(f'{which_sign}{tweak_value}')
        if which_item=='x':
            self.lineEdit_cx.setText(str(float(self.lineEdit_cx.text())+tweak_value_signed))
        elif which_item == 'y':
            self.lineEdit_cy.setText(str(float(self.lineEdit_cy.text())+tweak_value_signed))
        elif which_item == 'rot':
            self.lineEdit_rot_angle.setText(str(float(self.lineEdit_rot_angle.text())+tweak_value_signed))
        self.apply_new_state_geo()

    def highlightFirstImg(self):
        if len(self.field_list)!=0:
            self._clear_borders()
            self.update_field_current = self.field_img[0]
            self._show_border()
            self.update_geo()
        else:
            pass

    def highlightLastImg(self):
        if len(self.field_list)!=0:
            self._clear_borders()
            self.update_field_current = self.field_img[-1]
            self._show_border()
            self.update_geo()
        else:
            pass

    def nextImg(self):
        if self.update_field_current == None:
            pass
        else:
            next_ix = self.field_img.index(self.update_field_current)+1
            if next_ix==len(self.field_list):
                next_ix = 0
            self._clear_borders()
            self.update_field_current = self.field_img[next_ix]
            self._show_border()
            self.update_geo()

    def preImg(self):
        if self.update_field_current == None:
            pass
        else:
            pre_ix = self.field_img.index(self.update_field_current)-1
            self._clear_borders()
            self.update_field_current = self.field_img[pre_ix]
            self._show_border()
            self.update_geo()

    def apply_new_state_geo(self):
        # % apply the settings toward the dataset selected
        def _extract_input_box():
            pixdim = [float(self.ent_dimx.text()), float(self.ent_dimy.text()), float(self.ent_dimz.text())]
            center = [float(self.lineEdit_cx.text()), float(self.lineEdit_cy.text()), float(self.lineEdit_cz.text())]
            pixc = [int(self.lineEdit_pxc_x.text()), int(self.lineEdit_pxc_y.text()), int(self.lineEdit_pxc_z.text())]
            rot = float(self.lineEdit_rot_angle.text())
            return pixdim, center, pixc, rot
        pixdim, center, pixc, rot = _extract_input_box()
        width, height = pixdim[0]*pixc[0], pixdim[1]*pixc[1]
        self.move_box.setAngle(0,center=[0.5,0.5])
        new_roi_pos_before_rotation = pg.Point(center[0] - width/2, center[1]-height/2)
        self.move_box.setPos(new_roi_pos_before_rotation)
        self.move_box.setAngle(rot,center=[0.5,0.5])
        self.move_box.setSize(pg.Point(width, height),center=[0.5,0.5])

    #the state for resetting the roi afterwards will be stored
    def save_current_state_geo(self):
        self.reset_pos = self.update_field_current.pos()
        self.reset_angle = self.attrs_geo["Rotation"]
        outl = self.attrs_geo['Outline']
        self.reset_size = pg.Point(
            outl[1] - outl[0], \
            outl[3] - outl[2])
        
    #set the move_box to saved state
    def reset_move_box_geo(self):
        self.move_box.setPos(self.reset_pos)
        self.move_box.setAngle(self.reset_angle,center=[0,0])
        self.move_box.setSize(self.reset_size,center=[0,0])

    #called once at the beginning
    def display_move_box_geo(self):
        if self.update_field_current:
            if hasattr(self, 'move_box') and type(self.move_box)==pg.ROI:
                self.field.removeItem(self.move_box)
            if not self.update_field_current.isVisible():
                return None
            self.update_field_current.setBorder('r')
            self.reset_pos = self.update_field_current.pos()
            self.reset_angle = self.attrs_geo["Rotation"]
            outl = self.attrs_geo['Outline']
            self.reset_size = pg.Point(
                outl[1] - outl[0], \
                outl[3] - outl[2])
            dash_pen = pg.mkPen((255, 255, 255), width=1, dash=[4, 2])
            self.move_box = pg.ROI(self.reset_pos, size=self.reset_size, angle=self.reset_angle, pen=dash_pen)
            self.move_box.handleSize = 10
            self.move_box.handlePen = pg.mkPen("#FFFFFF")
            self.move_box.addRotateHandle([1, 0], [0.5, 0.5])
            self.move_box.addRotateHandle([0, 1], [0.5, 0.5])
            self.move_box.addScaleHandle([0, 0], [0.5, 0.5])
            self.move_box.addScaleHandle([1, 1], [0.5, 0.5])
            self._lockAspect()
            self.field.addItem(self.move_box)
            self.move_box.sigRegionChangeFinished.connect(self.update_box_geo)

    #callback func when manipulating roi (move_box): ie rotation, scaling, translating
    def update_box_geo(self):
        outl = self.attrs_geo['Outline']
        self.rot = self.move_box.angle()

        # % get the transformation as the delta between the two topleft corners
        # this is needed since move box rotate about center while the filed rotate about the top left corner
        delta_t = self.update_field_current.pos() - self.move_box.pos()

        # % reset the scaling to 1/1 prior to rotation
        s = list(self.update_field_current._scale)
        tr = QtGui.QTransform()
        tr.scale(1 / s[0], 1 / s[1])
        self.update_field_current.setTransform(tr)

        # absolute rather than relative rotation
        self.update_field_current.setRotation(self.rot)
        self.attrs_geo["Rotation"] = self.rot

        # // check for changes in the x scale
        if np.abs(outl[1] - outl[0]) != self.move_box.size()[0]:
            s[0] *= self.move_box.size()[0] / np.abs(outl[1] - outl[0])
            outl[1] = outl[0] + self.move_box.size()[0]

        # // check for changes in the y scale
        if np.abs(outl[3] - outl[2]) != self.move_box.size()[1]:
            s[1] *= self.move_box.size()[1] / np.abs(outl[3] - outl[2])
            outl[3] = outl[2] + self.move_box.size()[1]

        # self.update_field_current.scale(s[0], s[1])
        tr = QtGui.QTransform()
        tr.scale(s[0], s[1])
        self.update_field_current.setTransform(tr)

        self.update_field_current._scale = (s[0], s[1])

        # % apply the transform by moving the image
        # translation offset due to rotation point difference (top left corder vs center)
        self.update_field_current.setPos(self.update_field_current.pos() - delta_t)

        #update the width and height according to the roi
        self.update_field_current.update_dim(self.move_box.size())

        self.attrs_geo['Outline'] = self._cal_outl_from_roi()
        #self.recalc_values()
        self._update_input_values()

    def _cal_outl_from_roi(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x + width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area
        #roi position
        pos = np.array(self.move_box.pos())
        #width and height
        wd, ht = list(self.move_box.size())
        #rotation angle (0-360)
        ang = math.radians(self.move_box.angle()%360)
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, self.attrs_geo['Outline'][-2],self.attrs_geo['Outline'][-1]]
        return outl

    def _lockAspect(self):
        for info in self.move_box.handles:
            h = info["item"]
            info['lockAspect'] = True

    #fill in info based on new outline and rotation values
    def _update_input_values(self):
        """
        Function to update the values currently in the attributes
        :return:
        """
        outl = self.attrs_geo['Outline']
        rot = self.attrs_geo['Rotation']
        self._recalc_values(outl)
        self.ent_dimx.setText(str(round(self.pixdim[0],2)))
        self.ent_dimy.setText(str(round(self.pixdim[1],2)))
        self.ent_dimz.setText(str(round(self.pixdim[2],2)))
        self.lineEdit_cx.setText(str(round(self.center[0],1)))
        self.lineEdit_cy.setText(str(round(self.center[1],1)))
        self.lineEdit_cz.setText(str(round(self.center[2],1)))
        self.lineEdit_outl_x.setText(f"[{round(outl[0],1)},{round(outl[1],1)}]")
        self.lineEdit_outl_y.setText(f"[{round(outl[2],1)},{round(outl[3],1)}]")
        self.lineEdit_outl_z.setText(f"[{round(outl[4],1)},{round(outl[5],1)}]")
        self.lineEdit_pxc_x.setText(f"{int(self.shape_geo[0])}")
        self.lineEdit_pxc_y.setText(f"{int(self.shape_geo[1])}")
        self.lineEdit_pxc_z.setText(f"{int(self.shape_geo[2])}")
        self.lineEdit_rot_angle.setText(str(rot))

    #recal meta info from outline values
    def _recalc_values(self, outl):
        """
        Recalculates the pixdim, aspect ratios and center based on the outline and the dataset shape
        :return:
        """
        if outl[0] != outl[1]:
            self.x_aspect = self.shape_geo[self.axis_geo[0]] / abs(outl[0] - outl[1])
        else:
            self.x_aspect = 1
        if outl[2] != outl[3]:
            self.y_aspect = self.shape_geo[self.axis_geo[1]] / abs(outl[2] - outl[3])
        else:
            self.y_aspect = 1
        if outl[4] != outl[5]:
            self.z_aspect = self.shape_geo[self.axis_geo[2]] / abs(outl[4] - outl[5])
        else:
            self.z_aspect = 1
        # // self.pixdim is the pixel dimensions
        # here we assume each 1by1 pix has a dimension of 1um by 1um
        self.pixdim = [1, 1, 1]
        self.size = [1, 1, 1]
        self.size[0] = outl[1] - outl[0]
        self.size[1] = outl[3] - outl[2]
        self.size[2] = outl[5] - outl[4]
        self.attrs_geo["Size"] = self.size
        self.pixdim[0] = self.size[0] / self.shape_geo[self.axis_geo[0]]
        self.pixdim[1] = self.size[1] / self.shape_geo[self.axis_geo[1]]
        self.pixdim[2] = self.size[2] / self.shape_geo[self.axis_geo[2]]
        self.center = [0, 0, 0]
        self.center[0] = (outl[1] - outl[0]) / 2 + outl[0]
        self.center[1] = (outl[3] - outl[2]) / 2 + outl[2]
        self.center[2] = (outl[5] - outl[4]) / 2 + outl[4]
        self.attrs_geo["Center"] = self.center

'''
class geometry_dialog(QtWidgets.QDialog):
    """
    Module contains tool to change the position and rotation of the image in the workspace.
    """
    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)

    def __init__(self, parent, attrs, shape, axis=(0, 1, 2)):
        super(geometry_dialog, self).__init__(parent)
        uic.loadUi(str(ui_file_folder / 'util_geometry.ui'), self)
        self._parent = parent
        #for testing purpose
        self._parent.geo = self
        #####################
        self.attrs = attrs
        self.shape = shape
        self.axis = axis
        # // disable registration mark tab
        self.tabWidget.setTabEnabled(1, False)
        if len(self.shape) == 2:
            self.shape.append([1])

        # // enable field view
        self._parent.setEnabled(True)

        ## // lock the upper groupbox
        self._parent.gb_list.setEnabled(False)

        self.update_field_current = self._parent.update_field_current

        # % get length from outline
        if not 'Outline' in self.attrs.keys():
            self.attrs['Outline'] = [0, self.shape[self.axis[0]], 0, self.shape[self.axis[1]], 0,
                                     self.shape[self.axis[2]]]
        # // backup original position in the datasset attributes:
        else:
            # % don't overwrite original position
            if not 'Outline_r' in self.attrs.keys():
                self.attrs['Outline_r'] = \
                    self.attrs['Outline']

        if not "Rotation" in self.attrs.keys():
            self.attrs['Rotation'] = 0
        else:
            self.dial_rotation.setValue(int(self.attrs['Rotation']))
        if not "Rotation_r" in self.attrs:
            self.attrs['Rotation_r'] = self.attrs['Rotation']

        self.update_aspect_values()
        self.ent_dimx.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.ent_dimy.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.ent_dimz.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.ent_unitx.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.ent_unity.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.ent_unitz.setValidator(QtGui.QDoubleValidator(0, 9999999, 6))
        self.recalc_values()
        self.reset_input_boxes()
        self.display_move_box()
        # // lock the aspect
        self.cb_aspect_ratio.setChecked(True)
        self.lockAspect()
        # // display the selected image in the center
        self._parent.autoRange(items=[self.update_field_current])

        self.connect_slots()

    def connect_slots(self):
        self.buttonBox_aspect.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_aspect)
        self.buttonBox_aspect.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.restore_move_box)
        self.buttonBox_aspect.accepted.connect(self.ok_aspect)
        self.buttonBox_aspect.rejected.connect(self.reject_dialog)
        self.rb_pixdim.toggled.connect(self.reset_input_boxes)
        self.rb_totdim.toggled.connect(self.reset_input_boxes)
        self.rb_outline.toggled.connect(self.reset_input_boxes)
        self.rb_center.toggled.connect(self.reset_input_boxes)
        self.rb_rotation.toggled.connect(self.reset_input_boxes)
        self.dial_rotation.sliderReleased.connect(self.rotate_box)
        self.cb_aspect_ratio.clicked.connect(self.lockAspect)
        self.ent_dimx.editingFinished.connect(self.update_input_boxes)
        self.ent_dimy.editingFinished.connect(self.update_input_boxes)
        self.ent_dimz.editingFinished.connect(self.update_z)
        self.ent_unitx.editingFinished.connect(self.update_input_boxes)
        self.ent_unitz.editingFinished.connect(self.update_input_boxes)
        self.ent_unitz.editingFinished.connect(self.update_z)

    def ok_aspect(self):
        self.apply_aspect()
        if self.move_box in self._parent.field.allChildren():
            self._parent.field.removeItem(self.move_box)
            self.update_field_current.setBorder(None)
        try:
            pass
        except:
            pass

        self._parent.gb_list.setEnabled(True)
        self._parent.geo = None
        self.accept()

    def retrieve_attrs(self):
        return self.attrs

    def update_z(self):
        # % update the move box when the values in the input boxes have changed
        if self.rb_pixdim.isChecked():
            self.outl[5] = self.outl[4] + float(self.ent_dimz.text()) * self.shape[
                self.axis[2]]
        elif self.rb_center.isChecked():
            # % reposition the center of the z-dimension
            self.outl[4] = float(self.ent_dimz.text()) - self.size[2] // 2
            self.outl[5] = float(self.ent_dimz.text()) + self.size[2] // 2
        elif self.rb_outline.isChecked():
            # % change the pos
            self.outl[4] = float(self.ent_dimz.text())
            self.outl[5] = float(self.ent_unitz.text())
        elif self.rb_totdim.isChecked():
            self.outl[5] = self.outl[4] + float(self.ent_dimz.text())
        else:
            QtCore.qDebug("invalid radiobutton selection")

    def update_aspect_values(self):
        """
        Function to update the values currently in the attributes
        :return:
        """
        import copy
        self.outl = copy.deepcopy(self.attrs['Outline'])
        self.rot = copy.deepcopy(self.attrs['Rotation'])
        self.recalc_values()
        self.lbl_totdim.setText("{:.3f}".format(self.outl[1] - self.outl[0]) + 'x' + "{:.3f}".format(
            self.outl[3] - self.outl[2]) + 'x' + "{:.3f}".format(
            self.outl[5] - self.outl[4]))
        self.lbl_outline.setText(
            "[" + "{:.3f}".format(self.outl[0]) + "," + "{:.3f}".format(self.outl[1]) + "]" + "\n" +
            "[" + "{:.3f}".format(self.outl[2]) + "," + "{:.3f}".format(self.outl[3]) + "]" + "\n" +
            "[" + "{:.3f}".format(self.outl[4]) + "," + "{:.3f}".format(self.outl[5]) + "]")
        self.lbl_aspect_ratio.setText(
            "{:.3f}".format(self.x_aspect / self.y_aspect) + ',' + "{:.3f}".format(
                self.x_aspect / self.z_aspect) + ',' + "{:.3f}".format(
                self.y_aspect / self.z_aspect))
        if not 'AspectRatio' in self.attrs.keys():
            self.attrs.update({'AspectRatio': self.pixdim})
        self.lbl_pixcount.setText("{:.3f}".format(self.shape[self.axis[0]]) + 'x' + "{:.3f}".format(
            self.shape[self.axis[1]]) + 'x' + "{:.3f}".format(
            self.shape[self.axis[2]]))
        self.lbl_pixdim.setText(
            "{:.3f}".format(self.pixdim[0]) + 'x' + "{:.3f}".format(self.pixdim[1]) + 'x' + "{:.3f}".format(
                self.pixdim[2]))
        self.lbl_rot.setText("{:.3f}".format(self.rot))
        self.lbl_center_pos.setText("{:.3f}".format(self.attrs["Center"][0]) + 'x' + "{:.3f}".format(
            self.attrs["Center"][1]) + 'x' + "{:.3f}".format(self.attrs["Center"][2]))

    def recalc_values(self):
        """
        Recalculates the pixdim, aspect ratios and center based on the outline and the dataset shape
        :return:
        """
        if self.outl[0] != self.outl[1]:
            self.x_aspect = self.shape[self.axis[0]] / abs(self.outl[0] - self.outl[1])
        else:
            self.x_aspect = 1
        if self.outl[2] != self.outl[3]:
            self.y_aspect = self.shape[self.axis[1]] / abs(self.outl[2] - self.outl[3])
        else:
            self.y_aspect = 1
        if self.outl[4] != self.outl[5]:
            self.z_aspect = self.shape[self.axis[2]] / abs(self.outl[4] - self.outl[5])
        else:
            self.z_aspect = 1
        # // self.pixdim is the pixel dimensions
        self.pixdim = [1, 1, 1]
        self.size = [1, 1, 1]
        self.size[0] = self.outl[1] - self.outl[0]
        self.size[1] = self.outl[3] - self.outl[2]
        self.size[2] = self.outl[5] - self.outl[4]
        self.attrs["Size"] = self.size
        self.pixdim[0] = self.size[0] / self.shape[self.axis[0]]
        self.pixdim[1] = self.size[1] / self.shape[self.axis[1]]
        self.pixdim[2] = self.size[2] / self.shape[self.axis[2]]
        self.center = [0, 0, 0]
        self.center[0] = (self.outl[1] - self.outl[0]) / 2 + self.outl[0]
        self.center[1] = (self.outl[3] - self.outl[2]) / 2 + self.outl[2]
        self.center[2] = (self.outl[5] - self.outl[4]) / 2 + self.outl[4]
        self.attrs["Center"] = self.center

    def reset_input_boxes(self):
        if self.rb_pixdim.isChecked():
            self.lbl_box_x.setText('Pixel dimensions x')
            self.lbl_box_y.setText('Pixel dimensions y')
            self.lbl_box_z.setText('Pixel dimensions z')
            self.ent_dimy.setEnabled(True)
            self.ent_dimz.setEnabled(True)
            self.ent_unitx.setEnabled(False)
            self.ent_unity.setEnabled(False)
            self.ent_unitz.setEnabled(False)
            # // fill in the data in the entry boxes
            self.ent_dimx.setText("{:.3f}".format(self.pixdim[0]))
            self.ent_dimy.setText("{:.3f}".format(self.pixdim[1]))
            self.ent_dimz.setText("{:.3f}".format(self.pixdim[2]))
            self.ent_unitx.setText("")
            self.ent_unity.setText("")
            self.ent_unitz.setText("")
            self.dial_rotation.hide()
            self.ent_dimy.show()
            self.ent_dimz.show()
            self.ent_unity.show()
            self.ent_unitz.show()
            self.lbl_box_y.show()
            self.lbl_box_z.show()
        elif self.rb_center.isChecked():
            self.lbl_box_x.setText('Center x')
            self.lbl_box_y.setText('Center y')
            self.lbl_box_z.setText('Center z')
            self.ent_dimy.setEnabled(True)
            self.ent_dimz.setEnabled(True)
            self.ent_unitx.setEnabled(False)
            self.ent_unity.setEnabled(False)
            self.ent_unitz.setEnabled(False)
            # % fill in the data in the entry boxes
            self.ent_dimx.setText("{:.3f}".format(self.attrs["Center"][0]))
            self.ent_dimy.setText("{:.3f}".format(self.attrs["Center"][1]))
            self.ent_dimz.setText("{:.3f}".format(self.attrs["Center"][2]))
            self.ent_unitx.setText("")
            self.ent_unity.setText("")
            self.ent_unitz.setText("")
            self.dial_rotation.hide()
            self.ent_dimy.show()
            self.ent_dimz.show()
            self.ent_unity.show()
            self.ent_unitz.show()
            self.lbl_box_y.show()
            self.lbl_box_z.show()
        elif self.rb_totdim.isChecked():
            self.lbl_box_x.setText('Size x')
            self.lbl_box_y.setText('Size y')
            self.lbl_box_z.setText('Size z')
            self.ent_dimy.setEnabled(True)
            self.ent_dimz.setEnabled(True)
            self.ent_unitx.setEnabled(False)
            self.ent_unity.setEnabled(False)
            self.ent_unitz.setEnabled(False)
            # % fill in the data in the entry boxes
            self.ent_dimx.setText("{:.3f}".format(self.outl[1] - self.outl[0]))
            self.ent_dimy.setText("{:.3f}".format(self.outl[3] - self.outl[2]))
            self.ent_dimz.setText("{:.3f}".format(self.outl[5] - self.outl[4]))
            self.ent_unitx.setText("")
            self.ent_unity.setText("")
            self.ent_unitz.setText("")
            self.dial_rotation.hide()
            self.ent_dimy.show()
            self.ent_dimz.show()
            self.ent_unity.show()
            self.ent_unitz.show()
            self.lbl_box_y.show()
            self.lbl_box_z.show()
        elif self.rb_outline.isChecked():
            self.lbl_box_x.setText('Outline boundaries x')
            self.lbl_box_y.setText('Outline boundaries y')
            self.lbl_box_z.setText('Outline boundaries z')
            self.ent_dimy.setEnabled(True)
            self.ent_dimz.setEnabled(True)
            self.ent_unitx.setEnabled(True)
            self.ent_unity.setEnabled(True)
            self.ent_unitz.setEnabled(True)
            # % fill in the data in the entry boxes
            self.ent_dimx.setText("{:.3f}".format(self.outl[0]))
            self.ent_dimy.setText("{:.3f}".format(self.outl[2]))
            self.ent_dimz.setText("{:.3f}".format(self.outl[4]))
            self.ent_unitx.setText("{:.3f}".format(self.outl[1]))
            self.ent_unity.setText("{:.3f}".format(self.outl[3]))
            self.ent_unitz.setText("{:.3f}".format(self.outl[5]))
            self.dial_rotation.hide()
            self.ent_dimy.show()
            self.ent_dimz.show()
            self.ent_unity.show()
            self.ent_unitz.show()
            self.lbl_box_y.show()
            self.lbl_box_z.show()
        elif self.rb_rotation.isChecked():
            self.lbl_box_x.setText('Rotation')
            self.lbl_box_y.setText('-')
            self.lbl_box_z.setText('-')
            self.ent_dimy.setEnabled(False)
            self.ent_dimz.setEnabled(False)
            self.ent_unitx.setEnabled(False)
            self.ent_unity.setEnabled(False)
            self.ent_unitz.setEnabled(False)
            # % fill in the data in the entry boxes
            self.ent_dimx.setText("{:3f}".format(self.rot))
            self.ent_dimy.setText("")
            self.ent_dimz.setText("")
            self.ent_unitx.setText("")
            self.ent_unity.setText("")
            self.ent_unitz.setText("")
            self.dial_rotation.show()
            self.ent_dimy.hide()
            self.ent_dimz.hide()
            self.ent_unity.hide()
            self.ent_unitz.hide()
            self.lbl_box_y.hide()
            self.lbl_box_z.hide()

    def update_input_boxes(self):
        # // update the move box when the values in the input boxes have changed
        if self.rb_pixdim.isChecked():
            self.move_box.setSize([float(self.ent_dimx.text()) * self.shape[
                self.axis[0]], float(self.ent_dimy.text()) * self.shape[
                                       self.axis[1]]])
        elif self.rb_center.isChecked():
            # // position is left top corner
            self.move_box.setPos(QtCore.QPointF(float(self.ent_dimx.text()) - self.move_box.size().x() // 2,
                                                float(self.ent_dimy.text()) - self.move_box.size().y() // 2))
        elif self.rb_outline.isChecked():
            # // change the pos
            a = (abs(float(self.ent_unitx.text()) - float(self.ent_dimx.text())),
                 abs(float(self.ent_unity.text()) - float(self.ent_dimy.text())))
            self.move_box.blockSignals(True)
            self.move_box.setPos(QtCore.QPointF(float(self.ent_dimx.text()), float(self.ent_dimy.text())))
            self.move_box.blockSignals(False)
            # // change the size
            self.move_box.setSize(a)
        elif self.rb_rotation.isChecked():
            f = float(self.ent_dimx.text())
            if f < 360 and f >= 0:
                self.dial_rotation.setValue(int(f))
                self.rotate_box()
        elif self.rb_totdim.isChecked():
            self.move_box.setSize((float(self.ent_dimx.text()), float(self.ent_dimy.text())))
        else:
            QtCore.qDebug("invalid radiobutton selection")

    def apply_aspect(self):
        # % apply the settings toward the dataset selected
        if 'AspectRatio' in self.attrs.keys():
            aspect_ratio = self.attrs['AspectRatio']
        else:
            aspect_ratio = [0, 0, 0]
        aspect_ratio[0] = (self.outl[1] - self.outl[0]) / self.shape[self.axis[0]]
        aspect_ratio[1] = (self.outl[3] - self.outl[2]) / self.shape[self.axis[1]]
        aspect_ratio[2] = (self.outl[5] - self.outl[4]) / self.shape[self.axis[2]]
        if aspect_ratio[2] == 0:
            aspect_ratio[2] = 1

        self.attrs.update({'AspectRatio': aspect_ratio})
        self.attrs.update({'Outline': self.outl})
        self.attrs['Rotation'] = self.rot

        self.update_aspect_values()
        self.reset_input_boxes()

    def reject_dialog(self):
        # // reset the movebox
        # self.move_box.blockSignals(True)
        # self.dial_rotation.setValue(0)
        # self.rotate_box()
        self.move_box.blockSignals(True)
        self.move_box.setAngle(self.reset_angle)
        self.move_box.setSize(self.reset_size)
        # self.move_box.blockSignals(False)
        self.move_box.blockSignals(False)
        self.move_box.setPos(self.reset_pos)
        # self.dial_rotation.setValue(self.reset_angle)
        # self.rotate_box()
        try:
            if self.move_box in self._parent.field.allChildren():
                self._parent.field.removeItem(self.move_box)
            self.update_field_current.setBorder(None)
        except:
            pass
        self._parent.gb_list.setEnabled(True)
        self._parent.geo = None
        self.reject()

    def closeEvent(self, event):
        try:
            if self.move_box in self._parent.field.allChildren():
                self._parent.field.removeItem(self.move_box)
            self.update_field_current.setBorder(None)
            self._parent.geo = None
        except:
            pass

    def restore_move_box(self):
        if 'Outline_r' in self.attrs.keys():
            self.outl_r = self.attrs['Outline_r']
            a = (abs(self.outl_r[1] - self.outl_r[0]),
                 abs(self.outl_r[3] - self.outl_r[2]))
            # self.move_box.blockSignals(True)
            self.dial_rotation.setValue(0)
            self.rotate_box()

            self.move_box.setSize(a)
            # self.move_box.blockSignals(False)
            self.move_box.setPos(QtCore.QPointF(self.outl_r[0], self.outl_r[2]))

            if 'Rotation_r' in self.attrs.keys():
                self.dial_rotation.setValue(int(self.attrs['Rotation_r']))
                self.rotate_box()
            else:
                self.attrs['Rotation'] = 0

            # self.move_box.setPos(QtCore.QPointF(self.outl_r[0], self.outl_r[2]))

    def update_box(self):
        self.rot = self.move_box.angle()

        # % get the transformation as the delta between the two topleft corners
        # this is needed since move box rotate about center while the filed rotate about the top left corner
        delta_t = self.update_field_current.pos() - self.move_box.pos()

        # % reset the scaling to 1/1 prior to rotation
        s = list(self.update_field_current._scale)
        tr = QtGui.QTransform()
        tr.scale(1 / s[0], 1 / s[1])
        self.update_field_current.setTransform(tr)

        # absolute rather than relative rotation
        self.update_field_current.setRotation(self.rot)
        self.attrs["Rotation"] = self.rot

        # // check for changes in the x scale
        if np.abs(self.outl[1] - self.outl[0]) != self.move_box.size()[0]:
            s[0] *= self.move_box.size()[0] / np.abs(self.outl[1] - self.outl[0])
            self.outl[1] = self.outl[0] + self.move_box.size()[0]

        # // check for changes in the y scale
        if np.abs(self.outl[3] - self.outl[2]) != self.move_box.size()[1]:
            s[1] *= self.move_box.size()[1] / np.abs(self.outl[3] - self.outl[2])
            self.outl[3] = self.outl[2] + self.move_box.size()[1]

        # self.update_field_current.scale(s[0], s[1])
        tr = QtGui.QTransform()
        tr.scale(s[0], s[1])
        self.update_field_current.setTransform(tr)

        self.update_field_current._scale = (s[0], s[1])

        # % apply the transform by moving the image
        # translation offset due to rotation point difference (top left corder vs center)
        self.update_field_current.setPos(self.update_field_current.pos() - delta_t)

        self.outl = self.cal_outl_from_roi()
        self.recalc_values()
        self.reset_input_boxes()

    def cal_outl_from_roi(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x - width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area
        #roi position
        pos = np.array(self.move_box.pos())
        #width and height
        wd, ht = list(self.move_box.size())
        #rotation angle (0-360)
        ang = math.radians(self.move_box.angle()%360)
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, self.outl[-2],self.outl[-1]]
        return outl

    def lockAspect(self):
        if self.cb_aspect_ratio.isChecked():
            for info in self.move_box.handles:
                h = info["item"]
                info['lockAspect'] = True
        else:
            for info in self.move_box.handles:
                h = info["item"]
                info['lockAspect'] = False

    def rotate_box(self):
        val = self.dial_rotation.value()
        self.move_box.blockSignals(True)
        self.move_box.setAngle(val)
        self.move_box.blockSignals(False)
        # // translate move_box position
        v = rotatePoint(centerPoint=self.attrs["Center"], point=[self.outl[0], self.outl[2]],
                        angle=val)
        self.move_box.setPos(QtCore.QPointF(v[0], v[1]))
        if self.rb_rotation.isChecked():
            self.ent_dimx.setText(str(val))

    def display_move_box(self):
        if self.update_field_current:
            if not self.update_field_current.isVisible():
                return None
            self.update_field_current.setBorder('r')
            self.reset_pos = self.update_field_current.pos()
            self.reset_angle = self.attrs["Rotation"]
            outl = self.attrs['Outline']
            self.reset_size = pg.Point(
                outl[1] - outl[0], \
                outl[3] - outl[2])
            dash_pen = pg.mkPen((255, 255, 255), width=1, dash=[4, 2])
            self.move_box = pg.ROI(self.reset_pos, size=self.reset_size, angle=self.reset_angle, pen=dash_pen)
            self.move_box.handleSize = 10
            self.move_box.handlePen = pg.mkPen("#FFFFFF")
            self.move_box.addRotateHandle([1, 0], [0.5, 0.5])
            self.move_box.addRotateHandle([0, 1], [0.5, 0.5])
            self.move_box.addScaleHandle([0, 0], [0.5, 0.5])
            self.move_box.addScaleHandle([1, 1], [0.5, 0.5])
            self._parent.field.addItem(self.move_box)
            # self._parent.mdi_field_widget.update_field_current.setParentItem(self.move_box)
            self.move_box.sigRegionChangeFinished.connect(self.update_box)
'''
def main_test():
    import os, sys

if __name__ == "__main__":
    main_test()
