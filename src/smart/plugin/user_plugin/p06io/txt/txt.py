#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import numpy


class txt(object):

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Wrapper for txt that simplifies the use.

        Parameters
        ----------
        verbosity : int, optional
            Determines the verbosity output level.
        """

        self.verbosity = verbosity
        self._file_handle = None

    ######################
    # _create_filehandle #
    ######################

    def _create_filehandle(self, filename, mode):
        """
        Creates the file handle.

        Parameters
        ----------
        filename : str
            The path of the file.

        mode : str
            The mode with which the file shall be opened.
        """

        self._file_handle = open(filename, mode)

    #####################
    # _close_filehandle #
    #####################

    def _close_filehandle(self):
        """
        Closes the file handle.
        """

        self._file_handle.close()

    ##############
    # close_file #
    ##############

    def close_file(self):
        """
        Close the file.
        """

        self._close_filehandle()

    #############
    # open_file #
    #############

    def open_file(self, filename, mode="w"):
        """
        Opens a file.

        Parameters
        ----------
        filename : str
            The name of the file.

        mode : str, optional
            Modus to open the file with.
            r == read only
            w == write
            a == append to file
            Default is w.
        """

        self._create_filehandle(filename, mode)

    ###############
    # write_array #
    ###############

    def write_array(
            self, filename, data, fmt=None, delimiter=" ", newline="\n",
            header="", footer="", comment="#"):
        """
        Writes an array to a file.

        Parameters
        ----------
        filename : str
            File name.

        data : ndarray
            Array containing the data.

        fmt : list, optional
            List of string representing the column data format.

        delimiter : str, optional
            Delimiter which separates the different columns.
            Default value is " ".

        newline : str, optional
            New line character.
            Default is "\n"

        header : str, optional
            String that will be prepended to the file.
            Default is "".

        footer : str, optional
            String at will be appended to the file.

        comment : str, optional
            Character representing a comment.
            Default is "#".
        """

        if fmt is None:
            fmt = []
            for i in range(data.shape[1]):
                fmt.append("%s")

        numpy.savetxt(
            filename,
            data,
            delimiter=delimiter,
            newline=newline,
            header=delimiter.join(header),
            footer=footer,
            comments=comment,
            fmt=fmt
        )

    ##############
    # write_list #
    ##############

    def write_list(self, filename, list, delimiter="\n"):
        """
        Writes the provided list to a txt file.
        Each list item will be written on a new line.

        Parameters
        ----------
        filename : str
            Name of the output txt file.

        list : list
            List containing the data to be written to the file.
        """

        with open(filename, "w") as file_handle:
            for _item in list:
                file_handle.write(str(_item) + delimiter)

    #########
    # write #
    #########

    def write(self, text):
        """
        Writes the provided text to a txt file.

        Parameters
        ----------
        text : str
            Text to be written to the file.
        """

        self._file_handle.write(str(text) + "\n")
