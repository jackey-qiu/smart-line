from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import copy
import multiprocessing
import os
try:
    import queue
except ImportError:
    import Queue as queue
import time

# import inotify as _inotify
import inotify.constants as _constants


###########
# Inotify #
###########

class Inotify():
    """
    Wrapper around the inotify package.
    """

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Wrapper around the inotify package.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity
        self._comm_queue = multiprocessing.Queue()
        self._event_queue = multiprocessing.Queue()
        self._info_pipe, _info_pipe = multiprocessing.Pipe(duplex=True)

        self._inotify_proc = multiprocessing.Process(
            target=self._inotify_process,
            args=(self._comm_queue, self._event_queue, _info_pipe),
            kwargs={
                "verbosity": self.verbosity
            }
        )

        self._inotify_proc.start()

    #############
    # _get_mask #
    #############

    @staticmethod
    def _get_mask(masks):
        """
        Determines the binary mask.

        Parameters
        ----------
        masks : list of str
            The masks.
        """
        int_mask = 0
        mask_dict = {
            'in_close_write': _constants.IN_CLOSE_WRITE,
            'in_close_nowrite': _constants.IN_CLOSE_NOWRITE,
            'in_close': _constants.IN_CLOSE,
            'in_create': _constants.IN_CREATE,
            'in_modify': _constants.IN_MODIFY,
            'in_isdir': _constants.IN_ISDIR,
            'all': _constants.IN_ALL_EVENTS
        }

        for mask in masks:
            if mask in mask_dict:
                int_mask = int_mask | mask_dict[mask]

        return hex(int_mask)

    ####################
    # _inotify_process #
    ####################

    def _inotify_process(
            self, comm_queue, event_queue, info_pipe, timeout=0.01,
            verbosity=0):
        """
        The inotify process.

        Parameters
        ----------
        comm_queue : queue
            The communication queue.

        event_queue : queue
            The event queue.

        info_pipe : pipe
            The pipe used to reply to information polls.

        timeout : float, optional
            The timeout of the epoll to the kernel in seconds

        verbosity : int, optional
            The verbosity level.
        """

        import inotify.adapters as _inotify

        watch_dirs = {}
        updating_dirs = {}

        inotify_kernel = _inotify.Inotify(block_duration_s=timeout)
        update_kernel = _inotify.Inotify(block_duration_s=timeout)

        while True:
            # Comm queue
            comm_msg = None
            if not comm_queue.empty():
                comm_msg = comm_queue.get()

                # Add watch
                if comm_msg[0] == "add_watch":
                    if self.verbosity > 0:
                        print(
                            "Adding '{}' with mask: {}".format(
                                comm_msg[1]["path"],
                                comm_msg[1]["mask"]
                            )
                        )

                    # Only add when not watched yet.
                    if comm_msg[1]["path"] not in watch_dirs:
                        rep = inotify_kernel.add_watch(
                            comm_msg[1]["path"],
                            mask=int(comm_msg[1]["mask"], 16)
                        )

                        if rep > 0:
                            watch_dirs[comm_msg[1]["path"]] = comm_msg[1]

                        # Register for events when updating enabled.
                        if (
                                os.path.isdir(comm_msg[1]["path"])
                                and comm_msg[1]["updating"]):
                            rep = update_kernel.add_watch(
                                comm_msg[1]["path"],
                                mask=int(self._get_mask(["in_create"]), 16)
                            )

                            if rep > 0:
                                updating_dirs[comm_msg[1]["path"]] = (
                                    comm_msg[1]
                                )
                # Remove watch
                elif comm_msg[0] == "remove_watch":
                    if verbosity > 0:
                        print("Removing {}".format(comm_msg[1]["path"]))

                    # Not recursive
                    if not comm_msg[1]["recursive"]:
                        if comm_msg[1]["path"] in watch_dirs:
                            inotify_kernel.remove_watch(comm_msg[1]["path"])
                            del watch_dirs[comm_msg[1]["path"]]

                        if comm_msg[1]["path"] in updating_dirs:
                            update_kernel.remove_watch(comm_msg[1]["path"])
                            del updating_dirs[comm_msg[1]["path"]]

                    # Recursive remove watch
                    else:
                        for path in list(watch_dirs.keys()):
                            if path.startswith(comm_msg[1]["path"]):
                                inotify_kernel.remove_watch(
                                    path
                                )
                                del watch_dirs[path]

                        for path in list(updating_dirs.keys()):
                            if path.startswith(comm_msg[1]["path"]):
                                update_kernel.remove_watch(
                                    path
                                )
                                del updating_dirs[path]

                # Stop process
                elif comm_msg[0] == "stop":
                    break

            # Info pipe
            if info_pipe.poll():
                msg = info_pipe.recv()
                if msg == "get_watch_dirs":
                    info_pipe.send(watch_dirs)

            # inotify events
            events = list(inotify_kernel.event_gen(timeout_s=timeout))
            for event in events:
                if event is not None:
                    event_queue.put(event)

            # update events
            events = list(update_kernel.event_gen(timeout_s=timeout))
            for event in events:
                if event is not None:
                    if (
                            "IN_ISDIR" in event[1]
                            and "IN_CREATE" in event[1]):

                        path = os.path.join(event[2], event[3])
                        payload = copy.deepcopy(watch_dirs[event[2]])
                        payload["path"] = path
                        rep = inotify_kernel.add_watch(
                            path,
                            mask=int(payload["mask"], 16)
                        )

                        if rep > 0:
                            watch_dirs[path] = payload

                        # Register for events when updating enabled.
                        rep = update_kernel.add_watch(
                            path,
                            mask=int(self._get_mask(["in_create"]), 16)
                        )

                        if rep > 0:
                            updating_dirs[path] = payload

        if self.verbosity > 0:
            print("Inotify process stoppped.")

    #############
    # add_watch #
    #############

    def add_watch(
            self, paths, mask=["in_close_write"], recursive=False,
            updating=False):
        """
        Adds a watch to a file or directory.

        paths : str or list of strings
            The path to watch. or list of paths to watch.

        mask : list of str
            List containing the watch mask.

        recursive : boolean, optional
            In case the path is a directory, all subdirectories will be watched
            as well.

        updating : boolean, optional
            When new directories are added to the watch, they will
            automatically be watched as well
        """

        if not isinstance(paths, list):
            paths = [paths]

        payload_default = {
            "mask": self._get_mask(mask),
            "recursive": recursive,
            "updating": updating
        }

        for path in paths:
            if recursive:
                if os.path.isdir(path):
                    walker = os.walk(path)
                    for sub_dir in walker:
                        if os.path.isdir(sub_dir[0]):
                            payload = copy.deepcopy(payload_default)
                            payload["path"] = sub_dir[0]

                            if self.verbosity > 0:
                                print("Payload: {}".format(payload))

                            self._comm_queue.put(
                                [
                                    "add_watch",
                                    payload,
                                ]
                            )

            # Not recursive
            else:
                payload = copy.deepcopy(payload_default)
                payload["path"] = path
                self._comm_queue.put(
                    [
                        "add_watch",
                        payload
                    ]
                )

    ###################
    # event_available #
    ###################

    def event_available(self):
        """
        Determines if an event is available or not.

        Returns
        -------
        boolean
            True when an event is available. False when not.
        """

        return self._event_queue.empty()

    #############
    # get_event #
    #############

    def get_event(self, timeout=1):
        """
        Returns the next event when available.

        Parameters
        ----------
        timeout : float, optional
            The timeout in seconds.

        Returns
        -------
        dict
            The event dict or None upton timeout
        """

        try:
            event = self._event_queue.get(timeout=timeout)
            return {
                "directory": event[2],
                "event_type": event[1],
                "filename": event[3]
            }
        except queue.Empty:
            return None

    ###############
    # get_watches #
    ###############

    def get_watches(self, detailed=False, timeout=5):
        """
        Returns the watches.

        Parameters
        ----------
        detailed : boolean, optional
            Determines if the returned value is a list or a dict.

        Returns
        -------
        list or dict
            A list or a dictionary depending on the detailed kwarg.
        """

        self._info_pipe.send("get_watch_dirs")
        t_start = time.time()
        while True:
            ready = self._info_pipe.poll()
            if ready or time.time() - t_start > timeout:
                break

        if ready:
            watch_dirs = self._info_pipe.recv()
            if detailed:
                return watch_dirs
            else:
                return list(watch_dirs.keys())
        else:
            return None

    ################
    # remove_watch #
    ################

    def remove_watch(self, paths, recursive=True):
        """
        Removes a watch.

        Parameters
        ----------
        paths : str or list of strings
            The path to watch. or list of paths to watch.

        recursive : boolean, optional
            Default is True.
        """

        if not isinstance(paths, list):
            paths = [paths]
        for path in paths:
            payload = {
                "path": path,
                "recursive": recursive
            }

            self._comm_queue.put(
                [
                    "remove_watch",
                    payload
                ]
            )

    ########
    # stop #
    ########

    def stop(self):
        self._comm_queue.put(["stop"])
        self._inotify_proc.join()
