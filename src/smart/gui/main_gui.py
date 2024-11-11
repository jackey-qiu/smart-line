# -*- coding: utf-8 -*-


# // module to manage the field view
# from ui.workspace_widget import Ui_workspace_widget
import sys, socket
import yaml
from pathlib import Path
import numpy as np
import qdarkstyle
import pyqtgraph as pg
import pyqtgraph.functions as fn
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot, QTimer
from ..gui.widgets.scale_bar_tool import ScaleBar
from PyQt5.QtWidgets import QAction, QToolBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from ..plugin.builtin_plugin.geometry_unit import geometry_widget_wrapper
from ..plugin.builtin_plugin.field_dft_registration import MdiFieldImreg_Wrapper
from ..plugin.builtin_plugin.field_fiducial_markers_unit import (
    FiducialMarkerWidget_wrapper,
)
from smart import icon_path
from smart.util.util import remove_multiple_tabs_from_tabWidget
from ..plugin.builtin_plugin.camera_control_module import camera_control_panel
from ..plugin.builtin_plugin.particle_tool import particle_widget_wrapper
from ..plugin.builtin_plugin.beamline_control import beamlineControl
from ..plugin.builtin_plugin.synoptic_viewer_contol import synopticViewerControl
from ..plugin.user_plugin.queue_control import queueControl
from ..viewer.field_tools import FieldViewBox
from ..gui.widgets.context_menu_actions import (
    check_true,
    MoveMotorTool,
    GaussianFitTool,
    GaussianSimTool,
)
from ..gui.widgets.table_tree_widgets import TableWidgetDragRows
from ..resource.data_loaders.file_loader import load_align_xml
from ..resource.database_tool.image_buffer import ImageBufferInfo, ImageBufferObject
from sardana.taurus.qt.qtgui.extra_macroexecutor.macroexecutor import (
    MacroExecutionWindow,
    ParamEditorManager,
)
from taurus import Device
from taurus.core.util.containers import ArrayBuffer


setting_file = str(
    Path(__file__).parent.parent / "resource" / "config" / "appsettings.yaml"
)
ui_file_folder = Path(__file__).parent / "ui"
hostname = socket.gethostname()


