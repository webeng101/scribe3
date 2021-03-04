from ia_scribe.database.database import Database
from ia_scribe.utils import all_files_under
from ia_scribe.breadcrumbs.query import generate_sql


class DatabaseRange(Database):

    def __init__(self, **kwargs):
        kwargs['filename'] = ':memory:'
        self._base_dir = kwargs['basedir']
        super(DatabaseRange, self).__init__(**kwargs)
        self._active_dbs = {}
        if kwargs.get('autostart', False):
            self.start()
            self._load_dbs()

    def _load_dbs(self):
        for db in all_files_under(self._base_dir):
            self._add_target(db)

    def _remove_target(self, filename):
        target_filename = filename.split('.db')[0].split('/')[-1:][0]
        attach_query = "DETACH DATABASE '{}'".format(target_filename)
        res = self.query(attach_query)
        if type(res) is Exception:
            raise res
        del self._active_dbs[target_filename]
        return target_filename

    def _add_target(self, filename):
        target_date = filename.split('.db')[0].split('_')[-3:]
        target_filename = filename.split('.db')[0].split('/')[-1:][0]
        attach_query = "ATTACH DATABASE '{}' AS {}".format(filename, target_filename)
        res = self.query(attach_query)
        if type(res) is Exception:
            raise res
        entry = {'path' :filename,
                'year': target_date[0],
                'month': target_date[1],
                'day': target_date[2]}
        self._active_dbs[target_filename] = entry
        return target_filename, entry

    def scoped_query(self, database, aggregation, time_slice):
        query, generated_time_slice = generate_sql(aggregation,time_slice )
        target = '{}.events'.format(database)
        prepared_query = query.format(db=target, slice=generated_time_slice)
        result = self.query(prepared_query)
        return result