import io

import libconf
import p06io as _p06io


##########
# Ptycho #
##########

class Ptycho(object):
    '''
    Class to control the ptycho package.
    The class also offers extra possibilities, like config file creation.
    '''

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        '''
        Class to control the ptycho package.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        '''

        self.verbosity = verbosity

    ########################
    # _apply_custom_config #
    ########################

    def _apply_custom_config(self, config, template):
        '''
        Applies the custom configuration.

        Parameters
        ----------
        config : dict
            Dictionary containing the custom config.

        template : dict
            The template dictionary.

        Returns
        -------
        dict
            The configuration dictionary.
        '''

        for key in config.keys():

            if isinstance(config[key], dict):
                template[key].update(
                    self._apply_custom_config(
                        config[key],
                        template[key]
                    )
                )
            else:
                template[key] = config[key]

        return template

    #######################
    # get_config_template #
    #######################

    def get_config_template(self, version=None):
        '''
        Returns the config template.
        As a default the latest version is provided.

        Parameters
        ----------
        version : int, optional
            The version of the template to return.
            Default is the latest version.

        Returns
        -------
        dict
            Dictionary containing the latest version.
        '''

        if version is None:
            version = 1557229586
        elif version == "devel":
            version = 1570377799

        return self.read_config_file(
            '{}/packages/ptycho_templates/ptycho_{}.conf'.format(
                _p06io.__path__[0],
                version
            )
        )

    ######################
    # create_config_file #
    ######################

    def create_config_file(self, configuration, filename, version=None):
        '''
        Creates a ptycho config file.

        Parameters
        ----------
        configuration : dictionary
            Dictionary containing the options that need to be changed from
            standard.

        filename : str
            The filename of the config file.

        version : int, optional
            The version of the template to use.
        '''

        template = self.get_config_template(version)
        config = self._apply_custom_config(configuration, template)
        self.write_config_file(config, filename)

    #####################################
    # create_config_file_using_metadata #
    #####################################

    def create_config_file_using_metadata(
            self, metadata, location="beamline", version=None):
        '''
        Creates a ptycho config file.

        Parameters
        ----------
        metadata : dictionary
            Dictionary containing the scan metadata.

        location : str, optional
            The location used for the path selection.

        filename : str
            The filename of the config file.

        version : int, optional
            The version of the template to use.
        '''

        # configuration = metadata["processing_settings"]["ptycho"]
        # template = self.get_config_template(version)
        # config = self._apply_custom_config(configuration, template)
        # self.write_config_file(config, filename)
        pass

    ####################
    # read_config_file #
    ####################

    def read_config_file(self, filename):
        '''
        Reads a config file.

        Parameters
        ----------
        filename : str
            The filename of the file to read.

        Returns
        -------
        dict
            Dictionary containing the configuration.
        '''

        with io.open(filename, 'r') as file_handle:
            config = libconf.load(file_handle)

        return config

    #####################
    # write_config_file #
    #####################

    def write_config_file(self, configuration, filename):
        '''
        Writes the configuration to the file.
        '''

        with io.open(filename, 'w') as file_handle:
            libconf.dump(configuration, file_handle)
