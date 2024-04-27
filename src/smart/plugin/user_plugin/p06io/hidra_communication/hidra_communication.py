#!/usr/bin/env python

__author__ = ["Jan Garrevoet"]

import ast
import multiprocessing
import os
import re
import socket
import subprocess
import time

from hidra import Transfer

import p06io


################
# HidraControl #
################

class HidraControl(object):
    def __init__(self, beamline=None, detector=None, verbosity=0):
        """
        Class to control hidra.

        Parameters
        ----------
        beamline : str, optional
            The beamline identifier.

        detector : str, optional
            The detector host name.

        verbosity : int, optional
            Verbosity level.
        """

        self._beamline = beamline
        self._detector = detector
        self.verbosity = verbosity

        self._HIDRAPATH = (
            "/opt/hidra/src/hidra/hidra_control/client.py"
        )

    ###############
    # _call_hidra #
    ###############

    def _call_hidra(self, cmd):
        """
        Method to communicate with hidra.

        Parameters
        ----------
        cmd : list
            A list containing the command to execute.

        Returns
        -------
        tuple
            Tuple of stdout and stderr.
        """

        cmd = [
            "python3",
            self._HIDRAPATH,
            "--det",
            self._detector,
            "--beamline",
            self._beamline
        ] + cmd

        sp = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        reply = sp.communicate()

        if self.verbosity > 3:
            print("Hidra Call Reply: {}".format(reply))

        ret_val = []

        for item in reply:
            if isinstance(item, bytes):
                ret_val.append(item.decode("utf-8"))
            else:
                ret_val.append(item)

        return ret_val

    #########################
    # _cast_to_correct_type #
    #########################

    def _cast_to_correct_type(self, string):
        """
        Casts the provided string to the correct type.

        Parameters
        ----------
        string : str
            The string that needs to be casted.

        Returns
        -------
        any
            The string casted to the correct type.
        """

        if "[" in string or "]" in string:
            string = string.lstrip()
            string = ast.literal_eval(string)

        return string

    ##########
    # _clean #
    ##########

    def _clean(self, param):
        """
        Cleaning ang process parameter.

        Parameters
        ----------
        param : str
            The parameter to clean.

        Returns
        -------
        any
            The cleaned and correctly casted parameter.
        """

        param = self._cast_to_correct_type(param)
        param = self._clean_str(param)

        return param

    ################
    # _clean_reply #
    ################

    def _clean_reply(self, reply):
        """
        Cleans the reply from hidra to the status word.

        Parameters
        ----------
        reply : str
            The reply string from hidra.

        Returns
        -------
        str
            The status word of hidra.
        """

        reply = reply.split(":")[1].lstrip()
        reply = re.sub("\n", "", reply)
        # reply = re.sub("\\", "", reply)

        return reply

    ##############
    # _clean_str #
    ##############

    def _clean_str(self, string):
        """
        Removes unwanted characters from a string.

        Parameters
        ----------
        string : str
            The string which needs to be cleaned.

        Returns
        -------
        str
            The cleaned string.
        """

        if not isinstance(string, list):
            string = string.lstrip()
            string = string.rstrip()
            string = re.sub(" ", "_", string)

        return string

    ##################
    # _change_status #
    ##################

    def _change_status(self, cmd):
        """
        Executes the command to change the state and evaluates it.

        Parameters
        ----------
        cmd : list
            List of the command to execute.

        Returns
        -------
        int
            Returns 1 on success.

        Raises
        ------
        ValueError
            When the status message can not be evaluated.

        IOError
            When communication with hidra fails.
        """

        status = self._call_hidra(cmd)

        if status[1] is None:
            status = self._clean_reply(status[0])

            if status == "DONE":
                return 1
            elif status == "ALREADY_RUNNING":
                return 1
            elif status == "ALREADY_STOPPED":
                return 1
            else:
                raise ValueError(
                    "Unknown hidra status message: {}".format(
                        status
                    )
                )
        else:
            raise IOError("Unable to start hidra: {}".format(status[0]))

    ################
    # get_detector #
    ################

    def get_detector(self):
        """
        Returns the set detector.

        Returns
        -------
        str
            The detector host name.
        """

        return self._detector

    ################
    # get_settings #
    ################

    def get_settings(self):
        """
        Returns the settings with which hidra is running.

        Returns
        -------
        dict
            Dictionary containing the settings from hidra.
        """

        settings = {}

        cmd = ["--getsettings"]

        _settings = self._call_hidra(cmd)

        if self.verbosity > 1:
            print("Raw settings: {}".format(_settings))

        # No exception occurred.
        if _settings[1] is None:
            _settings = _settings[0].split("\n")

            for i in range(len(_settings)):
                tmp = _settings[i].split(":")
                if self.verbosity > 2:
                    print("Processing: {}".format(tmp))

                if tmp[0] == "Configured settings":
                    pass
                elif len(tmp) == 2:
                    settings[self._clean(tmp[0])] = self._clean(tmp[1])

                elif len(tmp) == 3:
                    settings[self._clean(tmp[0])] = (
                        self._clean(tmp[1])
                        + ":"
                        + self._clean(tmp[2])
                    )
        else:
            raise IOError("Unable to communicate with hidra.")

        return settings

    ##############
    # get_status #
    ##############

    def get_status(self):
        """
        Returns the status of hidra.

        Returns
        -------
        int
            -1 == Fault
            0 == Stopped
            1 == Running
        """

        cmd = ["--status"]

        _status = self._call_hidra(cmd)

        if _status[1] is None:
            _status = self._clean_reply(_status[0])

            if self.verbosity > 0:
                print("Evaluating: {}".format(_status))

            if _status == "RUNNING":
                status = 1
            elif _status == "NOT_RUNNING":
                status = 0
            elif _status == "ERROR":
                status = -1
            else:
                status = -1
        else:
            raise IOError("Unable to communicate with hidra.")

        return status

    ################
    # set_beamline #
    ################

    def set_beamline(self, beamline):
        """
        Sets the beamline.

        Parameters
        ----------
        beamline : str
            The beamline identifier.
        """

        self._beamline = beamline

    ################
    # set_detector #
    ################

    def set_detector(self, detector):
        """
        Sets the detector.

        Parameters
        ----------
        detector : str
            The detector host name.
        """

        self._detector = detector

    #########
    # start #
    #########

    def start(self, api=None):
        """
        Start the hidra instance using the set detector and beamline.

        Parameters
        ----------
        api : str, optional
            The API version of the detector when applicable.

        Returns
        -------

        """
        cmd = []

        if api is not None:
            cmd.append("--detapi")
            cmd.append(api)

        cmd.append("--start")

        retVal = self._change_status(cmd)

        return retVal

    ########
    # stop #
    ########

    def stop(self):
        """
        Stops the hidra instance for the set detector and beamline.

        Returns
        -------
        """

        cmd = ["--stop"]

        retVal = self._change_status(cmd)

        return retVal


