# -*- coding: utf-8 -*-
import os


import math
import numpy as np
from pyqtgraph.Point import Point
from pyqtgraph.graphicsItems.ItemGroup import ItemGroup
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ViewBox.ViewBoxMenu import ViewBoxMenu
from pyqtgraph.graphicsItems.ROI import PolyLineROI
import weakref
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from ..util.geometry_transformation import rotatePoint


from . import field_area_tool

__all__ = ['ViewBox']


class ChildGroup(ItemGroup):

    def __init__(self, parent):
        ItemGroup.__init__(self, parent)

        # Used as callback to inform ViewBox when items are added/removed from
        # the group.
        # Note 1: We would prefer to override itemChange directly on the
        #         ViewBox, but this causes crashes on PySide.
        # Note 2: We might also like to use a signal rather than this callback
        #         mechanism, but this causes a different PySide crash.
        self.itemsChangedListeners = WeakList()

        # exempt from telling view when transform changes
        self._GraphicsObject__inform_view_on_change = False

    def itemChange(self, change, value):
        ret = ItemGroup.itemChange(self, change, value)
        if change in [
            self.GraphicsItemChange.ItemChildAddedChange,
            self.GraphicsItemChange.ItemChildRemovedChange,
        ]:
            try:
                itemsChangedListeners = self.itemsChangedListeners
            except AttributeError:
                # It's possible that the attribute was already collected when the itemChange happened
                # (if it was triggered during the gc of the object).
                pass
            else:
                for listener in itemsChangedListeners:
                    listener.itemsChanged()
        return ret


class measureTool(PolyLineROI):
    sigClicked = Signal(object)
    def __init__(self, positions, closed=False, pos=None, **args):
        super().__init__(positions, closed=closed, pos=pos, **args)

