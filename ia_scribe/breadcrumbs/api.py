from functools import partial
from ia_scribe.breadcrumbs import adapters
from ia_scribe.breadcrumbs.stats_collector import _log_event
from ia_scribe.breadcrumbs.config import AGGREGATIONS
from ia_scribe.breadcrumbs.oracle import get_stats_by_range
from ia_scribe.breadcrumbs.events_processor import process_metrics_dir


def process_stats():
    return process_metrics_dir()


def log_event(component, metric, value, facet=None):
    _log_event(component, metric, value, facet)


def get_data_for_operator(operator, name, interval, slice='daily'):
    if operator in [None, '']:
        return {}
    where = """operator='{}'""".format(operator)
    res = get_data(name, interval, slice, where)
    return res


def get_data(name, interval, slice='daily', where=None):
     aggregation_metadata, res_raw = get_stats_by_range(name, interval, slice, where)
     if type(res_raw) is list:
        res = res_raw \
                    if len(res_raw) > 0 \
                    else [(None, '0')]
        if type(res[0]) in [tuple, list]:
            # if it's a tuple, it's a time series
            return_val = str(res[0][-1:][0])
        else:
            return_val = res
     elif type(res_raw) in [float, int, str]:
         res = return_val = str(res_raw)
     else:
         res = return_val = [(None, '-')]

     return {'name': name,
             'title': aggregation_metadata.get('human_name', name),
             'interval': interval,
             'slice': slice,
             'description': aggregation_metadata.get('description', ''),
             'value': return_val,
             'result_set': res,
             'icon': get_icon(name)}


def get_aggregation_metadata(name):
    return AGGREGATIONS[name]


def get_available_aggregatons():
    return list(AGGREGATIONS.keys())


def get_available_aggregations_and_metadata():
    ret = []
    for name in get_available_aggregatons():
        aggregation_metadata = get_aggregation_metadata(name)
        res = [(None, '')]
        entry =  {'name': name,
                'title': aggregation_metadata.get('human_name', name),
                'slice': '',
                'interval': '',
                'description': aggregation_metadata.get('description', ''),
                'value': str(res[0][-1:][0]),
                'result_set': res,
                'icon': get_icon(name)}
        ret.append(entry)
    return ret


def get_icon(metric_name):
    if 'uploaded' in metric_name:
        return 'button_upload_book_normal.png'
    elif 'downloaded' in metric_name:
        return 'download_black.png'
    elif 'task' in metric_name:
        return 'tasks_black.png'
    elif 'camera' in metric_name:
        return 'dslr-camera.png'
    elif 'capture' in metric_name:
        return 'dslr-camera.png'
    elif'book' in metric_name:
        return 'book.png'
    elif 'operator' in metric_name:
        return 'user.png'
    elif 'app' in metric_name:
        return 'ia_logo_black_small.png'
    else:
        return 'stats_black.png'

def get_adapter(name):
    if name == 'library':
        return adapters.book_adapter
    elif name == 'config':
        return adapters.config_adapter
    elif name == 'screen_manager':
        return adapters.screen_manager_adapter
    elif name == 'cameras':
        return adapters.cameras_adapter
    elif name == 'top_bar':
        return adapters.top_bar_adapter
    elif name == 'scheduler':
        return adapters.task_scheduler
    else:
        return partial(log_event, name)