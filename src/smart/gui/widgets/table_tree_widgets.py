from PyQt5 import QtGui, QtCore, QtWidgets

class CopyTable(QtWidgets.QTableWidget):
    """
    Class contains the methods that creates a table from which can be copied
    Contains also other utilities associated with interactive tables.
    """

    def __init__(self, parent=None):
        super(CopyTable, self).__init__(parent)
        self._parent = parent
        self.setAlternatingRowColors(True)

    def paste(self):
        s = self._parent.clip.text()
        rows = s.split("\n")
        selected = self.selectedRanges()
        rc = 1
        if selected:
            for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                if (len(rows) > rc):
                    v = rows[rc].split("\t")
                    cc = 1
                    for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        if (len(v) > cc):
                            self.item(r,c).setText(v[cc])
                        cc+=1
                rc+=1
        else:
            for r in range(0, self.rowCount()):
                if (len(rows) > rc):
                    v = rows[rc].split("\t")
                    cc = 1
                    for c in range(0, self.columnCount()):
                        if (len(v) > cc):
                            self.item(r,c).setText(v[cc])
                        cc+=1
                rc+=1

    def copy(self):
        selected = self.selectedRanges()
        if selected:
            if self.horizontalHeaderItem(0):
                s = '\t' + "\t".join([str(self.horizontalHeaderItem(i).text()) for i in
                                      range(selected[0].leftColumn(), selected[0].rightColumn() + 1)])
            else:
                s = '\t' + "\t".join([str(i) for i in range(selected[0].leftColumn(), selected[0].rightColumn() + 1)])
            s = s + '\n'
            for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                if self.verticalHeaderItem(r):
                    s += self.verticalHeaderItem(r).text() + '\t'
                else:
                    s += str(r) + '\t'
                for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                    try:
                        item_text = str(self.item(r, c).text())
                        if item_text.endswith("\n"):
                            item_text = item_text[:-2]
                        s += item_text + "\t"
                    except AttributeError:
                        s += "\t"
                s = s[:-1] + "\n"  # eliminate last '\t'
            self._parent.clip.setText(s)
        else:
            if self.horizontalHeaderItem(0):
                s = '\t' + "\t".join([str(self.horizontalHeaderItem(i).text()) for i in range(0, self.columnCount())])
            else:
                s = '\t' + "\t".join([str(i) for i in range(0, self.columnCount())])
            s = s + '\n'

            for r in range(0, self.rowCount()):
                if self.verticalHeaderItem(r):
                    s += self.verticalHeaderItem(r).text() + '\t'
                else:
                    s += str(r) + '\t'
                for c in range(0, self.columnCount()):
                    try:
                        item_text = str(self.item(r, c).text())
                        if item_text.endswith("\n"):
                            item_text = item_text[:-2]
                        s += item_text + "\t"
                    except AttributeError:
                        s += "\t"
                s = s[:-1] + "\n"  # eliminate last '\t'
            self._parent.clip.setText(s)

