from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import yaml as _yaml
import sys

if sys.version_info < (3, ):
    PYTHON_VERSION = 2
    ######################
    # construct_yaml_str #
    ######################

    def construct_yaml_str(self, node):
        """
        Override the default string handling function
        to always return unicode objects in py2
        """
        return self.construct_scalar(node)

    _yaml.Loader.add_constructor(
        'tag:yaml.org,2002:str',
        construct_yaml_str
    )
    _yaml.SafeLoader.add_constructor(
        'tag:yaml.org,2002:str',
        construct_yaml_str
    )
else:
    PYTHON_VERSION = 3


###############
# YamlHandler #
###############

class YamlHandler(object):
    '''
    Class to handle yaml files.
    '''

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        '''
        Handling IO with yaml files.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        '''

        self.verbosity = verbosity

    #############
    # read_file #
    #############

    def read_file(self, file_path):
        '''
        Reads a yaml file.

        Returns
        ------
        dict
            Dictionary containing the content of the yaml file.
        '''

        with open(file_path, 'r') as stream:
            # return _yaml.safe_load(stream)
            return _yaml.load(stream, Loader=_yaml.Loader)

    ##############
    # write_file #
    ##############

    def write_file(self, data, file_path):
        """
        Write content to a file.

        Parameters
        ----------
        data : any
            The data to write to a file.

        file_path : str
            The file path of the output file.
        """

        with open(file_path, 'w') as file_handle:
            file_handle.write(_yaml.dump(data))

    # ########################
    # # merge_and_read_files #
    # ########################

    # def merge_and_read_files(self, file_list):
    #     """
    #     Merges the multiple files into 1 and parses it.

    #     Parameters
    #     ----------
    #     file_list : list
    #         List contining the paths.

    #     Returns
    #     -------
    #     dict
    #         The parsed files.
    #     """

    #     data = []
    #     for filepath in file_list:
    #         with open(filepath) as file_handle:
    #             tmp_data = file_handle.readline()
    #             if not tmp_data[-1].endswith("\n"):
    #                 tmp_data[-1] += "\n"
    #             data.extend(tmp_data)

    #     str_data = "".join(data)
    #     data_stream = io.StringIO(str_data.decode("utf-8"))

    #     return _yaml.safe_load(data_stream)