class FieldViewBox(pg.ViewBox):
    """
    **Bases:** :class:`GraphicsWidget <pyqtgraph.GraphicsWidget>`
    Box that allows internal scaling/panning of children by mouse drag. 
    This class is usually created automatically as part of a :class:`PlotItem <pyqtgraph.PlotItem>` or
     :class:`Canvas <pyqtgraph.canvas.Canvas>` or with :func:`GraphicsLayout.addViewBox()
      <pyqtgraph.GraphicsLayout.addViewBox>`.
    Features:
    
    * Scaling contents by mouse or auto-scale when contents change
    * View linking--multiple views display the same data ranges
    * Configurable by context menu
    * Item coordinate mapping methods
    
    """
    
    #sigYRangeChanged = Signal(object, object)
    #sigXRangeChanged = Signal(object, object)
    #sigRangeChangedManually = Signal(object)
    #sigRangeChanged = Signal(object,object, object)
    #sigActionPositionChanged = QtCore.Signal(object)
    #sigStateChanged = Signal(object)
    #sigTransformChanged = Signal(object)
    #sigResized = Signal(object)

    pathExtractionClicked = Signal(object, object)
    distanceMeasuredMoved_sig = Signal(float,float,float)
    distanceMeasuredClicked_sig = Signal(float,float,float)
    rectangleSelected_sig = Signal(float,float,float,float)
    fiducialMarkerAdded_sig = Signal(object)
    stagePositionTarget_sig = Signal(float,float)
    stageMoveUpdate_sig = Signal(float, float)
    ## mouse modes
    #PanMode = 3
    #RectMode = 1
    
    ## axes
    #XAxis = 0
    #YAxis = 1
    #XYAxes = 2

    ## for linking views together
    #NamedViews = weakref.WeakValueDictionary()   # name: ViewBox
    #AllViews = weakref.WeakKeyDictionary()       # ViewBox: None

    def __init__(self, parent=None, border=None, lockAspect=False, enableMouse=True,
      invertY=False, enableMenu=True, name=None, invertX=False, defaultPadding=0.02,
      defaultSpotValue=[10,10],defaultSpotInterspacingValue=[10,10],_parent=None):
        """
        ==============  =============================================================
        **Arguments:**
        *parent*        (QGraphicsWidget) Optional parent widget
        *border*        (QPen) Do draw a border around the view, give any
                        single argument accepted by :func:`mkPen <pyqtgraph.mkPen>`
        *lockAspect*    (False or float) The aspect ratio to lock the view
                        coorinates to. (or False to allow the ratio to change)
        *enableMouse*   (bool) Whether mouse can be used to scale/pan the view
        *invertY*       (bool) See :func:`invertY <pyqtgraph.ViewBox.invertY>`
        *invertX*       (bool) See :func:`invertX <pyqtgraph.ViewBox.invertX>`
        *enableMenu*    (bool) Whether to display a context menu when 
                        right-clicking on the ViewBox background.
        *name*          (str) Used to register this ViewBox so that it appears
                        in the "Link axis" dropdown inside other ViewBox
                        context menus. This allows the user to manually link
                        the axes of any other view to this one. 
        ==============  =============================================================
        """
        super().__init__(parent=parent, border=border, lockAspect=lockAspect, enableMouse=enableMouse, invertY=invertY, enableMenu=enableMenu, name=name, invertX=invertX, defaultPadding=defaultPadding)
        self._parent = _parent

        # self.rbScaleBox = QtWidgets.QGraphicsRectItem(0, 0, 1, 1)
        # self.rbScaleBox.setPen(pg.functions.mkPen((255,255,100), width=1))
        # self.rbScaleBox.setBrush(pg.functions.mkBrush(255,255,0,100))
        # self.rbScaleBox.setZValue(1e9)
        # self.rbScaleBox.hide()
        # self.addItem(self.rbScaleBox, ignoreBounds=True)

        ## show target rect for debugging
        # self.target = QtWidgets.QGraphicsRectItem(0, 0, 1, 1)
        # self.target.setPen(pg.functions.mkPen('r'))
        # self.target.setParentItem(self)
        # self.target.hide()

        # self.axHistory = [] # maintain a history of zoom locations
        # self.axHistoryPointer = -1 # pointer into the history. Allows forward/backward movement, not just "undo"

        # self.setZValue(-100)
        # self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))

        # self.setAspectLocked(lockAspect)

        # if enableMenu:
            # self.menu = ViewBoxMenu(self)
        # else:
            # self.menu = None

        # self.register(name)
        # if name is None:
            # self.updateViewLists()


        # // initialize the viewbox in navigate mode
        self.mode = "select"
        self.tracking = True
        self.activeScanTool = 0
        self.fiducial_active = 0
        self.defaultSpotValue = defaultSpotValue
        self.defaultSpotInterspacingValue = defaultSpotInterspacingValue

        # // make tool to measure distances
        self.measure_tool = PolyLineROI(positions = [],closed=False, movable=False)
        self.measure_tool.hide()
        self.measure_tool.translatable =False
        self.measure_tool.setZValue(1e4)
        self.measure_tool.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.addItem(self.measure_tool)
        self.measure_tool.sigClicked.connect(self.measure_handle_tool_clicked)
        # self.rbGridBox = QtWidgets.QGraphicsRectItem(0, 0, 1, 1)
        # self.rbGridBox.setPen(pg.functions.mkPen('#99FF33', width=1, dash=[2, 2]))
        # self.rbGridBox.setBrush(pg.functions.mkBrush(0,0,0,0))
        # self.rbGridBox.setZValue(1e4)
        # self.rbGridBox.hide()
        # self.addItem(self.rbGridBox, ignoreBounds=True)
        

        self.borderRect = QtWidgets.QGraphicsRectItem(self.rect())
        self.borderRect.setParentItem(self)
        self.borderRect.setZValue(1e3)
        self.borderRect.setPen(self.border)

        # self.setAspectLocked(lockAspect)

        # if enableMenu:
            # self.menu = ViewBoxMenu(self)
        # else:
            # self.menu = None

        # self.register(name)
        # if name is None:
            # self.updateViewLists()
        # try:
        #     self._parent._parent.dock_lasing_pattern_editor.SpotSizeChange.connect(self.update_spotSize_slot)
        #     self._parent._parent.dock_lasing_pattern_editor.SpotInterspacingChange.connect(self.update_spotInterspacing_slot)
        # except:
        #     QtCore.qDebug("Failed to connect to parent 464df5846")

    @Slot(object)
    def remove_item(self, item):
        self.removeItem(item)

    @Slot(str)
    def set_mode(self, mode):
        assert isinstance(mode, str)
        if len(mode) == 0:
            # // get the mode from the parent widget
            mode = self.mode
        self.mode = mode

    def raiseContextMenu(self, ev):
        menu = self.getMenu(ev)
        menu.popup(ev.screenPos().toPoint())

    def measure_handle_tool_clicked(self, evt):
        pos = self.mapSceneToView(evt.scenePos())
        #% check for handles
        if len(self.measure_tool.handles)==0:
            self.distanceMeasuredMoved_sig.emit(0, 0, 0)
            return None
        dX = math.fabs(self.measure_tool.handles[0]['pos'].x()-pos.x())
        dY = math.fabs(self.measure_tool.handles[0]['pos'].y()-pos.y())
        dis = math.sqrt(dX**2+dY**2)
        self.distanceMeasuredClicked_sig.emit(dis, dX, dY)

    def _scale_rotate_and_translate(self, pot):
        if self._parent.update_field_current==None:
            return False, pot
        coords = np.array(rotatePoint([0,0], (np.array(pot)-np.array(self._parent.update_field_current.pos())) * (1/np.array(self._parent.update_field_current._scale)), -self._parent.update_field_current.loc['Rotation']))
        coords = [int(each) for each in coords]
        return self._parent.update_field_current.isUnderMouse(), coords
    
    def mouseMoved_custom(self,evt):
        if self.mode=='particle':
            if self.sceneBoundingRect().contains(evt):
                mousePoint = self.mapSceneToView(evt)
                # // check for handles
                if len(self.measure_tool.handles)==0:
                    self._parent.statusbar.showMessage('Length= 0.0000 mm , dX/dY= (0.0000 mm,0.0000 mm)')
                    self.distanceMeasuredMoved_sig.emit(0, 0, 0)
                    return None
                in_side_scene_p1, coords_p1 = self._scale_rotate_and_translate([self.measure_tool.handles[0]['pos'].x(),self.measure_tool.handles[0]['pos'].y()])
                in_side_scene_p2, coords_p2 = self._scale_rotate_and_translate([mousePoint.x(),mousePoint.y()])
                in_side_scene = in_side_scene_p1 and in_side_scene_p2
                shift_percent = 0.1
                if in_side_scene:
                    try:
                        dX_obj, dY_obj = np.array(coords_p1) - np.array(coords_p2)
                        dis_obj = str(round(math.sqrt(dX_obj**2 + dY_obj**2),4)*(1-shift_percent))
                    except:

                        dX_obj, dY_obj = 'NA', 'NA'
                        dis_obj = 'NA'
                else:
                    dX_obj, dY_obj = 'NA', 'NA'
                    dis_obj = 'NA'
                if dis_obj!='NA':
                    distance_str_obj = '        Length= '+ f'{dis_obj}' + f'obj pix unit , dX/dY= ({dX_obj*(1-shift_percent)} obj pix unit,{dY_obj*(1-shift_percent)} obj pix unit)'
                else:
                    distance_str_obj = '        Length= '+ f'{dis_obj}' + f'obj pix unit , dX/dY= ({dX_obj} obj pix unit,{dY_obj} obj pix unit)'
                dX = math.fabs(self.measure_tool.handles[0]['pos'].x()-mousePoint.x())
                dY = math.fabs(self.measure_tool.handles[0]['pos'].y()-mousePoint.y())
                dis = math.sqrt(dX**2+dY**2)
                self._parent.statusbar.showMessage('Length= '+ '{:.4f}'.format(dis*(1-shift_percent)) + 'vp unit , dX/dY= ({:.4f} vp unit,{:.4f} vp unit)'.format(dX*(1-shift_percent),dY*(1-shift_percent))+ distance_str_obj)
                self.distanceMeasuredMoved_sig.emit(dis, dX, dY)
                #10% shift along vector
                dX_ = self.measure_tool.handles[0]['pos'].x()-mousePoint.x()
                dY_ = self.measure_tool.handles[0]['pos'].y()-mousePoint.y()
                x_, y_ = self.measure_tool.handles[0]['pos'].x()-dX_ * (1-shift_percent), self.measure_tool.handles[0]['pos'].y()-dY_*(1-shift_percent)
                self.measure_tool.setPoints([self.measure_tool.handles[0]['pos'], [x_, y_]])
                # self.measure_tool.setPoints([self.measure_tool.handles[0]['pos'], [mousePoint.x(), mousePoint.y()]])
        elif self.mode=='fiducial_marker':
            if self.sceneBoundingRect().contains(evt) and self.fiducial_active:
                mousePoint = self.mapSceneToView(evt)
                self.activeScanTool.setPoints([[x['pos'].x(),x['pos'].y()] for x in self.activeScanTool.handles[:-1]]+[[mousePoint.x(),mousePoint.y()]])
        elif self.mode=='select':
            x, y = self.mapSceneToView(evt).x(), self.mapSceneToView(evt).y()
            in_side_scene, coords = self._scale_rotate_and_translate([x,y])
            if not in_side_scene:
                self._parent.statusbar.showMessage('viewport coords:'+str(self.mapSceneToView(evt)))
            else:
                self._parent.statusbar.showMessage('viewport coords:'+str(self.mapSceneToView(evt))+'obj coords:'+str(coords) + 'pix ntensity:'+str(self._parent.img_array_gray[coords[1], coords[0]]))

    def mouseDragFinishedEvent(self, ev):
        print(ev, self.mode)

    def mouseDragEvent(self, ev):

        if self.mode == 'fiducial_marker':
            if ev.button() == QtCore.Qt.LeftButton:
                ev.ignore()
            else:
                pg.ViewBox.mouseDragEvent(self, ev)
            ev.accept()
        elif self.mode =='dft':
            if ev.button() == QtCore.Qt.LeftButton:
                ev.ignore()    
            else:
                pg.ViewBox.mouseDragEvent(self, ev)
            ev.accept() 
            pos = ev.pos()
            if ev.button() == QtCore.Qt.LeftButton:
                if ev.isFinish():
                    self.clear_selection()
                    self.rbScaleBox.hide()
                    self.ax = QtCore.QRectF(Point(ev.buttonDownPos(ev.button())), Point(pos))
                    # self.ax = self.childGroup.mapRectFromParent(self.ax)
                    self.Coords =  self.ax.getCoords()

                    x0, x1, y0, y1 = ev.buttonDownPos().x(), ev.pos().x(),  ev.buttonDownPos().y(),  ev.pos().y()
                    if x0 > x1:
                        x0, x1 = x1, x0
                    if y0 > y1:
                        y0, y1 = y1, y0
                    if x0 < 0:
                        x0 = 0

                    p1 = self.mapSceneToView(QtCore.QPointF(x0,y0))
                    p2 = self.mapSceneToView(QtCore.QPointF(x1,y1))
                    # // emit the signal to other widgets
                    self.rectangleSelected_sig.emit(p1.x(), p1.y(), p2.x(), p2.y())
                    self._parent.statusbar.showMessage("Extend of the rectangle: X(lef-right): [{:.4}:{:.4}],  Y(top-bottom): [{:.4}:{:.4}]".format(p1.x()/1000, p2.x()/1000, p1.y()/1000, p2.y()/1000))
                    #self.getdataInRect()

                    # self.changePointsColors()

    def clear_selection(self):
        """

        :return:
        """
        # // remove all borders
        self._parent._clear_borders()
        # // clear selection from the render table
        self._parent.tbl_render_order.clearSelection()
        # // clear the currently selected image
        self._parent.update_field_current = None

    @Slot(object)
    def mouseClickEvent(self, ev):
        """
        Slot for a mouse click event
        :param ev:
        :return:
        """
        if ev.button() == QtCore.Qt.LeftButton:
            if self.mode == "fiducial_marker":
                # // check the number of handles
                mousePoint = self.mapSceneToView(ev.pos())
                if not self.fiducial_active:
                    # // create the line segment
                    self.activeScanTool = field_area_tool.fiducial_marker_tool(positions=[[mousePoint.x(), mousePoint.y()], [mousePoint.x(), mousePoint.y()]], closed=False, movable=False)
                    # self.activeScanTool.mouseClickEvent.
                    self.activeScanTool.setZValue(1e4)
                    self.addItem(self.activeScanTool)
                    self.fiducial_active = 1
            elif self.mode == 'particle':
                # // place a handle
                # print('clicked')
                mousePoint = self.mapSceneToView(ev.pos())
                self.measure_tool.clearPoints()
                self.measure_tool.setPoints([[mousePoint.x(),mousePoint.y()], [mousePoint.x(),mousePoint.y()]])
                # self.measure_tool.setZValue(-1e4)
            elif self.mode in ['select', 'dft']:
                pos = ev.scenePos()
                view = ev.currentItem
                view_point = view.mapToView(pos)
                # // check outline of every image displayed and check if the viewposition lies within their outline
                clicked_list = []
                # // select another dataset
                for k in self._parent.field_img:
                    if k.isUnderMouse():
                        clicked_list.append(k)
                    '''
                    if hasattr(k,'loc'):
                        if isinstance(k.loc, dict):
                            if "Outline" in k.loc.keys():
                                im_pos = QtCore.QRectF(k.pos(),pg.Point(k.loc["Outline"][1], k.loc["Outline"][3]))
                        elif isinstance(k.loc, Dataset):
                            if "Outline" in k.loc.attrs.keys():
                                im_pos = QtCore.QRectF(k.pos(),pg.Point(k.loc.attrs["Outline"][1], k.loc.attrs["Outline"][3]))
                        else:
                            continue
                        if im_pos.contains(view_point):
                            # // if the clicked point belongs to an image, add it to the list
                            clicked_list.append(k)
                    '''
                #print(view_point)
                #print(clicked_list)
                if len(clicked_list)>0:
                    self.clear_selection()
                    self.select_single_image(clicked_list)

        elif ev.button() == QtCore.Qt.RightButton:
            if self.mode == 'particle':
                # // place a handle
                self.measure_tool.show()
                self.measure_tool.clearPoints()
            else:
                if self.menuEnabled():
                    ev.accept()
                    self.raiseContextMenu(ev)

        elif ev.button() == QtCore.Qt.MiddleButton:
            pos = ev.scenePos()
            view = ev.currentItem
            view_point = view.mapToView(pos)
            if view_point:
                self.stageMoveUpdate_sig.emit(view_point.x(), view_point.y())

    def select_single_image(self, checked_list):
        if len(checked_list)>0:
            self._parent._clear_borders()
            self._parent.update_field_current = checked_list[0]
            self._parent.hist.setImageItem(checked_list[0])
            self._parent._show_border()
            if self.mode in ['select', 'dft']:
                self._parent.update_geo()
                if self.mode == 'dft':
                    self._parent.move_box.hide()
                
    def create_pattern(self):
        import numpy as np
        trajectory_nodes = np.zeros((2,0,3))
        zheight = 0

        if self.mode == "fiducial_marker":
            # // generate a pattern of the current scanTool and close it
            print('add one fiducial marker')
            self.fiducialMarkerAdded_sig.emit(self.activeScanTool)
            self.activeScanTool = 0
            self.fiducial_active = 0
            # // this pattern is not added to the scan list
            return


        else:
            scans=[]
