#! /usr/bin/env python

__author__ = ["Jan Garrevoet"]

import os
import subprocess

try:
    import HasyUtils
except ImportError:
    pass

# subprocess.check_output(['pidof','/usr/lib/tango/server/Petra3ICS', 'p06'])


###############
# TangoServer #
###############

class TangoServer(object):
    '''
    Class to control tango server.
    '''

    ############
    # __init__ #
    ############

    def __init__(self, server_name=None, instance=None, tango_host=None):
        '''
        Class to handle tango servers.

        Parameters
        ----------
        server_name : str, optional
            The tango server name/Instance name.

        instance : str, optional
            The server instance.

        tango_host : str, optional
            The tango host which hosts the server.
        '''

        self._server_name = server_name
        self._instance = instance
        self._tango_host = tango_host

    ###############
    # _get_server #
    ###############

    def _get_server(self, server, instance, tango_host):
        """
        Returns the server name and tango host

        Parameters
        ----------
        server : str
            The server name.

        instance : str
            The instance name.

        tango_host : str
            The tango host.

        Returns
        -------
        str
            The server name.

        str
            The tango host.
        """
        if (
                server is None
                and instance is None
                and tango_host is None
                and self._server_name is not None
                and self._instance is not None):
            server_name = '{}/{}'.format(self._server_name, self._instance)
            tango_host = self._tango_host

        elif server is not None and instance is not None:
            server_name = '{}/{}'.format(server, instance)

        else:
            raise ValueError(
                'One needs to provide a server name and an instance.'
            )

        return server_name, tango_host

    #########
    # start #
    #########

    def start(self, server_name=None, instance=None, tango_host=None):
        '''
        Starts a tango server.

        Parameters
        ----------
        server_name : str, optional
            The tango server name/Instance name.

        instance : str, optional
            The server instance.

        tango_host : str, optional
            The tango host which hosts the server.

        Returns
        -------
        boolean
            True on success. False when fails.
        '''

        server, tango_host = self._get_server(
            server_name, instance, tango_host
        )

        ret_val = HasyUtils.startServer(
            server,
            tangoHost=tango_host
        )

        return ret_val

    ###########
    # restart #
    ###########

    def restart(
            self, server_name=None, instance=None, tango_host=None,
            hard=False):
        '''
        Restarts a tango server.

        Parameters
        ----------
        server_name : str, optional
            The tango server name/Instance name.

        instance : str, optional
            The server instance.

        tango_host : str, optional
            The tango host which hosts the server.

        hard : boolean, optional
            Performs a hard kill if normally stopping the server fails.

        Returns
        -------
        boolean
            True on success. False when fails.
        '''

        ret_val = self.stop(
            server_name=server_name,
            instance=instance,
            tango_host=tango_host,
            hard=hard
        )

        if ret_val:
            ret_val = self.start(
                server_name=None,
                instance=None,
                tango_host=None
            )

        return ret_val

    ########
    # stop #
    ########

    def stop(
            self,
            server_name=None,
            instance=None,
            tango_host=None,
            hard=False):
        '''
        Stops a tango server.

        Parameters
        ----------
        server_name : str, optional
            The tango server name/Instance name.

        instance : str, optional
            The server instance.

        tango_host : str, optional
            The tango host which hosts the server.

        hard : boolean, optional
            Performs a hard kill if normally stopping the server fails.

        Returns
        -------
        boolean
            True on success. False when fails.
        '''

        server, tango_host = self._get_server(
            server_name, instance, tango_host
        )

        ret_val = HasyUtils.stopServer(
            server,
            tangoHost=tango_host
        )

        if ret_val is False and hard is True:
            try:
                ps_proc = subprocess.Popen(
                    ['ps', 'x'],
                    stdout=subprocess.PIPE
                )

                out, err = ps_proc.communicate()

                ps_items = out.split('\n')

                servers = []
                pid = []
                for item in ps_items:
                    if server in item and instance in item:
                        sub = item.split()
                        servers.append(sub[-2])
                        pid.append(int(sub[0]))

                if len(pid) < 2:
                    os.kill(pid[0], subprocess.signal.SIGKILL)
                    ret_val = True
                else:
                    raise ValueError(
                        'Too many servers fit the parameters.\n({})'.format(
                            servers
                        )
                    )

            except subprocess.CalledProcessError:
                ret_val = True
            except Exception:
                raise

        return ret_val
