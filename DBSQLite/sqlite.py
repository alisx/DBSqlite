import sqlite3
import logging
import threading

logger = logging.getLogger(__name__)


class Sqlite:
    def __init__(self, db, pool_size=5):
        self.db = db
        self.pool_size = pool_size
        self.lock = threading.Lock()  # 用于保护连接池的线程安全
        self.pool = self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        pool = []
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db)
            conn.row_factory = self.__dict_factory
            pool.append(conn)
        return pool
    
    def __del__(self):
        """对象销毁时，关闭所有连接"""
        with self.lock:
            while self.pool:
                conn = self.pool.pop()
                conn.close()

    def __dict_factory(self, cursor, row):
        """将查询结果转换为字典"""
        fields = [col[0] for col in cursor.description]
        return {fields[i]: row[i] for i in range(len(fields))}

    def get_conn(self):
        """获取一个连接"""
        with self.lock:
            if self.pool:
                return self.pool.pop()
            else:
                # 如果池已空，创建一个新的连接
                conn = sqlite3.connect(self.db)
                conn.row_factory = self.__dict_factory
                return conn
            
    def rls_conn(self, conn):
        """释放连接回池"""
        with self.lock:
            if len(self.pool) < self.pool_size:
                if conn:
                    self.pool.append(conn)
            else:
                # 如果池已满，关闭连接
                conn.close()

    def _query(self, sql, conn=None):
        is_inner = True if conn is None else False
        try:
            if is_inner:
                conn = self.get_conn()
            rows = []
            for row in conn.execute(sql):
                rows.append(row)
            if is_inner:
                conn.commit()
            return rows
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)

    def _get_table_fields(self, table_name, conn=None):
        is_inner = True if conn is None else False
        try:
            if is_inner:
                conn = self.get_conn()
            cur = conn.execute(f"PRAGMA table_info('{table_name}')")
            rows = cur.fetchall()
            if is_inner:
                conn.commit()
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)
            
        field_names = []
        primary_keys = []
        for r in rows:
            field_names.append(r['name'])
            if r.get('pk') >= 1:
                primary_keys.append(r['name'])

        ret = {
            'fields': field_names,
            'primary_keys': primary_keys
        }
        return ret

    def de(self, sql, conn=None):
        is_inner = True if conn is None else False
        try:
            if is_inner:
                conn = self.get_conn()
            for s in sql.split(";"):
                conn.execute(s)
            if is_inner:
                conn.commit()
            return True
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)

    def insert(self, table_name, rows, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.get_conn()

        all_fields = self._get_table_fields(table_name, conn)
        insert_fields = all_fields.get('fields')
        insert_sql = "insert into %s (%s) " % (
            table_name, '`'+'`,`'.join(insert_fields)+'`')
        insert_sql += "values(" + ','.join(['?'] * len(insert_fields)) + ")"

        values = []
        for row in rows:
            insert_values = []
            for f in insert_fields:
                val = row.get(f, None)
                if val is not None:
                    insert_values.append(row.get(f))
                else:
                    insert_values.append(None)
            values.append(insert_values)
        if len(values) == 0:
            return rows
        try:
            effect_count = 0
            if len(values) > 1:
                cur = conn.executemany(insert_sql, values[:-1])
                effect_count = cur.rowcount
            cur = conn.execute(insert_sql, values[-1])
            effect_count += cur.rowcount
            sql = 'select * from %(tb)s where %(pk)s>%(bid)d and %(pk)s<%(eid)d' % {
                'tb': table_name,
                'pk': all_fields.get('primary_keys')[0],
                'bid': cur.lastrowid-effect_count,
                'eid': cur.lastrowid+effect_count
            }
            if is_inner:
                conn.commit()
            rows = self.qj(sql, conn)
            if type(rows) == tuple:
                rows = list(rows)
            return rows
        except sqlite3.Error as e:
            logger.error(f"insert error:{e}")
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)

    def update(self, table_name, rows, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.get_conn()
        all_fields = self._get_table_fields(table_name, conn)

        conditions = ' AND '.join("`{}` = '%({})s'".format(key, key) for key in all_fields.get('primary_keys'))
        
        update_rows = []
        insert_rows = []

        for row in rows:# 有主键就更新，否则就插入这是不对的
            if all(key in row for key in all_fields.get('primary_keys')):
                # update
                # 需要查询一下数据库
                sql = "select count(*) from `{table}` where {conditions}"
                sql = sql.format(table=table_name, conditions=conditions)
                if self.qv(sql % row, conn) == 1:
                    update_rows.append(row)
                else:
                    insert_rows.append(row)
            else:
                # insert
                insert_rows.append(row)
        try:
            for row in update_rows:
                key_list = []
                for f in all_fields.get('fields'):
                    if f in all_fields.get('primary_keys'):  # 主键不参与更新
                        continue
                    val = row.get(f, None)
                    if val is not None:  # 有值
                        placeholder = "{}=".format(f) + "'%({})s'".format(f)
                        key_list.extend([placeholder])
                if len(key_list) > 0:
                    val_list = ",".join(key_list)
                    sql = "UPDATE `{table}` SET {values} WHERE {conditions};"
                    sql = sql.format(table=table_name, values=val_list, conditions=conditions)
                    conn.execute(sql % row)
            insert_rows = self.insert(table_name, insert_rows, conn)
            update_rows.extend(insert_rows)
            if is_inner:
                conn.commit()
            return update_rows
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)

    def qj(self, sql, conn=None):
        is_inner = True if conn is None else False
        try:
            if is_inner:
                conn = self.get_conn()
            cur = conn.execute(sql)
            rows = cur.fetchall()
            if is_inner:
                conn.commit()
            return rows
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)
    
    def qo(self, sql, conn=None):
        rows = self.qj(sql, conn)
        if len(rows) > 0:
            return rows[0]
        else:
            return None
    
    def qv(self, sql, conn=None):
        is_inner = True if conn is None else False
        try:
            if is_inner:
                conn = self.get_conn()
            cur = conn.execute(sql)
            rows = cur.fetchall()
            if is_inner:
                conn.commit()
            if len(rows) > 0:
                first_key = next(iter(rows[0]))
                return rows[0][first_key]
            else:
                return None
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.rls_conn(conn)

    def qvs(self, sql, conn=None):
        data = self.qj(sql, conn)
        ret = []
        for d in data:
            for f in d.keys():
                ret.append(d[f])
                break
        return ret
    
def test_get_table_fields(db):
    """测试 _get_table_fields 方法"""
    conn = db.get_conn()
    try:
        # 确保表结构正常返回
        result = db._get_table_fields("users", conn=conn)
        assert "id" in result["fields"]
        assert "name" in result["fields"]
        assert "age" in result["fields"]
        assert "id" in result["primary_keys"]
    finally:
        db.rls_conn(conn)