#################
# HidraReceiver #
#################

class HidraReceiver(object):

    ############
    # __init__ #
    ############

    def __init__(
            self,
            detector=None,
            hidra_host="asap3-p06.desy.de",
            port=50001,
            priority=2,
            detector_type="eiger",
            hidra_query="STREAM_METADATA",
            queue=None,
            verbosity=0):
        """
        Class that wraps the hidra transfer api to collect data via hidra.

        Parameters
        ----------
        detector : str, optional
            The detector of which to receive events.
            The detector shall only be used in the case of an Eiger.

        hidra_host : str, optional
            Host that runs hidra.
            In the case of eiger this is the proxy node (default).
            In the case of the pilatus it is the pilatus server.

        port : int, optional
            Port on which the communication should run.
            Default is 50001.

        priority : int, optional
            Priority on which you should get the data.
            Default is 2.

        detector_type : str, optional
            Determines which detector is being used.
            Default is eiger.

        hidra_query : str, optional
            Default is STREAM_METADATA.
            STREAM: A data stream is opened from which the metadata
                    and data of every file must be received
            STREAM_METADATA: A metadata stream is opened from which the
                    metadata only of every file must be received
            QUERY_NEXT: A query connection is opened from which data
                    and metadata is send after querying for it
            QUERY_METADATA: A query connection is opened from which metadata
                    only is send after querying for it

        queue : object
            A queue can be provided to which the queried data needs to be added
            instead of returning it.

        verbosity : int, optional
            Verbose level.
            Default is 0.
        """

        self.verbosity = verbosity
        self.detector_type = detector_type
        self.hidra_query = hidra_query.upper()
        self.queue = queue

        if detector_type == "pilatus" and hidra_query == "STREAM_METADATA":
            raise ValueError(
                "Use QUERY_NEXT as a hidra_query for the pilatus."
            )

        self._connect_hidra(hidra_host, detector, port, priority)

        if self.verbosity > 0:
            print("Hidra worker started.")

    ##################
    # _connect_hidra #
    ##################

    def _connect_hidra(self, host, detector, port, priority):
        """
        Connect to hidra.

        Parameters
        ----------
        host : str
            The host.

        detector : str
            The detector to get the events from.
        """

        target = [
            [
                socket.getfqdn(),
                port,
                priority
            ]
        ]

        if self.verbosity > 1:
            print(
                "Using the following port settings : {}".format(
                    target
                )
            )

        self._hidra = Transfer(
            self.hidra_query,
            signal_host=host,
            detector_id=detector,
            use_log="warning")

        self._hidra.initiate(target)
        self._hidra.start()

        self._hidra_conection_details = {
            "detector": detector,
            "host": host,
            "port": port,
            "priority": priority
        }

    ########
    # _get #
    ########

    def _get(self, timeout=1):
        """
        Low level get next from hidra.

        Parameters
        ----------
        timeout : float
            Timeout in seconds.
        """

        # Internal hidra timeout is in milliseconds.
        _timeout = timeout * 1e3

        return self._hidra.get(_timeout)

    #################
    # _get_filename #
    #################

    def _get_filename(self, metadata):
        """
        Constructs the scan filename.

        Parameters
        ----------
        metadata : dict
            The hidra metadata.

        Returns
        -------
        str
            String containing the patch to the file.
        """

        filename = os.path.join(
            "/gpfs",
            metadata["relative_path"],
            metadata["filename"]
        )

        return filename

    ####################
    # _reconnect_hidra #
    ####################

    def _reconnect_hidra(self):
        """
        Reconnect to the hidra instance.
        """

        self.stop()
        self._connect_hidra(
            self._hidra_conection_details["host"],
            self._hidra_conection_details["detector"],
            self._hidra_conection_details["port"],
            self._hidra_conection_details["priority"],
        )

    ############
    # get_data #
    ############

    def get_data(self, timeout=None):
        """
        """

        _tmp = self.get_raw(passQueue=True)

        if self.queue is None:
            return _tmp
        else:
            self.queue.put(_tmp)

    ################
    # get_filename #
    ################

    def get_filename(self, timeout=1):
        """
        Returns the filename as an absolute path.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds.

        Returns
        -------
        str
            The filename as an absolute path.
        """

        metadata = self.get_raw(
            passQueue=True,
            timeout=timeout
        )[0]
        if self.verbosity > 2:
            print("Raw message from hidra: {}".format(metadata))

        if metadata is not None:
            if self.detector_type in ["eiger", "pilatus"]:
                filename = self._get_filename(metadata)

                if self.queue is None:
                    return filename
                else:
                    self.queue.put(filename)

            else:
                if self.queue is None:
                    return metadata
                else:
                    self.queue.put(metadata)

    ################
    # get_metadata #
    ################

    def get_metadata(self, filtered=True, timeout=1):
        """
        Returns the metadata provided my hidra.


        Parameters
        ----------
        filtered : boolean, optional
            Filters the output to only include the useful things.
            Default is True.

        timeout : float, optional
            Timeout in seconds.

        Returns
        -------
        dict
            Metadata dictionary

        """

        _payload = self.get_raw(passQueue=True, timeout=timeout)[0]
        if _payload is not None:
            payload = {}
            _filename = self._get_filename(_payload)

            if filtered:
                payload = {}
                payload["file_create_time"] = _payload["file_create_time"]
                payload["filename"] = _filename
                payload["relative_path"] = _payload["relative_path"]

            else:
                payload = _payload

            if self.queue is None:
                return payload
            else:
                self.queue.put(payload)

        # Timeout return
        else:
            return None

    ###########
    # get_raw #
    ###########

    def get_raw(self, timeout=1, passQueue=False):
        """
        Returns what hidra returns.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds.
            Default, wait forever.

        passQueue : boolean, optional
            Determines if the queue gets bypassed, thus returning the raw data
            instead of adding it to the queue if one is provided.
        """

        _payload = self._get(timeout)

        if self.queue is None or passQueue is True:
            return _payload
        else:
            # Cope with timeout return
            if _payload is not None:
                self.queue.put(_payload)

    ########
    # stop #
    ########

    def stop(self):
        """
        Stops the hidra stream.
        """

        self._hidra.stop()


