from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal
import pyqtgraph.functions as fn
import cv2, tifffile, qimage2ndarray
import pyqtgraph as pg
from ...util.geometry_transformation import rotatePoint
from ...resource.data_loaders.file_loader import load_im_xml
from ...resource.data_writer.export_module import write_im_xml

class ImageBufferInfo(QtCore.QObject):
    statusMessage_sig = Signal(str)
    progressUpdate_sig = Signal(float)
    logMessage_sig = Signal(dict)

    def __init__(self, parent, img_backup_path):
        super(ImageBufferInfo, self).__init__()
        self.attrList = []
        self._parent = parent
        self.img_backup_path = img_backup_path

    def load_imagedb(self, xml_path, exclude_file_list=[]):
        tempAttrList = load_im_xml(xml_path, exclude_file=exclude_file_list,
                                   progressbar=None)
        self.logMessage_sig.emit({"type": "info",
                                  "message": "imagedb data files loaded into project.",
                                  "class": "ImportDialog"})
        for d in tempAttrList[::-1]:
            self.load_qi(d)
        self._parent.tbl_render_order.resizeRowsToContents()
        self._parent.tbl_render_order.setColumnWidth(0, 55)
        return tempAttrList

    def load_qi(self, d, showGUI=False):
        """
        This loads an image based on a dictionary of keys
        :param showGUI:
        :param d: the dictionary. It must have a Path, Center, Size, and Name keys as minimum
        :return:
        """
        import os
        image = None
        if os.path.exists(d['Path']):
            if os.path.splitext(d['Path'])[-1].lower() == ".bmp":
                qi = QtGui.QPixmap(d['Path'])
                image = cv2.imread(d['Path'])
            elif os.path.splitext(d['Path'])[-1].lower() == ".jpg" or os.path.splitext(d['Path'])[
                -1].lower() == ".jpeg":
                qi = QtGui.QPixmap(d['Path'])
                image = cv2.imread(d['Path'])
            elif os.path.splitext(d['Path'])[-1].lower() == ".png":
                qi = QtGui.QPixmap(d['Path'])
                image = cv2.imread(d['Path'])
                if not qi:
                    # // try to copy the png to bmp and import it. This is a workaround as the PNG is actually a BMP
                    import shutil
                    new_file = os.path.join(os.path.splitext(d['Path'])[0] + ".bmp")
                    shutil.copy(d['Path'], new_file)
                    qi = QtGui.QPixmap()
                    ret = qi.load(new_file, format="BMP")
            elif os.path.splitext(d['Path'])[-1].lower() == ".tif" or os.path.splitext(d['Path'])[
                -1].lower() == ".tiff":
                image = tifffile.imread(d['Path'])
                # image = cv2.convertScaleAbs(image, alpha=0.001, beta=50)
                qimage= qimage2ndarray.array2qimage(image)
                qi = QtGui.QPixmap(qimage)
            else:
                QtCore.qDebug("Image format not supported")
                qi = None
        else:
            QtCore.qDebug("Path not found")
            qi = None

        if qi:
            # // load the center and size keys into the dict using the aspect reatio tool (if needed)
            if ("Center" not in d.keys()):
                if ("Outline" not in d.keys()):
                    # // set the center to the current center in the workspace
                    d["Center"] = [0] * 3
                    d["Center"][0] = self._parent.X_controller_travel//2
                    d["Center"][1] = self._parent.Y_controller_travel//2
                    d["Center"][2] = 0
                else:
                    # // calculate the center based on the outline
                    d["Center"] = [0] * 3
                    d["Center"][0] = abs(d["Outline"][1] - d["Outline"][0]) / 2.0 + d["Outline"][0]
                    d["Center"][1] = abs(d["Outline"][3] - d["Outline"][2]) / 2.0 + d["Outline"][2]
                    d["Center"][2] = abs(d["Outline"][5] - d["Outline"][4]) / 2.0 + d["Outline"][4]

            if ("Size" not in d.keys()):
                if ("Outline" not in d.keys()):
                    d["Size"] = (qi.size().width(), qi.size().height(), 1)
                else:
                    d["Size"] = (abs(d["Outline"][1] - d["Outline"][0]),\
                                 abs(d["Outline"][3] - d["Outline"][2]),\
                                 abs(d["Outline"][5] - d["Outline"][4]))

            if "Outline" not in d.keys():
                if "Center" in d.keys() and "Size" in d.keys():
                    d["Outline"] = [0] * 6
                    d["Outline"][0] = d["Center"][0] - d["Size"][0] / 2
                    d["Outline"][1] = d["Center"][0] + d["Size"][0] / 2
                    d["Outline"][2] = d["Center"][1] - d["Size"][1] / 2
                    d["Outline"][3] = d["Center"][1] + d["Size"][1] / 2
                    if len(d["Size"]) > 2 and len(d["Center"]) > 2:
                        d["Outline"][4] = d["Center"][2] - d["Size"][2] / 2
                        d["Outline"][5] = d["Center"][2] + d["Size"][2] / 2

            if 'StageCoords_TL' not in d.keys():#top left stage coordinates
                d['StageCoords_TL'] = (0,0,0)
            else:
                d['StageCoords_TL'] = eval(d['StageCoords_TL'])
            aspect_ratio = []
            aspect_ratio.append(d["Outline"][1] - d["Outline"][0])
            aspect_ratio.append(d["Outline"][3] - d["Outline"][2])
            aspect_ratio.append(d["Outline"][5] - d["Outline"][4])
            try:
                aspect_ratio[0] /= qi.size().width()
                aspect_ratio[1] /= qi.size().height()
            except:
                aspect_ratio[0] /= d['Size'][0]
                aspect_ratio[1] /= d['Size'][1]

            aspect_ratio[2] /= 1
            d.update({'AspectRatio': aspect_ratio})

            if "Opacity" in d.keys():
                opa = float(d["Opacity"])
                if opa > 100:
                    opa = 100
                elif opa < 0:
                    opa = 0
            else:
                opa = 100

            # // calculate the outline based on the center and size
            img = ImageBufferObject(image = image, width=d['Size'][0], height=d['Size'][1],
                                    pos=(d["Outline"][0], d["Outline"][2]), pixmap=qi, opacity=opa,
                                    attrs=d)
            self._parent.field.addItem(img)
            # if os.path.splitext(d['Path'])[-1].lower() == ".tif" or os.path.splitext(d['Path'])[
                # -1].lower() == ".tiff":
                # img.setImage(image)
            self._parent.hist.setImageItem(img)
            # // reset the scale for rotation
            s = list(img._scale)
            if s[0] == 0:
                s[0] = 1
            if s[1] == 0:
                s[1] = 1

            # img.scale(1 / s[0], 1 / s[1])
            tr = QtGui.QTransform()
            tr.scale(1 / s[0], 1 / s[1])
            img.setTransform(tr)

            if not "Rotation" in d.keys():
                d["Rotation"] = 0
            # img.rotate(d['Rotation'])
            img.setRotation(d["Rotation"])
            # img.scale(s[0], s[1])
            tr = QtGui.QTransform()
            tr.scale(s[0], s[1])
            img.setTransform(tr)

            # // apply coordinate transformation for rotation in the XY plane
            
            v = rotatePoint(centerPoint=d['Center'], point=[d["Outline"][0], d["Outline"][2]],
                            angle=d['Rotation'])
            img.setPos(pg.Point(v[0], v[1]))
            self._parent.field.autoRange(padding=0.02)
            self._parent.field_img.insert(0, img)
            # // set current image in the field view
            self._parent.update_field_current = img
            # // attach the label to the image
            img.loc = d

            # // add to the renderlist
            rowPosition = 0
            self._parent.tbl_render_order.insertRow(rowPosition)

            cb = QtWidgets.QTableWidgetItem()
            cb.setBackground(QtGui.QColor("#368AD4"))
            cb.setCheckState(QtCore.Qt.CheckState.Checked)
            self._parent.tbl_render_order.setItem(rowPosition, 0, cb)
            self._parent.field_list.insert(0, img.loc)
            self._parent.tbl_render_order.itemClicked.connect(lambda item: self._parent.on_table_order_clicked(item))

            sb = QtWidgets.QSpinBox()
            sb.setRange(0, 100)
            sb.setValue(int(opa))
            sb.editingFinished.connect(self.update_opacity)
            self._parent.tbl_render_order.setCellWidget(rowPosition, 1, sb)
            sb.loc = img.loc

            p = QtWidgets.QTableWidgetItem(d["Name"])
            p.loc = d

            self._parent.tbl_render_order.setItem(rowPosition, 2, p)

            if showGUI:
                pass
                # // add the image to the imagebuffer
            # self._parent.update_geo()
            # self.addImgBackup(self._parent.attrs_geo)
            img.loc = d
            self.addImgBackup(d)

    def update_opacity(self):
        sb = self.sender()
        if sb.loc in self._parent.field_list:
            ind = self._parent.field_list.index(sb.loc)
            self._parent.field_img[ind].setOpacity(sb.value() / 100.0)
            sb.loc["Opacity"] = sb.value()
            self.writeImgBackup()

    def addImgBackup(self, dict_image):
        # // function to add a dataset to current backup file
        self.attrList.append(dict_image)
        self.writeImgBackup()

    def writeImgBackup(self, path = None):
        # // flushes the current image buffer to the backup file
        if path == None:
            write_im_xml(self.img_backup_path, self.attrList, distributed=True)
        else:
            write_im_xml(path, self.attrList, distributed=True)

    def updateImgBackup(self, newDict):
        """
        Function to update a ImageBufferObject in the backup file
        :return:
        """
        # //  search every image to remove from active list
        for i, n in enumerate(self.attrList):
            # // search for name match
            if n["Path"] == newDict["Path"]:
                # // found match
                self.attrList[i] = newDict

        # // update the backup file by refreshing
        self.writeImgBackup()

    def removeImgBackup(self, d):
        """
        Function to remove a file from the current backup file
        :param d:
        :return:
        """
        # //  search every image to remove from active list
        for i, n in enumerate(self.attrList):
            # // search for name match
            if n["Path"] == d["Path"]:
                # // found match
                del self.attrList[i]

        # // remove from the backup file by refreshing
        self.writeImgBackup()

    def writeimagedb(self, xml_path):
        # // save the image buffer to a specified location
        #settings = QtCore.QSettings(self._parent._parent.__appStore__, QtCore.QSettings.IniFormat)
        settings = self._parent.settings_object
        if settings['Hardware"]["CPUthreading'] == '1':
            def onDataReady(obj_result):
                self._parent.thread_func.quit()

            def func(self, progressSignal):
                write_im_xml = write_im_xml(xml_path, self.attrList, distributed=False)
                # // copy all images to the export folder
                import shutil
                l = len(self.attrList)
                for i, d in enumerate(self.attrList):
                    import os
                    if os.path.exists(d['Path']):
                        shutil.copy2(d['Path'], os.path.dirname(xml_path))
                    else:
                        QtCore.qDebug("Path not found")
                    progressSignal.emit(((i + 1) / l) * 100)
                    # self._parent._parent.progressbar.setValue(((i + 1) / l) * 100)
                return self

            self._parent.thread_func = QtCore.QThread(self._parent)

            class Worker(QtCore.QObject):
                finished = Signal()
                dataReady = Signal(object)
                progressSignal = Signal(float)

                def __init__(self, parent, func, *args, **kwargs):
                    # QtCore.QObject.__init__(self, *args, **kwargs)
                    super(Worker, self).__init__()
                    self.func = func
                    self.args = args
                    self.kwargs = kwargs

                @QtCore.Slot(str, object)
                def run_func(self):
                    r = func(*self.args, progressSignal=self.progressSignal, **self.kwargs)
                    self.dataReady.emit(r)
                    self.finished.emit()

            self.obj = Worker(self, func, self)
            self.obj.moveToThread(self._parent.thread_func)
            self.obj.progressSignal.connect(self._parent._parent.progressUpdate)
            self.obj.dataReady.connect(onDataReady)

            self._parent.thread_func.started.connect(self.obj.run_func)
            self._parent.thread_func.start()
        else:
            pass

    def recallImgBackup(self):
        import os
        # // recall the previous imagedb if the path is valid
        if self.img_backup_path:
            if os.path.exists(self.img_backup_path):
                dict_list = self.load_imagedb(xml_path=self.img_backup_path)
                # self.attrList = dict_list


