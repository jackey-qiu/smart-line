try:
    import tango as PyTango
except ImportError:
    import PyTango

from p06io.tango import tango_device


#################
# TangoDatabase #
#################

class TangoDatabase(object):
    """
    Class to handle database related actions.
    """

    ############
    # __init__ #
    ############

    def __init__(self, host=None, port=10000):
        """
        Class to handle database related actions.

        Parameters
        ----------
        host : str, optional
            The database host.

        port : int, optional
            The database port.
        """

        if host is None:
            self._database = PyTango.Database()
        else:
            self._database = PyTango.Database(host, port)

        self.host = self._database.get_db_host()
        self.port = self._database.get_db_port()

    ###################
    # get_server_list #
    ###################

    def get_server_list(self, filter="*"):
        """
        Returns servers matching the filter if set, otherwise all are
         retured.

        Parameters
        ----------
        filter : str, optional
            Wildcard fileter.

        Returns
        -------
        list
            List containing the servers that match the wildcard.
        """

        return list(self._database.get_server_list(filter).value_string)

    ####################################
    # get_devices_from_server_instance #
    ####################################

    def get_devices_from_server_instance(
            self, server_class, server_instance, device_class=None,
            fqdn=False, pqdn=True):
        """
        Returns a list of devices of the given server class and instance.

        Parameters
        ----------
        server_class : str
            The server class.

        server_instance : str
            The server instance.

        device_class : str, optional
            The device class.
            By default the server class is used.

        fqdn : boolean, optional
            Return FQDN style address back.

        qpdn : boolean, optional
            Return PQDN style address back.

        Returns
        -------
        list
            A list containing all the devices of the given server instance and
             device class.
        """

        if device_class is None:
            device_class = server_class

        ret_val = list(
            self._database.get_device_name(
                "{}/{}".format(server_class, server_instance),
                device_class
            ).value_string
        )

        if pqdn and fqdn:
            raise ValueError("FQDN and PQDN are mutually exclusive.")

        if pqdn:
            host = self.host.split(".")[0]
        elif fqdn:
            host = self.host

        if pqdn or fqdn:
            for index, item in enumerate(ret_val):
                ret_val[index] = "{}:{}/{}".format(host, self.port, item)

        return ret_val

    #########################################
    # get_proxy_for_server_instance_devices #
    #########################################

    def get_proxy_for_server_instance_devices(
            self, server_class, server_instance, device_class=None):
        """
        Returns a list of proxies to the devices of the given
         server class and instance.

        Parameters
        ----------
        server_class : str
            The server class.

        server_instance : str
            The server instance.

        device_class : str, optional
            The device class.
            By default the server class is used.
        """

        devices = self.get_devices_from_server_instance(
            server_class, server_instance, device_class=device_class
        )

        proxies = []

        for device in devices:
            proxies.append(
                tango_device(device)
            )

        return proxies
