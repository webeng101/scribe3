import datetime

from ia_scribe.breadcrumbs.config import AVAILABLE_RANGES
from ia_scribe.breadcrumbs.query import generate_sql

from ia_scribe.scribe_globals import (
    METRICS_DIR,
)
from ia_scribe.breadcrumbs.config import AGGREGATIONS, AVAILABLE_SLICES
from ia_scribe.database.metrics_database import MetricsDatabase
from ia_scribe.breadcrumbs.stats_collector import db as todays_events
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()

db = MetricsDatabase(basedir=METRICS_DIR,
                     metrics=AGGREGATIONS,
                     slices=AVAILABLE_SLICES)

if not config.is_true('stats_disabled'):
    db.start()

def query_today(name, slice='daily', where=None):
    today_query, generated_time_slice = generate_sql(name, slice, where=where)
    prepared_query = today_query.format(db='events', slice=generated_time_slice)
    result = todays_events.query(prepared_query)
    return result


def rollup(aggregation, results):
    rollup_strategy = aggregation['rollup_strategy'] if 'rollup_strategy' in aggregation else sum
    rollup_type = aggregation['rollup_type'] if 'rollup_type' in aggregation else float
    if hasattr(aggregation, 'group_by'):
        ret = rollup_strategy([x[1] for x in results])
    else:
        ret = rollup_strategy([rollup_type(x[1]) for x in results])
    return ret


def trim_by_range(dataset, slice, range_start, range_end):
    if slice == 'weekly':
        weekday = range_end.isoweekday()
        start = range_end - datetime.timedelta(days=weekday)
        datetime_dates = [start + datetime.timedelta(days=d) for d in range(7)]
        dates = [x.strftime(AVAILABLE_SLICES['daily']) for x in datetime_dates]
        in_range = lambda x: x[0] in dates
    else:
        datetime_range_start = datetime.datetime(range_start.year, range_start.month, range_start.day)
        datetime_range_end = datetime.datetime(range_end.year, range_end.month, range_end.day)
        parsed_timestamp = lambda x: datetime.datetime.strptime(x, AVAILABLE_SLICES[slice])
        in_range = lambda x: datetime_range_end >= parsed_timestamp(x[0]) >= datetime_range_start
    ret = [x for x in dataset if in_range(x)]
    return ret


def get_stats_by_interval(name, slice='daily', range_start=None, range_end=None, where=None, scalar_slice=None, ):
    aggregation = AGGREGATIONS[name]
    if slice == 'weekly':
        search_slice = 'daily'
    else:
        search_slice = slice
    res = db.get_metric(name, search_slice, where)
    todays_res = query_today(name, search_slice, where)
    for item in todays_res:
        if item not in res:
            res.append(item)
    trimmed_values = trim_by_range(res, slice, range_start, range_end)
    if slice == scalar_slice:
        return_value = rollup(aggregation, trimmed_values)
    else:
        return_value = trimmed_values
    return aggregation, return_value


def get_timeless_stat(name, slice, where):
    aggregation = AGGREGATIONS[name]
    query_res = db.get_metric(name, slice, where)
    res = [x[0] for x in query_res]
    todays_res = query_today(name, slice, where)
    for item in todays_res:
        if item[0] not in res:
            res.append(item[0])
    return aggregation, res


def get_stats_by_range(name, range, slice='daily', where=None):
    selected_range = AVAILABLE_RANGES[range]
    aggregation = AGGREGATIONS[name]
    if '{slice}' not in aggregation['select']:
        # this query does not return a timeseries
        return get_timeless_stat(name, slice, where)
    else:
        return get_stats_by_interval(name, slice,
                                 selected_range['range_start'],
                                 selected_range['range_end'],
                                 where,
                                 selected_range['scalar_slice'],)