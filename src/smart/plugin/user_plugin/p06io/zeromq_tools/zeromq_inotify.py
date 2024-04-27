from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os

try:
    import Queue as queue
except ImportError:
    import queue    # noqa F401
import socket

import threading

import p06io
import p06io.inotify_handler


##############
# ZmqInotify #
##############

class ZmqInotify(threading.Thread):
    '''
    An inotify service that sends out ZMQ messages.
    '''

    ############
    # __init__ #
    ############

    def __init__(self, host, port, verbosity=0, exclusions=None):
        '''
        An inotify service that sends out ZMQ messages.

        Parameters
        ----------
        host : str
            The host name where to send the messages to.

        port : int
            The port number of the host.

        verbosity : int, optional
            The verbosity level of the service.

        exclusions : list of strings, optional
            A list that contains the exclusiongs.
            By default the following exclusions are applied:
            ['.*.swp','.*.swx']

        '''

        self.verbosity = verbosity
        self._excluded_files = ['.*.swp', '.*.swx']

        self._zmq_client = (
            p06io.zeromq.ClientPush(
                host,
                port
            )
        )

        super(ZmqInotify, self).__init__()

        self._stop_event = threading.Event()
        self.inotify_host = socket.getfqdn()
        self._inotify = p06io.inotify_handler.Inotify(verbosity=0)

        self._zmq_thread = threading.Thread(target=self._zmq_thread)
        self._zmq_thread.start()

    ###########
    # __del__ #
    ###########

    def __del__(self):
        if self.verbosity > 0:
            print('Stopping threads')

        self.stop()

        if self.verbosity > 0:
            print('Closing')

    ############
    # _stopped #
    ############

    def _stopped(self):
        '''
        Return stopped status.
        '''

        return self._stop_event.is_set()

    ###############
    # _zmq_thread #
    ###############

    def _zmq_thread(self):
        if self.verbosity > 0:
            print('Starting zmq process')
        while not self._stopped():
            try:
                event = self._inotify.get_event(timeout=0.1)
                if event is not None:
                    if self.verbosity > 0:
                        print(
                            'maskname: {} | path: {}'.format(
                                event["event_type"],
                                os.path.join(
                                    event["directory"],
                                    event["filename"]
                                )
                            )
                        )

                    topic, message = self.process_event(event)

                    self._zmq_client.send_message([topic, message])
            except Exception as err:
                print(err)

        if self.verbosity > 0:
            print('ZMQ thread stopped.')

    #######################
    # add_watch_directory #
    #######################

    def add_watch_directory(
            self, directory, mask=["in_close_write"], recursive=False,
            updating=False):
        '''
        Adds a directory to the watch list.

        Parameters
        ----------
        directory : str
            The path of the directory to watch.

        mask : str, optional
            The event type to report on.

        recursive : boolean, optional
            In case the path is a directory, all subdirectories will be watched
            as well.

        updating : boolean, optional
            When new directories are added to the watch, they will
            automatically be watched as well
        '''

        path = os.path.abspath(os.path.expanduser(directory))

        self._inotify.add_watch(
            path, mask=mask, recursive=recursive, updating=updating
        )

        if self.verbosity > 0:
            print(
                'Added {} with {} mask.'.format(
                    path,
                    mask
                )
            )

    ###########################
    # get_watched_directories #
    ###########################

    def get_watched_directories(self):
        '''
        Returns the watch directories.

        Returns
        -------
        list
            List containing the watched directories.
        '''

        return self._inotify.get_watches()

    #################
    # process_event #
    #################

    def process_event(self, event):
        topic = 'new_file'
        message = {'file': {}}
        message['file']['filename'] = os.path.join(
            event["directory"],
            event["filename"]
        )
        message['file']['source'] = self.inotify_host
        return topic, message

    ##########################
    # remove_watch_directory #
    ##########################

    def remove_watch_directory(self, directory, recursive=True):
        '''
        Removes a directory from the watch list.

        Parameters
        ----------
        directory : str
            The path of the directory to remove.
        '''
        directory = os.path.abspath(os.path.expanduser(directory))

        self._inotify.remove_watch(directory, recursive=recursive)

    ########
    # stop #
    ########

    def stop(self):
        '''
        Stops the service.
        '''

        self._stop_event.set()
        self._inotify.stop()
        self._zmq_client.stop()
        self._zmq_thread.join(timeout=5)
