'''
@File    :   data_provider.py
@Time    :   2025/03/17 23:19:51
@Author  :   MuliMuri
@Version :   1.0
@Desc    :   Read dataset from MySQL then format to Dataframe.
'''


import warnings

from pandas import DataFrame
from torch.utils.data import Dataset
from tqdm import tqdm
from typing import Dict, List, Optional, Tuple

from mysql import MySQL, RetIndices


SQL_ALL_TABLE = "SHOW TABLES"

GLOBAL_READ_CACHE: Dict[Tuple, Dict[str, DataFrame]] = {}


class Dataset_MySQL(Dataset):
    def __init__(self,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 database: str,
                 refresh: bool = False,
                 appoint_tables: List[str] = ['*'],
                 table_conditions: Dict[str, str] = {}) -> None:
        """Obtaining data through MySQL Server
        When initialize this class, you can use 'self.df_raw' to get the dataset
        self.df_raw is a dict
        The format is {'table_name' : 'table_data', ...}
        table_name:str is table's name
        table_data:DataFrame is table's data

        Args:
            host (str): MySQL hostname
            port (int): MySQL port
            user (str): MySQL username
            password (str): MySQL username's password
            database (str): The database name where the data is located
            refresh (bool, optional):   After each database query, the query results will be automatically
                                        saved to 'GLOBAL_READ_HISTORY' dictionary
                                        (using 'database name', 'table name', and 'query condition' as keys),
                                        the dictionary result will be returned first during each query process.
                                        If you want to query the latest data, set the variable to True,
                                        and the query result will update the dictionary
                                        Warning: If set True, 'GLOBAL_READ_HISTORY' will be clear!
                                        Defaults to False. Default represents no refresh. Defaults to False.

            appoint_tables (List[str], optional):   The required data tables in the database.
                                                    Defaults to ['*']. Default represents all tables.

            table_conditions (Dict[str, str], optional):    Retrieve the specified data from the specified table
                                                            through SQL conditions. If the condition is to be applied
                                                            globally, apply 'GLOBAL' as the unique key,
                                                            for example {'GLOBAL ':' WHERE c1<=100... '}.
                                                            Otherwise, use the following example
                                                            {'table_name1': 'WHERE c1<=100...'},
                                                            where table_name1 is the specified table name.
                                                            If both GLOBAL and others are included,
                                                            all unspecified table conditions will be replaced
                                                            by GLOBAL conditions.
                                                            Defaults to {}. Default represents no condition to get all datas.

        Raises:
            ValueError: _description_
        """
        super().__init__()

        self.database = database
        self.refresh = refresh

        self.tables: Optional[List[str]] = None

        self.df_raws = {}
        self.db = MySQL(
            host=host,
            port=port,
            user=user,
            password=password
        )

        if (not self.db.switch_database(database)):
            raise ValueError(f"Appoint database '{database}' cannot switch.")

        # Check table exists.
        non_exists_table_list = self.__check_table_exists(appoint_tables)
        if (non_exists_table_list):
            warnings.warn(f"{non_exists_table_list} Not found in '{database}'.")

        # Build table conditions
        self.table_conditions = self.__build_table_conditions(table_conditions)

    def __check_table_exists(self, appoint_tables: List[str]) -> List[str]:
        if ("*" in appoint_tables):
            # Load all tables
            self.tables = self.__get_all_tables()
            return None

        non_exists_table_list = []
        self.tables = []

        for table_name in appoint_tables:
            if (not self.db._table_exists_func(table_name)):
                non_exists_table_list.append(table_name)
                continue

            self.tables.append(table_name)

    def __build_table_conditions(self, table_conditions: Dict[str, str]) -> Dict[str, str]:
        if (table_conditions):
            keys = list(table_conditions)

            # Is global condition
            if ("GLOBAL" in keys):
                others = list(set(self.tables).difference(keys))
                for other_table in others:
                    table_conditions[other_table] = table_conditions['GLOBAL']

                table_conditions.pop('GLOBAL')

            if (len(list(set(table_conditions).difference(self.tables)))):
                warnings.warn(f"There are non-existent tables {list(set(table_conditions).difference(self.tables))} in the conditions, which will be ignored.")     # noqa: E501

            return table_conditions

        return {}

    def __select_and_fresh(self, table_name: str, condition: str) -> None:
        column_names, results = self.db.select(table_name, condition)
        self.df_raws[table_name] = DataFrame(results, columns=column_names)
        GLOBAL_READ_CACHE[(self.database, table_name)][condition] = self.df_raws[table_name]

    def __get_all_tables(self) -> List[str]:
        table_list = self.db.execute(SQL_ALL_TABLE)[RetIndices.RESULT]
        return list(zip(*table_list))[0]

    def print_all_tables(self) -> None:
        for table_name in self.__get_all_tables():
            print(table_name)

    def read_data(self):
        # Init keys
        condition_keys = self.table_conditions.keys()

        # Init tables bar
        pbar = tqdm(self.tables)

        others_results_keys = list(GLOBAL_READ_CACHE.keys())
        for i, table_name in enumerate(pbar):
            pbar.set_description_str(desc=table_name)

            condition = ""
            if (table_name in condition_keys):
                # Read table with condition
                condition = self.table_conditions[table_name]

            # Check cache
            if (self.refresh):
                # Refresh cache
                GLOBAL_READ_CACHE.clear()
                self.__select_and_fresh(table_name, condition)
                return

            if ((self.database, table_name) in others_results_keys):
                # Check condition
                others_results_condition_keys = list(GLOBAL_READ_CACHE[(self.database, table_name)].keys())
                if (condition in others_results_condition_keys):
                    # Extract from cache
                    self.df_raws[table_name] = GLOBAL_READ_CACHE[(self.database, table_name)][condition]

                else:
                    self.__select_and_fresh(table_name, condition)

            else:
                GLOBAL_READ_CACHE[(self.database, table_name)] = {}
                self.__select_and_fresh(table_name, condition)
