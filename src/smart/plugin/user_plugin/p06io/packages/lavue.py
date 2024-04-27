#! /usr/bin/env python3

__author__ = ["Jan Garrevoet"]


import scipy.ndimage
import numpy

from ..zeromq import ServerPub


#################
# LavueStreamer #
#################

class LavueStreamer(object):
    """
    Class to stream data to lavue.
    """

    ############
    # __init__ #
    ############

    def __init__(self, port=None):
        """
        Class to stream data to lavue.

        Parameters
        ----------
        port : int, optional
        """

        self._publisher = ServerPub(port=port, serialisation="pickle")

    ##############################
    # publish_available_datasets #
    ##############################

    def publish_available_datasets(self, dataset_names):
        """
        Publishes the available datasets.

        Parameters
        ----------
        dataset_names : list
            The dataset names.
        """

        avail_datasets, _ = self._publisher._serialise(
            {"datasources": dataset_names}
        )
        self._publisher._connection.send_multipart(
            [
                b"datasources",
                avail_datasets
            ]
        )

    ####################
    # publish_datasets #
    ####################

    def publish_datasets(
            self, datasets, dataset_names, available_datasets=None,
            exclude_available=False,
            rotation=0):
        """
        Sends the datasets to lavue for visualisation.

        Parameters
        ----------
        datasets : list of numpy.ndarray
            The datasets to publish.

        dataset_names : list of str
            The dataset names.

        available_datasets : list of str, optional
            The available datasets that should be shown in lavue.

        exclude_available : boolean, optional
            Allows one to exclude the available datasets.

        rotation : float, optional
            The angle in degrees to rotate the data.
            Mathematical convention is used.

        Info
        ----
        The available datasets are automatically provided to lavue when sending
         multiple datasets.
        """

        if not exclude_available:
            if available_datasets is None:
                metadata = {"datasources": dataset_names}
            else:
                metadata = {"datasources": available_datasets}

        for index, dataset in enumerate(datasets):
            metadata["dtype"] = dataset.dtype.name
            metadata["shape"] = dataset.shape
            metadata_s, _ = self._publisher._serialise(metadata)

            if rotation != 0:
                dataset = scipy.ndimage.rotate(dataset, rotation)
                metadata["shape"] = dataset.shape

            if not dataset.flags["C_CONTIGUOUS"]:
                dataset = numpy.ascontiguousarray(dataset)

            self._publisher._connection.send_multipart(
                [
                    self._publisher._bytes_encode_check(dataset_names[index]),
                    dataset,
                    metadata_s
                ]
            )

    ########
    # stop #
    ########

    def stop(self):
        if hasattr(self, "_publisher"):
            self._publisher.stop(linger=0.1)
