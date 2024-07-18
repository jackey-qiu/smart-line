# -*- coding: utf-8 -*-
import os

# // module to manage the aligment tool in the field view
# QtCore.qInstallMsgHandler(lambda *args: None)
import pyqtgraph as pg
import numpy as np
import pandas as pd
import copy
import math
from smart.util.geometry_transformation import rotatePoint
from smart.util.util import get_stage_coords_from_tif_file_from_p06_desy
from PyQt5.QtWidgets import  QAbstractItemView
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from pathlib import Path
import qimage2ndarray
import cv2
import imreg_dft as ird
from smart.util.util import PandasModel, submit_jobs, findMainWindow


ui_file_folder = Path(__file__).parent.parent / 'ui'


def qt_image_to_array(img, share_memory=False):
    """ Creates a numpy array from a QImage.

        If share_memory is True, the numpy array and the QImage is shared.
        Be careful: make sure the numpy array is destroyed before the image,
        otherwise the array will point to unreserved memory!!
    """
    assert (img.format() == QtGui.QImage.Format.Format_RGB32 or \
            img.format() == QtGui.QImage.Format.Format_ARGB32_Premultiplied),\
        "img format must be QImage.Format.Format_RGB32, got: {}".format(
        img.format())

    '''
    img_size = img.size()
    buffer = img.constBits()
    buffer.setsize(img_size.height() * img_size.width() * img.depth() // 8)
    arr = np.frombuffer(buffer, np.uint8).reshape((img_size.width(), img_size.height(), img.depth() // 8))
    '''

    arr_rec = qimage2ndarray.recarray_view(img)
    #convert the grayscale already
    arr = arr_rec.r * 0.299 + arr_rec.g * 0.587 +arr_rec.b * 0.114

    if share_memory:
        return arr
    else:
        return copy.deepcopy(arr)

