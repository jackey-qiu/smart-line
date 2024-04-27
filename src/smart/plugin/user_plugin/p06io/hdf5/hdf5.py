#!/usr/bin/env python

__author__ = ["Jan Garrevoet"]

import difflib
import h5py
import numpy
import os
import sys

if sys.version_info < (3, ):
    PYTHON_VERSION = 2
else:
    PYTHON_VERSION = 3


########
# hdf5 #
########

class hdf5(object):
    """
    Class to handle hdf5 related actions.
    """
    # TODO:
    # + list all keys in file.

    # VDS
    # multiple datasets in one go. (provide list)
    # mirror input dataset list names in vds file.
    # cropping using VDS

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close_file()

    ############
    # __init__ #
    ############

    def __init__(self, filePath=None, mode='r', verbosity=0):
        '''
        Wrapper for h5py that simplifies the use.

        Parameters
        ----------
        filePath : str, optional
            File path of the hdf5 file.

        mode : str, optional
            Mode to open the file.
            Modes are r (read), w (write), and a (append).

        verbosity : int, optional
            Determines the verbosity output level.

        Note
        ----
        The file object can be created upon creation of the class instance
        when you foresee many interactions with the file
        or can be provided on method level when you foresee
        only one interaction with the file.
        '''

        self.verbosity = verbosity
        if filePath is not None:
            self.file_handle = self.open_file(filePath, mode)
        else:
            self.file_handle = None

    ################
    # __contains__ #
    ################

    def __contains__(self, item):
        """
        Wraps the h5py contains.
        """

        return item in self.file_handle

    ###########################
    # _create_virtual_dataset #
    ###########################

    def _create_virtual_dataset(
            self,
            file_handle,
            file_list,
            file_paths_in_vds,
            data_path_origin,
            data_path_target,
            shape,
            maxShape=None,
            expandAxis=0,
            appendAxis=False,
            cropping=None):
        '''
        Creates a virtual dataset.

        Parameters
        ----------
        file_handle : object
            The file object of the VDS file.

        file_list : list
            List containing the filenames.

        file_paths_in_vds : list
            List containing the file paths for inside the VDS.

        data_path_origin : str
            The path to the dataset inside the original HDF5 file.

        data_path_target : str
            The path to the dataset inside the VDS file.

        shape : tuple, optional
            The shape of the virtual dataset.

        maxShape : tuple, optional
            The maximum shape of the dataset.
            Use None to allow reshaping of the axis.

        expandAxis : int, optional
            The axis that is created to join the different source datasets.
            As a defaults an axis is prepended.

        appendAxis : boolean
            If True, the expandAxis is appended to.
            Default is False.

        cropping : list of int
            List containing the cropping coordinates.
        '''

        # FIXME:
        # add cropping
        # check if relative paths work

        dtype = self.get_dtype(
            data_path_origin,
            filePath=os.path.abspath(
                file_list[0]
            )
        )
        layout = h5py.VirtualLayout(
            shape=shape,
            maxshape=maxShape,
            dtype=dtype
        )

        if self.verbosity > 2:
            print('Created vds layout: {}'.format(layout.shape))

        layoutIndex = []
        for _ in range(len(shape)):
            layoutIndex.append(slice(None))

        for fileIndex, _ in enumerate(file_list):
            sourceShape = self.read_data_shape(
                data_path_origin,
                filePath=os.path.abspath(
                    file_list[fileIndex]
                )
            )

            if fileIndex == 0:
                base_shape = sourceShape

            virtualSource = h5py.VirtualSource(
                file_paths_in_vds[fileIndex],  # fixme
                # file_list[fileIndex],
                data_path_origin,
                shape=sourceShape
            )

            if appendAxis:
                layoutIndex[expandAxis] = slice(
                    # sourceShape[expandAxis]
                    base_shape[expandAxis]
                    * fileIndex,
                    base_shape[expandAxis]
                    * fileIndex
                    + sourceShape[expandAxis]
                )
                if self.verbosity > 2:
                    print(layoutIndex[expandAxis])
            else:
                layoutIndex[expandAxis] = fileIndex

            layout[tuple(layoutIndex)] = virtualSource

        file_handle.create_virtual_dataset(
            data_path_target,
            layout
        )

    ######################
    # _get_h5_file_paths #
    ######################

    def _get_h5_file_paths(
            self,
            vds_file_path,
            h5_file_path_list,
            method='relative',
            search_string=None,
            replace_string=None):
        '''
        Determines the file path of the files to include in the VDS file
        so the VDS file works after moving the files.

        Parameters
        ----------
        vds_file_path : str
            The absolute file path of the VDS output file.

        h5_file_path_list : list of str
            The absolute file path list of the files to include into the
            VDS file.

        method : str, optional
            The method used to determine the path inside the VDS file.
            Methods are:
            + relative
            + absolute

        search_string : str, optional
            The string to search for during the substitute method.

        replace_string : str, optional
            The string to replace the searched string with when the
            substitute method has been selected.

        Returns
        -------
        str
            The file path to use for the data files into the VDS file.
        '''
        output = []
        vds_base = os.path.split(vds_file_path)[0]
        h5_base = os.path.split(h5_file_path_list[0])[0]

        if method == 'absolute':
            output = h5_file_path_list

        elif method == 'relative':
            matcher = difflib.SequenceMatcher(
                None,
                vds_base,
                h5_base
            )

            match = matcher.find_longest_match(
                0,
                len(vds_base),
                0,
                len(h5_base)
            )

            for file_base in h5_file_path_list:
                output.append(file_base[match.size + 1:])

        elif method == 'substitute':
            for file_base in h5_file_path_list:
                output.append(
                    file_base.replace(
                        search_string,
                        replace_string
                    )
                )

        return output

    ##################
    # _get_vds_shape #
    ##################

    def _get_vds_shape(self, file_list, data_path, expand_axis, append_axis):

        shapeFirst = self.read_data_shape(
            data_path,
            filePath=file_list[0]
        )

        nbFiles = len(file_list)

        # Data is appended.
        if append_axis:
            shapeLast = self.read_data_shape(
                data_path,
                filePath=file_list[-1]
            )

            appendAxisShape = (
                (nbFiles - 1)
                * shapeFirst[expand_axis]
                + shapeLast[expand_axis]
            )

            vdsShape = list(shapeFirst)
            vdsShape[expand_axis] = appendAxisShape
            vdsShape = tuple(vdsShape)

        # An extra dimension is added.
        else:
            vdsShape = list(shapeFirst)
            if expand_axis != -1:
                vdsShape.insert(
                                expand_axis,
                                nbFiles
                                )
            else:
                vdsShape.append(nbFiles)

            vdsShape = tuple(vdsShape)

        if self.verbosity > 0:
            print('VDS shape: {}'.format(vdsShape))

        return vdsShape

    ##################
    # _unicode_check #
    ##################

    @staticmethod
    def _unicode_check(data):
        """
        Checks and converts unicode types to HDF5 compatible types.

        Parameters
        ----------
        data : any
            The data to be checked.

        Returns
        -------
        any
            The HDF5 compatible version.
        """

        if h5py.version.version_tuple[0] > 2:
            if PYTHON_VERSION > 2:
                if isinstance(data, (tuple, list, str, numpy.ndarray)):
                    # This first not to trigger an index error.
                    if isinstance(data, str):
                        data = numpy.array(
                            data,
                            dtype=h5py.string_dtype(encoding="utf-8")
                        )

                    elif isinstance(data[0], str):
                        data = numpy.array(
                            data,
                            dtype=h5py.string_dtype(encoding="utf-8")
                        )

            elif PYTHON_VERSION == 2:
                if isinstance(data, (tuple, list, unicode, numpy.ndarray)):  # noqa F821
                    if isinstance(data, unicode):   # noqa F821
                        data = numpy.array(
                            data,
                            dtype=h5py.string_dtype(encoding="utf-8")
                        )
                    elif isinstance(data[0], unicode):  # noqa F821
                        data = numpy.array(
                            data,
                            dtype=h5py.string_dtype(encoding="utf-8")
                        )

        return data

    #################
    # contains_path #
    #################

    def contains_path(self, data_path, filePath=None):
        '''
        Determines if the provided data path is present in the file.

        Parameters:
        -----------
        data_path : str
            Path to the data in the container

        filePath : str, optional
            Path to the file

        Returns
        -------
        boolean
            True when the data path exists. False when not present.
        '''

        # Get a file handle.
        file_handle = self._get_file_handle(filePath, 'a')

        return data_path in file_handle

    ##########################
    # create_virtual_dataset #
    ##########################

    def create_virtual_dataset(
            self,
            file_path,
            file_list,
            data_path_origin,
            data_path_target,
            expandAxis=0,
            appendAxis=False,
            cropping=None,
            coordinates=None,
            search_path=None):
        '''
        Creates a virtual dataset file.

        Parameters
        ----------
        file_path : str
            The path of the virtual dataset file.

        file_list : list of strings
            List containing all the file names of the source data files.

        data_path_origin : str
            The path to the dataset inside the original HDF5 file.

        data_path_target : str
            The path to the dataset inside the VDS file.

        expandAxis : int, optional
            The axis that is created to join the different source datasets.
            As a defaults an axis is prepended.

        coordinates : array, optional
            Array containing the coordinates on how to sort the data
            into the virtual dataset.

        search_path : tuple, optional
            Tuple containing the search and replace string.
        '''

        # Get a file handle.
        file_handle = self._get_file_handle(file_path, 'a')

        vdsShape = self._get_vds_shape(
            file_list,
            data_path_origin,
            expandAxis,
            appendAxis
        )

        # Convert file paths
        if search_path is None:
            file_paths_in_vds = self._get_h5_file_paths(
                file_path,
                file_list,
                method='absolute'
            )
        else:
            file_paths_in_vds = self._get_h5_file_paths(
                file_path,
                file_list,
                method='substitute',
                search_string=search_path[0],
                replace_string=search_path[1],
            )

        self._create_virtual_dataset(
            file_handle,
            file_list,
            file_paths_in_vds,
            data_path_origin,
            data_path_target,
            vdsShape,
            expandAxis=expandAxis,
            appendAxis=appendAxis,
            maxShape=vdsShape
        )

    ####################
    # _get_file_handle #
    ####################

    def _get_file_handle(self, file_path, mode):
        '''
        Returns file handle of the given file_path or returns the global
        file handle.

        Parameters
        ----------
        file_path : str
            File path of the file.

        mode : str
            File access mode.

        Returns
        -------
        object
            File handle
        '''
        if file_path is not None:
            file_handle = self.open_file(file_path, mode)
        elif file_path is None and self.file_handle is None:
            raise ValueError("No file provided.")
        else:
            file_handle = self.file_handle

        return file_handle

    ##############
    # close_file #
    ##############

    def close_file(self, fileHandle=None):
        '''
        Closes an HDF5 file.

        Parameters
        ----------
        fileHandle : object, optional
            File object handle.
        '''

        if self.verbosity > 0:
            print('Closing file.')
        if self.file_handle is None:
            fileHandle.close()
        else:
            self.file_handle.close()

    #############
    # get_dtype #
    #############

    def get_dtype(self, data_path, filePath=None):
        '''
        Returns the data type of the dataset.

        Parameters:
        -----------
        data_path : str
            Path to the data in the container

        filePath : str, optional
            Path to the file

        Returns
        -------
        numpy.dtype
            The dtype of the dataset.
        '''

        try:
            file_handle = self._get_file_handle(filePath, 'r')

            ret_val = file_handle[data_path].dtype

            return ret_val

        except Exception:
            raise
        #     print('Error: {}'.format(err))

        finally:
            # Only close when available and opened locally
            if self.file_handle is None and file_handle is not None:
                file_handle.close()

    ##################
    # get_group_tree #
    ##################

    def get_group_tree(self, group="/", file_path=None):
        """
        Returns the group tree.

        Parameters
        ----------
        group : str, optional
            The group of which to return the tree from.
            By default it returns the tree of the entire file.

        file_path : str, optional
            Path to the file

        Returns
        -------
        list
            List containing the tree in recursive order.
        """

        file_handle = self._get_file_handle(file_path, 'r')
        tree = []
        file_handle[group].visit(tree.append)
        return tree

    #################
    # has_attribute #
    #################

    def has_attribute(self, attribute_name, filePath=None):
        '''
        Checks if a file contains the provided attribute.

        Parameters
        ----------
        attribute_name : str
            Attribute name

        filePath : str, optional
            Path to the file.

        Returns
        -------
        Boolean
            True if the attribute exists, False if not.
        '''

        file_handle = self._get_file_handle(filePath, 'r')

        retVal = attribute_name in file_handle

        # Only close when available and opened locally
        if self.file_handle is None:
            self.close_file(file_handle)

        return retVal

    #############
    # open_file #
    #############

    def open_file(self, file_path, mode='r'):
        '''
        Opens an HDF5 file.

        Parameters
        ----------
        file_path : str
            Path to the file.

        Returns
        -------
        object
            Create the file object.
        '''

        file_handle = h5py.File(file_path, mode)
        return file_handle

    ##################
    # read_attribute #
    ##################

    def read_attribute(self, data_path, attribute_name, filePath=None):
        '''
        Returns the requested attribute.

        Parameters
        ----------
        data_path : str
            Path to the data in the container.

        attribute_name : str
            Attribute name

        filePath : str, optional
            Path to the file.

        Returns
        -------
        attribute
            Returns the attribute.
            If the attribute does not exists it returns None.
        '''

        try:
            file_handle = self._get_file_handle(filePath, 'r')

            if attribute_name in file_handle[data_path].attrs:
                return file_handle[data_path].attrs[attribute_name]
            else:
                raise ValueError("Data path has no attribute with that name.")

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if filePath is not None:
                self.close_file(file_handle)

    ######################
    # read_attribute_all #
    ######################

    def read_attribute_all(self, data_path, filePath=None):
        '''
        Returns the requested attribute.

        Parameters
        ----------
        data_path : str
            Path to the data in the container.

        filePath : str, optional
            Path to the file.

        Returns
        -------
        dict
            Returns all attributes of the data path in dict form.
        '''

        try:
            file_handle = self._get_file_handle(filePath, 'r')

            ret_val = {}
            for attr_name in file_handle[data_path].attrs:
                attr_value = self.read_attribute(
                    data_path,
                    attr_name,
                    filePath=filePath
                )
                ret_val[attr_name] = attr_value

            return ret_val

        except KeyError:
            raise ValueError("Dataset is not available.")

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if self.file_handle is None:
                self.close_file(file_handle)

    #############
    # read_data #
    #############

    def read_data(self, data_path, filePath=None, crop=False, reshape=False):
        '''
        Returns the requested data.

        Parameters:
        -----------
        data_path : str
            Path to the data in the container.

        filePath : str, optional
            Path to the file.

        crop : list of int, optional
            A list containing the cropping parameters.
            e.g. [None, [0, 10], None]
            By default the entire dataset is returned.

        reshape : boolean, optional
            Reshapes a 1D array to report properly size (?,1).

        Returns
        -------
        ndarray
            Array containing the requested dataset.
        '''

        try:
            if self.verbosity > 0:
                if filePath is not None:
                    print(
                        'Reading {} from {}'.format(
                            data_path,
                            filePath
                        )
                    )
                else:
                    print(
                        'Reading {}'.format(
                            data_path
                        )
                    )

            file_handle = self._get_file_handle(filePath, 'r')

            if data_path not in file_handle:
                raise KeyError('Dataset not found in file.')

            data_shape = file_handle[data_path].shape

            if crop and len(crop) != len(data_shape):
                raise ValueError(
                    'An incorrect number of cropping parameters were provided.'
                )

            if crop:
                slicer = []
                for i, _ in enumerate(data_shape):
                    if crop[i] is None:
                        slicer.append(slice(crop[i]))
                    else:
                        slicer.append(slice(crop[i][0], crop[i][1]))
                data = file_handle[data_path][tuple(slicer)]
            else:
                data = file_handle[data_path][:]

            # Reshape output
            if reshape:
                if len(data.shape) == 1:
                    data = data.reshape(
                        data.shape[0],
                        1
                    )

            return data

        except Exception as err:
            if self.verbosity > 0:
                print('Error: {}'.format(err))
            raise

        finally:
            # Only close when available and opened locally
            if self.file_handle is None:
                self.close_file(file_handle)

    ############################
    # read_data_multiple_files #
    ############################

    def read_data_multiple_files(
            self,
            data_path,
            file_dir,
            file_prefix,
            file_postfix,
            file_extension,
            index_start,
            index_end,
            index_length,
            appendAxis=0,
            crop=False,
            reshape=False):
        '''
        Returns the requested data.

        Parameters:
        -----------
        data_path : str
            Path to the data in the container.

        file_dir : str
            Directory path containing the files.

        file_prefix : str
            Prefix of the files.

        file_postfix : str
            Postfix of the files.

        file_extension : str
            Extension of the file.

        index_start : int
            First index of the fileset.

        index_end : int
            Last index of the fileset.

        index_length : int
            Total length of the file index.

        appendAxis : int, optional
            Axis to which the data in the different files is appended to.

        crop : list of int, optional
            A list containing the cropping parameters.
            e.g. [None, [0, 10], None]
            By default the entire dataset is returned.

        reshape : boolean, optional
            Reshapes a 1D array to report properly size (?,1).

        Returns
        -------
        ndarray
            Array containing the requested dataset in all the files
        '''

        if not file_dir.endswith('/'):
            file_dir += '/'

        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension

        # fixme should be _function
        # include a methods that reads from a file list
        for index in range(index_start, index_end + 1):
            _file = (
                file_dir
                + file_prefix
                + str(index).zfill(index_length)
                + file_postfix
                + file_extension
            )

            _tmpData = self.read_data(
                data_path,
                filePath=_file,
                crop=crop,
                reshape=reshape,
            )

            if appendAxis == len(_tmpData.shape):
                _tmpData = numpy.expand_dims(_tmpData, appendAxis)

            if index == index_start:
                _data = _tmpData
            else:
                _data = numpy.concatenate(
                    (_data, _tmpData),
                    axis=appendAxis
                )

        return _data

    ###################
    # read_data_shape #
    ###################

    def read_data_shape(self, data_path, filePath=None, axis=-1):
        '''
        Returns the requested data shape.

        Parameters:
        -----------
        data_path : str
            Path to the data in the container

        filePath : str, optional
            Path to the file

        axis : int, optional
            Which axis you want the shape of.
            Default it returns the shape of the entire dataset.
        '''

        try:
            file_handle = self._get_file_handle(filePath, 'r')

            if self.verbosity > 1:
                print(
                    'Reading data shape of:\n\tPath: {}\n\tAxis: {}'.format(
                        data_path,
                        axis
                    )
                )

            if axis == -1:
                _retVal = file_handle[data_path].shape
            else:
                # fixme, this should be cast to a tuple for uniformity
                _retVal = file_handle[data_path].shape[axis]

            if self.verbosity > 1:
                print(
                    '\tData shape: {}'.format(
                        _retVal
                    )
                )

            return _retVal

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if self.file_handle is None and file_handle is not None:
                file_handle.close()

    ###################
    # write_attribute #
    ###################

    def write_attribute(
            self,
            data_path,
            attribute_name,
            attribute_value,
            filePath=None):
        '''
        Adds the provided attribute to the given dataset.

        Parameters
        ----------
        data_path : str
            Path to the data in the container.

        attribute_name : str
            Attribute name.

        filePath : str, optional
            Path to the file.
        '''
        file_handle = None
        try:
            file_handle = self._get_file_handle(filePath, 'a')

            attribute_value = self._unicode_check(attribute_value)

            file_handle[data_path].attrs[attribute_name] = attribute_value

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if filePath is not None and file_handle is not None:
                self.close_file(file_handle)

    ########################
    # write_attribute_all #
    ########################

    def write_attribute_all(self, data_path, attributes, filePath=None):
        '''
        Adds the provided attribute to the given dataset.

        Parameters
        ----------
        data_path : str
            Path to the data in the container.

        attributes : list of tuples or dict
            List containing tuples consisting of
            (attribute name,attribute value)
            or a dictionary with the keys being the attribute names.

        filePath : str, optional
            Path to the file.
        '''

        # fixme: input should be an attribute dict and not a tuple
        file_handle = None
        try:
            file_handle = self._get_file_handle(filePath, 'a')

            if isinstance(attributes, tuple):
                attributes = [attributes]

            if isinstance(attributes, list):
                for attrs in attributes:
                    self.write_attribute(
                        data_path,
                        attrs[0],
                        attrs[1],
                        filePath=filePath
                    )
            elif isinstance(attributes, dict):
                for item, value in attributes.items():
                    self.write_attribute(
                        data_path,
                        item,
                        value,
                        filePath=filePath
                    )

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if file_handle is not None and filePath is not None:
                self.close_file(file_handle)

    #######################
    # write_compound_data #
    #######################

    def write_compound_data(
            self, data_path, data, data_type=None,
            file_path=None, append_data=False):
        """
        Writes a compound dataset to an HDF5 file.

        Parameters
        ----------
        data_path : str
            Path for the data in the container.

        data : ndarray
            Array containing the data.

        data_type : numpy.dtype, optional
            The data type of the dataset.

        file_path : str, optional
            Path to the file.

        append_data : boolean, optional
            If used, the data will be appended to axis 0.
        """

        try:
            file_handle = self._get_file_handle(file_path, 'a')

            if append_data and data_type is None and data_path in file_handle:
                data_type = file_handle[data_path].dtype

            if isinstance(data, list):
                if data_type is not None:
                    data = numpy.array(data, dtype=data_type)
            elif isinstance(data, tuple):
                data = numpy.array([data], dtype=data_type)
            elif isinstance(data, numpy.ndarray):
                if data_type is None:
                    data_type = data.dtype
            else:
                raise ValueError("Wrong data type provided.")

            if data_path not in file_handle:
                file_handle.create_dataset(
                    data_path,
                    (1,),
                    data_type,
                    maxshape=(None,)
                )
                file_handle[data_path][...] = data
            else:
                if append_data:
                    old_shape = file_handle[data_path].shape[0]
                    new_shape = old_shape + data.shape[0]
                    file_handle[data_path].resize(new_shape, axis=0)
                    file_handle[data_path][old_shape:, ...] = data
                else:
                    raise ValueError(
                        "The file already contains a dataset with this "
                        "path: {}".format(
                            data_path
                        )
                    )

        except Exception:
            raise

        finally:
            # Only close when available and opened locally
            if self.file_handle is None:
                file_handle.close()

    ##############
    # write_data #
    ##############

    def write_data(
            self,
            data_path,
            data,
            filePath=None,
            append=False,
            append_axis=0,
            create_append_axis=True,
            compression=None,
            compression_opts=None,
            chunks=None):
        """
        Writes a dataset to an HDF5 file.

        Parameters
        ----------
        data_path : str
            Path for the data in the container.

        data : ndarray
            Array containing the data.

        filePath : str, optional
            Path to the file.

        append : boolean, optional
            To append the dataset to an existing one or not.
            Default is False.

        append_axis : int, optional
            The axis which should be appended to.
            Default is 0.

        create_append_axis : boolean, optional
            To create the append axis or not.

        compression : str, optional
            The compression type.
            Default is none. Available are "gzip" and "lzf"

        compression_opts : any, optional
            The compression options. Used for gzip to set the level.

        chunks : tuple, optional
            The chunk size.
        """

        try:
            file_handle = self._get_file_handle(filePath, "a")

            data = self._unicode_check(data)

            if append and create_append_axis:
                data = numpy.expand_dims(data, append_axis)
                if chunks is not None:
                    chunks = list(chunks)
                    chunks.insert(append_axis, 1)
                    chunks = tuple(chunks)
            elif append and isinstance(data, list):
                data = numpy.asarray(data)

            if data_path not in file_handle:
                if isinstance(data, numpy.ndarray):
                    max_shape = data.shape
                elif isinstance(data, (int, float, bytes)):
                    max_shape = (1, )
                elif isinstance(data, list):
                    max_shape = numpy.asarray(data).shape
                else:
                    max_shape = None

                if append:
                    max_shape = list(max_shape)
                    max_shape[append_axis] = None
                    max_shape = tuple(max_shape)
                else:
                    if isinstance(data, (int, float, bytes)):
                        max_shape = None

                if compression != "gzip":
                    compression_opts = None

                if not isinstance(data, numpy.ndarray):
                    compression = None
                    compression_opts = None

                file_handle.create_dataset(
                    data_path,
                    data=data,
                    maxshape=max_shape,
                    compression=compression,
                    compression_opts=compression_opts,
                    chunks=chunks
                )
            else:
                if append:
                    old_size = file_handle[data_path].shape[append_axis]
                    new_size = (
                        old_size
                        + data.shape[append_axis]
                    )
                    new_shape = list(data.shape)
                    new_shape[append_axis] = new_size
                    new_shape = tuple(new_shape)

                    file_handle[data_path].resize(new_shape)
                    file_handle[data_path][old_size:] = data

        except Exception as err:
            raise
            if self.verbosity > 0:
                print('Error: {}'.format(err))

        finally:
            # Only close when available and opened locally
            if self.file_handle is None:
                file_handle.close()

    ###################
    # write_data_dict #
    ###################

    def write_data_dict(
            self,
            base_path,
            data):
        """
        Writes the content of a dictionary to a file.

        Parameters
        ----------
        base_path : str
            The base path for the dictionary root level in the container.

        data : dict
            Dictionary containing the data.
        """

        _ = self._get_file_handle(None, "a")

        for key, value in data.items():
            if isinstance(value, dict):
                self.write_data_dict("{}/{}".format(base_path, key), value)
            else:
                self.write_data("{}/{}".format(base_path, key), value)
