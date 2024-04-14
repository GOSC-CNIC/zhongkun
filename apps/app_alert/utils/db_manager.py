from django.conf import settings
import MySQLdb
import datetime
import MySQLdb.cursors


class MysqlManager(object):
    config = getattr(settings, "DATABASES").get("default")

    def __init__(self):
        self.connect = MySQLdb.connect(host=self.config["HOST"],
                                       user=self.config["USER"],
                                       passwd=self.config["PASSWORD"],
                                       db=self.config["NAME"],
                                       port=int(self.config["PORT"]),
                                       cursorclass=MySQLdb.cursors.DictCursor
                                       )
        self.cursor = self.connect.cursor()

    def _upsert(self, table_name, items):
        if not items:
            return
        tuples = [tuple(_.values()) for _ in items]
        keys = items[0].keys()
        keys = ['`{}`'.format(_) for _ in keys]
        keys_str = ",".join(keys)
        _s = ",".join(len(keys) * ["%s"])
        sql = f"INSERT  IGNORE  INTO {table_name} ({keys_str}) VALUES ({_s})"
        insert_count = self.cursor.executemany(sql, tuples)
        return "date:{}, table:{}, insert_count:{}".format(datetime.datetime.now(), table_name, insert_count)

    def upsert(self, table_name: str, items: list):
        try:
            return self._upsert(table_name, items)
        except Exception as e:
            print(e)
            for item in items:
                self._upsert(table_name, [item])

    def search(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def update(self, sql):
        ret = self.cursor.execute(sql)
        return ret

    def delete(self, sql):
        ret = self.cursor.execute(sql)
        return ret

    def _close(self):
        self.connect.commit()
        self.cursor.close()
        self.connect.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
