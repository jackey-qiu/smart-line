#!/usr/bin/env python

__author__ = ["Jan Garrevoet"]

import copy
import getpass
import random
import subprocess
import os

import p06io
import p06io.ldap


################
# SlurmManager #
################

class SlurmManager():
    """
    Class to manage slurm.
    """

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Class to manage slurm.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity
        self._ldap = p06io.ldap.LdapSearch()

    ###########################
    # _sbatch_default_options #
    ###########################

    def _sbatch_default_options(self):
        """
        Default header of a slurm sbatch job.

        Returns
        -------
        dict
            Dictionary containing the default parameters.
        """

        home_dir = os.path.expanduser("~")

        options = {
            "constraints": None,
            "email": None,
            "email_type": "ALL",
            "error": "%j-%x-%N.err",
            "job_name": None,
            "nodes": 1,
            "partition": None,
            "output": "%j-%x-%N.out",
            "time": "1-00:00:00",
            "workdir": home_dir + "/slurm_output"
        }

        return options

    ################
    # _create_file #
    ################

    def _create_file(self, commands, options):
        """
        Creates the sbatch file

        Parameters
        ----------
        commands : list
            List of the commands to execute

        options : dict
            Dictionary of options to use for the job.

        Returns
        -------
        str
            File name of the sbatch job.
        """

        # Populate the job options dict
        file_id = random.getrandbits(60)
        filename = "/tmp/{}.sh".format(file_id)
        with open(filename, "w") as f:
            f.write("#!/bin/bash\n")

            for key, value in options.items():
                line = (
                    "#SBATCH"
                    + "\t"
                    + "--"
                    + str(self._translate_sbatch_options(key))
                    + "="
                    + str(value)
                    + "\n"
                )

                f.write(line)
            for command in commands:
                f.write(command + "\n")

        return filename

    ####################
    # _process_options #
    ####################

    def _process_options(self, options):
        """
        Processes the provided job options and adds defaults.

        Parameters
        ----------
        options : dict
            Dictionary containing all the wanted options for the slurm job.

        returns
        -------
        dict
            The processed job options for the slurm job.
        """

        job_options = self._sbatch_default_options()
        job_options.update(options)

        tmp_options = copy.deepcopy(job_options)
        for key, value in tmp_options.items():

            # Remove spaces from option value
            if value is not None and isinstance(value, str):
                value = value.replace(" ", "")
                job_options[key] = value

            # Remove keys if no email notifications wanted
            if key == "email_type":
                value = value.upper()
                job_options[key] = value
                if value == "NONE":
                    job_options.pop("email_type")
                    try:
                        job_options.pop("email")
                    except KeyError:
                        pass

            # Automatically determine email address
            elif key == "email":
                if value is None:
                    job_options[key] = self._ldap.get_email(getpass.getuser())

            else:
                if value is None:
                    job_options.pop(key)

        if self.verbosity > 1:
            print("Job options: {}".format(job_options))

        return job_options

    ################
    # _remove_file #
    ################

    def _remove_file(self, filename):
        """
        Removes a file from the system.

        Parameters
        ----------
        filename : str
            The file to remove.

        Returns
        -------
        int
            0 on success, 1 on failure.
        """

        try:
            os.remove(filename)
            return 0
        except Exception:
            return 1

    ###############
    # _submit_job #
    ###############

    def _submit_job(self, commands, options):
        """
        Submits a slurm job.

        Parameters
        ----------
        commands : list
            List of commands to execute.

        options : dict
            Dictionary containing the job options.

        Returns
        -------
        int
            The job ID number.
        """

        options = self._process_options(options)
        sbatch_file = self._create_file(commands, options)
        cmd = ["sbatch", sbatch_file]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        output = p.stdout.readlines()
        self._remove_file(sbatch_file)

        if self.verbosity > 0:
            print(output[0])

        return output[0].split()[-1]

    #############################
    # _translate_sbatch_options #
    #############################

    def _translate_sbatch_options(self, option):
        """
        Translates the used parameters into sbatch parameters.

        Parameters
        ----------
        option : str
            The option to be translated.

        Returns
        -------
        str
            The translated option as a sbatch parameter.
        """

        translation_table = {
            "begin": "begin",
            "constraints": "constraint",
            "email": "mail-user",
            "email_type": "mail-type",
            "error": "error",
            "job_name": "job-name",
            "nodes": "nodes",
            "output": "output",
            "partition": "partition",
            "time": "time",
            "workdir": "chdir"
        }

        return translation_table[option]

    ###############################
    # _translate_scontrol_options #
    ###############################

    def _translate_scontrol_options(self, option):
        """
        Translates the used parameters into scontrol parameters.

        Parameters
        ----------
        option : str
            The option to be translated.

        Returns
        -------
        str
            The translated option as a scontrol parameter.
        """

        translation_table = {
            "constraints": "Features",
            "partitions": "Partition"
        }

        return translation_table[option]

    #######################
    # _update_job_options #
    #######################

    def _update_job_options(self, job_id, options):
        """
        Updates the options of a running job.

        Parameters
        ----------
        job_id : int
            The slurm job ID.
        """

        # cmd = ["scontrol", "update", "jobid={}".format(job_id)]

        # for option, value in job.items():
        #     scontrol_option = self._translate_scontrol_options(option)
        #     cmd.append("{}='{}'".format(scontrol_option, value))

        # if self.verbosity > 0:
        #     print("cmd: {}".format(cmd))

        # p = subprocess.Popen(
        #     cmd,
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT
        # )

        # squeue -u garrej -t pending -h -o "scontrol update '
        # 'jobid=%i Partition='ps,maxgpu,allgpu'"
        pass

    #####################
    # submit_sbatch_job #
    #####################

    def submit_sbatch_job(self, commands, **kwargs):
        """
        Submits an sbatch job.

        Parameters
        ----------
        commands : list of strings
            List of the commands to be executed.

        email : str, optional
            The email notifications should be send to.
            By default it will use your Desy email address.

        email_type : str, optional
            The type of email to send.
            Possibilities are: BEGIN,END,FAIL,ALL,NONE

        job_name : str, optional
            The name to give the job.

        nodes : int, optional
            The number of nodes to use.
            Default is 1.

        partition : str, optional
            The partition to use. If not provided your default partition
            will be used.

        constraints : str, optional
            The constraints for the job.
            E.g.: K40X, P100, GPU, CPU

        time : str, optional
            The time you think the job will take.
            Default is 1 day.

        begin : str, optional
            Determines when the job should start.
            By default the begin time is asap.
            Some examples:
            + A given time: "16:00"
            + An offset:
                + "now+60" (seconds by default)
                + "now+1hour"
                + "2010-01-20T12:34:00"


        Returns
        -------
        int
            The job ID number.
        """

        return self._submit_job(commands, kwargs)


############################
# zmq_sbatch_job_submitter #
############################

def zmq_sbatch_job_submitter(port, verbosity=0):
    """
    A ZMQ slurm sbatch job submitter.

    Parameters
    ----------
    port : int
        The port to connect to.

    verbosity : int, optional
        The verbosity level of the service.

    Info
    ----
    The jobs will be submitted by the user that started the service.
    The message is a list of [command,options]. For the syntax of command
    and options have a look at the submit_sbatch_job method of the
    SlurmManager class.
    """

    zmq_server = p06io.zeromq.ServerPull(port=port)
    slurm = SlurmManager()

    try:
        while True:
            message = zmq_server.receive_message(timeout=0.5)
            if verbosity > 2:
                print("message: {}".format(message))

            if message is not None:
                jobId = slurm.submit_sbatch_job(
                    message[0],
                    **message[1]
                )

                if verbosity > 0:
                    print("Job submitted: {}".format(jobId))

    except KeyboardInterrupt:
        zmq_server.stop()

    except Exception as err:
        if verbosity > 0:
            print("Error: {}".format(err))
        zmq_server.stop()