def qt_pixmap_to_array(pixmap, share_memory=False):
    """ Creates a numpy array from a QPixMap.
        If share_memory is True, the numpy array and the QImage is shared.
        Be careful: make sure the numpy array is destroyed before the image,
        otherwise the array will point to unreserved memory!!
    """
    assert isinstance(pixmap, QtGui.QPixmap), "pixmap must be a QtGui.QImage object"
    img_size = pixmap.size()
    img = pixmap.toImage()
    buffer = img.constBits()

    # Sanity check
    n_bits_buffer = len(buffer) * 8
    n_bits_image = img_size.width() * img_size.height() * img.depth()
    assert n_bits_buffer == n_bits_image, \
        "size mismatch: {} != {}".format(n_bits_buffer, n_bits_image)

    assert img.depth() == 32, "unexpected image depth: {}".format(img.depth())

    # Note the different width height parameter order!
    arr = np.ndarray(shape=(img_size.height(), img_size.width(), img.depth() // 8),
                     buffer=buffer,
                     dtype=np.uint8)

    if share_memory:
        return arr
    else:
        return copy.deepcopy(arr)


def mdi_field_imreg_show(self):
    """
    Launching the field registration tool
    :param self:
    :return:
    """
    self.mdi_field_registration_widget = MdiFieldImreg(self)
    # self.mdi_field_registration_widget.logMessage_sig.connect(self.dock_log.add_event)
    self.mdi_field_registration_widget.statusMessage_sig.connect(self.statusUpdate)
    self.mdi_field_registration_widget.progressUpdate_sig.connect(self.progressUpdate)
    self.mdi_field_registration_widget.updateFieldMode_sig.connect(self.field.set_mode)

    #self.dock_properties.grid_settings.addWidget(self.mdi_field_registration_widget)
    self.field.rectangleSelected_sig.connect(self.mdi_field_registration_widget.set_reference_zone)
    #self.mdi_field_widget.setEnabled(True)

    #self.dock_properties.stackedWidget.setCurrentIndex(1)

    # // enable pipeline selection
    #self.dock_pipe.setEnabled(True)
    #self.dock_properties.show()
    self.mdi_field_registration_widget.init_dft_mode()
    self.mdi_field_registration_widget.show()
    self.mdi_field_registration_widget.exec_()

class DFTRegistration(QtCore.QObject):

    sig_dft_finished = QtCore.pyqtSignal(object)
    sig_dft_status = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.reference_sub_frame = None
        self.target_zoom_frame = None

    def prepare_dft(self, reference, target):
        self.reference_sub_frame = reference
        self.target_zoom_frame = target

    def perform_dft(self):
        from smart.util.geometry_transformation import registration_dft_slice
        self.sig_dft_status.emit('Start DFT registration..')
        vector_dict = registration_dft_slice(self.reference_sub_frame, self.target_zoom_frame, iterations=5, \
                                                display=False,  progressbar=None,
                                                display_window=None)
        self.sig_dft_status.emit('DFT registration is finished!')
        self.sig_dft_finished.emit(vector_dict)

class MdiFieldImreg_Wrapper(object):
    """
    class around the GUI for image registration based on DFT-based input
    this class must be inherited by mainWindow
    """

    def __init__(self):
        """
        Initialize function
        :param parent:
        :param current_group:
        """
        self.roi_dft_active = False
        self.roi_dft = None
        self.target_frame = np.zeros((0,0))
        self.target_outline = [0,0,0,0,0,0]
        self.reference_frame = np.zeros((0, 0))
        self.reference_outline = [0,0,0,0,0,0]
        self.dft_reg_instance = DFTRegistration()
        self.dft_reg_thread = QtCore.QThread()
        self.dft_reg_instance.moveToThread(self.dft_reg_thread)
        self.dft_reg_thread.started.connect(self.dft_reg_instance.perform_dft)
        self.init_scan_list()
        self.scaling_ft_along_height = 1
        self.scaling_ft_along_width = 1
        self.beam_pos_vp = [0,0]
        # self.setMinimumWidth(self._parent.dock_properties.size().width() - 40)
        # self.connect_slots()

    def init_scan_list(self,table_view_widget_name='tableView_scan_list'):
        data = pd.DataFrame.from_dict({'roi_pos_x':np.array([]),'roi_pos_y':np.array([]),'roi_width':np.array([]),'roi_height':np.array([]),'scan macro':[]}, dtype='str')
        #data = data.astype({'roi_pos_x':'float', 'roi_pos_y': 'float', 'roi_width':'float', 'roi_height':'float','scan macro':'str'})
        self.pandas_model_scan_list = PandasModel(data, tableviewer = getattr(self, table_view_widget_name), main_gui=self)
        getattr(self, table_view_widget_name).setModel(self.pandas_model_scan_list)
        getattr(self, table_view_widget_name).resizeColumnsToContents()
        getattr(self, table_view_widget_name).setSelectionBehavior(QAbstractItemView.SelectRows)
        getattr(self, table_view_widget_name).horizontalHeader().setStretchLastSection(True)        

    def get_stage_info_P06(self):
        attrDict = self.reference_image.loc
        tiff_path = attrDict['Path']
        result = get_stage_coords_from_tif_file_from_p06_desy(tiff_path)
        origin, pix_size, unit = result['origin'], result['pix_size'], result['unit']
        pix_num = (self.reference_image.width, self.reference_image.height)
        if unit == 'microns':
            ref_img_width = pix_size[0]*pix_num[0]/1000
            ref_img_height = pix_size[1]*pix_num[1]/1000
            origin = list(np.array(origin)/1000)
        elif unit == 'mm':
            ref_img_width = pix_size[0]*pix_num[0]
            ref_img_height = pix_size[1]*pix_num[1]
        else:
            raise TypeError('Unsupported unit')
        return ref_img_width, ref_img_height, origin

    def fill_stage_info(self, standard = 'P06'):
        if standard == 'P06':
            hor_width, ver_width, origin = self.get_stage_info_P06()
            self.lineEdit_beampos_motors.setText(str(list(origin)))
            self.lineEdit_motor_range_along_width.setText(str(hor_width))
            self.lineEdit_motor_range_along_height.setText(str(ver_width))

    def cal_scaling_factors(self):
        frame_vp = [self.reference_image.width, self.reference_image.height]
        frame_stage = [self.lineEdit_motor_range_along_width.text(), self.lineEdit_motor_range_along_height.text()]
        if frame_stage[0] == 'None':
            try:
                height = float(frame_stage[1])
                width = height/frame_vp[1]*frame_vp[0]
                frame_stage = [width, height]
            except:
                print('Cannot convert the text to float!')
        elif frame_stage[1] == 'None':
            try:
                width = float(frame_stage[0])
                height = width/frame_vp[0]*frame_vp[1]
                frame_stage = [width, height]
            except:
                print('Cannot convert the text to float!') 
        else:
            frame_stage = [float(each) for each in frame_stage]      

        self._cal_scaling_factors(frame_vp, frame_stage)
        self.statusbar.showMessage(f'sf along width: {self.scaling_ft_along_width} mm/vpu; sf along height: {self.scaling_ft_along_height} mm/vpu')

    def _cal_scaling_factors(self, target_frame_dim_vp, target_frame_dim_stage):
        #target_frame_dim_vp: [width, height]
        #target_frame_dim_stage: [width, height]
        #return sf along width, sf along height
        assert isinstance(target_frame_dim_vp, list) and len(target_frame_dim_vp)==2, 'the vp dimension info provided for target frame is not in a corret form, should be a list of two items'
        width_viewport, height_viewport = target_frame_dim_vp
        assert isinstance(target_frame_dim_stage, list) and len(target_frame_dim_stage)==2, 'the stage dimension info provided for target frame is not in a corret form, should be a list of two items'
        width_stage, height_stage = target_frame_dim_stage

        self.scaling_ft_along_width = width_stage/width_viewport #mm per viewport unit
        self.scaling_ft_along_height = height_stage/height_viewport #mm per viewport unit

        #return scaling_ft_along_width, scaling_ft_along_height

    def generate_scan_macro(self):
        mot_name_along_width = self.settings_object['SampleStageMotorNames']['x']
        mot_name_along_height = self.settings_object['SampleStageMotorNames']['y']
        macro_name = self.lineEdit_macro_name.text()
        roi_width, roi_height = self.roi_dft.size()
        roi_x, roi_y = self.roi_dft.pos()
        beam_pos_vp = eval(self.lineEdit_beampos_coordinates.text())
        beam_pos_stage = eval(self.lineEdit_beampos_motors.text())
        dwell_time = float(self.lineEdit_dwell_time.text())
        pix_size = eval(self.lineEdit_beamsize.text()) # [hor, ver] in um

        mot_start_pos_along_width = round((roi_x - beam_pos_vp[0])*self.scaling_ft_along_width + beam_pos_stage[0],4)
        mot_start_pos_along_height = round((roi_y - beam_pos_vp[1])*self.scaling_ft_along_width + beam_pos_stage[1],4)
        mot_end_pos_along_width = round(mot_start_pos_along_width + roi_width * self.scaling_ft_along_width,4)
        mot_end_pos_along_height = round(mot_start_pos_along_height + roi_height * self.scaling_ft_along_height, 4)
        steps_along_width = int(abs(mot_end_pos_along_width - mot_start_pos_along_width)/(pix_size[0]/1000))
        steps_along_height = int(abs(mot_end_pos_along_height - mot_start_pos_along_height)/(pix_size[0]/1000))
        macro_string = f"{macro_name} {mot_name_along_width} {mot_start_pos_along_width} {mot_end_pos_along_width} {steps_along_width} {mot_name_along_height} {mot_start_pos_along_height} {mot_end_pos_along_height} {steps_along_height} {dwell_time}"
        new_row_in_table = [str(roi_x), str(roi_y), str(roi_width), str(roi_height), macro_string]
        self.pandas_model_scan_list._data.loc[len(self.pandas_model_scan_list._data)] = new_row_in_table
        self.pandas_model_scan_list.update_view()

        return macro_string

    def drop_selected_row(self):
        selected_rows = self.tableView_scan_list.selectionModel().selectedRows()
        if len(selected_rows)>0:
            row = selected_rows[0].row()
            self.pandas_model_scan_list._data.drop(row, inplace=True)
            self.pandas_model_scan_list._data.reset_index(drop=True, inplace=True)
            self.pandas_model_scan_list.update_view()

    def update_dft_roi_on_click_table_row(self):
        selected_rows = self.tableView_scan_list.selectionModel().selectedRows()
        if len(selected_rows)>0:
            row = selected_rows[0].row()
            x0 = float(self.pandas_model_scan_list._data['roi_pos_x'][row])
            y0 = float(self.pandas_model_scan_list._data['roi_pos_y'][row])
            
            width = float(self.pandas_model_scan_list._data['roi_width'][row])
            height = float(self.pandas_model_scan_list._data['roi_height'][row])
            x1 = x0 + width
            y1 = y0 + height

            self.field.rectangleSelected_sig.emit(x0, y0, x1, y1)

    def update_beam_pos_vp(self):
        if not hasattr(self, 'reference_image'):
            self.statusbar.showMessage('You should pick the reference image first!')
            return
        beampos = []
        loc = self.comboBox_ref_frame_pos.currentText()
        if loc=='top left':
            beampos = list(self.reference_image.pos())
        elif loc=='top right':
            beampos = np.array(list(self.reference_image.pos())) + [self.reference_image.width, 0]
        elif loc=='bottom left':
            beampos = np.array(list(self.reference_image.pos())) + [0, self.reference_image.height]
        elif loc=='bottom right':
            beampos = np.array(list(self.reference_image.pos())) + [self.reference_image.width, self.reference_image.height]
        self.lineEdit_beampos_coordinates.setText(str([round(each, 4) for each in beampos]))

    def submit_jobs_to_run(self):
        jobs = list(self.pandas_model_scan_list._data['scan macro'])
        submit_jobs(self.widget_sequencer, jobs)

    @QtCore.pyqtSlot(str)
    def update_status(self,string):
        self.statusbar.showMessage(string)

    def connect_slots_dft(self):
        """
        Connect all slots within the software
        :return:
        """
        #connect signals
        self.statusMessage_sig.connect(self.statusUpdate)
        self.progressUpdate_sig.connect(self.progressUpdate)
        # self.updateFieldMode_sig.connect(self.field.set_mode)
        self.field.rectangleSelected_sig.connect(self.set_reference_zone)
        #connect widget events
        self.bt_registration.clicked.connect(self.prepare_dft)
        self.pushButton_move.clicked.connect(self.translate_target)
        self.bt_add_ref.clicked.connect(self.add_reference)
        self.bt_add_target.clicked.connect(self.add_target)
        self.pushButton_roi_on_target.clicked.connect(self.extract_target_sub_frame)
        self.pushButton_roi_on_reference.clicked.connect(self.extract_ref_sub_frame)
        self.dft_reg_instance.sig_dft_status.connect(self.update_status)
        self.dft_reg_instance.sig_dft_finished.connect(self.dft_imreg2)
        self.comboBox_ref_frame_pos.currentIndexChanged.connect(self.update_beam_pos_vp)
        self.pushButton_cal_sf.clicked.connect(self.cal_scaling_factors)
        self.pushButton_fill_stage_info.clicked.connect(self.fill_stage_info)
        self.pushButton_add_row.clicked.connect(self.generate_scan_macro)
        self.pushButton_remove_row.clicked.connect(self.drop_selected_row)
        self.tableView_scan_list.clicked.connect(self.update_dft_roi_on_click_table_row)
        # self.pushButton_submit_jobs.clicked.connect(self.submit_jobs_to_run)
        self.pushButton_submit_jobs.clicked.connect(lambda: self.submit_jobs_to_queue_server(viewer = 'img_reg'))

    def cal_union_region_target_and_reference(self):
        x_min, x_max, y_min, y_max = 0, 0, 0, 0
        assert hasattr(self, 'target_image') and hasattr(self, 'reference_image'), 'pick both target and reference images first'
        #origin coordinates of target image wrt viewport
        x0_tg, y0_tg = self.target_image.pos()
        #coordinates of diagonal point wrt viewport (assume the scaling is 1)
        x1_tg = x0_tg + self.target_image.width
        y1_tg = y0_tg + self.target_image.height
        #origin coordinates of reference image wrt viewport
        x0_rf, y0_rf = self.reference_image.pos()
        #coordinates of diagonal point wrt viewport (assume the scaling is 1)
        x1_rf = x0_rf + self.reference_image.width
        y1_rf = y0_rf + self.reference_image.height

        #now cal the min and max of x and y
        x_min = min(x0_tg, x0_rf,x1_tg,x1_rf)
        x_max = max(x0_tg, x0_rf,x1_tg,x1_rf)
        y_min = min(y0_tg, y0_rf,y1_tg,y1_rf)
        y_max = max(y0_tg, y0_rf,y1_tg,y1_rf)

        return int(x_min), int(x_max), int(y_min), int(y_max)

    def find_relative_center_for_rot_and_scaling(self, img_buffer, union_bounds):

        #viewport coords system
        target_center = sum(union_bounds[0:2])/2.0, sum(union_bounds[2:])/2.0
        #img origin
        origin_img = list(img_buffer.pos())
        img_outl = img_buffer.loc['Outline']
        img_width = abs(img_outl[0] - img_outl[1])
        img_height = abs(img_outl[2] - img_outl[3])
        #rotation center wrt img
        return (target_center[0] - origin_img[0])/img_width, (target_center[1] - origin_img[1])/img_height

    def _move_to_dft_sweat_spot(self):
        #send rotation angle to 0
        self.move_box.rotate(0-self.move_box.angle(), center = (0.5,0.5))
        #assume same aspect ratio in x and y direction
        self.move_box.scale(1/self.pixdim[0])
        #go to integer coordinate pos
        self.move_box.setPos(*[int(each) for each in self.move_box.pos()])

    def add_target(self):
        """
        Adds the target slice. This can be from an image in the workspace, or from a dataset
        :return:
        """
        self._move_to_dft_sweat_spot()
        self.target_image = self.update_field_current
        current_loc = self.update_field_current.loc
        self.outl_target = current_loc['Outline']
        if isinstance(current_loc, dict):
            self.target_attrs = current_loc
            self.target_frame = qt_image_to_array(self.target_image.pixmap.toImage())
            # // grayscale conversion
            # self.target_frame = np.dot(self.target_frame[..., :3], [0.299, 0.587, 0.114])
            self.ent_target.setText(current_loc["Path"])
            self.statusbar.showMessage(f'Target image added: {current_loc["Path"]}')
        elif isinstance(current_loc, Group):
            dset = current_loc.get_dataset()
            self.target_attrs = dset.attrs
            # // grab the array and the positions of the outline
            self.target_frame = np.atleast_2d(
                self.position_tracker.retrieve_slice(dset, ["spatialx", "spatialy"],
                                                            channel_spec=1)).astype(
                float)
            self.ent_target.setText(dset.name)
            self.statusbar.showMessage(f'Target image added: {dset.name}')
        else:
            self.statusbar.showMessage(f'Fail to add target image')
            raise ValueError("Unexpected type: {}".format(type(current_loc)))

    def add_reference(self):
        """
        Adds the reference slice. This can be from an image in the workspace, or from a dataset
        :return:
        """
        self._move_to_dft_sweat_spot()

        self.reference_image = self.update_field_current
        current_loc = self.update_field_current.loc
        self.outl_reference = current_loc['Outline']
        if isinstance(current_loc, dict):
            self.reference_attrs = current_loc
            self.reference_frame = qt_image_to_array(self.reference_image.pixmap.toImage())
            # // grayscale conversion
            # self.reference_frame = np.dot(self.reference_frame[..., :3], [0.299, 0.587, 0.114])
            self.ent_ref.setText(current_loc["Path"])
            self.statusbar.showMessage(f'Reference image added: {current_loc["Path"]}')
        else:
            self.statusbar.showMessage(f'Fail to add reference image: {current_loc["Path"]}')
            raise ValueError("Unexpected type: {}".format(type(current_loc)))

    @Slot(float,float,float,float)
    def set_reference_zone(self, x0, y0, x1, y1):
        """
        Sets the coordinates of the rectangle selection within the reference zone

        :param x0: left-top corner x coordinate
        :param y0: left-top corner y coordinate
        :param x1: right-bottom corner x coordinate
        :param y1: right-bottom corner y coordinate
        :return:
        """
        if self.roi_dft_active:
            self.field.removeItem(self.roi_dft)
        pen = pg.mkPen((0, 200, 200), width=1)
        self.roi_dft = pg.ROI([x0, y0], [x1-x0, y1-y0], pen=pen)
        self.roi_dft.handleSize = 10
        self.roi_dft.handlePen = pg.mkPen("#FFFFFF")
        self.roi_dft.addScaleHandle([0, 0], [0.5, 0.5])
        self.roi_dft.addScaleHandle([1, 1], [0.5, 0.5])
        self.roi_dft.sigRegionChangeFinished.connect(self.update_outl_dft)
        self.field.addItem(self.roi_dft)
        self.current_roi_dft_outline = (x0, x1, y0, y1)
        self.roi_dft_active = True

    def update_outl_dft(self):
        pos = np.array(self.roi_dft.pos())
        #width and height
        wd, ht = list(self.roi_dft.size())
        x0, x1, y0, y1 = pos[0], pos[0]+wd, pos[1], pos[1]+ht
        self.current_roi_dft_outline = (x0, x1, y0, y1)

    def restore(self):
        if 'Outline_r' in self.dset.attrs.keys():
            outl = self.dset.attrs['Outline_r']
            self.dset.attrs['Outline'] = outl
            if 'Rotation_r' in self.dset.attrs.keys():
                self.dset.attrs['Rotation'] = self.dset.attrs[
                    'Rotation_r']
            else:
                self.dset.attrs['Rotation'] = 0

        # // reset the field box
        if outl[0] != outl[1]:
            if self.axis[0] > -1:
                x_aspect = self.dset.shape[self.axis[0]] / abs(outl[0] - outl[1])
            else:
                x_aspect = 1
        else:
            x_aspect = 1
        if outl[2] != outl[3]:
            if self.axis[1] > -1:
                y_aspect = self.dset.shape[self.axis[1]] / abs(outl[2] - outl[3])
            else:
                y_aspect = 1
        else:
            y_aspect = 1

        s = list(self.update_field_current._scale)
        self.update_field_current.scale(1 / s[0], 1 / s[1])

        # // rotate the dataset if a rotation transformation is required]
        if 'Rotation_r' in self.dset.attrs.keys():
            rot = self.dset.attrs['Rotation_r']
            self.update_field_current.rotate(-rot)
            self.update_field_current._rot = self.update_field_current._rot - rot
            self.dset.attrs['Rotation'] = self.move_box.angle()
        else:
            self.update_field_current._rot = 0.0
            self.dset.attrs['Rotation'] = 0.0

        self.update_field_current.scale(1 / x_aspect, 1 / y_aspect)
        self.update_field_current._scale = (1 / x_aspect, 1 / y_aspect)

        # // translates the dataset in the field view based on the left corner coordinate in the outline
        self.update_field_current.setPos(pg.Point(outl[0], outl[2]))
        # self._parent.mdi_field_widget.update_field()

    def extract_ref_sub_frame(self):
        assert self.roi_dft_active, "No roi has been selected. Click and drag the mouse to make a roi selection first!"
        assert hasattr(self, 'reference_frame'), "No reference frame has been registered!"
        self.reference_sub_outline = self.current_roi_dft_outline
        self.reference_sub_frame = self.roi_dft.getArrayRegion(self.reference_frame, self.reference_image)
        self.statusbar.showMessage('Feature being extracted from reference')

    def extract_target_sub_frame(self):
        assert self.roi_dft_active, "No roi has been selected. Click and drag the mouse to make a roi selection first!"
        assert hasattr(self, 'target_frame'), "No target frame has been registered!"
        self.target_sub_frame = self.roi_dft.getArrayRegion(self.target_frame, self.target_image)
        self.target_sub_outline = self.current_roi_dft_outline
        self.statusbar.showMessage('Feature being extracted from target')
        # cv2.imwrite(r"C:\\Users\\qiucanro\\Downloads\\target_sub_frame.jpg", self.target_sub_frame)

    def _update_outl(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x + width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area

        original_outl = self.target_attrs['Outline']
        wd_o, ht_o = original_outl[1]-original_outl[0], original_outl[3]-original_outl[2]
        #roi position
        pos = np.array(self.target_image.pos())
        #width and height
        wd, ht = wd_o*self.scale_factor, ht_o*self.scale_factor
        #rotation angle (0-360)
        #ang = math.radians(self.move_box.angle()%360)
        ang = math.radians(self.target_attrs['Rotation'])
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, original_outl[-2],original_outl[-1]]
        self.target_attrs['Outline'] = outl

    def translate_target(self):
        def _center(outl):
            return np.array([(outl[0]+outl[1])/2, (outl[2]+outl[3])/2])
        translation_vector = QtCore.QPointF(*list(_center(self.reference_sub_outline))) - QtCore.QPointF(*list(_center(self.target_sub_outline)))
        self.field.select_single_image([self.target_image])
        self.move_box.setPos(translation_vector + self.move_box.pos())

    def translate_move_box(self, tvec):
        dy, dx = tvec
        translation_vector = QtCore.QPointF(dx, dy)
        self.move_box.setPos(translation_vector + self.move_box.pos())

    def _padding_to_union_size(self, array_frame, outline, union_outline):
        x_min, x_max, y_min, y_max = union_outline
        x0, x1, y0, y1 = [int(round(each)) for each in outline]
        # print([(y0-y_min, y_max-y1),(x0-x_min, x_max-x1)])
        return np.pad(array_frame, pad_width=[(y0-y_min, y_max-y1),(x0-x_min, x_max-x1)], mode='constant', constant_values=250)
    
    def prepare_dft(self):
        assert hasattr(self, 'reference_sub_outline'), "reference sub frame not yet selected"
        assert hasattr(self, 'target_sub_outline'), "target sub frame not yet selected"
        output_text = []
        # // determine the image registration transform
        #do pading here
        union_outline = self.cal_union_region_target_and_reference()
        self.target_zoom_frame = self._padding_to_union_size(self.target_sub_frame,self.target_sub_outline,union_outline)
        self.reference_sub_frame = self._padding_to_union_size(self.reference_sub_frame,self.reference_sub_outline,union_outline)
        min_y_dim = min([self.target_zoom_frame.shape[0],self.reference_sub_frame.shape[0]])
        min_x_dim = min([self.target_zoom_frame.shape[1],self.reference_sub_frame.shape[1]])
        #trim it down
        self.target_zoom_frame = self.target_zoom_frame[0:min_y_dim,0:min_x_dim]
        self.reference_sub_frame = self.reference_sub_frame[0:min_y_dim,0:min_x_dim]

        cv2.imwrite(os.path.join(self.settings_object["FileManager"]["currentimagedbDir"],"target_sub_frame_downscaled.jpg"), self.target_zoom_frame)
        #print("shapes:{}{}".format(self.target_zoom_frame.shape,self.reference_sub_frame.shape))
        output_text.append("shapes:{}{}".format(self.target_zoom_frame.shape,self.reference_sub_frame.shape))
        # // match the shape of reference (template) frame and current frame (image to be transformed
        # if self.target_zoom_frame.shape != self.reference_sub_frame.shape:
        #     # // pad on the right side
        #     x_diff = self.reference_sub_frame.shape[0]-self.target_zoom_frame.shape[0]
        #     y_diff = self.reference_sub_frame.shape[1] - self.target_zoom_frame.shape[1]
        #     left_pad = x_diff//2
        #     right_pad = x_diff - left_pad
        #     top_pad = y_diff//2
        #     bottom_pad = y_diff - top_pad
        #     if x_diff>=0 and y_diff>=0:
        #         self.target_zoom_frame = np.pad(self.target_zoom_frame, ((left_pad,right_pad), (top_pad, bottom_pad)), "edge")
        #     else:
        #         self.target_zoom_frame = self.target_zoom_frame[:self.reference_sub_frame.shape[0], :self.reference_sub_frame.shape[1]]
        # else:
        #     output_text.append("no padding required")
        output_text.append("shapes:{}{}".format(self.target_zoom_frame.shape, self.reference_sub_frame.shape))

        cv2.imwrite(os.path.join(self.settings_object["FileManager"]["currentimagedbDir"],"reference_sub_frame.jpg"), self.reference_sub_frame)

        # import cv2
        cv2.imwrite(os.path.join(self.settings_object["FileManager"]["currentimagedbDir"],"target_zoom_frame_padded.jpg"), self.target_zoom_frame)
        self.dft_reg_instance.prepare_dft(self.reference_sub_frame, self.target_zoom_frame)
        try:
            self.dft_reg_thread.terminate()
        except:
            pass
        self.dft_reg_thread.start()


    @QtCore.pyqtSlot(object)
    def dft_imreg2(self, vector_dict):
        union_outline = self.cal_union_region_target_and_reference()
        output_text=['DFT registration results']
        if vector_dict["success"]:
            net_rotation_degrees = -vector_dict["angle"]
            full_rotation_degrees = self.target_attrs["Rotation"] + net_rotation_degrees
            ##self.target_attrs['Rotation'] = self.target_attrs["Rotation"] + net_rotation_degrees
            # // note that the scale factor is calculated under the assumption that the images have the same pixel
            # // size, which is not the case
            self.scale_factor = vector_dict["scale"]
            # // correct for pixel size to calculate the correct scale factor

            arr = ird.imreg.transform_img_dict(self.target_zoom_frame, tdict=vector_dict, bgval=None, order=1,
                                               invert=False)
            cv2.imwrite(os.path.join(self.settings_object["FileManager"]["currentimagedbDir"],"target_sub_frame_transformed.jpg"), arr)

            output_text.append("tvec: {}".format(vector_dict["tvec"]))
            output_text.append("angle: {}, {}".format(vector_dict["angle"], self.target_attrs["Rotation"]))
            output_text.append("scale: {}".format(vector_dict["scale"]))
            #set rotation and scaling via manipulating roi
            self.field.select_single_image([self.target_image])
            #scaling center
            self.move_box.rotate(0, center=(0.5,0.5))
            center = self.find_relative_center_for_rot_and_scaling(self.update_field_current, union_outline)
            #print('center:', center)
            self.move_box.scale(vector_dict["scale"], center = center)
            center = self.find_relative_center_for_rot_and_scaling(self.update_field_current, union_outline)
            #print('center:', center)
            self.move_box.rotate(full_rotation_degrees, center = center)
            self.translate_move_box(vector_dict["tvec"]) 
            #self.move_box.setPos(new_roi_pos_before_rotation)
            # self.translate_move_box(vector_dict["tvec"])
            # self.move_box.setAngle(self.target_attrs['Rotation'],center=[0.5,0.5])
            # self.move_box.scale(self.scale_factor,center=[0.5,0.5])
            #output info
            self.textEdit.setPlainText('\n'.join(output_text))
            self.field.removeItem(self.roi_dft)
            return vector_dict

class MdiFieldImreg(QtWidgets.QDialog):
    """
    class around the GUI for image registration based on DFT-based input
    """
    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)
    updateFieldMode_sig = Signal(str)

    def __init__(self, parent):
        """
        Initialize function
        :param parent:
        :param current_group:
        """
        super(MdiFieldImreg, self).__init__(parent)
        uic.loadUi(str(ui_file_folder/'field_registration.ui'),self)
        self._parent = parent
        parent.widget_terminal.update_name_space('dft_obj', self)
        self.roi_active = False
        self.roi = None
        self.target_frame = np.zeros((0,0))
        self.target_outline = [0,0,0,0,0,0]
        self.reference_frame = np.zeros((0, 0))
        self.reference_outline = [0,0,0,0,0,0]
        # self.setMinimumWidth(self._parent.dock_properties.size().width() - 40)
        self.connect_slots()

    def init_dft_mode(self):
        self.updateFieldMode_sig.emit('dft')

    def connect_slots(self):
        """
        Connect all slots within the software
        :return:
        """
        self.bt_registration.clicked.connect(self.dft_imreg2)
        self.pushButton_move.clicked.connect(self.translate_target)
        self.bt_add_ref.clicked.connect(self.add_reference)
        self.bt_add_target.clicked.connect(self.add_target)
        self.buttonBox.accepted.connect(self.accept_dialog)
        self.buttonBox.rejected.connect(self.reject_dialog)
        self.pushButton_roi_on_target.clicked.connect(self.extract_target_sub_frame)
        self.pushButton_roi_on_reference.clicked.connect(self.extract_ref_sub_frame)

    def add_target(self):
        """
        Adds the target slice. This can be from an image in the workspace, or from a dataset
        :return:
        """
        self.target_image = self._parent.update_field_current
        current_loc = self._parent.update_field_current.loc
        self.outl_target = current_loc['Outline']
        if isinstance(current_loc, dict):
            self.target_attrs = current_loc
            self.target_frame = qt_image_to_array(self.target_image.pixmap.toImage())
            # // grayscale conversion
            # self.target_frame = np.dot(self.target_frame[..., :3], [0.299, 0.587, 0.114])
            self.ent_target.setText(current_loc["Path"])
        elif isinstance(current_loc, Group):
            dset = current_loc.get_dataset()
            self.target_attrs = dset.attrs
            # // grab the array and the positions of the outline
            self.target_frame = np.atleast_2d(
                self._parent.position_tracker.retrieve_slice(dset, ["spatialx", "spatialy"],
                                                            channel_spec=1)).astype(
                float)
            self.ent_target.setText(dset.name)
        else:
            raise ValueError("Unexpected type: {}".format(type(current_loc)))

    def add_reference(self):
        """
        Adds the reference slice. This can be from an image in the workspace, or from a dataset
        :return:
        """
        self.reference_image = self._parent.update_field_current
        current_loc = self._parent.update_field_current.loc
        self.outl_reference = current_loc['Outline']
        if isinstance(current_loc, dict):
            self.reference_attrs = current_loc
            self.reference_frame = qt_image_to_array(self.reference_image.pixmap.toImage())
            # // grayscale conversion
            # self.reference_frame = np.dot(self.reference_frame[..., :3], [0.299, 0.587, 0.114])
            self.ent_ref.setText(current_loc["Path"])
        else:
            raise ValueError("Unexpected type: {}".format(type(current_loc)))

    @Slot(float,float,float,float)
    def set_reference_zone(self, x0, y0, x1, y1):
        """
        Sets the coordinates of the rectangle selection within the reference zone

        :param x0: left-top corner x coordinate
        :param y0: left-top corner y coordinate
        :param x1: right-bottom corner x coordinate
        :param y1: right-bottom corner y coordinate
        :return:
        """
        if self.roi_active:
            self._parent.field.removeItem(self.roi)
        pen = pg.mkPen((0, 200, 200), width=1)
        self.roi = pg.ROI([x0, y0], [x1-x0, y1-y0], pen=pen)
        self.roi.handleSize = 10
        self.roi.handlePen = pg.mkPen("#FFFFFF")
        # self.roi.addRotateHandle([1, 0], [0.5, 0.5])
        # self.roi.addRotateHandle([0, 1], [0.5, 0.5])
        self.roi.addScaleHandle([0, 0], [0.5, 0.5])
        self.roi.addScaleHandle([1, 1], [0.5, 0.5])
        self.roi.sigRegionChangeFinished.connect(self.update_outl)
        self._parent.field.addItem(self.roi)
        self.current_roi_outline = (x0, x1, y0, y1)
        self.roi_active = True

    def update_outl(self):
        pos = np.array(self.roi.pos())
        #width and height
        wd, ht = list(self.roi.size())
        x0, x1, y0, y1 = pos[0], pos[0]+wd, pos[1], pos[1]+ht
        self.current_roi_outline = (x0, x1, y0, y1)

    def set_auto_reference_zone(self, image, scale=1.1):
        """
        This method is meant to increase a zone around the current image, in order to constrain the region of the
        reference image in which a match will be found
        :param pos1:
        :param pos2:
        :param scale:
        :return:
        """
        pass

    def accept_dialog(self):
        try:
            if self.roi in self._parent.field.allChildren():
                self._parent.field.removeItem(self.roi)
                self.updateFieldMode_sig.emit('select')
            self.update_field_current.setBorder(None)
        except:
            pass
        self.accept()

    def reject_dialog(self):
        # clear_preview(self._parent, "signaltrace")
        if self.roi in self._parent.field.allChildren():
            self._parent.field.removeItem(self.roi)
            self.updateFieldMode_sig.emit('select')
        self.reject()

    def closeEvent(self, event):
        try:
            if self.roi in self._parent.field.allChildren():
                self._parent.field.removeItem(self.roi)
                self.updateFieldMode_sig.emit('select')
            self.update_field_current.setBorder(None)
            self._parent.widget_terminal.update_name_space('dft_obj', None)
        except:
            pass

    def restore(self):
        if 'Outline_r' in self.dset.attrs.keys():
            outl = self.dset.attrs['Outline_r']
            self.dset.attrs['Outline'] = outl
            if 'Rotation_r' in self.dset.attrs.keys():
                self.dset.attrs['Rotation'] = self.dset.attrs[
                    'Rotation_r']
            else:
                self.dset.attrs['Rotation'] = 0

        # // reset the field box
        if outl[0] != outl[1]:
            if self._parent.axis[0] > -1:
                x_aspect = self.dset.shape[self._parent.axis[0]] / abs(outl[0] - outl[1])
            else:
                x_aspect = 1
        else:
            x_aspect = 1
        if outl[2] != outl[3]:
            if self._parent.axis[1] > -1:
                y_aspect = self.dset.shape[self._parent.axis[1]] / abs(outl[2] - outl[3])
            else:
                y_aspect = 1
        else:
            y_aspect = 1

        s = list(self.update_field_current._scale)
        self.update_field_current.scale(1 / s[0], 1 / s[1])

        # // rotate the dataset if a rotation transformation is required]
        if 'Rotation_r' in self.dset.attrs.keys():
            rot = self.dset.attrs['Rotation_r']
            self.update_field_current.rotate(-rot)
            self.update_field_current._rot = self.update_field_current._rot - rot
            self.dset.attrs['Rotation'] = self.move_box.angle()
        else:
            self.update_field_current._rot = 0.0
            self.dset.attrs['Rotation'] = 0.0

        self.update_field_current.scale(1 / x_aspect, 1 / y_aspect)
        self.update_field_current._scale = (1 / x_aspect, 1 / y_aspect)

        # // translates the dataset in the field view based on the left corner coordinate in the outline
        self.update_field_current.setPos(pg.Point(outl[0], outl[2]))
        # self._parent.mdi_field_widget.update_field()

    def extract_ref_sub_frame(self):
        assert self.roi_active, "No roi has been selected. Click and drag the mouse to make a roi selection first!"
        assert hasattr(self, 'reference_frame'), "No reference frame has been registered!"
        self.reference_sub_outline = self.current_roi_outline
        self.reference_sub_frame = self.roi.getArrayRegion(self.reference_frame, self.reference_image)

    def extract_target_sub_frame(self):
        assert self.roi_active, "No roi has been selected. Click and drag the mouse to make a roi selection first!"
        assert hasattr(self, 'target_frame'), "No target frame has been registered!"
        self.target_sub_frame = self.roi.getArrayRegion(self.target_frame, self.target_image)
        self.target_sub_outline = self.current_roi_outline
        cv2.imwrite(r"C:\\Users\\qiucanro\\Downloads\\target_sub_frame.jpg", self.target_sub_frame)

    def _update_outl(self):
        #outl should only reflect the width and the height of roi with the right rotation center
        #outl = [c_x - width/2, c_x + width/2, c_y - height/2, c_y + height/2, -0.5, 0.5] for 2d image
        #NOTE: outl is not the coordiates of physical boundary of rectangle roi area

        original_outl = self.target_attrs['Outline']
        wd_o, ht_o = original_outl[1]-original_outl[0], original_outl[3]-original_outl[2]
        #roi position
        pos = np.array(self.target_image.pos())
        #width and height
        wd, ht = wd_o*self.scale_factor, ht_o*self.scale_factor
        #rotation angle (0-360)
        #ang = math.radians(self.move_box.angle()%360)
        ang = math.radians(self.target_attrs['Rotation'])
        diag_point_1 = pos + np.array([wd * math.cos(ang),wd * math.sin(ang)])
        diag_point_2 = pos + np.array([-ht * math.sin(ang),ht * math.cos(ang)])
        c_x, c_y = (diag_point_1 + diag_point_2)/2
        outl = [c_x-wd/2, c_x+wd/2, c_y-ht/2, c_y+ht/2, original_outl[-2],original_outl[-1]]
        self.target_attrs['Outline'] = outl

    def translate_target(self):
        def _center(outl):
            return np.array([(outl[0]+outl[1])/2, (outl[2]+outl[3])/2])
        translation_vector = QtCore.QPointF(*list(_center(self.reference_sub_outline))) - QtCore.QPointF(*list(_center(self.target_sub_outline)))
        self.target_image.setPos(translation_vector + self.target_image.pos())

    def dft_imreg2(self, downscale_target=True):
        """

        :return:
        """
        assert hasattr(self, 'reference_sub_outline'), "reference sub frame not yet selected"
        assert hasattr(self, 'target_sub_outline'), "target sub frame not yet selected"

        # // determine the image registration transform
        angle = (0,20)
        scale = (1,0.3)
        tx = (0,50)
        ty = (0,50)

        target_outline = self.target_sub_outline

        # // calculate new target size
        target_x_size = target_outline[1] - target_outline[0]
        target_y_size = target_outline[3] - target_outline[2]

        pixel_scale_ref = pixel_scale_target = 1
        self.target_zoom_frame = self.target_sub_frame

        '''
        import scipy.ndimage.interpolation as ndii
        if downscale_target:
            self.target_zoom_frame=ndii.zoom(self.target_sub_frame, (pixel_scale_ref/pixel_scale_target))
        else:
            # Alternatively, upscale the reference sub frame to the resolution of the target. Warning; this may
            # increase compute time.
            self.reference_sub_frame = ndii.zoom(self.reference_sub_frame, (pixel_scale_target/pixel_scale_ref))
            self.target_zoom_frame = self.target_sub_frame
        '''
        cv2.imwrite(r"C:\\Users\\qiucanro\\Downloads\\target_sub_frame_downscaled.jpg", self.target_zoom_frame)

        print("shapes:", self.target_zoom_frame.shape, self.reference_sub_frame.shape)
        # // match the shape of reference (template) frame and current frame (image to be transformed
        if self.target_zoom_frame.shape != self.reference_sub_frame.shape:
            # // pad on the right side
            x_diff = self.reference_sub_frame.shape[0]-self.target_zoom_frame.shape[0]
            y_diff = self.reference_sub_frame.shape[1] - self.target_zoom_frame.shape[1]
            left_pad = x_diff//2
            right_pad = x_diff - left_pad
            top_pad = y_diff//2
            bottom_pad = y_diff - top_pad
            if x_diff>=0 and y_diff>=0:
                self.target_zoom_frame = np.pad(self.target_zoom_frame, ((left_pad,right_pad), (top_pad, bottom_pad)), "edge")
            else:
                self.target_zoom_frame = self.target_zoom_frame[:self.reference_sub_frame.shape[0], :self.reference_sub_frame.shape[1]]
        else:
            print("no padding required")
        print("shapes:", self.target_zoom_frame.shape, self.reference_sub_frame.shape)
        # self.target_image.setImage(self.target_frame)
        # import cv2
        cv2.imwrite(r"C:\\Users\\qiucanro\\Downloads\\reference_sub_frame.jpg", self.reference_sub_frame)

        # import cv2
        cv2.imwrite(r"C:\\Users\\qiucanro\Downloads\\target_zoom_frame_padded.jpg", self.target_zoom_frame)

        # // get different frames (taking into account the scaling)
        
        vector_dict = registration_dft_slice(self.reference_sub_frame, self.target_zoom_frame, scale=scale, angle=angle,
                                                tx=tx, ty=ty, iterations=5, \
                                                display=True,  progressbar=None,
                                                display_window=None)

        if vector_dict["success"]:
            net_rotation_degrees = -vector_dict["angle"]
            #full_rotation_degrees = self.target_attrs["Rotation"] + net_rotation_degrees
            self.target_attrs['Rotation'] = self.target_attrs["Rotation"] + net_rotation_degrees
            # // note that the scale factor is calculated under the assumption that the images have the same pixel
            # // size, which is not the case
            self.scale_factor = vector_dict["scale"]
            # // correct for pixel size to calculate the correct scale factor

            arr = ird.imreg.transform_img_dict(self.target_sub_frame, tdict=vector_dict, bgval=None, order=1,
                                               invert=False)
            cv2.imwrite(r"C:\\Users\\qiucanro\\Downloads\\target_sub_frame_transformed.jpg", arr)

            print('DFT registration results:')
            print("tvec: ", vector_dict["tvec"])
            print("angle: ", vector_dict["angle"], self.target_attrs["Rotation"])
            print("scale: ", vector_dict["scale"])
            print(self.reference_image._scale, self.target_image._scale)
            print("scalefactor: ", self.scale_factor)

            #set rotation
            self.target_image.setRotation(self.target_attrs['Rotation'])

            #scale the image
            s = list(self.target_image._scale)
            tr = QtGui.QTransform()
            #scale it back according to the original scale
            tr.scale(1/s[0], 1/s[1])
            self.target_image.setTransform(tr)
            #now apply the real scaling factor
            tr = QtGui.QTransform()
            tr.scale(self.scale_factor*(s[0]), self.scale_factor*(s[1]))
            self.target_image.setTransform(tr)
            #store the new scaling factor
            self.target_image._scale = (self.scale_factor*s[0], self.scale_factor*s[1])
            #update outline info
            self._update_outl()

            return vector_dict

            # // the correction of the position for the rotation is needed.
            target_outline = self.target_attrs["Outline"].copy()
            pos1 = QtCore.QPointF((target_outline[1] - target_outline[0]) / 2, (target_outline[3] - target_outline[2]) / 2)
            pos2 = rotatePoint(centerPoint=(0.0, 0.0),
                                         point=((target_outline[1] - target_outline[0]) / 2, (target_outline[3] - target_outline[2]) / 2),
                                         angle=self.target_attrs["Rotation"])
            pos3 = rotatePoint(centerPoint=(0.0, 0.0),
                               point=pos2,
                               angle=-vector_dict["angle"])
            rotation_correction = (QtCore.QPointF(pos3[0], pos3[1]) - QtCore.QPointF(pos2[0], pos2[1]))
            self.target_image.setPos(self.target_image.pos() - rotation_correction)

            # // the correction is basically the distance between the image pos (left-top-corner) and the center, with a fraction of the scaling
            scale_position_correction = (1-vector_dict["scale"])*(QtCore.QPointF(pos3[0], pos3[1]))
            print("scale_position_correction:", scale_position_correction)
            self.target_image.setPos(self.target_image.pos() + scale_position_correction)

            # // convert tvec in pixel in the target image
            if downscale_target:
                vector_dict["tvec"] *= pixel_scale_target*(pixel_scale_ref / pixel_scale_target)
            # print(vector_dict["tvec"])
            # // convert shift in pixel into micron

            translation_component = QtCore.QPointF(vector_dict["tvec"][1], vector_dict["tvec"][0])
            print("translation_component",translation_component)
            self.target_image.setPos(self.target_image.pos() + translation_component)
        return vector_dict
