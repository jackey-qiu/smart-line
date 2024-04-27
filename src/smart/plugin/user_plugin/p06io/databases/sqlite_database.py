import sqlite3


##################
# SqliteDatabase #
##################

class SqliteDatabase(object):
    """
    Sqlite database manager.
    """

    ###########
    # __del__ #
    ###########

    def __del__(self):
        """
        Delete exec.
        """
        self.close_database_connection()

    ############
    # __exit__ #
    ############

    def __exit__(self, *args):
        """
        Exit exec.
        """
        self.close_database_connection()

    ############
    # __init__ #
    ############

    def __init__(self, filepath, verbosity=0):
        """
        Sqlite database manager.

        Parameters
        ----------
        filepath : str
            The path to the database file.

        verbosity : int, optional
            The verbosity level.
        """

        self._open_database_connection(filepath)

    #############################
    # _open_database_connection #
    #############################

    def _open_database_connection(self, filename):
        """
        Opens the database connection.

        Parameters
        ----------
        filename : list of str
            The filename of the database.

        database_id : list of str
            The identifier name for the database.
        """

        self._connection = sqlite3.connect(filename)
        self._cursor = self._connection.cursor()

    ##############################
    # close_database_connection #
    ##############################

    def close_database_connection(self):
        """
        Closes the database connection.

        Parameters
        ----------
        database_id : str
            The ID name of the database.
        """

        self._connection.close()

    ################
    # delete_table #
    ################

    def delete_table(self, table_name):
        """
        Deletes a table from the database.

        Parameters
        ----------
        table_name : str
            The table name.
        """

        cmd = "DROP TABLE IF EXISTS '{}'".format(table_name)
        self.execute(cmd)

    ###########
    # execute #
    ###########

    def execute(self, cmd, commit=True):
        """
        Execute a command and commit it to the database.

        Parameters
        ----------
        cmd : str
            The command to execute.

        commit : boolean, optional
            Determines if things are commited to the database or not.

        Returns
        -------
        any
            The return value of the cursor execution.
        """
        try:
            ret_val = self._cursor.execute(cmd)
        except sqlite3.OperationalError as err:
            raise ValueError(
                "The current SQL command is not valid. ({})".format(err)
            )
        if commit:
            self._connection.commit()

        return ret_val

    ###############################
    # get_most_recent_table_entry #
    ###############################

    def get_most_recent_table_entry(self, table_name):
        """
        Returns the most recent table entry.

        Parameters
        ----------
        table_name : str
            The table name.

        Returns
        -------
        list
            List containing the most recent table entry.
        """

        cmd = (
            "SELECT * FROM '{0}' WHERE rowid=(SELECT MAX(rowid) FROM '{0}')".
            format(
                table_name
            )
        )

        query = self.execute(cmd, commit=False)

        ret_val = []

        while True:
            value = query.fetchone()
            if value is not None:
                ret_val = list(value)
            else:
                break

        return ret_val

    ####################
    # get_table_header #
    ####################

    def get_table_header(self, table_name):
        """
        Returns the table header.

        Parameters
        ----------
        table_name : str
            The table name.

        Returns
        -------
        list
            List containing the names of the columns.
        """

        cmd = "select * from '{}'".format(table_name)
        self.execute(cmd)
        query = self._cursor.description
        ret_val = []
        for i in query:
            ret_val.append(i[0])
        return ret_val

    ###################
    # get_table_names #
    ###################

    def get_table_names(self):
        """
        Returns all available tables.
        """

        cmd = (
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY 1;"
        )

        query = self.execute(cmd, commit=False)

        ret_val = []

        while True:
            value = query.fetchone()
            if value is not None:
                ret_val.append(value[0])
            else:
                break

        return ret_val

    ################
    # rename_table #
    ################

    def rename_table(self, current_name, new_name):
        """
        Rename a table.

        Parameters
        ----------
        current_name : str
            The current name of the table.

        new_name : str
            The new name of the table.
        """

        cmd = (
            "ALTER TABLE {} RENAME TO {}".format(current_name, new_name)
        )

        self.execute(cmd)
