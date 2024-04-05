# -*- coding: utf-8 -*-


# // module to manage the field view
# from ui.workspace_widget import Ui_workspace_widget
import sys
from pathlib import Path
import numpy as np
import pyqtgraph as pg
import pyqtgraph.functions as fn
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from ..gui.widgets.scale_bar_tool import ScaleBar
from ..plugin.builtin_plugin.geometry_unit import geometry_widget_wrapper
from ..plugin.builtin_plugin.field_dft_registration import MdiFieldImreg_Wrapper
from ..plugin.builtin_plugin.field_fiducial_markers_unit import FiducialMarkerWidget_wrapper
from ..plugin.builtin_plugin.camera_control_module import camera_control_panel
from ..plugin.builtin_plugin.particle_tool import particle_widget_wrapper
from ..viewer.field_tools import FieldViewBox
from ..gui.widgets.context_menu_actions import check_true, MoveMotorTool, GaussianFitTool, GaussianSimTool
from ..gui.widgets.table_tree_widgets import TableWidgetDragRows
from ..resource.data_loaders.file_loader import load_align_xml
from ..resource.database_tool.image_buffer import ImageBufferInfo, ImageBufferObject
from sardana.taurus.qt.qtgui.extra_macroexecutor.macroexecutor import MacroExecutionWindow, ParamEditorManager
from taurus import Device
from taurus.core.util.containers import ArrayBuffer

setting_file = str(Path(__file__).parent.parent / 'resource' / 'config' / 'appsettings.ini')
ui_file_folder = Path(__file__).parent / 'ui'