class TableWidgetDragRows(QtWidgets.QTableWidget):
    def __init__(self, parent, *args, **kwargs):
        super(TableWidgetDragRows, self).__init__(parent)
        self.imageBuffer = None
        self._parent = parent
        self.copy_image_to_project_idx = 0
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.horizontalHeader().setStretchLastSection(True)
        self.installEventFilter(self)

    def setMultiRowSel(self, selection):
        self.setSelectionMode(self.MultiSelection)
        for i in selection:
            self.selectRow(i)
        self.setSelectionMode(self.ExtendedSelection)
        # self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = []
            for row_index in rows:
                row_data = []
                for column_index in range(self.columnCount()):
                    if column_index == 1:
                        row_data += [self.cellWidget(row_index, 1)]
                        # self.removeCellWidget(row_index,1)
                    else:
                        row_data += [QtWidgets.QTableWidgetItem(self.item(row_index, column_index))]
                rows_to_move += [row_data]

            for i, row in enumerate(rows_to_move):
                row[2].loc = self.item(rows[i], 2).loc

            # //increase row count
            # self.setRowCount(self.rowCount()+1)

            # // reorganize field list by inserting the new rows
            for row_index in reversed(rows):
                self._parent.field_list.insert(drop_row, self._parent.field_list.pop(row_index))
                self._parent.field_img.insert(drop_row, self._parent.field_img.pop(row_index))

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    if column_index == 1:
                        self.setCellWidget(row_index, 1, column_data)
                    else:
                        self.setItem(row_index, column_index, column_data)

                self.setRowHeight(row_index, 20)
                self.setRowHeight(drop_row, 20)

            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                self.item(drop_row + row_index, 2).setSelected(True)

            for row_index in reversed(rows):
                if row_index < drop_row:
                    self.removeRow(row_index)
                else:
                    self.removeRow(row_index + len(rows_to_move))

            self.field_order_update()
            event.accept()

        super().dropEvent(event)

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (
                    int(self.model().flags(index)) & QtCore.Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()

    def field_order_update(self):
        # // reset the Z-order based on the field_img order
        p = len(self._parent.field_img)
        for i, k in enumerate(self._parent.field_img):
            k.setZValue(p - i)

    def eventFilter(self, widget, event):
        if (event.type() == QtCore.QEvent.KeyPress and widget is self):
            if event.key() == QtCore.Qt.Key_Delete:
                self.deleteSelection()
            elif event.key() == QtCore.Qt.Key_Home:
                self.zorder_up_full()
                return True
            elif event.key() == QtCore.Qt.Key_End:
                self.zorder_down_full()
                return True
            elif event.key() == QtCore.Qt.Key_Up:
                self.zorder_up()
                return True
            elif event.key() == QtCore.Qt.Key_Down:
                self.zorder_down()
                return True

        return QtWidgets.QWidget.eventFilter(self, widget, event)

    def zorder_up_full(self):
        # // change the render order
        row = self.currentRow()
        if row > 0:
            field_i = self._parent.field_list.index(self.item(row, 2).loc)
            # // move item completly upwards in the table
            column = 1
            self.insertRow(0)
            self.setRowHeight(0, 20)
            for i in range(self.columnCount()):
                if i == 1:
                    # // moving the progressbar
                    pb = self.cellWidget(row + 1, 1)
                    self.setCellWidget(0, 1, pb)
                else:
                    self.setItem(0, i, self.takeItem(row + 1, i))
                    self.setCurrentCell(0, column)
            self.removeRow(row + 1)
            # // mirror change in field_img and field_list
            temp = self._parent.field_img[field_i]
            del self._parent.field_img[field_i]
            self._parent.field_img.insert(0, temp)
            temp = self._parent.field_list[field_i]
            del self._parent.field_list[field_i]
            self._parent.field_list.insert(0, temp)
        self.field_order_update()

    def zorder_up(self):
        # // change the render order
        row = self.currentRow()
        if row > 0:
            field_i = self._parent.field_list.index(self.item(row, 2).loc)
            # // move item upwards in the table
            column = 1
            self.insertRow(row - 1)
            for i in range(self.columnCount()):
                if i == 1:
                    # // moving the progressbar
                    pb = self.cellWidget(row + 1, 1)
                    self.setCellWidget(row - 1, 1, pb)
                else:
                    self.setItem(row - 1, i, self.takeItem(row + 1, i))
                    self.setCurrentCell(row - 1, column)
            self.setRowHeight(row, 20)
            self.setRowHeight(row - 1, 20)
            self.removeRow(row + 1)
            # // mirror change in field_img and field_list
            self._parent.field_img[field_i], self._parent.field_img[field_i - 1] = self._parent.field_img[field_i - 1], \
                                                                                   self._parent.field_img[field_i]
            self._parent.field_list[field_i], self._parent.field_list[field_i - 1] = self._parent.field_list[
                                                                                         field_i - 1], \
                                                                                     self._parent.field_list[field_i]
        self.field_order_update()

    def zorder_down(self):
        # // change the render order
        row = self.currentRow()
        if row < self.rowCount() - 1:
            field_i = self._parent.field_list.index(self.item(row, 2).loc)
            # // move item downwards in the table
            column = 1
            self.insertRow(row + 2)
            for i in range(self.columnCount()):
                if i == 1:
                    # // moving the progressbar
                    pb = self.cellWidget(row, 1)
                    self.setCellWidget(row + 2, 1, pb)
                else:
                    self.setItem(row + 2, i, self.takeItem(row, i))
                    self.setCurrentCell(row + 2, column)
            self.removeRow(row)
            # // mirror change in field_img and field_list
            self._parent.field_img[field_i], self._parent.field_img[field_i + 1] = self._parent.field_img[field_i + 1], \
                                                                                   self._parent.field_img[field_i]
            self._parent.field_list[field_i], self._parent.field_list[field_i + 1] = self._parent.field_list[
                                                                                         field_i + 1], \
                                                                                     self._parent.field_list[field_i]
            self.resizeRowsToContents()
        self.field_order_update()

    def zorder_down_full(self):
        # // change the render order
        row = self.currentRow()
        if row < self.rowCount() - 1:
            field_i = self._parent.field_list.index(self.item(row, 2).loc)
            # // move item downwards in the table
            column = 1
            final_row = self.rowCount()
            self.insertRow(final_row)
            self.setRowHeight(0, 20)
            for i in range(self.columnCount()):
                if i == 1:
                    # // moving the progressbar
                    pb = self.cellWidget(row, 1)
                    self.setCellWidget(final_row, 1, pb)
                else:
                    self.setItem(final_row, i, self.takeItem(row, i))
                    self.setCurrentCell(final_row, column)
            self.removeRow(row)
            # // mirror change in._parent field_img and._parent field_list
            temp = self._parent.field_img[field_i]
            del self._parent.field_img[field_i]
            self._parent.field_img.append(temp)
            temp = self._parent.field_list[field_i]
            del self._parent.field_list[field_i]
            self._parent.field_list.append(temp)
        self.resizeRowsToContents()
        self.field_order_update()

    def deleteSelection(self):
        items = self.selectedItems()
        if len(items) == 0:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       """<p>No image selected in the render table. Therefore, no image can be deleted from the render table.<p>""")
            return None

        # // list the location to remove
        locToRemove = []
        for k in items:
            if k.column() == 2:
                loc = self.item(k.row(), 2).loc
                locToRemove.append(loc)

        # // remove the locations in the list
        for loc in locToRemove:
            if isinstance(loc, dict):
                # // delete from table and update render order
                self._parent.field_remove(loc)

    def contextMenuEvent(self, event):
        if self.columnAt(event.pos().x()) == 2:
            a = self.item(self.rowAt(event.pos().y()), 2).loc
            if isinstance(a, dict):
                self.copy_image_to_project_idx = self._parent.field_list.index(a)
                self.menu = QtWidgets.QMenu(self)
                copy_action = QtGui.QAction('Remove Image', self.deleteSelection)
                copy_action.triggered.connect(self.remove)
                self.menu.addAction(copy_action)

                # copy_action = QtGui.QAction('Add Image Recognition Zone', self)
                # copy_action.triggered.connect(self.set_selection_zone)
                # self.menu.addAction(copy_action)
                self.menu.popup(QtGui.QCursor.pos())