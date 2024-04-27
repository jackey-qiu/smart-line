import datetime
import logging
import logging.handlers
import threading
import zmq.log.handlers

import p06io


#############
# ZmqLogger #
#############

class ZmqLogger(object):
    """
    ZMQ enabled logger.
    """

    ############
    # __init__ #
    ############

    def __init__(self, host, port, logger_name, verbosity=0):
        """
        A ZMQ based logger, sending the log messages to a central location.

        Parameters
        ----------
        host : str
            The host name of the log writer.

        port : int
            The port number of the log writer.

        logger_name : str
            The name to give the logging instance.
            This name will be the identifier used in the log file.

        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity

        self._sender = p06io.zeromq.ClientPub(host, port)
        self._handler = zmq.log.handlers.PUBHandler(
            self._sender._connection
        )
        self._logger = logging.getLogger(logger_name)
        self.set_logger_name(logger_name)
        self._logger.addHandler(self._handler)

    #####################
    # _create_log_entry #
    #####################

    def _create_log_entry(self, msg, level, exc_info):
        """
        Creates the log entry.

        Parameters
        ----------
        msg : str
            The message to log.

        level : int
            The logging level.

        exc_info : boolean
            Determines if the exception error is appended or not.
        """
        _time = datetime.datetime.astimezone(datetime.datetime.now())
        payload = {
            "msg": msg,
            "time": _time.strftime(
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
        }

        self._logger.log(
            level,
            payload,
            exc_info=exc_info
        )

    ############
    # critical #
    ############

    def critical(self, msg, error=False):
        """
        Logs a critical log message.

        Parameters
        ----------
        msg : str
            The message to log.

        error : boolean, optional
            Default is False.
            When enabled the information from  sys.exc_info() is added.
        """

        self._create_log_entry(msg, logging.CRITICAL, exc_info=error)

    #########
    # debug #
    #########

    def debug(self, msg, error=False):
        """
        Logs a debug log message.

        Parameters
        ----------
        msg : str
            The message to log.

        error : boolean, optional
            Default is False.
            When enabled the information from  sys.exc_info() is added.
        """

        self._create_log_entry(msg, logging.DEBUG, exc_info=error)

    #########
    # error #
    #########

    def error(self, msg, error=True):
        """
        Logs an error log message.

        Parameters
        ----------
        msg : str
            The message to log.

        error : boolean, optional
            Default is True.
            When enabled the information from  sys.exc_info() is added.
        """

        self._create_log_entry(msg, logging.ERROR, exc_info=error)

    ########
    # info #
    ########

    def info(self, msg, error=False):
        """
        Logs an info log message.

        Parameters
        ----------
        msg : str
            The message to log.

        error : boolean, optional
            Default is False.
            When enabled the information from  sys.exc_info() is added.
        """

        self._create_log_entry(msg, logging.INFO, exc_info=error)

    ###################
    # set_logger_name #
    ###################

    def set_logger_name(self, name):
        """
        Sets the logger name.

        Parameters
        ----------
        name : string
            The name for the logging instance.
        """

        self._handler.root_topic = name

    #####################
    # set_logging_level #
    #####################

    def set_logging_level(self, level):
        """
        Sets the logging level.

        Parameters
        ----------
        level : str
            The logging level.
        """

        LOG_LEVELS = {
            "CRITICAL": logging.CRITICAL,
            "DEBUG": logging.DEBUG,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING
        }

        if level.upper() in LOG_LEVELS:
            self._logger.setLevel(LOG_LEVELS[level.upper()])
        else:
            raise ValueError(
                "Only the following logging levels are supported: {}".format(
                    LOG_LEVELS.keys()
                )
            )

    ########
    # stop #
    ########

    def stop(self, linger=0.1):
        """
        Stops the logger.

        Parameters
        ----------
        linger : float, optional
            The time, in seconds, to linger before the ZMQ socket is closed
             when messages are still in the queue.
        """

        self._handler.close()
        self._sender.stop(linger=linger)

    ###########
    # warning #
    ###########

    def warning(self, msg, error=False):
        """
        Logs a warning log message.

        Parameters
        ----------
        msg : str
            The message to log.

        error : boolean, optional
            Default is False.
            When enabled the information from  sys.exc_info() is added.
        """

        self._create_log_entry(msg, logging.WARNING, exc_info=error)


################
# ZmqLogWriter #
################

class ZmqLogWriter(threading.Thread):
    """
    Zmq enabled log writer.
    """

    ############
    # __init__ #
    ############

    def __init__(
            self, output_file, port=None, nb_backup_files=31,
            roll_over="midnight", interval=1, verbosity=0):
        """
        A log writer that receives the log messages via ZMQ.

        Parameters
        ----------
        output_file : str
            The log file path.

        port : int, optional
            The port.

        nb_backup_files : int, optional
            The number of backup files to keep after rolling over.
            Default is 31.

        roll_over : str, optional
            Default is at midnight.

        interval : float, optional
            The roll_over is determined by the product of roll_over and
             interval.
            Default is 1.

        verbosity : int, optional
            The verbosity level
        """

        super(ZmqLogWriter, self).__init__()
        self.verbosity = verbosity
        self._LOG_LEVELS = {
            "CRITICAL": logging.CRITICAL,
            "DEBUG": logging.DEBUG,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING
        }

        self._receiver = p06io.zeromq.ServerSub(port=port)
        self._logger = logging.getLogger()
        filehandler = logging.handlers.TimedRotatingFileHandler(
            output_file,
            when=roll_over,
            interval=interval,
            backupCount=nb_backup_files
        )
        self._logger.addHandler(filehandler)
        self._logger.setLevel(logging.DEBUG)
        self._event = threading.Event()
        self._event.set()

        self.logging_thread = threading.Thread(target=self._logging_thread)
        self.logging_thread.start()

    ##################
    # _get_log_level #
    ##################

    def _get_log_level(self, msg):
        """
        Returns the logger level from the log message.

        Parameters
        ----------
        msg : str
            The log message.

        Returns
        -------
        str
            The log level.
        """

        return msg[0].split(".")[-1]

    ###############
    # _get_source #
    ###############

    def _get_source(self, msg):
        """
        Get the log message source.

        Parameters
        ----------
        msg : str
            The log message.

        Returns
        -------
        str
            The log message source.
        """

        return ".".join(msg[0].split(".")[:-1])

    ################
    # _log_message #
    ################

    def _log_message(self, msg):
        """
        Logs the log message.

        Parameters
        ----------
        msg : str
            The log message.
        """

        try:
            level = self._get_log_level(msg)
            source = self._get_source(msg)

            log_msg = (
                "{}:{}:{}".format(
                    level,
                    source,
                    msg[1]
                )
            )

            self._logger.log(
                self._LOG_LEVELS[level],
                log_msg
            )
        except Exception as err:
            log_msg = (
                "ERROR:log_writer:Unable to log received message:{}".format(
                    err
                )
            )

            self._logger.log(
                self._LOG_LEVELS["ERROR"],
                log_msg
            )

    ####################
    # _log_new_message #
    ####################

    def _log_new_message(self, timeout):
        """
        Logs a new incoming message.

        Parameters
        ----------
        timeout : float, optional
            The timeout in seconds.
        """

        msg = self._receive_message(timeout)
        if self.verbosity > 0 and msg is not None:
            print("Received log msg: {}".format(msg))

        if msg is None:
            if self.verbosity > 1:
                print("Timeout")
        else:
            if isinstance(msg, list):
                for index, item in enumerate(msg):
                    if isinstance(item, bytes):
                        msg[index] = item.decode("utf-8")

            if self.verbosity > 0 and msg is not None:
                print("Received log msg: {}".format(msg))

            # This condition to filter out the announce message.
            if msg[0] == "":
                if self.verbosity > 0:
                    print("New client connected.")
            else:
                self._log_message(msg)

    ###################
    # _logging_thread #
    ###################

    def _logging_thread(self):
        """
        The logging thread.
        """

        while self._event.is_set():
            self.log_message(timeout=0.2)

    ####################
    # _receive_message #
    ####################

    def _receive_message(self, timeout):
        """
        Receives the logging message.

        Parameters
        ----------
        timeout : float, optional
            The timeout in seconds.
        """

        if self._receiver.check_incoming(timeout=timeout):
            return self._receiver._connection.recv_multipart()
        else:
            return None

    ###############
    # log_message #
    ###############

    def log_message(self, timeout=None):
        """
        Logs a new incoming message.

        Parameters
        ----------
        timeout : float, optional
            The timeout in seconds.
        """

        self._log_new_message(timeout)

    ##########################
    # get_connection_details #
    ##########################

    def get_connection_details(self):
        """
        Get the connection details of the log writer.

        Returns
        -------
        list
            Containing the protocol, host, and port.
        """

        return self._receiver.get_connection_details()

    ########
    # stop #
    ########

    def stop(self):
        """
        Stops the log writer.
        """

        self._event.clear()
        self.logging_thread.join()
        self._receiver.stop(linger=0.1)
