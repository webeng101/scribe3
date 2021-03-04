import queue
import threading
from queue import Queue
import sqlite3

from kivy.logger import Logger


class Database(object):

    def __init__(self, **kwargs):
        self._db_filename = kwargs['filename']
        self._db_name = kwargs['name']
        self._schema = kwargs.get('schema')
        self._worker_thread = None
        self._db = None
        self._task_queue = None
        self._result_queue = None
        self._stop_event = threading.Event()
        self._done_event = threading.Event()
        self._running = False

    def start(self):
        if not self._running:
            self.stop()
            self._task_queue = queue.Queue()
            self._result_queue = queue.Queue()
            self._worker_thread = threading.Thread(target=self._db_worker,
                                                   name='{}-DatabaseWorkerThread'.format(self._db_name))
            self._worker_thread.daemon = True
            self._worker_thread.start()
            self._running = True
            Logger.debug('Database: Started')

    def stop(self):
        if self._running:
            self._task_queue.put(self._stop_event)
            self._done_event.wait()
            self._task_queue = None
            self._result_queue = None
            self._running = False
            Logger.debug('Database: Stopped')

    # The generic entry point to run queries (the idea is that we do want to expose an SQL interface)
    def query(self, query):
        self._put_task(query)
        error, result = self._result_queue.get()
        self._result_queue.task_done()
        if not error:
            return result
        return error

    # convenience method that uses the schema definition to pre-fill the query
    # It expects a tuple of the right length. No validation is done as of yet
    def insert(self, table, tuple):
        columns_string = ', '.join([x['name'] for x in self._schema[table] if not x.get('meta')] ,)
        values_string = ', '.join(['\'{}\''.format(x) for x in tuple])
        query_string = '''INSERT INTO {table} ({columns}) VALUES ({values})'''.format(
            table = table,
            columns = columns_string,
            values = values_string,
        )
        self.query(query_string)

    def upsert(self, table, tuple):
        columns_string = ', '.join([x['name'] for x in self._schema[table] if not x.get('meta')], )
        values_string = ', '.join(['\'{}\''.format(x) for x in tuple])
        query_string = '''REPLACE INTO {table} ({columns}) VALUES ({values})'''.format(
            table=table,
            columns=columns_string,
            values=values_string,
        )
        self.query(query_string)

    def _put_task(self, query):
        self._task_queue.put(query)

    def _put_task_result(self, query, error, result):
        res = result.fetchall() if result != None else result
        self._result_queue.put((error, res))

    def _open_db(self):
        try:
            db = sqlite3.connect(self._db_filename)
            return db
        except Exception as e:
            Logger.exception('Database: Failed to open database file: {}\nError was: {}'
                             .format(self._db_filename, e))
            return None

    def _ensure_db_is_inizialized(self):
        if not self._schema:
            Logger.debug('No schema specified, hoping for the best')
            return

        def table_exists(table_name):
            try:
                cur_res = c.execute('''SELECT name FROM sqlite_master 
                                    WHERE type='table' 
                                    AND name='{table_name}';'''
                                .format(
                    table_name=table_name))
                res = cur_res.fetchall()
                ret = len(res) > 0
            except sqlite3.OperationalError as e:
                ret = False
            return ret

        def create_table(table_name, schema):
            Logger.debug('Creating table {}'.format(table_name))
            columns = ''
            for n, entry in enumerate(schema):
                column = '{name} {type} {options}'.\
                        format(name=entry['name'],
                               type=entry['type'],
                               options=entry.get('options', ''))
                final = column if n == len(schema)-1 else column + ',\n'
                columns += final
                Logger.debug('Adding column: {}'.format(column))

            statement = '''CREATE TABLE {table_name} ({columns});'''.\
                        format(table_name=table_name,
                                columns = columns,)
            c.execute(statement)

        Logger.debug('Verifying database {} is initialized'.format(self._db_name))
        c = self._db.cursor()
        for table_name, fields in self._schema.items():
            if not table_exists(table_name):
                Logger.debug('Looks like table {} needs to be created'.format(table_name))
                create_table(table_name, fields)
                Logger.debug('Done!')
            else:
                Logger.debug('Table {} exists.'.format(table_name))

    # Worker thread methods
    #________________________________________________________________
    def _db_worker(self):
        self._db = self._open_db()
        Logger.debug('Database {}: Worker starting'.format(self._db))
        if not self._db:
            self._done_event.set()
            self.stop()
            return
        self._ensure_db_is_inizialized()
        while True:
            task = self._task_queue.get()
            if task is self._stop_event:
                self._task_queue.task_done()
                break
            else:
                self._handle_task(task)
                self._task_queue.task_done()
        self._done_event.set()
        Logger.debug('Database: Worker stopped')

    def _handle_task(self, query):
        Logger.debug('Database: Handling task "{}"'.format(query))
        result = error = None
        try:
            cursor = self._db.cursor()
            result = cursor.execute(query)
            self._db.commit()
        except Exception as e:
            Logger.exception('Database: Failed to call method "{}" on '
                             'database {}'.format(query, self._db_name))
            error = e
        self._put_task_result(query, error, result)

