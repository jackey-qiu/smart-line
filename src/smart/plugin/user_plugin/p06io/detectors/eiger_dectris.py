from io import BytesIO
import requests
import re
import socket

import tifffile


################
# EigerMonitor #
################

class EigerMonitor(object):
    """
    Provides an interface to monitor the eiger images during acquisition.
    """

    ############
    # __init__ #
    ############

    def __init__(self, hostname, api_version="1.6.0"):
        """
        Provides an interface to monitor the eiger images during acquisition.

        Parameters
        ----------
        hostname : str
            The host name of the detector.

        api_version : str, optional
            The api version.
        """

        self._host_ip = socket.gethostbyname(hostname)
        self._api_version = api_version
        self._session = requests.Session()

    ##################
    # _construct_url #
    ##################

    def _construct_url(self, req_class, api_request):
        """
        Constructs the request url.

        Parameters
        ----------
        req_class : str
            The request class

        api_request : str
            The request.

        Returns
        -------
        str
            The request url.
        """

        return (
            "http://{}/{}/api/{}/{}".format(
                self._host_ip,
                req_class,
                self._api_version,
                api_request
            )
        )

    ############
    # _request #
    ############

    def _request(self, url, raw=False):
        """
        Does the communication with the detector.

        Parameters
        ----------
        url : str
            The request url.

        raw : boolean, optional
            Determines if the request already does some filtering on the reply.
            Default is False.

        Returns
        -------
        object
            The request object.
        """

        reply = self._session.get(url)

        if reply.status_code == 200:
            return reply
        elif reply.status_code == 400:
            raise IOError("No reply from the detector.")
        elif reply.status_code == 408:
            return None

        return reply

    #####################
    # get_exposure_time #
    #####################

    def get_exposure_time(self):
        """
        Gets the exposure time currently set to the detector.

        Returns
        -------
        float
            The exposure time in seconds.
        """

        url = self._construct_url("detector", "config/count_time")
        reply = self._request(url)

        if reply is not None:
            data = eval(reply.content)
            return data["value"]
        else:
            return reply

    #############
    # get_image #
    #############

    def get_image(self, remove_gaps=True):
        """
        Tries to get an image from the monitor buffer.

        Parameters
        ----------
        remove_gaps : boolean, optional
            Determines if the values of the gaps are set to zero.
            Default is True.

        Returns
        -------
        numpy.ndarray
            The image as a numpy array or None when no image is available.

        Raises
        ------
        IOError
            When the detector does not reply.
        """

        url = self._construct_url("monitor", "images/monitor")
        reply = self._request(url)
        if reply is not None:

            img = tifffile.imread(BytesIO(reply.content))

            if remove_gaps:
                dtype = int(
                    re.match(
                        r"([a-z]+)([0-9]+)", str(img.dtype)
                    ).groups()[-1]
                )

                img[img == 2**dtype - 1] = 0

            return img

        else:
            return None
