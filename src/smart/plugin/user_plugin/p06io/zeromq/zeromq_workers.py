#!/usr/bin/env python

import itertools
import multiprocessing
import os
import re

import fabio
import numpy
import p06io
import tifffile

__all__ = [
    'ZmqHdf5Streamer',
    'zmq_hdf5',
    'hdf52tiff_master',
    'zmq_cbf_writer',
    'zmq_tiff_writer'
]


###################
# ZmqHdf5Streamer #
###################

class ZmqHdf5Streamer(p06io.hdf5):
    '''
    Class that enables sending data from an HDF5 file.
    '''

    def __init__(self, output_connection, verbosity=0):
        '''
        Class for hdf5 handling with zmq.

        Parameters
        ----------
        output_connection : object
            The output connection object.

        verbosity : int, optional
            The verbosity level.
        '''

        super(ZmqHdf5Streamer, self).__init__()

        # self._input_connection = input_connection
        self._output_connection = output_connection
        self.verbosity = verbosity
        self.hdf5 = p06io.hdf5()

    #####################
    # _iterator_counter #
    #####################

    def _iterator_counter(self, start, stop, interval=1):
        '''
        Providing an iterating counter object.

        Parameters
        ----------
        start : int
            The start value.
        stop : int
            The final value.

        interval : int, optional
            The increment.
            Default is 1.

        Returns
        -------
        instance
            Iterator instance.
        '''

        return itertools.chain(
            range(
                start,
                stop,
                interval
            )
        )

    ##############
    # _send_data #
    ##############

    def _send_data(self, zmq_connection, data, metadata=None):
        '''
        Sends the data over the socket as a numpy array.

        Parameters
        ----------
        zmq_connection : instance
            The ZMQ connection instance.

        data : ndarray or list
            The data to be send.

        metadata : dict, optional
            Dictionary containing extra metadata.
        '''

        try:
            if isinstance(data, list):
                if self.verbosity > 1:
                    print('Sending multi part dataset')
                    for i, _ in enumerate(data):
                        try:
                            print(
                                'Element {} | {}'.format(
                                    i,
                                    data[i].shape
                                )
                            )
                        except Exception:
                            # For when not a numpy.ndarray
                            pass

                zmq_connection.send_multi_dataset(
                    data,
                    metadata=metadata
                )

            elif isinstance(data, numpy.ndarray):
                if self.verbosity > 2:
                    print(
                        'sending numpy array with shape: {}'.format(
                            data.shape
                        )
                    )

                zmq_connection.send_numpy_array(
                    data,
                    metadata=metadata
                )
            else:
                raise TypeError(
                    'Received unsupported dtype: {}'.format(
                        type(data)
                    )
                )

        except Exception as err:
            print(err)

    ################
    # send_dataset #
    ################

    def prepare_sending_dataset(
            self,
            filename,
            dataset,
            frame_split=False,
            frame_axis=0,
            frame_split_size=1,
            acq_index_start=0,
            acq_index_end=None,
            crop=False,
            metadata=None):
        '''
        Sends a dataset.

        Parameters
        ----------
        filename : str
            File path of the file.

        dataset : list
            List of paths of the datasets inside the HDF5 container.

        frame_split : boolean, optional
            Splits the dataset into frames that will be send as separate
            messages.
            Default is False.

        frame_axis : int or list, optional
            Determines which axis defines the different frames when frame_split
            is enabled.
            By default the first axis (0) is used to split the dataset if the
            number of dimensions > 1.

        frame_split_size : int, optional
            The number of frames to send when frame_split is enabled
            upon 1 request.
            Default is 1.

        acq_index_start : int, optional
            The acquisition index start of the scan file.

        acq_index_end : int, optional
            The acquisition index end of the scan file.

        crop : list of a list of int, optional
            A list containing the cropping parameters.
            e.g. [[None, [0, 10], None]] when 1 dataset is defined in dataset.

        metadata : dict, optional
            Metadata to be added to the data.
        '''

        self.frame_split = frame_split

        if isinstance(frame_axis, int):
            self.frame_axis = [frame_axis]
            if len(dataset) > 1:
                for i, _ in enumerate(dataset):
                    if i != 0:
                        self.frame_axis.append(0)

        elif isinstance(frame_axis, list):
            self.frame_axis = frame_axis

        if self.frame_split is not None and self.frame_axis is None:
            self.frame_axis = []
            for i, _ in enumerate(dataset):
                self.frame_axis.append(0)

        self.frame_split_size = frame_split_size
        self.metadata = metadata
        self.data = []
        try:
            for i, datapath in enumerate(dataset):
                if self.verbosity > 0:
                    print('Reading dataset: {}'.format(datapath))

                data_shape = self.hdf5.read_data_shape(
                    datapath,
                    filePath=filename
                )

                if crop:
                    if len(data_shape) != len(crop[i]):
                        raise ValueError(
                            'For dataset: {} are not the correct amount of '
                            'cropping parameters provided.'.format(
                                datapath
                            )
                        )

                    self.data.append(
                        self.hdf5.read_data(
                            datapath,
                            filePath=filename,
                            crop=crop[i]
                        )
                    )

                else:
                    self.data.append(
                        self.hdf5.read_data(
                            datapath,
                            filePath=filename
                        )
                    )

        except KeyError:
            raise

        # Add metadata when needed.
        if self.metadata is None:
            self.metadata = {}

        if 'data' not in self.metadata:
            self.metadata['data'] = {}

        if 'filename' not in self.metadata['data']:
            self.metadata['data']['filename'] = filename

        if 'data_path' not in self.metadata:
            self.metadata['data']['data_path'] = dataset

        if self.verbosity > 0:
            print('final metadata: {}'.format(self.metadata))

        if self.frame_split:
            for dataset_nb, _ in enumerate(self.data):
                if (self.frame_axis[dataset_nb]
                        > len(self.data[dataset_nb].shape) - 1):
                    raise ValueError(
                        'Axis number ({}) out of bounds ({}).'.format(
                            self.frame_axis[dataset_nb],
                            len(self.data[dataset_nb].shape) - 1
                        )
                    )

                # Axis needs to be 0 in the loop otherwise
                # the data is not contiguous
                if self.frame_axis[dataset_nb] != 0:
                    if self.verbosity > 1:
                        print(
                            'Moving axis for dataset {} '
                            'from axis {} to 0'.format(
                                dataset_nb,
                                self.frame_axis[dataset_nb]
                            )
                        )
                    self.data[dataset_nb] = numpy.ascontiguousarray(
                        numpy.moveaxis(
                            self.data[dataset_nb],
                            self.frame_axis[dataset_nb],
                            0
                        )
                    )

        if self.frame_split:
            self.last_frame_index = self.data[0].shape[0] - 1
        else:
            self.last_frame_index = 0
            self.frame_split_size = self.last_frame_index + 1

        self.frame_counter = self._iterator_counter(
            0,
            self.last_frame_index + 1,
            self.frame_split_size
        )

        if acq_index_start is not None and acq_index_end is not None:
            self.acquisition_index_counter = self._iterator_counter(
                acq_index_start,
                acq_index_end + 1,
                self.frame_split_size
            )

    #######################
    # send_next_data_part #
    #######################

    def send_next_data_part(self):
        '''
        Send the next data part.

        Raises
        ------
        StopIteration
            Gets raised when all data parts are sent.
        '''

        if self.frame_split:
            frame_index_start = next(self.frame_counter)

            frame_index_end = frame_index_start + self.frame_split_size - 1
            self.metadata['data']['frame_index'] = (
                frame_index_start,
                frame_index_end
            )

            if hasattr(self, 'acquisition_index_counter'):
                acq_index_start = next(self.acquisition_index_counter)
                acq_index_end = acq_index_start + self.frame_split_size - 1

                self.metadata['data']['acquisition_index'] = (
                    acq_index_start,
                    acq_index_end
                )

            if self.verbosity > 0:
                print(
                    'Current frame index: {}'.format(
                        frame_index_start
                    )
                )

            if len(self.data) > 1:
                data = []
                for dataset in self.data:
                    data.append(
                        dataset[frame_index_start:frame_index_end + 1, ...]
                    )
                self._send_data(
                    self._output_connection,
                    data,
                    metadata=self.metadata
                )
            else:
                self._send_data(
                    self._output_connection,
                    self.data[0][frame_index_start:frame_index_end + 1, ...],
                    metadata=self.metadata
                )

        else:
            frame_index_start = next(self.frame_counter)
            # frame_index_start = 0
            frame_index_end = frame_index_start + self.data[0].shape[0] - 1
            if self.verbosity > 0:
                print(
                    'Current frame: {} till: {}'.format(
                        frame_index_start,
                        frame_index_end
                    )
                )

            self.metadata['data']['frame_index'] = (
                frame_index_start,
                frame_index_end
            )

            if hasattr(self, 'acquisition_index_counter'):
                acq_index_start = next(self.acquisition_index_counter)
                acq_index_end = acq_index_start + self.data[0].shape[0] - 1

                self.metadata['data']['acquisition_index'] = (
                    acq_index_start,
                    acq_index_end
                )

            if len(self.data) > 1:
                self._send_data(
                    self._output_connection,
                    self.data,
                    metadata=self.metadata,
                )
            else:
                self._send_data(
                    self._output_connection,
                    self.data[0],
                    metadata=self.metadata,
                )

        if frame_index_end >= self.last_frame_index:
            self.file_completed = True
        else:
            self.file_completed = False


