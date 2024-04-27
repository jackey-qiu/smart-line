from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import subprocess


##############
# LdapSearch #
##############

class LdapSearch(object):
    """
    Class to interact with the desy LDAP server via the 'ldapsearch tool'.

    This class uses the ldapsearch tools since this tool is installed on all
     desy machines.
    """

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Class to interact with the desy LDAP server.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity
        self._ldap_server = 'it-ldap-slave.desy.de'

    ################
    # _ldap_search #
    ################

    def _ldap_search(self, username):
        """
        Search the ldap server for info about a user.

        Returns
        -------
        dict
            A dictionary containing the user information.
        """

        cmd = [
            'ldapsearch',
            '-x',
            '-LLL',
            '-S',
            'sn',
            '-h',
            self._ldap_server,
            '-b',
            'ou=people,o=desy,c=de',
            '(& (uid={}))'.format(username)
        ]

        if self.verbosity > 0:
            print('Command: {}'.format(cmd))

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        lines = p.stdout.readlines()
        if self.verbosity > 2:
            print("LDAP reply: {}".format(lines))
            print(type(lines))
        output = {}
        for line in lines:
            if isinstance(line, bytes):
                line = line.decode("utf-8")

            if line.startswith('uid'):
                output['uid'] = line.split()[1]
            elif line.startswith('cn'):
                output['name'] = line.split()[1:]
            elif line.startswith('telephoneNumber'):
                output['phone'] = line.split()[1]
            elif line.startswith('roomNumber'):
                output['room'] = line.split()[1]
            elif line.startswith('mail'):
                output['email'] = line.split()[1]

        return output

    #############
    # get_email #
    #############

    def get_email(self, username):
        """
        Returns the email of the provided username.

        Parameters
        ----------
        username : str
            The user name of which you want to get the email address.

        Returns
        -------
        str
            The email address of the provided user name.
        """

        _info = self._ldap_search(username)
        return _info['email']