####################
# hicra_pub_server #
####################

class hidra_pub_server():

    ############
    # __init__ #
    ############

    def __init__(
            self,
            pub_port,
            mode="metadata",
            hwm=None,
            hidra_host=None,
            hidra_port=None,
            hidra_priority=None,
            req_host=None,
            req_port=None,
            verbosity=0):
        """
        A worker that collects hidra events and publishes them via zmq.

        Parameters
        ----------
        pub_port : int
            Port on which the pub socket runs.

        mode : str
            Mode of operation which determines which data is provided.
            Default is metadata.
            metadata: Only publishes the metadata.

        hwm : int
            High water mark.

        hidra_host : str, optional
            Host that runs hidra.

        hidra_port : int, optional
            Port hidra will reply on.

        hidra_priority : int, optional
            Priority on which you should get the data.
            Default is 2.

        req_host : str
            Host to connect the req port to, to obtain the scan
            metadata.

        req_port : int
            Port to connect the req port to, to obtain the scan
            metadata.

        verbosity : int
            Verbose level.

        needs to include:
        + a port for req rep
        + hidra setup

        """

        # FIXME
        # main thread should have the heart beat implemented
        # should check the state of the other processes.

        self.pub_port = pub_port
        self.hwm = hwm
        self.hidra_host = hidra_host
        self.hidra_port = hidra_port
        self.hidra_priority = hidra_priority
        self.req_host = req_host
        self.req_port = req_port
        self.verbosity = verbosity

        self.queue = multiprocessing.Queue()
        self.manager = multiprocessing.Manager()
        self.namespace = self.manager.Namespace()

        self.namespace.run = True
        self._terminate = multiprocessing.Event()

        if mode == "metadata":
            self.hidra_query = "STREAM_METADATA"

    #######
    # run #
    #######

    def run(self):

        try:
            pubProcess = multiprocessing.Process(
                target=self.pub_process,
                args=(
                    self.queue,
                    self.pub_port,
                    self.hwm,
                    self.req_host,
                    self.req_port,
                    self._terminate,
                    self.verbosity
                )
            )

            pubProcess.start()

            hidraProcess = multiprocessing.Process(
                target=self.hidra_process,
                args=(
                    self.queue,
                    self.hidra_host,
                    self.hidra_port,
                    self.hidra_priority,
                    self.hidra_query,
                    self._terminate,
                    self.verbosity
                )
            )

            hidraProcess.start()

        except Exception as err:
            self._terminate.set()
            print(err)

    ########
    # stop #
    ########

    def stop(self):
        self._terminate.set()

    ###########
    # __del__ #
    ###########

    def __del__(self):
        self.stop()

    ############
    # __exit__ #
    ############

    def __exit__(self):
        self.stop()

    ###############
    # pub_process #
    ###############

    def pub_process(
            self,
            queue,
            port,
            hwm,
            req_host,
            req_port,
            terminate,
            verbosity):
        zmqServer = (
            p06io.zeromq.ServerPub(
                port=port,
                hwm=hwm,
                verbosity=verbosity
            )
        )

        try:
            while not terminate.is_set():
                if not queue.empty():
                    # Get new data from queue
                    _payload = queue.get()

                    if verbosity > 3:
                        print("Payload: {}".format(_payload))

                    # Get scan metadata
                    _filename = os.path.basename(_payload["filename"])

                    if verbosity > 0:
                        print("Last : {}".format(_filename))

                    zmqServer.send_message(_payload)
                else:
                    time.sleep(0.1)

        except Exception as err:
            if verbosity > 0:
                print(err)
            terminate.set()

        finally:
            if verbosity > 0:
                print("Stopping zmq pub socket.")
            zmqServer.stop()
            # reqClient.stop()

    #################
    # hidra_process #
    #################

    def hidra_process(
            self,
            queue,
            hidra_host,
            hidra_port,
            hidra_priority,
            hidra_query,
            terminate,
            verbosity):
        kwargs = {}

        if hidra_host is not None:
            kwargs["hidraHost"] = hidra_host
        if hidra_port is not None:
            kwargs["port"] = hidra_port
        if hidra_priority is not None:
            kwargs["priority"] = hidra_priority

        kwargs["queue"] = queue
        kwargs["verbosity"] = verbosity

        hidra = p06io.hidra_communication.HidraReceiver(**kwargs)

        try:
            while not terminate.is_set():
                hidra.get_metadata(timeout=1)
                # hidra.get_filename(timeout = 1)

        except Exception as err:
            if verbosity > 0:
                print(err)

        finally:
            if verbosity > 0:
                print("Stopping hidra.")
            hidra.stop()
            terminate.set()