############
# zmq_hdf5 #
############

class zmq_hdf5(p06io.hdf5):
    '''
    Class that enables sending data from or to an HDF5 file.
    '''

    ############
    # __init__ #
    ############

    def __init__(
            self,
            inputHost=None,
            inputPort=None,
            inputType=None,
            inputPortType=None,
            # inputProtocol = 'tcp',
            commHost=None,
            commPort=None,
            commType='server',
            commPortType='rep',
            # commProtocol = 'tcp',
            outputHost=None,
            outputPort=None,
            outputType=None,
            outputPortType=None,
            # outputProtocol = 'tcp',
            verbosity=0):
        '''

        Parameters
        ----------


        inputType : list
            List containing server/client and socket type.
        '''
        super(zmq_hdf5, self).__init__()

        self.inputType = inputType
        self.inputPortType = inputPortType
        self.outputType = outputType
        self.outputPortType = outputPortType
        self.commType = commType
        self.commPortType = commPortType

        self.verbosity = verbosity

        # Input socket
        if (inputHost is not None
                and inputPort is not None
                and inputType is not None
                and inputPortType is not None):
            print('Init input')
            self.inputSocket = self._init_socket(
                inputHost,
                inputPort,
                self.inputType,
                self.inputPortType
                # inputProtocol
            )
        else:
            self.inputSocket = None

        # Output socket
        if (outputHost is not None
                and outputPort is not None
                and outputType is not None):
            print('Init output')

            self.outputSocket = self._init_socket(
                outputHost,
                outputPort,
                self.outputType,
                self.outputPortType
                # outputProtocol
            )
        else:
            self.outputSocket = None

        # HDF5 instance
        self.hdf5 = p06io.hdf5()

    ################
    # _init_socket #
    ################

    def _init_socket(self, host, port, processType, portType, protocol='tcp'):

        if processType == 'client':
            if portType == 'req':
                return p06io.zeromq.ClientReq(
                    host,
                    port,
                    verbosity=self.verbosity
                )
            else:
                raise ValueError('Sorry not implemented yet')
        elif processType == 'server':
            if portType == 'req':
                return p06io.zeromq.ServerReq(port=port)
            elif portType == 'rep':
                return p06io.zeromq.ServerRep(port=port)
            else:
                raise ValueError('Sorry not implemented yet')
        else:
            raise ValueError('Sorry not implemented yet')

        if self.verbosity > 1:
            print(
                'Socket initialised on {}:{}'.format(
                    host,
                    port
                )
            )

    ################
    # request_file #
    ################

    def request_file(self, request='next', timeout=0.5):
        '''
        Requests a new file from a zmq source.

        Parameters
        ----------
        request : any, optional
            The request message content.

        timeout : float, optional
            The timeout of the reply.

        Returns
        -------
        any
            The reply of the remote.
        '''

        return self.inputSocket.send_receive_message(
            request,
            timeout=timeout
        )

    ##############
    # _send_data #
    ##############

    def _send_data(self, socket, data, metadata=None, topic=None):
        '''
        Sends the data over the socket as a numpy array.

        Parameters
        ----------
        data : ndarray
            The data.

        metadata : dict, optional
            Dictionary containing extra metadata.
        '''

        # FIXME add other schemes

        try:
            if self.outputPortType == 'rep':

                _msg = self.outputSocket.receive_message()

                if self.verbosity > 3:
                    print('_send_data received message: {}'.format(_msg))

                if _msg == 'next':
                    if self.verbosity > 2:
                        print(
                            'sending numpy array with shape: {}'.format(
                                data.shape
                            )
                        )

                    socket.send_numpy_array(
                        data,
                        metadata=metadata
                    )
        except Exception as err:
            print(err)

    ################
    # send_dataset #
    ################

    def send_dataset(
            self,
            file,
            dataset,
            frameSplit=False,
            frameAxis=None,
            topic=None,
            metadata=None):
        '''
        Sends a dataset.

        Parameters
        ----------
        file : str
            File path of the file.

        dataset : str
            Path of the dataset inside the HDF5 container.

        frameSplit : boolean, optional
            Splits the dataset into frames that will be send as separate
            messages.
            Default is False.

        frameAxis : int, optional
            Determines which axis defines the different frames when frameSplit
            is enabled.
            By default the last axis is used to split the dataset if the
            number of dimensions > 1.

        topic : str, optional
            Topic that will be used when using a pub socket.
            Default is None.

        metadata : dict, optional
            Metadata to be added to the data.
        '''

        try:
            _data = self.hdf5.read_data(
                dataset,
                filePath=file
            )

            _dataAvailable = True
        except KeyError:
            _dataAvailable = False

        if _dataAvailable is True:
            if self.verbosity > 0:
                print('Dataset shape: {}'.format(_data.shape))
                print('Initial metadata: {}'.format(metadata))

            # Add metadata when needed.
            if metadata is None:
                metadata = {}

            if 'filename' not in metadata.keys():
                metadata['filename'] = file

            if 'dataset' not in metadata.keys():
                metadata['dataset'] = dataset

            if self.verbosity > 0:
                print('final metadata: {}'.format(metadata))

            if frameSplit:
                if frameAxis > len(_data.shape) - 1:
                    raise ValueError('Axis number out of bounds.')

                # Axis needs to be 0 in the loop otherwise
                # the data is not contiguous
                if frameAxis != 0:
                    _tmpData = numpy.moveaxis(_data, frameAxis, 0)
                else:
                    _tmpData = _data

                for frame in range(_tmpData.shape[0]):
                    # Add acquisition number metadata
                    metadata['data_index'] = frame
                    self._send_data(
                        self.outputSocket,
                        _tmpData[frame, ...],
                        metadata=metadata,
                        topic=topic
                    )

            else:
                self._send_data(
                    self.outputSocket,
                    _data,
                    metadata=metadata,
                    topic=topic
                )

    ########
    # stop #
    ########

    def stop(self):
        if self.inputSocket is not None:
            self.inputSocket.stop()

        if self.outputSocket is not None:
            self.outputSocket.stop()

    ###############
    # _write_data #
    ###############

    def _write_data(
            self,
            fileHandle,
            dataset,
            data,
            shape=None,
            appendAxis=None):
        pass

    def write_dataset(
            self,
            file,
            dataset,
            stream=False,
            shape=None):
        '''
        Receives data on the input socket and writes it to a file.

        Parameters
        ----------
        file : str
            File path of the file.

        dataset : str
            Path to the dataset.

        stream : boolean, optional
            When stream is enabled it keeps the file open until the file is
            closed manually. This allows for lower overhead when streaming
            data to a dataset.

        shape : list, optional
            List of ints containing
        '''
        pass