class smartGui(
    MacroExecutionWindow,
    MdiFieldImreg_Wrapper,
    geometry_widget_wrapper,
    FiducialMarkerWidget_wrapper,
    particle_widget_wrapper,
    camera_control_panel,
    beamlineControl,
    synopticViewerControl,
    queueControl,
):
    """
    Main class of the workspace
    """

    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)
    switch_selection_sig = Signal(str)
    # fiducial marking signals
    updateFieldMode_sig = Signal(str)
    removeTool_sig = Signal(object)
    saveimagedb_sig = Signal()

    def __init__(self, parent=None, designMode=False, config="default"):
        """
        Initialize the class
        :param parent: parent widget
        :param settings_object: settings object
        """
        MacroExecutionWindow.__init__(self, parent, designMode)
        self.user_right = "normal"
        self.__init_gui(config=config)
        self.init_taurus()
        self.add_smart_toolbar()
        self._connect_device_at_startup()
        self.widget_pars.init_pars(self.settings_object)
        remove_multiple_tabs_from_tabWidget(self.settings_object.get('viewerTabWidgetVisibility',{}), self.tabWidget_viewer)

    def _upon_settings_change(self):
        self._connect_device_at_startup()
        if (
            "FileManager" in self.settings_object
            and "restoreimagedb" in self.settings_object["FileManager"]
        ):
            self.img_backup_path = self.settings_object["FileManager"]["restoreimagedb"]

        self.imageBuffer = ImageBufferInfo(self, self.img_backup_path)
        self.tbl_render_order.imageBuffer = self.imageBuffer

        self.imageBuffer.recallImgBackup()

    def _connect_device_at_startup(self):
        #connect tango model at startup?
        if 'connect_model_startup' in self.settings_object['General']:
            if self.settings_object['General']['connect_model_startup']:
                try:
                    self.set_models()
                except:
                    pass
                self.start_cam_stream()
                self._resume_prim_beam_pos(direct=True)
                self.camara_widget.isoLine_h.sigPositionChanged.connect(self._calibrate_pos)
                self.camara_widget.isoLine_v.sigPositionChanged.connect(self._calibrate_pos)
            else:
                self.camara_widget.isoLine_h.sigPositionChanged.connect(self._calibrate_pos)
                self.camara_widget.isoLine_v.sigPositionChanged.connect(self._calibrate_pos)
        else:
            try:
                self.set_models()
            except:
                pass
            self.start_cam_stream()
            self._resume_prim_beam_pos(direct=True)
            self.camara_widget.isoLine_h.sigPositionChanged.connect(self._calibrate_pos)
            self.camara_widget.isoLine_v.sigPositionChanged.connect(self._calibrate_pos)

    def __init_gui(self, config):
        uic.loadUi(str(ui_file_folder / "smart_main_window.ui"), self)
        if config == "default":
            # self.settings_object = QtCore.QSettings(setting_file, QtCore.QSettings.IniFormat)
            self.setting_file_yaml = str(setting_file)
            with open(str(setting_file), "r", encoding="utf8") as f:
                self.settings_object = yaml.safe_load(f.read())
        else:
            self.setting_file_yaml = str(config)
            with open(str(config), "r", encoding="utf8") as f:
                self.settings_object = yaml.safe_load(f.read())
            # self.settings_object = QtCore.QSettings(config, QtCore.QSettings.IniFormat)

        if self.settings_object["General"]["beamlinePCHostName"] == hostname:
            self.user_right = "super"
        MdiFieldImreg_Wrapper.__init__(self)
        geometry_widget_wrapper.__init__(self)
        FiducialMarkerWidget_wrapper.__init__(self)
        particle_widget_wrapper.__init__(self)
        camera_control_panel.__init__(self)
        beamlineControl.__init__(self)
        synopticViewerControl.__init__(self)
        queueControl.__init__(self)
        self.setMinimumSize(800, 600)
        self.widget_terminal.update_name_space("gui", self)
        # self.widget_motor_widget.set_parent(self)
        # self.widget_synoptic.set_parent(self)
        # self.widget_queue_synoptic_viewer.set_parent(self)
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
        self.graphicsView_field_color_bar.addItem(self.hist, row=0, col=0)
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
            self.field.setLimits(
                xMin=-0.6 * d,
                xMax=1.2 * d,
                yMin=-0.1 * d * v,
                yMax=1.1 * d * v,
                minXRange=2,
                minYRange=2 * v,
                maxXRange=1.2 * d,
                maxYRange=1.2 * d * v,
            )

        resizeEventWrapper._original = original
        self.field.resizeEvent = resizeEventWrapper
        self.drawMode = "auto"

        # self.update_environment_color(self.settings_object.value("Visuals/environmentBackgroundColor"))
        # self.update_environment_color(self.settings_object["Visuals"]['environmentBackgroundColor'])

        # // check for the ablation cell:

        self.X_controller_travel, self.Y_controller_travel = 100000, 100000
        if "Stages" in self.settings_object:
            if "(100 mm X 100mm)" in self.settings_object["Stages"]:
                self.X_controller_travel, self.Y_controller_travel = 100000, 100000
            elif "(150 mm X 150 mm)" in self.settings_object["Stages"]:
                self.X_controller_travel, self.Y_controller_travel = 150000, 150000
            elif "(50 mm X 50 mm)" in self.settings_object["Stages"]:
                self.X_controller_travel, self.Y_controller_travel = 50000, 50000

        # self.add_workspace()
        # self.autoRange(padding=0.02)
        if (
            "FileManager" in self.settings_object
            and "restoreimagedb" in self.settings_object["FileManager"]
        ):
            self.img_backup_path = self.settings_object["FileManager"]["restoreimagedb"]

        self.imageBuffer = ImageBufferInfo(self, self.img_backup_path)
        self.tbl_render_order.imageBuffer = self.imageBuffer

        # // draw scalebar
        # self.draw_scalebar()

        self.connect_slots()
        self.init_attribute_values()
        self.imageBuffer.recallImgBackup()
        self.highlightFirstImg()

    def change_stylesheet(self, on_or_off, action_icons):
        if hasattr(self, 'app'):
            app = self.app
            if on_or_off:
                app.setStyleSheet('')
            else:
                app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        str_mode = ['k','w'][int(on_or_off)]
        self.camara_widget.setBackground(str_mode)
        self.graphicsView_field.setBackground(str_mode)
        self.graphicsView_field_color_bar.setBackground(str_mode)
        self.widget_taurus_plot.setBackground(str_mode)
        self.widget_taurus_2d_plot.setBackground(str_mode)
        if on_or_off:
            action_icons[0].setVisible(False)
            action_icons[1].setVisible(True)
        else:
            action_icons[1].setVisible(False)
            action_icons[0].setVisible(True)

    def add_smart_toolbar(self):
        tb = QToolBar("SMART Toolbar")
        tb.setObjectName("SMART Toolbar")
        #        tb.addAction(self.changeTangoHostAction)
        #        tb.addWidget(self.taurusLogo)
        connect = QAction(QIcon(str(icon_path / 'others' / 'connect.png')),'connect tango device',self)
        connect.setStatusTip('Connect tango device servers and setup spock section.')
        connect.triggered.connect(self.set_models)
        save = QAction(QIcon(str(icon_path / 'smart' / 'save.png')),'save config file',self)
        save.setStatusTip('Save config file.')
        save.triggered.connect(self.update_setting_file)
        stop = QAction(QIcon(str(icon_path / 'smart' / 'stop_macro.png')),'abort macro run',self)
        stop.setStatusTip('Stop currently running macro.')
        stop.triggered.connect(lambda: Device(self.settings_object['spockLogin']['doorName']).AbortMacro())
        lighton = QAction(QIcon(str(icon_path / 'smart' / 'lighton.png')),'turn on light',self)
        lighton.setStatusTip('Change the GUI stylesheet to light mode.')
        lighton.setVisible(False)
        lightoff = QAction(QIcon(str(icon_path / 'smart' / 'lightoff.png')),'turn off light',self)
        lightoff.setStatusTip('Change the GUI stylesheet to dark mode.')
        lighton.triggered.connect(lambda: self.change_stylesheet(True,[lighton,lightoff]))        
        lightoff.triggered.connect(lambda: self.change_stylesheet(False,[lighton,lightoff]))  
        self.change_stylesheet(True,[lighton,lightoff])
        lightoff.setVisible(True)
        tb.addAction(connect)
        tb.addAction(save)
        tb.addAction(stop)
        tb.addAction(lighton)
        tb.addAction(lightoff)
        self.smart_toolbar = tb
        self.addToolBar(self.smart_toolbar)

    def init_attribute_values(self):
        #TODO: this func should be get rid of, since these attributes are synoptic specific for psd pump, should not be set as global ones
        self.first_client = True
        self.mvp_pos = 1
        self.auto_exchange = True
        self.leftover_vol = 1000
        self.volume_change_on_the_fly = 50
        self.volume_syringe_1 = 0
        self.volume_syringe_2 = 0
        self.volume_syringe_3 = 0
        self.volume_syringe_4 = 0
        self.volume_reservoir = 0
        self.volume_cell = 0
        self.volume_waste = 0
        self.exchange_timer = QTimer()
        self.check_vol_timer = QTimer()
        self.syringe_lines_container = {}
        self.lines_draw_before = []
        self.lines_draw_after = []
        self.pen_lines_draw_before = []
        self.pen_lines_draw_after = []

    def init_taurus(self):
        # ui is a *.ui file from qt designer
        self._qDoor = None
        self.doorChanged.connect(self.onDoorChanged)
        # TaurusMainWindow.loadSettings(self)
        # sequencer slot
        self.widget_sequencer.doorChanged.connect(self.widget_sequencer.onDoorChanged)
        self.registerConfigDelegate(self.widget_sequencer)
        self.widget_sequencer.shortMessageEmitted.connect(self.onShortMessage)
        self.createFileMenu()
        self.createViewMenu()
        self.createToolsMenu()
        # self.createTaurusMenu()
        self.createHelpMenu()
        # it is needed for backward compatibility for using qtspock
        if self.settings_object['spockLogin']['useQTSpock']:
            self.widget_spock.kernel_manager.is_valid_spock_profile = True
            self.widget_spock.set_default_style("linux")

    def connect_mouseClick_event_for_online_monitor(self):
        self.move_motor_action = None
        self.motor_pos_marker = None
        plots = list(self.widget_online_monitor._plots.keys())
        plots_motor_as_x_axis = [
            plot for plot in plots if plot.x_axis["name"] != "point_nb"
        ]
        if len(plots_motor_as_x_axis) > 1:
            plots_motor_as_x_axis = plots_motor_as_x_axis[0:1]
        # self.sig_proxy_test =pg.SignalProxy(list(self.widget_online_monitor._plots.keys())[0].scene().sigMouseClicked, slot = self.onMouseClicked_online_monitor)

        def onMouseClicked_online_monitor(evt):

            if evt[0].button() == 1:  # ignore left click
                return
            else:
                if self.move_motor_action == None:
                    self.motor_pos_marker = pg.InfiniteLine(
                        angle=90,
                        movable=True,
                        pen=pg.mkPen("g", width=1, style=QtCore.Qt.SolidLine),
                    )
                    self.motor_pos_marker.sigPositionChangeFinished.connect(
                        self.move_motor_to_finishing_line
                    )
                    self.move_motor_action = MoveMotorTool(
                        self,
                        door_device=self.widget_online_monitor.manager.door,
                        motor_marker_line_obj=self.motor_pos_marker,
                    )
                    self.move_motor_action.attachToPlotItem(plot)
                    self.widget_online_monitor.manager.bind_obj = self.motor_pos_marker
                    # device_name = Device(self.settings_object['spockLogin']['doorName']).getParentObj().getTangoDB().get_device_alias(plot.x_axis["name"])
                    self.widget_online_monitor.manager.setModel(
                        # Device(plot.x_axis["name"])._full_name + "/Position",
                        f"{self.settings_object['motor_alias_address_map'][plot.x_axis['name']]}/Position",
                        key="motor",
                    )
                    plot.addItem(self.motor_pos_marker)
                    self.gaussian_fit_menu = GaussianFitTool(self)
                    self.gaussian_fit_menu.attachToPlotItem(plot)
                    self.gaussian_fit_menu.add_actions(plot, curves)
                    self.gaussian_sim_menu = GaussianSimTool(self)
                    self.gaussian_sim_menu.attachToPlotItem(plot)
                    self.gaussian_sim_menu.add_actions(plot, curves)
                # self.test_evt = evt
                pos_scene = evt[0].pos()
                pos_view = plot.vb.mapSceneToView(pos_scene)
                mot_name = plot.x_axis["name"]
                self.move_motor_action.setText(
                    f"move {mot_name} to {round(pos_view.x(),3)}?"
                )
                self.move_motor_action.motor_pos = round(pos_view.x(), 3)
                self.move_motor_action.motor_name = mot_name

                self.statusbar.showMessage(f"click at pos: {pos_view}")

        for plot in plots_motor_as_x_axis:
            # self.widget_online_monitor.setModel('motor/motctrl01/1/Position',key='motor')
            curves = list(self.widget_online_monitor._plots[plot].values())
            # now make a new plot for holding fit (eg gaussian or Lorenz) result
            nb_points = curves[-1].curve_data.maxSize()
            curve_item = plot.plot(name="fit")
            curve_item.curve_data = ArrayBuffer(np.full(nb_points, np.nan))
            curves.append(curve_item)
            self.signal_proxy = pg.SignalProxy(
                plot.scene().sigMouseClicked, slot=onMouseClicked_online_monitor
            )

    @Slot(object)
    def move_motor_to_finishing_line(self, infinitline_obj):
        self.widget_online_monitor.manager.door.runMacro(
            f'<macro name="mv"><paramrepeat name="motor_pos_list"><repeat nr="1">\
                                <param name="motor" value="{self.move_motor_action.motor_name}"/><param name="pos" value="{infinitline_obj.value()}"/>\
                                </repeat></paramrepeat></macro>'
        )

    def setCustomMacroEditorPaths(self, customMacroEditorPaths):
        MacroExecutionWindow.setCustomMacroEditorPaths(self, customMacroEditorPaths)
        ParamEditorManager().parsePaths(customMacroEditorPaths)
        ParamEditorManager().browsePaths()

    def updateParameter(self):
        self.taurusCommandButton.setParameters([self.lineEdit_mot1.text()])

    def onDoorChanged(self, doorName):
        MacroExecutionWindow.onDoorChanged(self, doorName)
        if self._qDoor:
            self._qDoor.macroStatusUpdated.disconnect(
                self.widget_sequencer.onMacroStatusUpdated
            )
        if doorName == "":
            return
        self._qDoor = Device(doorName)
        self._qDoor.macroStatusUpdated.connect(
            self.widget_sequencer.onMacroStatusUpdated
        )
        self.widget_sequencer.onDoorChanged(doorName)
        self.widget_online_monitor.setModel(doorName)
        self.widget_motor_widget.update_motor_viewer()
        self.widget_spock.setModel(doorName)

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
        if "select" in text:
            self.field.measure_tool.hide()
            self.field.set_mode("select")
            self.update_geo()
            if hasattr(self, "move_box"):
                self.move_box.show()
        elif "fiducial" in text:
            self.field.measure_tool.hide()
            self.field.set_mode("fiducial_marker")
            self.update_fiducial()
            if hasattr(self, "move_box"):
                self.move_box.hide()
        elif "dft" in text:
            self.field.measure_tool.hide()
            self.field.set_mode("dft")
            if hasattr(self, "move_box"):
                self.move_box.hide()
        elif "particle" in text:
            self.field.set_mode("particle")
            self.field.measure_tool.show()
            if hasattr(self, "move_box"):
                self.move_box.hide()
            self.set_pars_for_locating_particle_on_gui()

    @Slot(int)
    def switch_mode(self, tabIndex):
        tabText = self.tabWidget_2.tabText(tabIndex).lower()
        if "fiducial" in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode("fiducial_marker")
            self.update_fiducial()
            if hasattr(self, "move_box"):
                self.move_box.hide()
            self.radioButton_fiducial.click()
        elif "dft" in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode("dft")
            if hasattr(self, "move_box"):
                self.move_box.hide()
            self.radioButton_dft.click()
        elif "geometry" in tabText:
            self.field.measure_tool.hide()
            self.field.set_mode("select")
            self.update_geo()
            if hasattr(self, "move_box"):
                self.move_box.show()
            self.radioButton_select.click()
            # if 'particle' in tabText:#filled the save pars for particle tracking
            # self.set_pars_for_locating_particle_on_gui()
        elif "particle" in tabText:
            self.field.set_mode("particle")
            self.field.measure_tool.show()
            if hasattr(self, "move_box"):
                self.move_box.hide()
            self.set_pars_for_locating_particle_on_gui()
            self.radioButton_particle.click()

    @Slot(int)
    def switch_mode_viewer_tab(self, tabIndex):
        tabText = self.tabWidget_viewer.tabText(tabIndex).lower()
        if "camerastream" in tabText:
            self.camToolBar.show()
        else:
            self.camToolBar.hide()
        if "scan queue" in tabText:
            self.queueToolBar.show()
        else:
            self.queueToolBar.hide()

    def set_cursor_icon(self, cursor_type="cross"):
        """
        Change the cursor icon
        :param type:
        :return:
        """
        if cursor_type == "cross":
            cursor_custom = QtGui.QCursor(
                QtGui.QPixmap(
                    str(
                        ui_file_folder / "icons" / "Cursors" / "target_cursor_32x32.png"
                    )
                )
            )
        elif cursor_type == "pen":
            cursor_custom = QtGui.QCursor(
                QtGui.QPixmap(":/icon/cursor_pen.png"), hotX=26, hotY=23
            )
        elif cursor_type == "align":
            cursor_custom = QtGui.QCursor(
                QtGui.QPixmap(
                    str(
                        ui_file_folder
                        / "icons"
                        / "Cursors"
                        / "registration_cursor_32x32.png"
                    )
                ),
                hotX=26,
                hotY=23,
            )
        self.graphicsView_field.setCursor(cursor_custom)

    def connect_slots(self):
        """
        :return:
        """
        # synoptic viewer slots
        self.widget_synoptic.connect_slots_synoptic_viewer()
        # online monitor event
        self.widget_online_monitor.manager.newPrepare.connect(
            self.connect_mouseClick_event_for_online_monitor
        )
        self.widget_online_monitor.manager.newShortMessage.connect(
            self.statusbar.showMessage
        )
        # save image buffer sig
        self.saveimagedb_sig.connect(self.imageBuffer.writeImgBackup)
        # tabwidget signal
        self.tabWidget_2.tabBarClicked.connect(self.switch_mode)
        # viewer tabwidget signal
        self.tabWidget_viewer.tabBarClicked.connect(self.switch_mode_viewer_tab)
        # dft slots
        self.connect_slots_dft()
        # fiducial slots
        self.connect_slots_fiducial()
        # geo slots
        self.connect_slots_geo()
        # particle slots
        self.connect_slots_par()
        # cam stream slots
        self.connect_slots_cam()
        # beamline control slots
        self.connect_slots_beamline_control()
        # synoptic viewer control slots
        self.connect_slots_synoptic_viewer_control()
        # queue control slots
        self.connect_slots_queue_control()
        # widget events
        self.bt_removeMenu.setMenu(QtWidgets.QMenu(self.bt_removeMenu))
        self.bt_removeMenu.clicked.connect(self.bt_removeMenu.showMenu)
        self.bt_delete = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_removeMenu)
        action.setDefaultWidget(self.bt_delete)
        self.bt_removeMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "close_file_128x128.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.bt_delete.setIcon(icon1)
        self.bt_delete.setIconSize(QtCore.QSize(32, 32))
        self.bt_delete.setText("Delete Selected Images")
        self.bt_delete.clicked.connect(self.tbl_render_order.deleteSelection)
        self.bt_clear_tbl = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_removeMenu)
        action.setDefaultWidget(self.bt_clear_tbl)
        self.bt_removeMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "close_file_128x128.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
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
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "open_folder_128x128.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.bt_recall_imagedb.setIcon(icon1)
        self.bt_recall_imagedb.setIconSize(QtCore.QSize(32, 32))
        self.bt_recall_imagedb.setText("Load Image Database")
        self.bt_recall_imagedb.clicked.connect(self.loadImgBufferFromDisk)

        self.bt_export_imagedb = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_export_imagedb)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "save_as_128x128.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.bt_export_imagedb.setIcon(icon1)
        self.bt_export_imagedb.setIconSize(QtCore.QSize(32, 32))
        self.bt_export_imagedb.setText("Save and export images")
        self.bt_export_imagedb.clicked.connect(self.saveImageBuffer)

        self.bt_import_cam_image = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_import_cam_image)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "load_cam_img.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.bt_import_cam_image.setIcon(icon1)
        self.bt_import_cam_image.setText("Import camera image")
        self.bt_import_cam_image.setIconSize(QtCore.QSize(32, 32))
        self.bt_import_cam_image.clicked.connect(lambda: self.camara_widget.export_and_load_image())

        self.bt_import_image = QtWidgets.QPushButton(self)
        action = QtWidgets.QWidgetAction(self.bt_imageMenu)
        action.setDefaultWidget(self.bt_import_image)
        self.bt_imageMenu.menu().addAction(action)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(
                str(ui_file_folder / "icons" / "FileSystem" / "open_folder_128x128.png")
            ),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.bt_import_image.setIcon(icon1)
        self.bt_import_image.setText("Import local image ")
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
        if check_true(self.settings_object["Visuals"]["showBox"]):
            border_pen = fn.mkPen(
                color=eval(self.settings_object["Visuals"]["boxColor"]),
                width=int(self.settings_object["Visuals"]["boxLinewidth"]),
            )
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

    def import_image_from_disk(self, source_path_list=[], use_cam_geo = False):
        # // open up an image for importing data
        import os

        if len(source_path_list) < 1:
            dialog = QtWidgets.QFileDialog()
            path = QtCore.QDir.toNativeSeparators(
                self.settings_object["FileManager"]["currentimagedbDir"]
            )
            if os.path.exists(path):
                try:
                    os.chdir(path)
                except:
                    QtCore.qDebug("Error: invalid directory")
            source_path_list, _ = dialog.getOpenFileNames(
                self,
                "Open image file to be imported",
                os.getcwd(),
                "Image file (*.tif *.tiff *.png *.jpeg *.jpg *.bmp);;All Files (*)",
            )

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
                if use_cam_geo:
                    d['StageCoords_TL'] = self.camara_widget._cal_scan_topleft_coordinates()
                    width, height = self.camara_widget._get_img_dim_in_mm()
                    d["Outline"] = [50000-width/2, 50000+width/2, 50000-height/2,50000+height/2,-0.5,0.5]
                # // check for .align file
                if os.path.exists(os.path.splitext(filePath)[0] + ".Align"):
                    xml_path = os.path.splitext(filePath)[0] + ".Align"
                    ret = load_align_xml(xml_path)
                    if ret:
                        d.update(ret)

                self.imageBuffer.load_qi(d)

            self.settings_object["FileManager"]["currentimagedbDir"] = os.path.dirname(
                source_path_list[0]
            )
            self.tbl_render_order.resizeRowsToContents()
            self.tbl_render_order.setColumnWidth(0, 55)

    def loadImgBufferFromDisk(self):
        import os

        dialog = QtWidgets.QFileDialog()
        # path = QtCore.QDir.toNativeSeparators(self.settings_object.value("FileManager/currentimagedbDir"))
        path = QtCore.QDir.toNativeSeparators(
            self.settings_object["FileManager"]["currentimagedbDir"]
        )
        if os.path.exists(path):
            try:
                os.chdir(path)
            except:
                QtCore.qDebug("Error: invalid directory")
        source_path_list, _ = dialog.getOpenFileName(
            self,
            "Open .imagedb file to be imported",
            os.getcwd(),
            "imagedb files (*.imagedb);;All Files (*)",
        )

        # // select files based on tumbnails
        exclude_file_list = []

        if os.path.exists(source_path_list):
            dict_list = self.imageBuffer.load_imagedb(
                xml_path=source_path_list, exclude_file_list=exclude_file_list
            )
            # self.settings_object.setValue("FileManager/currentimagedbDir", os.path.dirname(source_path_list))
            self.settings_object["FileManager"]["currentimagedbDir"] = os.path.dirname(
                source_path_list
            )
        else:
            self.statusMessage_sig.emit("Invalid path for the .imagedb file")
            return None

        if dict_list:
            self.imageBuffer.attrList += dict_list
            self.imageBuffer.writeImgBackup()

    def saveImageBuffer(self):
        import os

        dialog = QtWidgets.QFileDialog()
        path = QtCore.QDir.toNativeSeparators(
            self.settings_object["FileManager"]["currentimagedbDir"]
        )
        if os.path.exists(path):
            os.chdir(path)
        source_path_list, _ = dialog.getSaveFileName(
            self,
            "Open .imagedb file to be imported",
            os.getcwd(),
            "imagedb files (*.imagedb);;All Files (*)",
        )
        if os.path.exists(os.path.dirname(source_path_list)):
            # self.imageBuffer.writeimagedb(xml_path=source_path_list)
            self.imageBuffer.writeImgBackup(path=source_path_list)
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", """<p>Invalid export path.<p>"""
            )

    def draw_scalebar(self):
        """
        Draw a scalebar
        :return:
        """
        # // remove current scalebar

        if hasattr(self, "sb"):
            if self.sb in self.field.scene().items():
                self.sb.hide()
                self.sb.update()
                self.field.removeItem(self.sb)
                self.field.scene().update()

        if self.settings_object["Visuals"]["showScalebar"]:
            zoom = 1.0

        # // save this settings to the settings file
        self.sb = ScaleBar(
            size=float(self.settings_object["ScaleSize"]),
            height=int(self.settings_object["ScaleHeight"]),
            position=self.settings_object["ScalePosition"],
            brush=self.settings_object["ScaleColor"],
            pen=self.settings_object["ScaleColor"],
            fs=int(self.settings_object["ScaleFontSize"]),
            suffix="um",
        )
        self.field.addItem(self.sb)
        self.sb.setParentItem(self.field)
        self.sb._scaleAnchor__parent = self.field
        # self.sb.anchor((1, 1), (1, 1), offset=(-30, -30))
        self.sb.updateBar()
        self.show_scale_bar(self.settings_object["Visuals"]["showScalebar"])
        # print(type(self.settings_object.value("Visuals/showScalebar")))
        # self.show_scale_bar(False)

    def show_scale_bar(self, enabled):
        if type(enabled) == str:
            if enabled in ["0", "False", "false"]:
                enabled = False
            else:
                enabled = True
        elif type(enabled) == bool:
            pass
        elif type(enabled) == int:
            if enabled == 0:
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
        self.tbl_render_order.horizontalHeader().ResizeMode = (
            QtWidgets.QHeaderView.ResizeToContents
        )

        # // remove colorbar
        if hasattr(self, "cb"):
            if self.cb in self.field.scene().items():
                self.field.scene().removeItem(self.cb)
                self.field.scene().update()

        # // remove scale
        if hasattr(self, "sb"):
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
            bounds = self.field.mapFromItemToView(
                items[0], items[0].boundingRect()
            ).boundingRect()
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

    def update_setting_file(self):
        self.camara_widget.update_img_settings()
        try:
            with open(self.setting_file_yaml, "w") as f:
                yaml.dump(self.settings_object, f, default_flow_style=False)
            self.statusUpdate('Success to save yaml config file locally!')
        except Exception as err:
            self.statusUpdate('Fail to save config due to:', str(err))

    def closeEvent(self, event):
        quit_msg = "About to Exit the program, are you sure? "
        reply = QMessageBox.question(
            self, "Message", quit_msg, QMessageBox.Yes, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            reply2 = QMessageBox.question(
                self,
                "Message",
                "Do you want to save the image setting to db before exit?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply2 == QMessageBox.Yes:
                self.saveimagedb_sig.emit()
                self.update_setting_file()
                event.accept()
            else:
                event.accept()
            self.camara_widget.thread_period_timer_forceRead.quit()
        elif reply == QMessageBox.No:
            event.ignore()
