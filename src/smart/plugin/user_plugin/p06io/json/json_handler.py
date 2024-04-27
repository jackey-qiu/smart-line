from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json as _json


################
# json_handler #
################

class json_handler(object):
    """
    Class to handle json files.
    """

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Class to handle json files.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity

    #############
    # read_file #
    #############

    def read_file(self, file_path, clean=False):
        with open(file_path) as file_handle:
            if clean:
                print('Cleaning is not implemented yet.')
                # TODO: include cleaning procedure so that comments
                #      can be used in a json file.

            else:
                ret_val = _json.load(file_handle)

        return ret_val
