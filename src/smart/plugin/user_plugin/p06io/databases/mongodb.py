#!/usr/bin/env python

__author__ = ["Jan Garrevoet"]

import sys

import pymongo as _pymongo

if sys.version_info < (3, ):
    PYTHON_VERSION = 2
else:
    PYTHON_VERSION = 3

# index_information()
# drop_index()


###########
# MongoDB #
###########

class MongoDB(object):
    """
    Class to interact with mongo DB.
    """

    ############
    # __init__ #
    ############

    def __init__(
            self, host="127.0.0.1", port=27017, username=None,
            password=None, database=None, collection=None,
            verbosity=0):
        """
        Class to interact with mongo DB.

        Parameters
        ----------
        host : str, optional
            The MongoDB host.

        port : int, optional
            The MongoDB port.

        username : str, optional
            The username used for the authentication.

        password : str, optional
            The password for the user authentication.

        database : str, optional
            The database name.

        collection : str, optional
            The collection name.

        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity
        self._ASCENDING = _pymongo.ASCENDING
        self._DESCENDING = _pymongo.DESCENDING
        self._errors = _pymongo.errors
        if (
                (username is None and password is not None)
                or (username is not None and password is None)):
            raise ValueError(
                "Both username and password need to be provided."
            )

        else:
            self._client = _pymongo.MongoClient(
                host, port, username=username, password=password
            )

        self._databases = {}

        if database is not None:
            self.connect_database(database)

        if database is not None and collection is not None:
            self.connect_collection(database, collection)

    ###############
    # _check_dict #
    ###############

    def _check_dict(self, data):
        """
        Checks if the dict keys are strings.
        """

        for key, value in list(data.items()):
            if PYTHON_VERSION == 2:
                if not isinstance(key, unicode):    # noqa F821
                    del data[key]
                    data[str(key)] = value
            else:
                if not isinstance(key, str):
                    del data[key]
                    data[str(key)] = value

            if isinstance(value, dict):
                data[str(key)] = self._check_dict(value)

        return data

    ####################
    # connect_database #
    ####################

    def connect_database(self, database):
        """
        Connect to a database.

        Parameters
        ----------
        database : str
            The database name.
        """
        if database not in self._databases:
            self._databases[database] = {
                "database": self._client[database],
                "collections": {}
            }

    ######################
    # connect_collection #
    ######################

    def connect_collection(self, database, collection):
        """
        Connect to a collection.

        Parameters
        ----------
        database : str
            The database name.

        collection
            The name of the collection to connect to.
        """

        if database not in self._databases:
            self.connect_database(database)

        (
            self._databases[database]["collections"]
            [collection]) = self._databases[database]["database"][collection]

    ################
    # create_index #
    ################

    def create_index(self, database, collection, index_info, unique=True):
        """
        Creates an index for the collection.

        Parameters
        ----------
        database : str
            The database name.

        collection
            The name of the collection.

        index_info : list
            A list of tuples containing the index field name and the indexing
            order ("ascending" or "descending")

        unique : boolean, optional
            If the indexed field(s) should be unique or not.
            Default is True.
        """

        index_entry = []
        for index in index_info:
            if index[1] == "ascending":
                order = self._ASCENDING
            elif index[1] == "descending":
                order = self._DESCENDING
            else:
                raise ValueError("Unknown ordering provided.")

            index_entry.append((index[0], order))

        try:
            self._databases[database]["collections"][collection].create_index(
                index_entry,
                unique=unique
            )
        except KeyError:
            raise IOError(
                "Trying to create an index on a non connected collection."
            )

    ###################
    # delete_database #
    ###################

    def delete_database(self, database):
        """
        Delete a database.

        Parameters
        ----------
        database : str
            The database name.
        """

        self._client.drop_database(database)
        if database in self._databases:
            self._databases.pop(database)

    ############
    # distinct #
    ############

    def distinct(self, database, collection, key, filter=None):
        """
        Find the distinct values of the given key.

        Parameters
        ----------
        database : str
            The database name.

        collection
            The name of the collection.

        key : str
            The key to get the distinct values of.

        Returns
        -------
        list
            A list containing all the distinct values of the key.
        """

        try:
            ret_val = (
                self._databases[database]["collections"][collection].distinct(
                    key,
                    filter=filter
                )
            )
            return ret_val
        except KeyError:
            raise IOError(
                "Trying to perform an operation on a database or collection"
                " that is not connected."
            )

    ########
    # find #
    ########

    def find(
            self, database, collection, fields, values, iterator=False,
            projection=None):
        """
        Find entries.

        Parameters
        ----------
        database : str
            The database name.

        collection : str
            The collection name.

        fields : list of str
            The field to query.

        values : list of str
            The query value.

        iterator : boolean, optional
            Determines if the return value is an iterator of a list.
            Default is False.

        projection : dict, optional
            A dictionary of whih entries (keys) should be kept. The values are
             zero or one.

        Returns
        -------
        list or iterator
            Default is a list.
            An iterator over the results when the iterator kwargs is True.
        """

        query = {}

        if isinstance(fields, str):
            fields = [fields]
        if isinstance(values, str):
            values = [values]
        if projection is not None:
            if not isinstance(projection, dict):
                raise TypeError("Projections need to be a dict.")

        if len(fields) != len(values):
            raise ValueError("Different ammount of fields and values defined.")

        for index, field in enumerate(fields):
            query[field] = values[index]

        try:
            result = (
                self._databases[database]["collections"][collection].find(
                    query,
                    projection=projection
                )
            )
        except StopIteration:
            result = iter([])

        if iterator:
            return result
        else:
            list_result = []
            try:
                while True:
                    list_result.append(next(result))
            except StopIteration:
                pass

            return list_result

    #######################
    # get_collection_info #
    #######################

    def get_collection_info(self, database, collection=None):
        """
        Returns information on all collections or on the provided collection
        in the database.

        Parameters
        ----------
        database : str
            The database name.

        collection : str, optional
            The collection name.

        Returns
        -------
        dict
            Dictionary containing information on all or the requested database.
        """

        iterator = self._databases[database]['database'].list_collections()
        ret_val = {}
        while True:
            try:
                data = next(iterator)
                name = data.pop("name")
                if collection is None:
                    ret_val[name] = data
                else:
                    if collection == name:
                        ret_val[name] = data
            except StopIteration:
                break

        return ret_val

    #############################
    # get_connected_collections #
    #############################

    def get_connected_collections(self, database):
        """
        Returns the names of the connected collections.

        Parameters
        ----------
        database : str
            The database name.

        Returns
        -------
        list
            List containing the names of the connected databases.
        """

        return list(self._databases[database]['collections'].keys())

    ###########################
    # get_connected_databases #
    ###########################

    def get_connected_databases(self):
        """
        Returns the names of the connected databases.

        Returns
        -------
        list
            List containing the names of the connected databases.
        """

        return list(self._databases.keys())

    #####################
    # get_database_info #
    #####################

    def get_database_info(self, database=None):
        """
        Returns information on all databases or on the provided database.

        Parameters
        ----------
        database : str, optional
            The database name.

        Returns
        -------
        dict
            Dictionary containing information on all or the requested database.
        """

        iterator = self._client.list_databases()
        ret_val = {}
        while True:
            try:
                data = next(iterator)
                name = data.pop("name")
                if database is None:
                    ret_val[name] = data
                else:
                    if database == name:
                        ret_val[name] = data
            except StopIteration:
                break

        return ret_val

    #################
    # get_databases #
    #################

    def get_databases(self):
        """
        Returns the names of the hosted databases.

        Returns
        -------
        list
            List containing the names of the hosted databases.
        """

        return self._client.list_database_names()

    ################
    # insert_entry #
    ################

    def insert_entry(
            self, database, collection, entry, check=True, auto_create=True):
        """
        Inserts an entry into a collection.

        Parameters
        ----------
        database : str
            The database name.

        collection
            The name of the collection to connect to.

        entry : dict
            The entry to add.

        check : boolean, optional
            Checks the dict for unsupported keys.
            Default is True, which is safer but slower.

        auto_create : boolean, optional
            Will automatically create the database and collection when not
            available yet.
            Default is True.
        """

        if check:
            entry = self._check_dict(entry)

        if auto_create:
            self.connect_collection(database, collection)

        try:
            return (
                self._databases[database]["collections"][collection].
                insert_one(
                    entry
                )
            )
        except KeyError:
            raise IOError(
                "Trying to insert an entry in a non connected database"
                " or collection."
            )

    ################
    # update_entry #
    ################

    def update_entry(
            self, database, collection, fields, values, new_value,
            upsert=False):
        """
        Find entries.

        Parameters
        ----------
        fields : list of str
            The field to query.

        values : list of str
            The query value.

        upsert : boolean, optional
            Insert a new document entry when no entry is returned.

        Returns
        -------
        list or iterator
            Default is a list.
            An iterator over the results when the iterator kwargs is True.
        """

        query = {}

        if isinstance(fields, str):
            fields = [fields]
        if isinstance(values, str):
            values = [values]

        if len(fields) != len(values):
            raise ValueError("Different ammount of fields and values defined.")

        for index, field in enumerate(fields):
            query[field] = values[index]

        result = (
            self._databases[database]["collections"][collection].update_one(
                query,
                {"$set": new_value},
                upsert=upsert
            )
        )

        return result
