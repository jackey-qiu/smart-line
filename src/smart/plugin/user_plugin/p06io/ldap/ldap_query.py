import time

import ldap as _ldap


#############
# LdapQuery #
#############

class LdapQuery(object):
    """
    Supports full ldap support.
    """

    ############
    # __init__ #
    ############

    def __init__(self, server=None, verbosity=0):
        """
        Supports full ldap support.

        Parameters
        ----------
        server : str, optional
            The server addess.

        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity
        if server is not None:
            self._ldap_server = server
        else:
            self._ldap_server = "it-ldap-slave.desy.de"

        self._BASE_DN_GROUP = "ou=group,ou=rgy,o=DESY,c=DE"
        self._BASE_DN_USER = "ou=people,ou=rgy,o=DESY,c=DE"
        self.RECONNECT_ATTEMPTS = 5

        self._init_ldap_connection()

    #########################
    # _init_ldap_connection #
    #########################

    def _init_ldap_connection(self):
        """
        Initialises the ldap connection.
        """

        self._connection = _ldap.initialize("ldap://" + self._ldap_server)
        self._connection.set_option(_ldap.OPT_REFERRALS, 0)

    ###################
    # _get_group_info #
    ###################

    def _get_group_info(self, group_name):
        """
        Query the ldap for group info.

        Parameters
        ----------
        group_name : str
            The group name to query.

        Returns
        -------
        list
            A list containing data blobs regarding the group.
        """

        info = self._search(
            self._BASE_DN_GROUP,
            _ldap.SCOPE_SUBTREE,
            "cn={}".format(group_name)
        )

        return info

    ##################
    # _get_user_info #
    ##################

    def _get_user_info(self, username):
        """
        Query the user info.
        """

        info = self._search(
            self._BASE_DN_USER,
            _ldap.SCOPE_SUBTREE,
            "uid={}".format(username)
        )

        return info

    ##############
    # _reconnect #
    ##############

    def _reconnect(self, error, reconnect_counter):
        """
        Attempts to reconnect to the ldap server.

        Parameters
        ----------
        error : ldap.LDAPError
            The exception that was raised.

        reconnect_counter : int
            The number of reconnects that already happened.
        """

        if reconnect_counter < self.RECONNECT_ATTEMPTS:
            if reconnect_counter > 0:
                time.sleep(1)
            if self.verbosity > 0:
                print(
                    "Reconnectiong attempt: {}".format(reconnect_counter + 1)
                )
            self._init_ldap_connection()
        else:
            raise _ldap.CONNECT_ERROR(
                "Unable to connect to LDAP server after "
                "{} reconnect attempts. ({})".format(
                    reconnect_counter,
                    error
                )
            )

    ###########
    # _search #
    ###########

    def _search(self, base, scope, search_filter):
        """
        Searches the LDAP server.

        Parameters
        ----------
        base : str
            The base

        scope : str
            The scope

        search_filter : str
            The query filter.

        Returns
        -------
        list
            The result list.
        """

        reconnects = 0

        while True:
            try:
                ret_val = self._connection.search_s(base, scope, search_filter)
                break
            except _ldap.LDAPError as err:
                # Error numbers
                # 2: SERVER_DOWN
                # 32: ?
                if err.args[0]["errno"] in [2, 32]:
                    self._reconnect(err, reconnects)
                    reconnects += 1
                else:
                    raise

        return ret_val

    #####################
    # get_group_members #
    #####################

    def get_group_members(self, group_name):
        """
        Returns a list containing the members of a group.

        Parameters
        ----------
        group_name : str
            The group name to query.

        Returns
        -------
        list of str
            A list containing all the usernames that are members of the group.
        """

        ret_val = []

        info = self._get_group_info(group_name)
        # len == 0 when group does not exists.
        if len(info) != 0:
            try:
                for entry in info[0][1]['uniqueMember']:
                    if isinstance(entry, bytes):
                        entry = entry.decode()

                    for part in entry.split(','):
                        if part.startswith("uid="):
                            ret_val.append(part.split("uid=")[1])

            # No users assigned to the group
            except KeyError:
                pass

        return ret_val
