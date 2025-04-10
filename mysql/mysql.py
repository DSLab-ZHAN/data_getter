#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   mysql.py
@Time    :   2024/10/14 22:27:01
@Author  :   MuliMuri
@Version :   1.0
@Desc    :   MySQL interface implementation
'''


import pymysql
import threading
import warnings

from typing import Any, Dict, List, Optional, Tuple

from .common import \
    IDBCommon, DBWarnings, RetIndices, \
    covert_to_sql_type, check_database_selected, check_data_field_type, \
    check_database_exists, check_table_exists


SQL_DICT = {
    'check_database_exists': "SHOW DATABASES LIKE '{database_name}'",
    'create_database': "CREATE DATABASE IF NOT EXISTS `{database_name}`",
    'drop_database': "DROP DATABASE IF EXISTS `{database_name}`",

    'check_table_exists': "SELECT TABLE_NAME FROM information_schema.`TABLES` \
                           WHERE TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = '{database_name}'",
    'create_table': "CREATE TABLE IF NOT EXISTS `{table_name}` ({columns})",
    'drop_table': "DROP TABLE IF EXISTS `{table_name}`",

    'insert_data': "INSERT INTO `{table_name}` ({columns}) VALUES ({values})",
    'delete_data': "DELETE FROM `{table_name}` {condition}",
    'update_data': "UPDATE `{table_name}` SET {sets} {condition}",
    'select_data': "SELECT * FROM `{table_name}` {condition}"
}


class MySQL(IDBCommon):
    def __init__(self,
                 host: str,
                 port: int,
                 user: str,
                 password: str
                 ) -> None:

        super(MySQL, self).__init__()

        self.conn_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'charset': 'utf8mb4'
        }

        self.db = pymysql.connect(**self.conn_params)
        self.db.autocommit(True)
        self.cursor = self.db.cursor()

        self.lock_exec = threading.RLock()

        self._register_database_exists_func(self.__is_database_exists)
        self._register_table_exists_func(self.__is_table_exists)

    def __is_database_exists(self, database_name: str) -> bool:
        sql = SQL_DICT['check_database_exists'].format(database_name=database_name)
        results = self.execute(sql)[RetIndices.RESULT]

        if (len(results) != 0):
            return True

        return False

    def __is_table_exists(self, table_name: str) -> bool:
        sql = SQL_DICT['check_table_exists'].format(
            table_name=table_name, database_name=self._curr_database_name
        )

        results = self.execute(sql)[RetIndices.RESULT]

        if (len(results) != 0):
            return True

        return False

    def reconnect(self) -> None:
        self.db = pymysql.connect(**self.conn_params)
        self.db.autocommit(True)
        self.cursor = self.db.cursor()

        if (self._curr_database_name is not None):
            self.switch_database(self._curr_database_name)

    @check_database_exists
    def create_database(self, database_name: str) -> bool:
        sql = SQL_DICT['create_database'].format(
            database_name=database_name
        )

        return self.execute(sql)[RetIndices.STATUS]

    @check_database_exists
    def switch_database(self, database_name: str) -> bool:
        self.db.select_db(database_name)

        if (self.cursor):
            self.cursor.close()

        self.cursor = self.db.cursor()
        self._curr_database_name = database_name

        return True

    @check_database_exists
    def drop_database(self, database_name: str) -> bool:
        sql = SQL_DICT['drop_database'].format(
            database_name=database_name
        )

        return self.execute(sql)[RetIndices.STATUS]

    @check_database_selected
    @check_table_exists
    def create_table(self,
                     table_name: str,
                     column_infos: List[Tuple[str, Any]]) -> bool:

        columns = []

        for i, (name, value) in enumerate(column_infos):
            type_str = covert_to_sql_type(value)
            columns.append(f"{name} {type_str}")

        sql = SQL_DICT['create_table'].format(
            table_name=table_name,
            columns=str(",".join(columns))
        )

        return self.execute(sql)[RetIndices.STATUS]

    @check_database_selected
    @check_table_exists
    def drop_table(self, table_name: str) -> bool:
        sql = SQL_DICT['drop_table'].format(
            table_name=table_name
        )

        return self.execute(sql)[RetIndices.STATUS]

    @check_database_selected
    @check_table_exists
    @check_data_field_type
    def insert(self,
               table_name: str,
               data: Dict[str, Any]) -> bool:

        column_names = ",".join(list(data.keys()))
        values = tuple(data.values())
        holders = ",".join(["%s" for _ in range(len(values))])

        sql = SQL_DICT['insert_data'].format(
            table_name=table_name,
            columns=column_names,
            values=holders
        )

        exec_ret = self.execute(sql, values)

        if (not exec_ret[RetIndices.STATUS] and exec_ret[RetIndices.ERROR_CODE] in [1366, 1265]):
            # Mismatched data type

            # Error 1366: Incorrect string value - Raised when trying to insert a value
            # that does not match the column's charset or format (e.g., invalid characters).
            # Often occurs with charset mismatch or invalid numeric format.

            # Error 1265: Data truncated - Raised when the value is implicitly converted
            # and some part of the data is lost (e.g., when inserting a value that exceeds
            # the column's size or an implicit type conversion results in truncation).

            warnings.warn(DBWarnings.TypeMismatchedWarning(exec_ret[RetIndices.ERROR_MSG]))

        return exec_ret[RetIndices.STATUS]

    @check_database_selected
    @check_table_exists
    def delete(self,
               table_name: str,
               condition: str) -> bool:

        sql = SQL_DICT['delete_data'].format(
            table_name=table_name,
            condition=condition
        )

        return self.execute(sql)[RetIndices.STATUS]

    @check_database_selected
    @check_table_exists
    def select(self,
               table_name: str,
               condition: Optional[str] = None) -> Tuple[Tuple, List]:

        sql = SQL_DICT['select_data'].format(
            table_name=table_name,
            condition=condition
        )

        exec_ret = self.execute(sql)

        return (exec_ret[RetIndices.COLUMN_NAME], exec_ret[RetIndices.RESULT])

    @check_database_selected
    @check_table_exists
    @check_data_field_type
    def update(self,
               table_name: str,
               data: Dict[str, Any],
               condition: str) -> bool:

        sets = ",".join(
            f"`{column}`={value}" for column, value in data.items()
        )

        sql = SQL_DICT['update_data'].format(
            table_name=table_name,
            sets=sets,
            condition=condition
        )

        return self.execute(sql)[RetIndices.STATUS]

    def execute(self, sql: str, data: Tuple = ()) -> Tuple:
        with self.lock_exec:
            status = False
            err_code = 0
            err_msg = None

            # Ensure connect
            if (not self.db.open):
                self.db.ping(reconnect=True)
                self.switch_database(self._curr_database_name)

            try:
                self.cursor.execute(sql, data)
                status = True

            except Exception as e:
                self.db.rollback()
                err_code, err_msg = e.args

            column_name = list(zip(*self.cursor.description))[0] if (self.cursor.description is not None) else None

            return (status, err_code, column_name, self.cursor.fetchall(), err_msg)

    def transaction(self):
        class TransactionManager():
            def __init__(self, outer: 'MySQL') -> None:
                self.outer = outer

            def __enter__(self) -> 'MySQL':
                self.outer.lock_exec.acquire()
                self.outer.db.autocommit(False)

                return self.outer

            def __exit__(self, exc_type, exc_val, exc_tb):
                try:
                    if exc_type is None:
                        self.outer.db.commit()
                        self.outer.db.autocommit(True)
                finally:
                    self.outer.lock_exec.release()

        return TransactionManager(self)