class smartGui(MacroExecutionWindow, MdiFieldImreg_Wrapper, geometry_widget_wrapper, FiducialMarkerWidget_wrapper, particle_widget_wrapper, camera_control_panel):
    """
    Main class of the workspace
    """
    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)
    switch_selection_sig = Signal(str)
    #fiducial marking signals
    updateFieldMode_sig = Signal(str)
    removeTool_sig = Signal(object)
    saveimagedb_sig = Signal()

    def __init__(self, parent = None, designMode = False):
        """
        Initialize the class
        :param parent: parent widget
        :param settings_object: settings object
        """
        MacroExecutionWindow.__init__(self, parent, designMode)
        self.__init_gui()
        self.init_taurus()

    def __init_gui(self):
        uic.loadUi(str(ui_file_folder / 'img_reg_main_window.ui'), self)
        self.settings_object = QtCore.QSettings(setting_file, QtCore.QSettings.IniFormat)

        MdiFieldImreg_Wrapper.__init__(self)
        geometry_widget_wrapper.__init__(self)
        FiducialMarkerWidget_wrapper.__init__(self)
        particle_widget_wrapper.__init__(self)
        camera_control_panel.__init__(self)
        self.setMinimumSize(800, 600)
        self.widget_terminal.update_name_space('gui', self)
        self.widget_motor_widget.set_parent(self)
        self.widget_synoptic.set_parent(self)
        self._parent = self

        self.img_backup_path = "ImageBackup.imagedb"
        self.zoomfactor_relative_to_cam = 0
        self.field_list = []
        self.field_img = []
        self.patternCollection = []
        self.tbl_render_order = TableWidgetDragRows(self)
        self.tbl_render_order.setMaximumWidth(5000)
        self.tbl_render_order.setColumnCount(3)
        self.tbl_render_order.setHorizontalHeaderLabels(["Show", "Opacity", "Layer"])
        self.gridLayout_renderTable.addWidget(self.tbl_render_order)

        # // set up the custom view box
        self.field = FieldViewBox(lockAspect=True, _parent=self)
        self.field.invertY()

        from pyqtgraph import GraphicsLayoutWidget
        self.graphicsView_field = GraphicsLayoutWidget(self)
        self.graphicsView_field_color_bar = GraphicsLayoutWidget(self)
        self.graphics_layout.addWidget(self.graphicsView_field)
        self.grid_alignment.addWidget(self.graphicsView_field_color_bar)
        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        # self.hist.sigLevelChangeFinished.connect(lambda:self.statusbar.showMessage(str(self.hist.getLevels())))
        self.graphicsView_field_color_bar.addItem(self.hist,row=0,col=0)
        self.graphicsView_field.setCentralItem(self.field)
        self.set_cursor_icon()

        self.field.scene().sigMouseMoved.connect(self.field.mouseMoved_custom)

        self.ScanList_items = []
        self.move_box = None
        self.update_field_current = None
        self.field.enableAutoRange(x=False, y=False)

        original = self.field.resizeEvent

        def resizeEventWrapper(event):
            original(event)

            # // range restriction
            v = self.field.height() / self.field.width()
            d = np.max((self.X_controller_travel, self.Y_controller_travel)) / v
            self.field.setLimits(xMin=-0.6 * d,
                                 xMax=1.2 * d, \
                                 yMin=-0.1 * d * v,
                                 yMax=1.1 * d * v, \
                                 minXRange=2, minYRange=2 * v, \
                                 maxXRange=1.2 * d,
                                 maxYRange=1.2 * d * v)

        resizeEventWrapper._original = original
        self.field.resizeEvent = resizeEventWrapper
        self.drawMode = 'auto'

        self.update_environment_color(self.settings_object.value("Visuals/environmentBackgroundColor"))

        # // check for the ablation cell:

        self.X_controller_travel, self.Y_controller_travel = 100000, 100000
        if self.settings_object.contains("Stages"):
            if "(100 mm X 100mm)" in self.settings_object.value('Stages'):
                self.X_controller_travel, self.Y_controller_travel = 100000, 100000
            elif "(150 mm X 150 mm)" in self.settings_object.value('Stages'):
                self.X_controller_travel, self.Y_controller_travel = 150000, 150000
            elif "(50 mm X 50 mm)" in self.settings_object.value('Stages'):
                self.X_controller_travel, self.Y_controller_travel = 50000, 50000

        # self.add_workspace()
        # self.autoRange(padding=0.02)
        if self.settings_object.contains("FileManager/restoreimagedb"):
            self.img_backup_path = self.settings_object.value("FileManager/restoreimagedb")

        self.imageBuffer = ImageBufferInfo(self,
                                           self.img_backup_path)
        self.tbl_render_order.imageBuffer = self.imageBuffer

        # // draw scalebar
        self.draw_scalebar()
        self.connect_slots()
        self.imageBuffer.recallImgBackup()
        self.highlightFirstImg()

    def init_taurus(self):
        #ui is a *.ui file from qt designer
        self._qDoor = None
        self.doorChanged.connect(self.onDoorChanged)
        # TaurusMainWindow.loadSettings(self)
        #sequencer slot
        self.widget_sequencer.doorChanged.connect(
        self.widget_sequencer.onDoorChanged)
        self.registerConfigDelegate(self.widget_sequencer)
        self.widget_sequencer.shortMessageEmitted.connect(
            self.onShortMessage)
        self.createFileMenu()
        self.createViewMenu()
        self.createToolsMenu()
        # self.createTaurusMenu()
        self.createHelpMenu()
        #it is needed for backward compatibility for using qtspock
        self.widget_spock.kernel_manager.is_valid_spock_profile = True
        self.widget_spock.set_default_style('linux')

    def connect_mouseClick_event_for_online_monitor(self):
        self.move_motor_action = None
        self.motor_pos_marker = None
        plots = list(self.widget_online_monitor._plots.keys())
        plots_motor_as_x_axis = [plot for plot in plots if plot.x_axis['name'] != 'point_nb']
        if len(plots_motor_as_x_axis)>1:
            plots_motor_as_x_axis = plots_motor_as_x_axis[0:1]
        # self.sig_proxy_test =pg.SignalProxy(list(self.widget_online_monitor._plots.keys())[0].scene().sigMouseClicked, slot = self.onMouseClicked_online_monitor)

        def onMouseClicked_online_monitor(evt):

            if evt[0].button()==1:#ignore left click
                return
            else:
                if self.move_motor_action == None:
                    self.motor_pos_marker = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('g', width=1, style=QtCore.Qt.SolidLine))
                    self.motor_pos_marker.sigPositionChangeFinished.connect(self.move_motor_to_finishing_line)
                    self.move_motor_action = MoveMotorTool(self, door_device=self.widget_online_monitor.manager.door, motor_marker_line_obj=self.motor_pos_marker)
                    self.move_motor_action.attachToPlotItem(plot)
                    self.widget_online_monitor.manager.bind_obj = self.motor_pos_marker
                    self.widget_online_monitor.manager.setModel(Device(plot.x_axis['name'])._full_name+'/Position', key='motor')
                    plot.addItem(self.motor_pos_marker)
                    self.gaussian_fit_menu = GaussianFitTool(self)
                    self.gaussian_fit_menu.attachToPlotItem(plot)
                    self.gaussian_fit_menu.add_actions(plot, curves)
                    self.gaussian_sim_menu = GaussianSimTool(self)
                    self.gaussian_sim_menu.attachToPlotItem(plot)
                    self.gaussian_sim_menu.add_actions(plot, curves)
                #self.test_evt = evt
                pos_scene = evt[0].pos()
                pos_view = plot.vb.mapSceneToView(pos_scene)
                mot_name = plot.x_axis['name']
                self.move_motor_action.setText(f'move {mot_name} to {round(pos_view.x(),3)}?')
                self.move_motor_action.motor_pos = round(pos_view.x(),3)
                self.move_motor_action.motor_name = mot_name

                self.statusbar.showMessage(f"click at pos: {pos_view}")
        for plot in plots_motor_as_x_axis:
            # self.widget_online_monitor.setModel('motor/motctrl01/1/Position',key='motor')
            curves = list(self.widget_online_monitor._plots[plot].values())
            #now make a new plot for holding fit (eg gaussian or Lorenz) result
            nb_points = curves[-1].curve_data.maxSize()
            curve_item = plot.plot(name = 'fit')
            curve_item.curve_data = ArrayBuffer(np.full(nb_points, np.nan))
            curves.append(curve_item)
            self.signal_proxy = pg.SignalProxy(plot.scene().sigMouseClicked, slot = onMouseClicked_online_monitor)

    @Slot(object)
    def move_motor_to_finishing_line(self, infinitline_obj):
        self.widget_online_monitor.manager.door.runMacro(f'<macro name="mv"><paramrepeat name="motor_pos_list"><repeat nr="1">\
                                <param name="motor" value="{self.move_motor_action.motor_name}"/><param name="pos" value="{infinitline_obj.value()}"/>\
                                </repeat></paramrepeat></macro>')

    def setCustomMacroEditorPaths(self, customMacroEditorPaths):
        MacroExecutionWindow.setCustomMacroEditorPaths(
            self, customMacroEditorPaths)
        ParamEditorManager().parsePaths(customMacroEditorPaths)
        ParamEditorManager().browsePaths()

    def updateParameter(self):
        self.taurusCommandButton.setParameters([self.lineEdit_mot1.text()])        

    def onDoorChanged(self, doorName):
        MacroExecutionWindow.onDoorChanged(self, doorName)
        if self._qDoor:
            self._qDoor.macroStatusUpdated.disconnect(
                self.widget_sequencer.onMacroStatusUpdated)
        if doorName == "":
            return
        self._qDoor = Device(doorName)
        self._qDoor.macroStatusUpdated.connect(
            self.widget_sequencer.onMacroStatusUpdated)
        self.widget_sequencer.onDoorChanged(doorName)
        self.widget_online_monitor.setModel(doorName)
        self.widget_spock.setModel(doorName)
        self.widget_motor_widget.update_motor_viewer()


    def setModel(self, model):
        MacroExecutionWindow.setModel(self, model)
        self.widget_sequencer.setModel(model)  

    def contextMenuEvent(self, event):
        """Reimplemented to show self.taurusMenu in as a context Menu
        See https://gitlab.com/taurus-org/taurus/-/merge_requests/906
        """
        try:
            self.taurusMenu.exec_(event.globalPos())
        except:
            pass

    def switch_mode_from_radio_button_control(self, text):
        if 'select' in text:
            self.field.measure_tool.hide()
            self.field.set_mode('select')
            self.update_geo()
            if hasattr(self, 'move_box'):
                self.move_box.show()
        elif 'fiducial' in text:
            self.field.measure_tool.hide()
            self.field.set_mode('fiducial_marker')
            self.update_fiducial()
            if hasattr(self, 'move_box'):
                self.move_box.hide()
        elif 'dft' in text:
            self.field.measure_tool.hide()
            self.field.set_mode('dft')
            if hasattr(self, 'move_box'):
                self.move_box.hide()
        elif 'particle' in text:
            self.field.set_mode('particle')
            self.field.measure_tool.show()
            if hasattr(self, 'move_box'):
                self.move_box.hide()
            self.set_pars_for_locating_particle_on_gui()

    @Slot(int)    
    def switch_mode(self, tabIndex):
        tabText = self.tabWidget.tabText(tabIndex).lower()
        if 'fiducial' in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode('fiducial_marker')
            self.update_fiducial()
            if hasattr(self, 'move_box'):
                self.move_box.hide()
            self.radioButton_fiducial.click()
        elif 'dft' in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode('dft')
            if hasattr(self, 'move_box'):
                self.move_box.hide()
            self.radioButton_dft.click()
        elif 'geometry' in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode('select')
            self.update_geo()
            if hasattr(self, 'move_box'):
                self.move_box.show()
            self.radioButton_select.click()
            # if 'particle' in tabText:#filled the save pars for particle tracking
                # self.set_pars_for_locating_particle_on_gui()
        elif 'particle' in tabText:
            self.field.set_mode('particle')
            self.field.measure_tool.show()
            if hasattr(self, 'move_box'):
                self.move_box.hide()
            self.set_pars_for_locating_particle_on_gui()
            self.radioButton_particle.click()

    def set_cursor_icon(self, cursor_type="cross"):
        """
        Change the cursor icon
        :param type:
        :return:
        """
        if cursor_type == "cross":
            cursor_custom = QtGui.QCursor(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'Cursors' / 'target_cursor_32x32.png')))
        elif cursor_type == "pen":
            cursor_custom = QtGui.QCursor(QtGui.QPixmap(":/icon/cursor_pen.png"), hotX=26, hotY=23)
        elif cursor_type == "align":
            cursor_custom = QtGui.QCursor(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'Cursors' / "registration_cursor_32x32.png")), hotX=26, hotY=23)
        self.graphicsView_field.setCursor(cursor_custom)

    def connect_slots(self):
        """
        :return:
        """
        #online monitor event
        self.widget_online_monitor.manager.newPrepare.connect(self.connect_mouseClick_event_for_online_monitor)
        self.widget_online_monitor.manager.newShortMessage.connect(self.statusbar.showMessage) 
        #save image buffer sig
        self.saveimagedb_sig.connect(self.imageBuffer.writeImgBackup)
        #tabwidget signal
        self.tabWidget.tabBarClicked.connect(self.switch_mode)
        #dft slots
        self.connect_slots_dft()
        #fiducial slots
        self.connect_slots_fiducial()
        #geo slots
        self.connect_slots_geo()
        #particle slots
        self.connect_slots_par()
        #cam stream slots
        self.connect_slots_cam()
        #widget events
        self.bt_removeMenu.setMenu(QtWidgets.QMenu(self.bt_removeMenu))
        self.bt_removeMenu.clicked.connect(self.bt_removeMenu.showMenu)
        self.bt_delete = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_removeMenu)
        action.setDefaultWidget(self.bt_delete)
        self.bt_removeMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'FileSystem' / 'close_file_128x128.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bt_delete.setIcon(icon1)
        self.bt_delete.setIconSize(QtCore.QSize(32, 32))
        self.bt_delete.setText("Delete Selected Images")
        self.bt_delete.clicked.connect(self.tbl_render_order.deleteSelection)
        self.bt_clear_tbl = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_removeMenu)
        action.setDefaultWidget(self.bt_clear_tbl)
        self.bt_removeMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'FileSystem' / 'close_file_128x128.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bt_clear_tbl.setIcon(icon1)
        self.bt_clear_tbl.setIconSize(QtCore.QSize(32, 32))
        self.bt_clear_tbl.setText("Clear workspace")
        self.bt_clear_tbl.clicked.connect(self.clear)
        self.tbl_render_order.cellClicked.connect(self.tblItemClicked)

        self.bt_imageMenu.setMenu(QtWidgets.QMenu(self.bt_imageMenu))
        self.bt_imageMenu.clicked.connect(self.bt_imageMenu.showMenu)
        self.bt_recall_imagedb = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_recall_imagedb)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'FileSystem' / 'open_folder_128x128.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bt_recall_imagedb.setIcon(icon1)
        self.bt_recall_imagedb.setIconSize(QtCore.QSize(32, 32))
        self.bt_recall_imagedb.setText("Load Image Database")
        self.bt_recall_imagedb.clicked.connect(self.loadImgBufferFromDisk)

        self.bt_export_imagedb = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_export_imagedb)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'FileSystem' / 'save_as_128x128.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bt_export_imagedb.setIcon(icon1)
        self.bt_export_imagedb.setIconSize(QtCore.QSize(32, 32))
        self.bt_export_imagedb.setText("Save and export images")
        self.bt_export_imagedb.clicked.connect(self.saveImageBuffer)

        self.bt_import_image = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_import_image)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(str(ui_file_folder / 'icons' / 'FileSystem' / 'open_folder_128x128.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bt_import_image.setIcon(icon1)
        self.bt_import_image.setText("Import image")
        self.bt_import_image.setIconSize(QtCore.QSize(32, 32))
        self.bt_import_image.clicked.connect(lambda: self.import_image_from_disk())

    def expand_full(self):
        self.mdi_field_widget.autoRange()

    def update_environment_color(self, color):
        """
        Updates the color of the widget
        :param color:
        :return:
        """
        if color:
            self.field.setBackgroundColor(color)

    def _clear_borders(self):
        # // when a new dataset is added, remove the selection box in the field view
        for k in self.field_img:
            if isinstance(k, pg.ImageItem):
                k.setBorder(None)

            elif isinstance(k, list):
                for v in k:
                    v.setBorder(None)
            elif isinstance(k, ImageBufferObject):
                k.setBorder(None)
            else:
                # // must be scatterplotitem
                print(type(k))

    def _show_border(self):
        if check_true(self.settings_object.value("Visuals/showBox")):
            border_pen = fn.mkPen(color=self.settings_object.value("Visuals/boxColor"),
                                  width=int(self.settings_object.value("Visuals/boxLinewidth")))
            self.update_field_current.setBorder(border_pen)
        else:
            self.update_field_current.setBorder(None)

    def tblItemClicked(self, row, column):
        # // set a border around the clicked item and set it as the current image
        loc = self.tbl_render_order.item(row, 2).loc
        # // in theory, the row should be == self.field_list.index(loc)
        if self.field_list.index(loc) >= 0:
            self._clear_borders()
            self.update_field_current = self.field_img[self.field_list.index(loc)]
            self._show_border()

    def import_image_from_disk(self, source_path_list = []):
        # // open up an image for importing data
        import os
        if len(source_path_list) < 1:
            dialog = QtWidgets.QFileDialog()
            path = QtCore.QDir.toNativeSeparators(self.settings_object.value("FileManager/currentimagedbDir"))
            if os.path.exists(path):
                try:
                    os.chdir(path)
                except:
                    QtCore.qDebug("Error: invalid directory")
            source_path_list, _ = dialog.getOpenFileNames(self, "Open image file to be imported", os.getcwd(), \
                                                        "Image file (*.tif *.tiff *.png *.jpeg *.jpg *.bmp);;All Files (*)")
        

        if len(source_path_list) > 0:
            for filePath in source_path_list:
                if not os.path.exists(filePath):
                    continue
                d = {}
                d["Path"] = filePath
                d["Name"] = os.path.split(filePath)[-1]
                d["Focus"] = 0.0
                d["Opacity"] = 100
                d["Visible"] = True
                d["Parent"] = ""
                d["DTYPE"] = "RGBA"
                d["BaseFolder"] = os.path.dirname(filePath)
                # // check for .align file
                if os.path.exists(os.path.splitext(filePath)[0] + ".Align"):
                    xml_path = os.path.splitext(filePath)[0] + ".Align"
                    ret = load_align_xml(xml_path)
                    if ret:
                        d.update(ret)

                self.imageBuffer.load_qi(d)

            self.settings_object.setValue("FileManager/currentimagedbDir", os.path.dirname(source_path_list[0]))
            self.tbl_render_order.resizeRowsToContents()
            self.tbl_render_order.setColumnWidth(0, 55)
        
    def loadImgBufferFromDisk(self):
        import os
        dialog = QtWidgets.QFileDialog()
        path = QtCore.QDir.toNativeSeparators(self.settings_object.value("FileManager/currentimagedbDir"))
        if os.path.exists(path):
            try:
                os.chdir(path)
            except:
                QtCore.qDebug("Error: invalid directory")
        source_path_list, _ = dialog.getOpenFileName(self, "Open .imagedb file to be imported", os.getcwd(), \
                                                     "imagedb files (*.imagedb);;All Files (*)")

        # // select files based on tumbnails
        exclude_file_list = []

        if os.path.exists(source_path_list):
            dict_list = self.imageBuffer.load_imagedb(xml_path=source_path_list, exclude_file_list=exclude_file_list)
            self.settings_object.setValue("FileManager/currentimagedbDir", os.path.dirname(source_path_list))
        else:
            self.statusMessage_sig.emit("Invalid path for the .imagedb file")
            return None

        if dict_list:
            self.imageBuffer.attrList += dict_list
            self.imageBuffer.writeImgBackup()

    def saveImageBuffer(self):
        import os
        dialog = QtWidgets.QFileDialog()
        path = QtCore.QDir.toNativeSeparators(self.settings_object.value("FileManager/currentimagedbDir"))
        if os.path.exists(path):
            os.chdir(path)
        source_path_list, _ = dialog.getSaveFileName(self, "Open .imagedb file to be imported", os.getcwd(), \
                                                     "imagedb files (*.imagedb);;All Files (*)")
        if os.path.exists(os.path.dirname(source_path_list)):
            # self.imageBuffer.writeimagedb(xml_path=source_path_list)
            self.imageBuffer.writeImgBackup(path=source_path_list)
        else:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       """<p>Invalid export path.<p>""")

    def draw_scalebar(self):
        """
        Draw a scalebar
        :return:
        """
        # // remove current scalebar

        if hasattr(self, 'sb'):
            if self.sb in self.field.scene().items():
                self.sb.hide()
                self.sb.update()
                self.field.removeItem(self.sb)
                self.field.scene().update()

        if self.settings_object.value("Visuals/showScalebar"):
            zoom = 1.0

        
        # // save this settings to the settings file
        self.sb = ScaleBar(size=float(self.settings_object.value("ScaleSize")),
                           height=int(self.settings_object.value("ScaleHeight")),
                           position=self.settings_object.value("ScalePosition"),
                           brush=self.settings_object.value("ScaleColor"),
                           pen=self.settings_object.value("ScaleColor"),
                           fs=int(self.settings_object.value("ScaleFontSize")),
                           suffix='um')
        self.field.addItem(self.sb)
        self.sb.setParentItem(self.field)
        self.sb._scaleAnchor__parent = self.field
        # self.sb.anchor((1, 1), (1, 1), offset=(-30, -30))
        self.sb.updateBar()
        self.show_scale_bar(self.settings_object.value("Visuals/showScalebar"))
        # print(type(self.settings_object.value("Visuals/showScalebar")))
        #self.show_scale_bar(False)

    def show_scale_bar(self, enabled):
        if type(enabled)==str:
            if enabled in ['0', 'False', 'false']:
                enabled = False
            else:
                enabled = True
        elif type(enabled) == bool:
            pass
        elif type(enabled)==int:
            if enabled==0:
                enabled = False
            else:
                enabled = True
        if enabled:
            self.sb.show()
        else:
            self.sb.hide()

    def delete(self, row):
        """
        Deletes a specific row from the table
        :param row:
        :return:
        """
        item = self.tbl_render_order.item(row, 2)
        if item.loc in self.field_list:
            i = self.field_list.index(item.loc)

            # // delete image from the buffer
            if isinstance(self.field_img[i], ImageBufferObject):
                self.imageBuffer.removeImgBackup(item.loc)
            # // untick the image in the pipeline
            elif isinstance(self.field_img[i], pg.ImageItem):
                self.clearSingleTick.emit(item.loc)

            self.field.removeItem(self.field_img[i])
            del self.field_img[i]
            del self.field_list[i]

        # // removing row from field list
        self.tbl_render_order.removeRow(row)

        # // recalculate_all the render order
        self.tbl_render_order.field_order_update()

    def clear(self):
        """
        Clear the workspace by removing all images.
        :return:
        """
        # // clear internal list
        self.field.clear()
        # // alternative is to delete all items in the field view
        for img in self.field_img:
            self.field.removeItem(img)
            img.deleteLater()

        self.field_list = []
        self.field_img = []
        self.move_box = False
        self.update_field_current = None

        # // clear imageBuffer and backup
        self.imageBuffer.attrList = []
        self.imageBuffer.writeImgBackup()

        # // clear table
        self.tbl_render_order.clear()
        self.tbl_render_order.setColumnCount(3)
        self.tbl_render_order.setRowCount(0)
        self.tbl_render_order.setHorizontalHeaderLabels(["Show", "Opacity", "Layer"])
        # self.tbl_render_order.setAlternatingRowColors(True)
        self.tbl_render_order.horizontalHeader().ResizeMode = QtWidgets.QHeaderView.ResizeToContents

        # // remove colorbar
        if hasattr(self, 'cb'):
            if self.cb in self.field.scene().items():
                self.field.scene().removeItem(self.cb)
                self.field.scene().update()

        # // remove scale
        if hasattr(self, 'sb'):
            if self.sb in self.field.scene().items():
                self.field.removeItem(self.sb)
                self.field.scene().update()

    def on_table_order_clicked(self, item):
        row = item.row()
        if item:
            pass
        else:
            return None

        current_group = self.tbl_render_order.item(row, 2).loc
        if 1:
            field_i = self.field_list.index(current_group)
            if self.tbl_render_order.item(row, 0).checkState():
                self.field_img[field_i].show()
            elif not self.tbl_render_order.item(row, 0).checkState():
                self.field_img[field_i].hide()
            return None

    def autoRange(self, items=None, padding=0.2):
        """
        Set the range of the view box to make all children visible.
        Note that this is not the same as enableAutoRange, which causes the view to 
        automatically auto-range whenever its contents are changed.
        
        ==============  ============================================================
        **Arguments:**
        padding         The fraction of the total data range to add on to the final
                        visible range. By default, this value is set between 0.02
                        and 0.1 depending on the size of the ViewBox.
        items           If specified, this is a list of items to consider when
                        determining the visible range.
        ==============  ============================================================
        """
        if items:
            bounds = self.field.mapFromItemToView(items[0], items[0].boundingRect()).boundingRect()
        else:
            bounds = self.field.childrenBoundingRect(items=items)
        if bounds is not None:
            self.field.setRange(bounds, padding=padding)

    def field_remove(self, current_group):
        # // update the table and the render order
        if current_group in self.field_list:
            try:
                self.delete(self.field_list.index(current_group))
            except:
                QtCore.qDebug("Failed to delete group")

    def progressUpdate(self, v):
        # slot for updating the progressbar
        self.progressbar.setValue(v)

    def statusUpdate(self, m):
        # slot for showing a message in the statusbar.
        self.statusbar.showMessage(m)

    def closeEvent(self, event):
        import time
        quit_msg = "About to Exit the program, are you sure? "
        reply = QMessageBox.question(self, 'Message', 
                        quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:        
            reply2 = QMessageBox.question(self, 'Message', 
                        "Do you want to save the image setting to db before exit?", QMessageBox.Yes, QMessageBox.No)
            if reply2 == QMessageBox.Yes:
                self.saveimagedb_sig.emit()
                event.accept()
            else:
                event.accept()
        elif reply == QMessageBox.No:
            event.ignore()