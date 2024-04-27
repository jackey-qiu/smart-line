import pyads


#########################
# BeckhoffCommunication #
#########################

class BeckhoffCommunication(object):
    """
    Class to communicate with Beckhoff devices.
    """

    ############
    # __init__ #
    ############

    def __init__(
            self, plc_ip=None, plc_port=None, plc_ams_net_id=None,
            verbosity=0):
        """
        Class to communicate with a Beckhoff device.

        Parameters
        ----------
        plc_ip : str, optional
            The IP address of the PLC.

        plc_port : int, optional
            The port on which the ADS server is running.

        plc_ams_net_id : str, optional
            The PLC AMS net ID.

        verbosity : int, optional
            The verbosity level.
        """

        # Made PLC data types available.
        for item in vars(pyads.constants).items():
            if item[0].startswith("PLCTYPE_"):
                exec("self.{} = item[1]".format(item[0]))

        self._variable_handles = {}
        self.verbosity = verbosity

        # Create the connection to the PLC.
        if (
                plc_ip is not None
                and plc_port is not None
                and plc_ams_net_id is not None):
            self.connect_to_plc(plc_ip, plc_port, plc_ams_net_id)

    ########################
    # _get_variable_handle #
    ########################

    def _get_variable_handle(self, variable):
        """
        Gets a variable handle for faster access.

        Parameters
        ----------
        variable : str
            The variable name.

        Returns
        -------
        int
            The PLC variable handle.
        """

        return self._connection.get_handle(variable)

    #################
    # _search_cache #
    #################

    def _search_cache(self, variable, handle, data_type, auto_cache=True):
        """
        Gets the handle to use for a faster call and the data_type.

        Parameters
        ----------
        variable : str
            The variable name.

        handle : str
            The provided handle.

        Returns
        -------
        handle
            The variable handle.

        data_type
            The PLC data type.
        """

        if auto_cache and variable not in self._variable_handles:
            self.create_variable_handle(variable, data_type)

        if variable in self._variable_handles:
            if handle is None:
                handle = self._variable_handles[variable]["handle"]
            if data_type is None:
                data_type = self._variable_handles[variable]["dtype"]

        return handle, data_type

    ##################
    # connect_to_plc #
    ##################

    def connect_to_plc(self, plc_ip, plc_port, plc_ams_net_id):
        """
        Creates a connection to the PLC.

        Parameters
        ----------
        plc_ip : str, optional
            The IP address of the PLC.

        plc_port : int, optional
            The port on which the ADS server is running.

        plc_ams_net_id : str, optional
            The PLC AMS net ID.
        """

        self._connection = pyads.Connection(
            plc_ams_net_id,
            plc_port,
            plc_ip
        )

        self._connection.open()

    ###############################
    # create_all_variable_handles #
    ###############################

    def create_all_variable_handles(self, variables, data_types):
        """
        Create all variable handles.

        Parameters
        ----------
        variables : list of str
            List of variable names.

        data_types : list of PLCTYPE
            The PLC metadata types.
        """

        for index, variable in enumerate(variables):
            self.create_variable_handle(variable, data_types[index])

    ##########################
    # create_variable_handle #
    ##########################

    def create_variable_handle(self, variable, data_type):
        """
        Adds variable handle to the local database.

        Parameters
        ----------
        variable : str
            The variable name.

        data_type : PLCTYPE
            The PLC metadata type.
        """

        if variable not in self._variable_handles:
            self._variable_handles[variable] = {}

        self._variable_handles[variable]["handle"] = (
            self._get_variable_handle(variable)
        )

        self._variable_handles[variable]["dtype"] = data_type

    #################
    # read_variable #
    #################

    def read_variable(self, variable, data_type=None, handle=None, cast=True):
        """
        Reads a variable.

        Parameters
        ----------
        variable : str
            The name of the variable.

        data_type : ctype, optional
            The PLC data type. These start with PLCTYPE.
            The data type is optional when a handle has been created for
             the variable.

        handle : int, optional
            The variable handle.

        cast : boolean, optional
            Casts the known c data type to python data types.
        """

        handle, data_type = self._search_cache(variable, handle, data_type)

        value = self._connection.read_by_name(
            variable,
            data_type,
            handle
        )

        if cast:
            return value.value

        return value

    ##################
    # write_variable #
    ##################

    def write_variable(self, variable, value, data_type=None, handle=None):
        """
        Wrties a variable to the PLC.
        """

        handle, data_type = self._search_cache(variable, handle, data_type)

        self._connection.write_by_name(
            variable,
            value,
            data_type,
            handle
        )