###############################################################################
# legacy code
###############################################################################

####################
# hdf52tiff_master #
####################

class hdf52tiff_master(object):

    def __init__(self, inputHost, inputPort, outputPort, verbosity=0):

        self.inputHost = inputHost
        self.inputPort = inputPort
        self.outputPort = outputPort
        self.verbosity = verbosity

        self.queue = multiprocessing.Queue()
        self._terminate = multiprocessing.Event()

    def sub_process(self, inputHost, inputPort, queue, terminate, verbosity):

        subClient = p06io.zeromq.ClientSub(
            inputHost,
            inputPort,
            verbosity=verbosity
        )
        subClient.add_subscription_topic("eiger4m_01")
        try:
            while not terminate.is_set():
                _msg = subClient.receive_message(0.1)
                if _msg is not None:
                    _msg, _ = _msg
                    if verbosity > 0:
                        print('Adding: {}'.format(_msg))

                    queue.put(_msg)
        except Exception as err:
            print(err)
            terminate.set()
        finally:
            print('Stopping sub client.')
            subClient.stop()

    def rep_process(self, outputPort, queue, terminate, verbosity):
        repServer = p06io.zeromq.ServerRep(
            port=outputPort,
            verbosity=verbosity
        )

        try:
            while not terminate.is_set():
                _msg = repServer.receive_message(timeout=0.1)
                if (verbosity > 1 and _msg is not None) or verbosity > 3:
                    print(_msg)
                if _msg == 'next':
                    if not queue.empty():
                        _payload = queue.get()
                    else:
                        _payload = None

                    if self.verbosity > 1:
                        print(_payload)
                    repServer.send_message(_payload)
        except Exception as err:
            print(err)
            terminate.set()
        finally:
            if self.verbosity > 0:
                print('Stopping reply server.')
            repServer.stop()

    def run(self):
        try:
            subProcess = multiprocessing.Process(
                target=self.sub_process,
                args=(
                    self.inputHost,
                    self.inputPort,
                    self.queue,
                    self._terminate,
                    self.verbosity
                )
            )

            subProcess.start()

            repProcess = multiprocessing.Process(
                target=self.rep_process,
                args=(
                    self.outputPort,
                    self.queue,
                    self._terminate,
                    self.verbosity
                )
            )

            repProcess.start()

        except Exception as err:
            self._terminate.set()
            print(err)

    def stop(self):
        self._terminate.set()