# class ImageBufferObject(pg.GraphicsObject):
class ImageBufferObject(pg.ImageItem):
    """
    This class is meant for displaying a picture in the field view, without listing it in the field render list
    """

    def __init__(self, image = None, width=None, height=None, pos=(0, 0), rot=0, Visible=True, pixmap=None, attrs={}, opacity=100):
        pg.ImageItem.__init__(self, image)
        self.width = width
        self.height = height
        self.axisOrder = 'row-major'
        self._scale = [1, 1]
        self.attrs = attrs
        if not image.any() and (pixmap is not None):
            self.setPixmap(pixmap)
            self.pixmap = pixmap
        else:
            self.pixmap = pixmap

        if width is not None and height is None:
            # s = float(width) / self.pixmap.width()
            s = float(width) / self.image.shape[1]
            self.scale(s, s)
            self._scale = (s, s)
        elif height is not None and width is None:
            # s = float(height) / self.pixmap.height()
            s = float(height) / self.image.shape[0]
            self.scale(s, s)
            self._scale = (s, s)
        elif width is not None and height is not None and (self.image.shape[0] > 0) and (self.image.shape[1] > 0):
            # self._scale = (float(width) / self.pixmap.width(), float(height) / self.pixmap.height())
            self._scale = (float(width) / self.image.shape[1], float(height) / self.image.shape[0])
            # self.scale(self._scale[0], self._scale[1])
            tr = QtGui.QTransform()
            tr.scale(self._scale[0], self._scale[1])
            self.setTransform(tr)
        else:
            self._scale = (width, height)
            self.scale(self._scale[0], self._scale[1])
            

        self.setOpacity(opacity / 100)
        self.border = None

    def update_dim(self, new_dims):
        self.width, self.height = new_dims

    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def paint_(self, p, *args):
        p.setRenderHint(p.Antialiasing)
        p.drawPixmap(0, 0, self.pixmap)
        if self.border is not None:
            p.setPen(self.border)
            p.drawRect(self.boundingRect())

    def boundingRect(self):
        return QtCore.QRectF(self.pixmap.rect())

    def setBorder(self, b):
        self.border = fn.mkPen(b)
        self.update()

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