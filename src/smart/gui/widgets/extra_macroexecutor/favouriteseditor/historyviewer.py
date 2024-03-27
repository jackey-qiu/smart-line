#!/usr/bin/env python

##############################################################################
##
# This file is part of Sardana
##
# http://www.sardana-controls.org/
##
# Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
# Sardana is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
##
# Sardana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
##
# You should have received a copy of the GNU Lesser General Public License
# along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################

"""
historyviewer.py:
"""
import copy
import os

from sardana import sardanacustomsettings
from taurus.external.qt import Qt, compat
from taurus.qt.qtgui.container import TaurusWidget
from taurus.qt.qtcore.configuration import BaseConfigurableClass
from .model import MacrosListModel


class HistoryMacrosViewer(TaurusWidget):
    __pyqtSignals__ = ("modelChanged(const QString &)",)

    def __init__(self, parent=None, designMode=False):
        TaurusWidget.__init__(self, parent, designMode)
        self.setObjectName(self.__class__.__name__)
        self.registerConfigProperty("toXmlString", "fromXmlString", "history")

        self._historyPath = str(Qt.QDir.homePath())

        self.registerConfigProperty(
            "historyPath", "setHistoryPath", "historyPath")
        self.exportAllAction = Qt.QAction(Qt.QIcon("actions:format-indent-more.svg"),
                                          "Export", self)
        self.exportAllAction.triggered.connect(self.exportAllMacros)
        self.exportAllAction.setToolTip(
            "Clicking this button will export all macros from history.")

        self.importAllAction = Qt.QAction(Qt.QIcon("actions:format-indent-less.svg"),
                                          "Import", self)
        self.importAllAction.triggered.connect(self.importAllMacros)
        self.importAllAction.setToolTip(
            "Clicking this button will import an history of macros.")
        self.initComponents()

    def initComponents(self):
        self.setLayout(Qt.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.list = HistoryMacrosList(self)
        self._model = MacrosListModel()
        max_history = getattr(sardanacustomsettings,
                              "MACROEXECUTOR_MAX_HISTORY",
                              None)
        self._model.setMaxLen(max_history)
        self.list.setModel(self._model)

# self.registerConfigDelegate(self.list)
        self.layout().addWidget(self.list)

        actionBar = self.createActionBar()
        self.layout().addLayout(actionBar)

    def createActionBar(self):
        layout = Qt.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        deleteSelectedButton = Qt.QToolButton()
        deleteSelectedButton.setDefaultAction(self.list.removeSelectedAction)
        layout.addWidget(deleteSelectedButton)
        exportAllButton = Qt.QToolButton()
        exportAllButton.setDefaultAction(self.exportAllAction)
        layout.addWidget(exportAllButton)
        importAllButton = Qt.QToolButton()
        importAllButton.setDefaultAction(self.importAllAction)
        layout.addWidget(importAllButton)
        spacerItem = Qt.QSpacerItem(
            0, 0, Qt.QSizePolicy.Fixed, Qt.QSizePolicy.Expanding)
        layout.addItem(spacerItem)
        return layout

    def listElementUp(self):
        indexPos = self.list.currentIndex()
        if indexPos.isValid() and indexPos.row() >= 1:
            self.list.setCurrentIndex(indexPos.sibling(
                indexPos.row() - 1, indexPos.column()))
        else:
            self.selectFirstElement()

    def listElementDown(self):
        indexPos = self.list.currentIndex()
        if indexPos.isValid() and indexPos.row() < self._model.rowCount() - 1:
            self.list.setCurrentIndex(indexPos.sibling(
                indexPos.row() + 1, indexPos.column()))
        elif indexPos.row() == self._model.rowCount() - 1:
            return
        else:
            self.selectFirstElement()

    def addMacro(self, macroNode):
        self.list.insertMacro(macroNode)

    def toXmlString(self, pretty=False):
        return self.list.toXmlString(pretty)

    def fromXmlString(self, xmlString):
        self.list.fromXmlString(xmlString)
        historyList = self.list.model().list
        macroServerObj = self.getModelObj()
        if macroServerObj is None:
            return

        for macroNode in historyList:
            macroServerObj.fillMacroNodeAdditionalInfos(macroNode)
    
    def exportAllMacros(self):
        historyPath = self.historyPath()
        if historyPath == "":
            historyPath = str(Qt.QDir.homePath())

        historyPath = os.path.join(historyPath, "History.xml")
        fileName, _ = compat.getSaveFileName(
            self,
            "Choose a history file name...",
            historyPath,
            "*.xml")
        if fileName == "":
            return
        try:
            with open(fileName,'w') as file:
                file.write(self.toXmlString(pretty=True))
            self.setHistoryPath(str.join("/", fileName.rsplit("/")[:-1]))
        except Exception as e:
            Qt.QMessageBox.warning(
                self,
                "Error while saving macro history",
                "There was a problem while writing to the file:"
                .format(fileName))
            print(e)

    def importAllMacros(self):
        if self.list.model().hasRows():
            if Qt.QMessageBox.question(
                    self,
                    "Import history",
                    "Do you want to save existing history?",
                    Qt.QMessageBox.Yes,
                    Qt.QMessageBox.No) == Qt.QMessageBox.Yes:
                self.exportAllMacros()
            
        historyPath = self.historyPath()
        fileName, _ = compat.getOpenFileName(
            self,
            "Choose a history to import...",
            historyPath,
            "*")
        try:
            with open(fileName,'r') as file:
                newHistory = file.read()
            self.list.model().clearData()
            self.fromXmlString(newHistory)
            self.setHistoryPath(str.join("/", fileName.rsplit("/")[:-1]))

        except Exception as e:
            Qt.QMessageBox.warning(
                self,
                "Error while loading macro history",
                "There was a problem while reading the file:"
                .format(fileName))
            print(e)
    
    def historyPath(self):
        return self._historyPath

    def setHistoryPath(self, historyPath):
        self._historyPath = historyPath

    def selectFirstElement(self):
        self.list.removeSelectedAction.setEnabled(True)
        self.list.setCurrentIndex(self._model.index(0))

    @classmethod
    def getQtDesignerPluginInfo(cls):
        return None


class HistoryMacrosList(Qt.QListView, BaseConfigurableClass):

    historySelected = Qt.pyqtSignal(compat.PY_OBJECT)

    def __init__(self, parent=None):
        Qt.QListView.__init__(self, parent)
        self.setSelectionMode(Qt.QListView.ExtendedSelection)

        self.removeSelectedAction = Qt.QAction(Qt.QIcon("places:user-trash.svg"),
                                          "Remove", self)
        self.removeSelectedAction.triggered.connect(self.removeSelectedMacros)
        self.removeSelectedAction.setToolTip(
            "Clicking this button will remove selected macros from history.")
        self.removeSelectedAction.setEnabled(False)

    def currentChanged(self, current, previous):
        macro = copy.deepcopy(self.currentIndex().internalPointer())
        self.historySelected.emit(macro)
        Qt.QListView.currentChanged(self, current, previous)
        self.checkRemoveButtonState()

    def mousePressEvent(self, e):
        clickedIndex = self.indexAt(e.pos())
        if clickedIndex.isValid():
            macro = copy.deepcopy(self.currentIndex().internalPointer())
            self.historySelected.emit(macro)
        Qt.QListView.mousePressEvent(self, e)
        self.checkRemoveButtonState()

    def checkRemoveButtonState(self):
        if len(self.selectedIndexes()) > 0:
            self.removeSelectedAction.setEnabled(True)
        else:
            self.removeSelectedAction.setEnabled(False)

    def insertMacro(self, macroNode):
        idx = self.model().insertRow(macroNode)
        self.setCurrentIndex(idx)
        self.removeSelectedAction.setEnabled(True)

    def removeSelectedMacros(self):
        slist = sorted(self.selectedIndexes(),
                       key=lambda index: index.row(), reverse=True)
        for index in slist:
            self.model().removeRow(index.row())

        self.removeSelectedAction.setEnabled(False)

    def toXmlString(self, pretty=False):
        return self.model().toXmlString(pretty=pretty)

    def fromXmlString(self, xmlString):
        self.model().fromXmlString(xmlString)


def test():
    import sys
    import taurus
    import time
    from taurus.core.util.argparse import get_taurus_parser
    from taurus.qt.qtgui.application import TaurusApplication

    parser = get_taurus_parser()
    app = TaurusApplication(sys.argv, cmd_line_parser=parser)

    historyViewer = HistoryMacrosViewer()

    args = app.get_command_line_args()
    historyViewer.setModel(args[0])
    time.sleep(1)
    macroNode = historyViewer.getModelObj().getMacroNodeObj(str(args[1]))
    historyViewer.addMacro(macroNode)
    historyViewer.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    test()
