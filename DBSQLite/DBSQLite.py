import sqlite3
import logging

logger = logging.getLogger(__name__)


class Sqlite:
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._conn = None

    def __del__(self):
        if self._conn:
            self._conn.close()

    def __dict_factory(self, cursor, row):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    def __get_conn(self):
        if not self._conn:
            self._conn = sqlite3.connect(self.db)
            self._conn.row_factory = self.__dict_factory
        return self._conn

    def __close_conn(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _query(self, sql, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.__get_conn()
        # cur = conn.cursor()
        rows = []
        for row in conn.execute(sql):
            rows.append(row)
        if is_inner:
            self.__close_conn()
        return rows

    def _get_table_fields(self, table_name, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.__get_conn()
            
        cur = conn.execute(f"PRAGMA table_info('{table_name}')")
        rows = cur.fetchall()
        # logger.debug(f"_get_table_fields rows:{rows}")
        # conn.close()
        if is_inner:
            self.__close_conn()
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
        if is_inner:
            conn = self.__get_conn()
        # cur = conn.cursor()
        for s in sql.split(";"):
            conn.execute(s)
        conn.commit()
        # cur.close()
        if is_inner:
            self.__close_conn()
        return True

    def insert(self, table_name, rows, conn=None):
        is_inner = True if conn is None else False
        # logger.debug(f">>>>> DBSQLite insert is_inner:{is_inner}")
        if is_inner:
            conn = self.__get_conn()

        all_fields = self._get_table_fields(table_name, conn)
        # logger.debug(f"all_fields:{all_fields}")
        insert_fields = all_fields.get('fields')
        insert_sql = "insert into %s (%s) " % (
            table_name, '`'+'`,`'.join(insert_fields)+'`')
        # logger.debug(f"insert_fields: {insert_fields}")
        insert_sql += "values(" + ','.join(['?'] * len(insert_fields)) + ")"
        # logger.debug(f"insert_sql: {insert_sql}")

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
        # print("DBSQLite values:", values)
        if len(values) == 0:
            return rows
        try:
            effect_count = 0
            conn = self.__get_conn()
            # cursor = conn.cursor()
            if len(values) > 1:
                # print(insert_sql)
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
            # cursor.close()
            if is_inner:
                conn.commit()
            rows = self.qj(sql, conn)
            if type(rows) == tuple:
                rows = list(rows)
        except sqlite3.Error as e:
            logger.error(f"insert error:{e}")
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.__close_conn()
        return rows

    def update(self, table_name, rows, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.__get_conn()
        # print('update:', is_inner)
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
            # cursor = conn.cursor()
            for row in update_rows:
                key_list = []
                for f in all_fields.get('fields'):
                    if f in all_fields.get('primary_keys'):  # 主键不参与更新
                        continue
                    val = row.get(f, None)
                    if val is not None:  # 有值
                        placeholder = "{}=".format(f) + "'%({})s'".format(f)
                        key_list.extend([placeholder])
                # print('key_list', key_list)
                if len(key_list) > 0:
                    val_list = ",".join(key_list)
                    sql = "UPDATE `{table}` SET {values} WHERE {conditions};"
                    sql = sql.format(table=table_name, values=val_list, conditions=conditions)
                    # logger.debug(f'Update sql:{sql}')
                    # print(f'Update sql:{sql}')
                    # print('row:', row)
                    conn.execute(sql % row)
            # cursor.close()
            insert_rows = self.insert(table_name, insert_rows, conn)
            # print(">>>> DBSQLite insert ok")
            update_rows.extend(insert_rows)
            if is_inner:
                conn.commit()
        except sqlite3.Error as e:
            if is_inner:
                conn.rollback()
            raise e
        finally:
            if is_inner:
                self.__close_conn()
            

        return update_rows

    def qj(self, sql, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.__get_conn()
        # cur = conn.cursor()
        cur = conn.execute(sql)
        rows = cur.fetchall()
        # cur.close()
        if is_inner:
            self.__close_conn()
        return rows
    
    def qo(self, sql, conn=None):
        rows = self.qj(sql, conn)
        if len(rows) > 0:
            return rows[0]
        else:
            return None
    
    def qv(self, sql, conn=None):
        is_inner = True if conn is None else False
        if is_inner:
            conn = self.__get_conn()
        # cur = conn.cursor()
        cur = conn.execute(sql)
        rows = cur.fetchall()
        # cur.close()
        if is_inner:
            self.__close_conn()

        if len(rows) > 0:
            first_key = next(iter(rows[0]))
            return rows[0][first_key]
        else:
            return None

    def qvs(self, sql, conn=None):
        data = self.qj(sql, conn)
        ret = []
        for d in data:
            for f in d.keys():
                ret.append(d[f])
                break
        return ret