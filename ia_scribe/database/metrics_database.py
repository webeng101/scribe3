import os
from ia_scribe.database.database import Database
from ia_scribe.abstract import singleton
import gc

@singleton
class MetricsDatabase(object):
    databases = {}

    def __init__(self, **kwargs):
        self._base_dir = kwargs['basedir']
        self._metrics = kwargs['metrics']
        self._slices = kwargs['slices']

    def start(self):
        self._load_dbs()

    def _generate_schema(self, metric):
        schema = {}
        agg = self._metrics[metric]
        if 'timeless' in self._metrics[metric] \
                and self._metrics[metric]['timeless'] is True:
            temp_table = []
            for column in agg.get('select'):
                if column == '{slice}':
                    continue
                elif '(' in column:
                    column = column.split('(')[0]
                col = {'name': column, 'type': 'TEXT', }
                temp_table.append(col)
            schema[metric] = temp_table
        else:
            for slice in self._slices:
                slice_table = [{'name': 'time', 'type': 'TEXT', }]
                for column in agg.get('select'):
                    if column == '{slice}':
                        continue
                    elif '(' in column:
                        column = column.split('(')[0]
                    col = {'name': column, 'type': 'TEXT', }
                    slice_table.append(col)
                schema[slice] = slice_table
        return schema

    def _get_init_params(self, metric):
        filename = os.path.join(self._base_dir, metric)
        name = metric
        schema = self._generate_schema(metric)
        return filename, name, schema

    def _load_dbs(self):
        for metric in self._metrics:
            filename, name, schema = self._get_init_params(metric)
            self.databases[metric] = [filename, name, schema]

    def _get_db(self, metric):
        filename, name, schema = self.databases[metric]
        db = Database(filename=filename,
                      name=name,
                      schema=schema)
        return db

    def db_method(self, metric, method, *args, **kwargs):
        db = self._get_db(metric)
        db.start()
        func = getattr(db, method)
        res = func(*args, **kwargs)
        db.stop()
        return res

    def get_metric(self, metric, time_slice, where=None):
        select_statement = self._metrics[metric]['rollup_select']
        group_by_statement = self._metrics[metric]['rollup_group_by']
        target_table = metric if 'timeless' in self._metrics[metric] \
                and self._metrics[metric]['timeless'] is True else time_slice
        statement = 'select {select} from {table} '.format(
            select=select_statement,
            table=target_table)
        if where:
            statement += " WHERE {} ".format(where)

        statement += ' group by {groupby}'.format(groupby=group_by_statement)
        res = self.db_method(metric,'query',statement)
        return res

    def put_metric(self, metric, time_slice, value_tuple):
        if self.is_timeless(metric):
            res = self.db_method(metric, 'insert', metric, value_tuple)
        else:
            res = self.db_method(metric, 'insert', time_slice, value_tuple)
        return res

    def update_metric(self, metric, time_slice, values):
        for value in values:
            self.put_metric(metric, time_slice, value)

    def is_timeless(self, metric):
        return self._metrics[metric].get('timeless', False)