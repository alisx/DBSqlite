# DBSqlite

基于 Sqlite3 的数据操控工具，对连接(connect)、游标（cursor）概念进行了封装，支持使用 Dict 数据类型来操作数据库。

## 简单示例

```python
from DBSqlite import Sqlite

db = Sqlite('mydb.db')

rows = [{'name': 'xiaoming', 'age': '12', 'gender': 'male'},
        {'name': 'xiaohong', 'age': '11', 'gender': 'female'}]
ret = db.insert('table_student', rows)
print('ret:',ret)

# print
# ret:[{'id': 1, 'name': 'xiaoming', 'age': '12', 'gender': 'male', 'class': None}, {'id': 2, 'name': 'xiaohong', 'age': '11', 'gender': 'female', 'class': None}]
```

## 依赖

- python3.6+
- sqlite3: `pip install pysqlite3`

## 方法

### **`DBSqlite`** 创建一个数据库工具实例

- *必选参数*：
  - `db`：数据库文件路径

- *返回*：DBSqlit 示例

### `qj` 执行一个查询语句，query json 的简写

- *参数*：
  - `sql` 查询语句字符串

- *返回*：查询结果，数据结构为 `list`

### **`qvs`** 执行一个查询语句， query values 的简写

- *参数*：
  - `sql` 查询语句字符串

- *返回*：查询结果集的第一列组成的 `list`

### **`qv`** 执行一个查询语句， query value 的简写

- *参数*：
  - `sql` 查询语句字符串

- *返回*：查询结果集的第一行第一列的值

### **`qo`** 执行一个查询语句 query object 的简写

- *参数*：
  - `sql` 查询语句字符串

- *返回*：查询结果集的第一行的`dict`

### **`de`** 执行一个sql语句 do execute 的简写

- *参数*：
  - `sql` 查询语句字符串

- *返回*：影响行数

### **`insert`** 向库表中插入多行记录

> *说明*
>
> 1. 以库表字段为主，记录中不提供视为None
> 2. 每行记录的字段可以不一致
> 3. 记录中不属于库表的字段会被忽略

- *参数*：
  - `table_name` 库表名称
  - `rows` 需要插入的记录，`list`类型

- *返回*：插入库表的结果，`list`类型

### *`update`* 更新库表中的多行记录

> *说明*
>
> 1. 只更新库表中存在且记录中提供的字段
> 2. 每行记录的字段可以不一致
> 3. 如果记录中没有提供主键，会被做插入处理

- *参数*

  - `table_name` 库表名称
  - `rows` 需要更新的记录，`list`类型

- *返回*：更新库表的结果，`list`类型
