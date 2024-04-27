from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import xlwt


############
# document #
############

class document(object):
    """
    Class handling spreadsheet documents.
    """

    ############
    # __init__ #
    ############

    def __init__(self, filename):
        """
        Class handling spreadsheet documents.

        Parameters
        ----------
        filename : str
            The path of the file.
        """

        self._row_auto_index = 0
        self._document = xlwt.Workbook()
        self.sheets = {}
        self.filename = filename

    #############
    # add_sheet #
    #############

    def add_sheet(self, name):
        '''
        Adds a sheet to the document.

        Parameters
        ----------
        name : str
            The name of the sheet.
        '''

        if name not in self.sheets:
            self.sheets[name] = self._document.add_sheet(name)
        else:
            raise ValueError('Sheet already exists.')

    ##############
    # get_sheets #
    ##############

    def get_sheets(self):
        '''
        Get all the defined sheets.
        '''

        return list(self.sheets.keys())

    ########
    # save #
    ########

    def save(self):
        '''
        Saves the document to disk.
        '''

        self._document.save(self.filename)

    ##############
    # write_data #
    ##############

    def write_data(self, data, sheet, row, column):
        '''
        Writes data to the sheet.

        Parameters
        ----------
        data : any
            The data you want to write.

        sheet : str
            The sheet you want to write to.

        row : int
            The row coordinate of the cell.
            Index starts at zero.

        column : int
            The column coordinate of the cell.
            Index starts at zero.
        '''

        if sheet not in self.sheets:
            raise ValueError('Sheet not defined.')

        self.sheets[sheet].write(row, column, data)

    #####################
    # write_to_next_row #
    #####################

    def write_to_next_row(self, data, sheet):
        for col in range(len(data)):
            self.write_data(data[col], sheet, self._row_auto_index, col)

        self._row_auto_index += 1

    ################
    # write_header #
    ################

    def write_header(self, header, sheet):
        '''
        Writes the header to the selected sheet.

        Parameters
        ----------
        header : list
            A list containing the headers of the columns.

        sheet : str
            The name of the sheet to write the header to.
        '''

        for col in range(len(header)):
            self.write_data(header[col], sheet, 0, col)

        if self._row_auto_index == 0:
            self._row_auto_index += 1
