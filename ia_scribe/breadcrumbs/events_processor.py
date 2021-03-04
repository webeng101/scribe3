import os, shutil
from ia_scribe.utils import all_files_under
from ia_scribe.breadcrumbs.stats_collector import get_db_filename
from ia_scribe.breadcrumbs.config import AGGREGATIONS, AVAILABLE_SLICES, AVAILABLE_RANGES
from ia_scribe.database.metrics_database import MetricsDatabase

from ia_scribe.scribe_globals import (
    STATS_DIR,
    METRICS_DIR,
    PROCESSED_STATS_DIR
)

from ia_scribe.database.database_range import DatabaseRange

_db = MetricsDatabase(basedir = METRICS_DIR,
                      metrics= AGGREGATIONS,
                      slices= AVAILABLE_SLICES)


def put_in_cold_storage(aggregator, database):
    filename = aggregator._remove_target(database)
    shutil.move(database, os.path.join(PROCESSED_STATS_DIR, filename))


def store_aggregations(results):
    for metric in results:
        for time_slice, values in results[metric].items():
            _db.update_metric(metric, time_slice, values)
    return True


def load_database(aggregator, db_path):
    target_filename, entry = aggregator._add_target(db_path)
    return target_filename


def aggregate_from_events(aggregator, database):
    ret = {}
    for aggregation in AGGREGATIONS:
        ret[aggregation] = {}
        for time_slice in AVAILABLE_SLICES:
            res = aggregator.scoped_query(database, aggregation, time_slice)
            ret[aggregation][time_slice] = res
    return ret


def process_database(aggregator, db_path):
    database = load_database(aggregator, db_path)
    aggregation_results = aggregate_from_events(aggregator, database)
    try:
        result = store_aggregations(aggregation_results)
    except Exception as e:
        result = None
    if result:
        put_in_cold_storage(aggregator, db_path)
    else:
        print('------>>> No result processing {} - Error {}'.format(db_path, e))


def process_metrics_dir():
    aggregator = DatabaseRange(
        name='aggregator',
        basedir=METRICS_DIR,
    )
    aggregator.start()

    today = get_db_filename()
    for db in all_files_under(STATS_DIR):
        if db == today:
            continue
        if not db.endswith('.db'):
            continue
        process_database(aggregator, db)

    aggregator.stop()
    del aggregator
