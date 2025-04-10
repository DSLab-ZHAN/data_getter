# Data_Getter 数据集接入文档

## 类概览
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
MySQL 数据加载器，支持两种使用模式：
1. **直接实例化**：快速获取指定数据库表数据
2. **继承扩展**：作为自定义 Dataset 基类使用

## 初始化参数说明
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | str | 必填 | MySQL 服务器地址 |
| port | int | 必填 | MySQL 服务端口 |
| user | str | 必填 | 数据库用户名 |
| password | str | 必填 | 数据库密码 |
| database | str | 必填 | 目标数据库名称 |
| refresh | bool | False | 缓存刷新开关<br>True=清空全局缓存并重新加载<br>False=优先使用缓存数据 |
| appoint_tables | List[str] | ['*'] | 指定加载表清单<br>`['*']`加载所有表<br>`['table1','table2']`加载指定表 |
| table_conditions | Dict[str, str] | { } | 数据过滤条件字典<br>`{'GLOBAL':'WHERE id>100'}`全局条件<br>`{'table1':'WHERE date > 20230101'}`表级条件 |

## 核心属性
### df_raws
- 类型: `Dict[str, DataFrame]`
- 说明: 原始数据容器，键为表名，值为对应 DataFrame
- 访问示例:
```python
# 获取日行情数据，表名为 'daily_price'
daily_df = dataset.df_raws["daily_price"]
```

### tables
- 类型: `Optional[List[str]]`
- 说明: 实际加载的数据表名称列表

## 主要方法
### read_data()
```python
def read_data() -> None
```
**功能**：执行数据加载流程
**特性**：
- 自动缓存管理（相同条件查询复用缓存）
- 带进度条显示（使用 tqdm 实现）
- 自动处理表级 / 全局条件

### print_all_tables()
```python
def print_all_tables() -> None
```
**功能**：打印当前数据库所有可用表
**输出示例**：
```
daily_price
financial_report
company_info
```

## 使用示例
### 函数调用式用法

```python
# 实例化数据加载器
dataset = Dataset_MySQL(
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="im_a_database",
    appoint_tables=["daily_kline", "index_weight"],
    table_conditions={
        "GLOBAL": "WHERE trade_date > 20230101",
        "index_weight": "WHERE index_code = '000300'"
    }
)


# 执行数据加载
dataset.read_data()

# 访问指数成分数据
index_components = dataset.df_raws["index_weight"]
```
- 对于 index_weight 表，将应用 WHERE index_code = '000300' 查询条件

- 对于 daily_kline 表，GLOBAL 条件将自动应用

### 继承用法
```python
class CustomDataset(Dataset_MySQL):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._preprocess()

    def _preprocess(self):
        # 执行数据加载
        self.read_data()

        # 合并多个数据表
        merged_df = pd.merge(
            self.df_raws["daily_kline"],
            self.df_raws["index_weight"],
            on="trade_date"
        )
        # ... 其他预处理逻辑 ...
```

## 缓存机制
### 全局缓存结构
```python
GLOBAL_READ_CACHE = {
    (数据库名, 表名): {
        过滤条件: 对应DataFrame,
        "WHERE id > 100": DataFrame(...),
        ...
    }
}
```

### 缓存规则
1. 相同数据库 + 表名 + 查询条件组合自动复用缓存
2. 当 `refresh=True` 时：
   - 清空全局缓存 `GLOBAL_READ_CACHE`
   - 强制重新加载所有数据

## 注意事项

1. **表存在性检查**：当 `appoint_tables` 包含不存在的表时，会触发警告并自动过滤

2. **条件格式规范**：
   - WHERE 子句不需要包含`WHERE`关键字
   - 示例有效条件：`"trade_date > 20230101 AND volume > 10000"`

3. **缓存管理**：
   - 修改数据库数据后需设置`refresh=True`获取最新数据
   - 不同实例共享全局缓存

4. **继承使用**：
   - 必须调用 `super().__init__()` ，以此来调用父类 `__init__()` 方法
   - `df_raws` 仅在调用 `read_data()` 后可用
