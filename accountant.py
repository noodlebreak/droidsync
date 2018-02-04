"""
All the record keeping of sync pushes and pulls is done here.
sqlite3 is used as the local database.
"""

import sqlite3

DEFAULT_TYPE = 'TEXT'
COL_TYPE_MAP = {
    int: 'INT',
    str: 'TEXT',
    float: 'REAL',
}


class Accountant(object):

    def __init__(self, *args, **kwargs):
        self.db_name = kwargs.get('db_name')
        self.connection = self._get_db_connection()
        self.table_name = kwargs.get('table_name')
        column_creation_statements = []
        column_info = kwargs['column_info']
        for col in column_info:
            # COLUMN INFO    NAME    TYPE   IS-NULL    PRIMARY_KEY
            # column_info = ('xyz', 'int', True/False, True/False)
            col_declaration = "{col_name} {col_type} {primary_key} {not_null}".format(
                col_name=col[0],
                col_type=COL_TYPE_MAP.get(col[1], DEFAULT_TYPE),
                primary_key=['', 'PRIMARY KEY'][col[3] is True],
                not_null=['NULL', 'NOT NULL'][col[2] is True]
            )
            column_creation_statements.append(col_declaration)
        self.col_declarations = ",\n".join(column_creation_statements)
        self.column_names = ",".join([col[0] for col in column_info])

    def _get_db_connection(self):
        connection = sqlite3.connect(self.db_name)
        return connection

    def _format_kwargs(self, key_value_pairs):
        val = ", ".join("{}={}".format(key, val) for key, val in key_value_pairs.items())
        return val

    def create_table(self, **kwargs):
        """
        ac.connection.execute('''CREATE TABLE xxx
                 (ID INT PRIMARY KEY     NOT NULL,
                 FILE_NAME           TEXT    NOT NULL,
                 FILE_PATH            INT     NOT NULL,
                 is_dir        BOOL);''')
        """
        self.connection.execute(
            '''CREATE TABLE {table_name} ({col_declarations});'''.format(
                table_name=self.table_name,
                col_declarations=self.col_declarations,
            )
        )

    def read(self, **kwargs):
        assert isinstance(kwargs.get('where_clause_dict'), dict), "WHERE clause data must be a dict"
        self.connection.execute(
            '''SELECT {col_names} FROM {table} WHERE {where_clause};'''.format(
                col_names=self.column_names,
                table=self.table_name,
                where_clause=self._format_kwargs(kwargs['where_clause_dict'])
            )
        )

    def create(self, **kwargs):
        assert isinstance(kwargs.get('values'), dict), "INSERT values must be a non empty dict"
        self.connection.execute(
            '''INSERT INTO {table_name} {column_names} VALUES ({values});'''.format(
                table_name=self.table_name,
                column_names="({})".format(self.column_names),
                values=",".join(kwargs['values'].values())
            )
        )

    def update(self, **kwargs):
        assert kwargs.get('update_dict') is not None, "update_dict not passed"
        assert kwargs.get('where_clause_dict') is not None, "WHERE clause dict not given"

        update_kwargs = self._format_kwargs(kwargs['update_dict'])
        where_clause = self._format_kwargs(kwargs['where_clause_dict'])
        self.connection.execute(
            '''UPDATE {table_name} SET {update_kwargs} WHERE {where_clause};'''.format(
                table_name=self.table_name,
                update_kwargs=update_kwargs,
                where_clause=where_clause
            ))
