
import sys
import os

# 将 lib 目录添加到 sys.path
sys.path.append("..")

import pytest
from DBSQLite import Sqlite

@pytest.fixture(scope="module")
def db():
    """创建内存数据库实例"""
    db = Sqlite(":memory:", pool_size=2)
    db.de('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        );
    ''')
    yield db
    del db

def test_insert(db):
    """测试插入功能"""
    # 插入单条记录
    data = [{"id": 1, "name": "Alice", "age": 30}]
    result = db.insert("users", data)
    assert len(result) == 1
    assert result[0]["name"] == "Alice"

    # 插入多条记录
    data = [
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35}
    ]
    result = db.insert("users", data)
    assert len(result) == 2
    assert result[1]["name"] == "Charlie"

def test_query(db):
    """测试查询功能"""
    # 查询所有记录
    result = db.qj("SELECT * FROM users")
    assert len(result) == 3

    # 查询单条记录
    result = db.qo("SELECT * FROM users WHERE id = 1")
    assert result["name"] == "Alice"

    # 查询单个值
    count = db.qv("SELECT COUNT(*) FROM users")
    assert count == 3

def test_update(db):
    """测试更新功能"""
    # 更新记录
    data = [{"id": 1, "name": "Alice Updated", "age": 31}]
    result = db.update("users", data)
    assert len(result) == 1
    assert result[0]["name"] == "Alice Updated"

def test_transaction(db):
    """测试事务功能"""
    conn = db.get_conn()
    try:
        # 插入数据
        db.de("INSERT INTO users (id, name, age) VALUES (4, 'David', 40);", conn=conn)

        # 查询事务中的数据
        result = db.qo("SELECT * FROM users WHERE id = 4", conn=conn)
        assert result["name"] == "David"

        # 模拟事务回滚
        raise Exception("模拟事务失败")
    except Exception:
        conn.rollback()
    finally:
        db.rls_conn(conn)

    # 确保数据未提交
    result = db.qo("SELECT * FROM users WHERE id = 4")
    assert result is None

@pytest.mark.parametrize("data,expected_count", [
    ([{"id": 5, "name": "Eve", "age": 28}], 1),
    ([{"id": 6, "name": "Frank", "age": 32}, {"id": 7, "name": "Grace", "age": 29}], 2)
])
def test_parameterized_insert(db, data, expected_count):
    """测试参数化插入功能"""
    result = db.insert("users", data)
    assert len(result) == expected_count