##################
# zmq_cbf_writer #
##################

def zmq_cbf_writer(
        host, port, metadata={}, protocol=None, worker=False, max_dtype=32,
        verbosity=0):

    zmqReq = p06io.zeromq.ClientReq(
        host, port, protocol=protocol, verbosity=verbosity
    )

    """
    Writes a cbf file.

    Parameters
    ----------
    filename : str
        Filename of the cbf file.

    data : ndarray
        Data to be written.

    metadata : dict, optional
        Metadata to include into your tiff file.
    """

    _run = True

    while _run:

        status = zmqReq.send_message("next", timeout=1)

        if status == 1:
            rcv_msg = zmqReq.receive_numpy_array()
            if rcv_msg is not None:
                data, metadata = rcv_msg

                if verbosity > 1:
                    print("File metadata: {}".format(metadata))

                if "cbf_filename" in metadata.keys():
                    filename = metadata["cbf_filename"]

                else:
                    try:
                        if metadata["output_base"] is not None:
                            tmp = re.compile("/raw|processed/")
                            base_name = tmp.sub(
                                "/scratch_bl",
                                metadata["filename"]
                            )
                        else:
                            base_name = filename
                    except KeyError:
                        base_name = filename

                    base_name = os.path.splitext(base_name)[0]

                    metadata["cbf_filename"] = (
                        base_name
                        + "_"
                        + str(metadata["data_index"]).zfill(6)
                        + ".cbf"
                    )
                    _dir = os.path.split(metadata["cbf_filename"])[0]
                    if not os.path.isdir(_dir):
                        os.makedirs(_dir)

                if max_dtype < 32:
                    if data.dtype == numpy.uint32:
                        data = numpy.asarray(data, dtype=numpy.uint16)

                if verbosity > 0:
                    print("Saving: {}".format(metadata["cbf_filename"]))

                cbf = fabio.cbfimage.cbfimage(data=data)
                cbf.write(metadata["cbf_filename"])

                # Needed to change the padding for eiger images.
                if "eiger" in metadata["cbf_filename"]:
                    search_str = b"X-Binary-Size-Padding: 1"
                    replace_str = b"X-Binary-Size-Padding: 2"
                    header = True

                    try:
                        handle = open(metadata["cbf_filename"], mode="r+b")
                        lines = handle.readlines()
                        handle.seek(0)
                        for line in lines:
                            if header:
                                handle.write(
                                    line.replace(search_str, replace_str)
                                )
                            else:
                                handle.write(line)

                            if line == b"\r\n":
                                header = False
                    except Exception as err:
                        if verbosity > 1:
                            print(err)
                    finally:
                        handle.close()

                if not worker:
                    _run = False


