#!/bin/env python
# -*- coding: utf-8 -*-

import sys

try:
    import tango as PyTango
except ImportError:
    import PyTango
import time

if sys.version_info < (3, ):
    PYTHON_VERSION = 2
else:
    PYTHON_VERSION = 3


################
# tango_device #
################

class tango_device(object):

    ############
    # __init__ #
    ############

    def __init__(self, device=None, verbosity=0):
        '''
        Class to control devices using tango.

        Parameters
        ----------
        device : str, optional
            Device path.
        '''

        if device is not None:
            self._proxy = self._create_proxy(device)
        else:
            self._proxy = None

        self.verbosity = verbosity

        self._states = PyTango.DevState

    #################
    # _create_proxy #
    #################

    def _create_proxy(self, device):
        '''
        Create a tango device proxy

        Parameters
        ----------
        device : str
            Device path.

        Returns
        -------
        instance
            Instance of the device proxy.
        '''

        return PyTango.DeviceProxy(device)

    #########################
    # _get_attribute_config #
    #########################

    def _get_attribute_config(self, proxy, attribute):
        '''
        Gets the attribute config.

        Parameters
        ----------
        proxy : instance
            The proxy instance of the tango device.

        attribute : str
            The attribute of which the config needs to be read.

        Returns
        -------
        PyTango Attribute Info Instance
            Instance containing all the config of the attribute.
        '''

        return proxy.get_attribute_config(attribute)

    ##############
    # _get_proxy #
    ##############

    def _get_proxy(self, device):
        '''
        Gets the device proxy. It determines if it should use the locally
        defined one or generally defined one.

        Parameters
        ----------
        device : str
            Device path.

        Returns
        -------
        instance
            Instance of the device proxy.
        '''

        if device is None:
            # Raise error when no device has been defined.
            if self._proxy is None:
                raise ValueError('No device has been provided.')

            _proxy = self._proxy
        else:
            _proxy = self._create_proxy(device)

        return _proxy

    ###################
    # execute_command #
    ###################

    def execute_command(
            self,
            command,
            value=None,
            device=None,
            retries=2,
            retryTimeout=0.05):
        '''
        Executes the given Command.

        Parameters
        ----------
        command : str
            The command to execute

        value : any, optional
            The value that the command should set.
            The type is dependent on the command and the tango server.

        device : str, optional
            Device address.

        retries : int, optional
            The number of retries to write an attribute before raising
            an exception.

        retryTimeout : float, optional
            The time to wait between retries.

        Returns
        -------
        any
            The return of the command. Type is dependent on the command
            and tango server.
        '''

        _proxy = self._get_proxy(device)
        _retry = 0

        while True:
            try:
                _returnValue = _proxy.command_inout(
                    command,
                    cmd_param=value
                )

                _retVal = _returnValue
                break

            except Exception as err:
                _retry += 1
                time.sleep(retryTimeout)
                if _retry >= retries:
                    if value is None:
                        raise IOError(
                            'Failed to send {} command'
                            ' to {}.\n Error: {}'.format(
                                command,
                                _proxy,
                                err
                            )
                        )
                    else:
                        raise IOError(
                            'Failed to send {} command'
                            ' to {} with value {}.\n'
                            'Error:{}'.format(
                                command,
                                _proxy,
                                value,
                                err
                            )
                        )

        return _retVal

    ######################
    # get_attribute_list #
    ######################

    def get_attribute_list(self, device=None):
        '''
        Returns the attribute list of the device.

        Parameters
        ----------
        device : str, optional
            The device address.

        Returns
        -------
        list
            List containing the available attributes.
        '''

        proxy = self._get_proxy(device)

        return list(proxy.get_attribute_list())

    #########################
    # get_attribute_quality #
    #########################

    def get_attribute_quality(self, attribute, device=None):
        '''
        Gets the attribute quality.

        Parameters
        ----------
        attribute : str
            The attribute name.

        device : str, optional
            The device address.

        Returns
        -------
        str
            The quality of the attribute.
            Possible qualities:
            + alarm
            + changing
            + invalid
            + valid
            + warning
        '''

        proxy = self._get_proxy(device)

        quality = proxy.read_attribute(attribute).quality

        if quality == PyTango.AttrQuality.ATTR_ALARM:
            ret_val = 'alarm'
        elif quality == PyTango.AttrQuality.ATTR_CHANGING:
            ret_val = 'changing'
        elif quality == PyTango.AttrQuality.ATTR_INVALID:
            ret_val = 'invalid'
        elif quality == PyTango.AttrQuality.ATTR_VALID:
            ret_val = 'valid'
        elif quality == PyTango.AttrQuality.ATTR_WARNING:
            ret_val = 'warning'
        else:
            raise ValueError('Unknown quality. ({})'.format(quality))

        return ret_val

    ################
    # get_property #
    ################

    def get_property(self, property):
        '''
        Returns the requested property.

        Parameters
        ----------
        property : str
            The name of the property.

        Returns
        -------
        List
            List of strings containing the value(s) of the property.
            Up to the user to cast to the correct type.
        '''

        prop = self._proxy.get_property(property)

        return prop[property]

    ##################
    # get_properties #
    ##################

    def get_properties(self, properties):
        '''
        Returns the requested property.

        Parameters
        ----------
        properties : list
            List of names of the properties.

        Returns
        -------
        dict
            All the requested properties.
        '''

        prop = self._proxy.get_property(properties)

        return prop

    #############
    # get_state #
    #############

    def get_state(self, device=None):
        '''
        Retuns the device state.

        Parameters
        ----------

        device : str, optional
            The device path.

        Returns
        -------
        Tango state
        '''

        return self.execute_command('State', device=device)

    ##############
    # get_status #
    ##############

    def get_status(self, device=None):
        '''
        Retuns the device state.

        Parameters
        ----------

        device : str, optional
            The device path.
            If none provided the device will be used that was set during
            the initialisation of the class instance.

        Returns
        -------
        Tango state
        '''

        return self.execute_command('Status', device=device)

    ##############################
    # get_attribute_alarm_levels #
    ##############################

    def get_attribute_alarm_levels(self, attribute, device=None):
        '''
        Returns the alarm levels of the attribute.

        Parameters
        ----------
        attribute : str
            The attribute to read.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.

        Returns
        -------
        tuple
            The min and max alarm level of the attribute.
            When an alarm level has not been set 'Not specified' is returned.
        '''

        _proxy = self._get_proxy(device)

        attr = self._get_attribute_config(_proxy, attribute)
        return attr.alarms.min_alarm, attr.alarms.max_alarm

    ##############################
    # get_attribute_display_unit #
    ##############################

    def get_attribute_display_unit(self, attribute, device=None):
        '''
        Returns the display unit of the attribute.

        Parameters
        ----------
        attribute : str
            The attribute to read.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.

        Returns
        -------
        str
            The display unit of the attribute.
        '''

        _proxy = self._get_proxy(device)

        attr = self._get_attribute_config(_proxy, attribute)
        return attr.display_unit

    ################################
    # get_attribute_warning_levels #
    ################################

    def get_attribute_warning_levels(self, attribute, device=None):
        '''
        Returns the warning levels of the attribute.

        Parameters
        ----------
        attribute : str
            The attribute to read.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.

        Returns
        -------
        tuple
            The min and max warning level of the attribute.
            When a warning level has not been set 'Not specified' is returned.
        '''

        _proxy = self._get_proxy(device)

        attr = self._get_attribute_config(_proxy, attribute)
        return attr.alarms.min_warning, attr.alarms.max_warning

    ######################
    # get_attribute_unit #
    ######################

    def get_attribute_unit(self, attribute, device=None):
        '''
        Returns the unit of the attribute.

        Parameters
        ----------
        attribute : str
            The attribute to read.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.

        Returns
        -------
        str
            The unit of the attribute.
        '''

        _proxy = self._get_proxy(device)

        attr = self._get_attribute_config(_proxy, attribute)
        return attr.unit

    #################
    # has_attribute #
    #################

    def has_attribute(self, attribute, device=None):
        '''
        Checks if a device has the requested attribute.

        Parameters
        ----------
        attribute : str
            The attribute name.

        Returns
        -------
        boolean
            False if it does not has the attribute.
            True if it does have the attribute.
        '''

        _proxy = self._get_proxy(device)

        try:
            _proxy.attribute_query(attribute)
            retVal = True
        except PyTango.DevFailed:
            retVal = False

        return retVal

    ################
    # put_property #
    ################

    def put_property(self, property, value):
        '''
        Writes the property value to the property.

        Parameters
        ----------
        property : str
            The name of the property.

        value : any
            The value of the property.
        '''

        prop = {
            property: value
        }

        self._proxy.put_property(prop)

    ##################
    # put_properties #
    ##################

    def put_properties(self, properties):
        '''
        Returns the requested property.

        Parameters
        ----------
        properties : dict
            Dictionary with the properties as keys.
        '''

        self._proxy.put_property(properties)

    ##################
    # read_attribute #
    ##################

    def read_attribute(
            self,
            attribute,
            device=None,
            retries=2,
            retryTimeout=0.05):
        '''
        Reads the value of an attribute.

        Parameters
        ----------
        attribute : str
            The attribute to read.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.

        retries : int, optional
            The number of retries to write an attribute before raising
            an exception.

        retryTimeout : float, optional
            The time to wait between retries.

        Returns
        -------
        any
            The type of the return value depends on the attribute
            of the tango device.
        '''

        _proxy = self._get_proxy(device)
        _retry = 0

        while True:
            try:
                _retVal = _proxy.read_attribute(attribute).value
                if PYTHON_VERSION == 2:
                    if isinstance(_retVal, str):
                        _retVal = _retVal.decode("utf-8")
                break
            except Exception as err:
                _retry += 1
                time.sleep(retryTimeout)
                if self.verbosity > 0:
                    print('Try {} failed.'.format(_retry))
                if _retry >= retries:
                    raise IOError(
                        'Failed to read {}: {}'.format(
                            attribute,
                            err
                        )
                    )

        return _retVal

    ###############
    # set_timeout #
    ###############

    def set_timeout(self, timeout, device=None):
        '''
        Sets the server timeout time.

        Parameters
        ----------
        timeout : float
            Timeout in seconds.

        device : str, optional
            The device from which the attribute needs to be read.
            If not provided the device will be used that was set during
            the initialisation of the class instance.
        '''

        _proxy = self._get_proxy(device)

        _proxy.set_timeout_millis(int(timeout*1000))

    ###################
    # write_attribute #
    ###################

    def write_attribute(
            self,
            attribute,
            value,
            device=None,
            retries=2,
            retryTimeout=0.05,
            asynchronous=False):
        '''
        Writes the value of the provided attribute to the device.

        Parameters
        ----------
        proxy : instance
            Proxy instance of the server.

        attribute : str
            The attribute to write.

        value : any
            The value to which the attribute needs to be set.
            The type is dependent on the command and the tango server.

        server : str, optional
            The server to which the attribute needs to be set.
            If not provided the server will be used that was set during
            the initialisation of the class instance.

        retries : int, optional
            The number of retries to write an attribute before raising
            an exception.

        retryTimeout : float, optional
            The time to wait between retries.

        asynchonous : bool, optional
            Writing the attribute synchronous or asynchronous.
            Default is False so synchronous writing.
        '''

        _proxy = self._get_proxy(device)
        _retry = 0

        while True:
            try:
                if asynchronous:
                    _proxy.write_attribute_asynch(attribute, value)
                else:
                    _proxy.write_attribute(attribute, value)
                break

            except Exception as err:
                _retry += 1
                time.sleep(retryTimeout)
                if _retry >= retries:
                    raise IOError(
                        'Failed to set {}: {} ({})'.format(
                            attribute,
                            value,
                            err
                        )
                    )
