from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import random
import subprocess
import sys
import time

import p06io

# todo:
# + propagate wave field: 259


########
# Tomo #
########

class Tomo(object):
    """
    Class wrapping the tomo packages of FS-Petra.
    """

    def __init__(self, verbosity=0):
        """
        Wrapper for the tomo packages.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity

    ############
    # _execute #
    ############

    def _execute(self, *args):
        '''
        Executes the commands
        '''

        tomo_commands = list(args)

        # Generate filename
        filename = (
            '/tmp/tomo_'
            + str(random.random())[2:]
            + '.input'
        )

        # Write commands to file
        writer = p06io.txt()
        writer.write_list(filename, tomo_commands)

        cmd = ['tomo', '-f', filename]
        sub_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        t_start = time.time()
        while sub_proc.poll() is None:
            if self.verbosity > 0:
                print(
                    'Working: {:0.1f}'.format(
                        time.time()
                        - t_start
                    ),
                    end='\r'
                )
                sys.stdout.flush()
            time.sleep(0.1)
        os.remove(filename)

    ################
    # unwrap_phase #
    ################

    def unwrap_phase(self, input_file):
        '''
        Unwraps the provided image.
        The unwrapped file will have the postfix '_unwrap'

        Parameters
        ----------
        input_file : str
            File path of the file.
        '''

        input_file = os.path.abspath(input_file)

        input_base, input_ext = os.path.splitext(input_file)
        output_base = input_base + '_unwrap'

        tomo_commands = (
            826,
            0,
            input_base,
            input_ext,
            input_ext,
            output_base,
            0,
            1,
            99
        )

        if os.path.isfile(input_file):
            if self.verbosity > 0:
                print('Current: {}'.format(input_file))
            self._execute(*tomo_commands)
        else:
            raise ValueError('File missing: {}'.format(input_file))