###################
# zmq_tiff_writer #
###################

def zmq_tiff_writer(
        host, port, metadata={}, protocol=None, worker=False, max_dtype=32,
        verbosity=0):

    zmqReq = p06io.zeromq.ClientReq(
        host,
        port,
        protocol=protocol,
        verbosity=verbosity
    )

    '''
    Writes a tiff file.

    Parameters
    ----------
    filename : str
        Filename of the tiff file.

    data : ndarray
        Data to be written.

    metadata : dict, optional
        Metadata to include into your tiff file.
    '''

    _run = True

    while _run:
        kwargs = {}

        _return = zmqReq.send_message('next', timeout=1)

        if _return == 1:
            _rcv = zmqReq.receive_numpy_array()
            if _rcv is not None:
                _data, _metadata = _rcv
                if verbosity > 1:
                    print('File metadata: %s' % _metadata)

                if 'tiff_filename' in _metadata:
                    filename = _metadata['tiff_filename']

                else:
                    # if 'eiger' in _metadata['filename']:
                    #     _metadata['file_index_start'] = 1
                    #     _metadata['file_index'] = int(
                    #         _metadata['filename'][-9,-3]
                    #     )

                    # else:
                    #     _metadata['file_index_start'] = 0

                    if _metadata['output_base'] is not None:
                        _tmp = re.compile('/raw|processed/')
                        _baseName = _tmp.sub(
                            '/scratch_bl',
                            _metadata['filename']
                        )
                    else:
                        _baseName = filename

                    _baseName = os.path.splitext(_baseName)[0]

                    _metadata['tiff_filename'] = (
                        _baseName
                        + '_'
                        + str(_metadata['data_index']).zfill(6)
                        + '.tiff'
                    )
                    _dir = os.path.split(_metadata['tiff_filename'])[0]
                    if not os.path.isdir(_dir):
                        os.makedirs(_dir)

                if max_dtype < 32:
                    if _data.dtype == numpy.uint32:
                        _data = numpy.asarray(_data, dtype=numpy.uint16)

                if verbosity > 0:
                    print('Saving: %s' % _metadata['tiff_filename'])

                tifffile.imsave(_metadata['tiff_filename'], _data, **kwargs)

                if not worker:
                    _run = False
