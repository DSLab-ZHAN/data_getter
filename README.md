# Data_Getter Documentation

## Class Overview
```python
class Dataset_MySQL(torch.utils.data.Dataset):
    def __init__(self,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 database: str,
                 refresh: bool = False,
                 appoint_tables: List[str] = ['*'],
                 table_conditions: Dict[str, str] = {}) -> None:
```
MySQL Data Loader supporting two usage patterns:
1. **Direct Instantiation**: Fast data retrieval from specified tables
2. **Inheritance Extension**: Can be used as base class for custom Datasets

## Initialization Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| host | str | Required | MySQL server address |
| port | int | Required | MySQL service port |
| user | str | Required | Database username |
| password | str | Required | Database password |
| database | str | Required | Target database name |
| refresh | bool | False | Cache refresh switch<br>True=Clear global cache & reload<br>False=Use cached data first |
| appoint_tables | List[str] | ['*'] | Tables to load<br>`['*']` loads all tables<br>`['table1','table2']` loads specified tables |
| table_conditions | Dict[str, str] | { } | Data filtering conditions<br>`{'GLOBAL':'id>100'}` global condition<br>`{'table1':'date > 20230101'}` table-specific condition |

## Core Properties
### df_raws
- Type: `Dict[str, DataFrame]`
- Description: Raw data container with table names as keys and corresponding DataFrames as values
- Example:
```python
# Access daily price data (table name: 'daily_price')
daily_df = dataset.df_raws["daily_price"]
```

### tables
- Type: `Optional[List[str]]`
- Description: List of actually loaded table names

## Key Methods
### read_data()
```python
def read_data() -> None
```
**Function**: Executes data loading process
**Features**:
- Automatic cache management (reuses cached results for identical queries)
- Progress bar visualization (using tqdm)
- Automatic handling of table/global conditions

### print_all_tables()
```python
def print_all_tables() -> None
```
**Function**: Prints all available tables in current database
**Sample Output**:
```
daily_price
financial_report
company_info
```

## Usage Examples
### Functional Usage
```python
# Instantiate data loader
dataset = Dataset_MySQL(
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="im_a_database",
    appoint_tables=["daily_kline", "index_weight"],
    table_conditions={
        "GLOBAL": "trade_date > 20230101",
        "index_weight": "index_code = '000300'"
    }
)

# Execute data loading
dataset.read_data()

# Access index component data
index_components = dataset.df_raws["index_weight"]
```
- For `index_weight` table: Applies `index_code = '000300'` condition

- For `daily_kline` table: Automatically applies GLOBAL condition

### Inheritance Usage
```python
class CustomDataset(Dataset_MySQL):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._preprocess()

    def _preprocess(self):
        # Execute data loading
        self.read_data()

        # Merge multiple tables
        merged_df = pd.merge(
            self.df_raws["daily_kline"],
            self.df_raws["index_weight"],
            on="trade_date"
        )
        # ... Additional preprocessing logic ...
```

## Cache Mechanism
### Global Cache Structure
```python
GLOBAL_READ_CACHE = {
    (database_name, table_name): {
        query_condition: corresponding_DataFrame,
        "id > 100": DataFrame(...),
        ...
    }
}
```

### Cache Rules
1. Automatic cache reuse for identical (database + table + condition) combinations
2. When `refresh=True`:
   - Clears `GLOBAL_READ_CACHE`
   - Forces complete data reload

## Important Notes
1. **Table Existence Checks**: Non-existent tables in `appoint_tables` will trigger warnings and be filtered out

2. **Condition Formatting**:
   - Omit `WHERE` keyword in conditions
   - Valid example: `"trade_date > 20230101 AND volume > 10000"`

3. **Cache Management**:
   - Set `refresh=True` after database modifications to get fresh data
   - Global cache is shared across instances

4. **Inheritance Usage**:
   - Must call `super().__init__()` to initialize parent class
   - `df_raws` becomes available only after calling `read_data()`
