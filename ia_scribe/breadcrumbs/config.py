import datetime

AVAILABLE_SLICES = {
    'hourly': '%Y-%m-%d-%H',
    'daily': '%Y-%m-%d',
    'weekly': '%Y-%W',
    'monthly': '%Y-%m',
    }

AVAILABLE_RANGES = {
    'past_week': {
            'range_start': datetime.datetime.today().date() - datetime.timedelta(days=7),
            'range_end': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'scalar_slice': 'weekly',
          },
    'past_month':
        {
            'range_start': datetime.datetime.today().date() - datetime.timedelta(days=30),
            'range_end': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'scalar_slice': 'monthly',
          },
    'past_year':
        {
            'range_start': datetime.datetime.today().date() - datetime.timedelta(days=365),
            'range_end': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'scalar_slice': 'yearly',
          },
    'today':
        {
            'range_start': datetime.datetime.today().date(),
            'range_end': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'scalar_slice': 'daily',
          },
    'yesterday': {
            'range_start': datetime.datetime.today().date() - datetime.timedelta(days=2),
            'range_end': datetime.datetime.today().date() - datetime.timedelta(days=1),
            'scalar_slice': 'daily',
          },
    }

AGGREGATIONS = {
    'total_captures':  {
        'human_name': '# total captures',
        'description': 'Camera shots taken',
        'select': ['{slice}', 'count(metric)'],
        'where': "metric='capture_time'",
        'rollup_select': 'time, sum(count)',
        'rollup_group_by': 'time',
        'rollup_strategy': sum,
        'rollup_type': int,
        },
    'average_capture_speed': {
        'human_name': 'Average capture speed',
        'description': 'Average capture speed',
        'select': ['{slice}', 'avg(CAST(value as REAL))'],
        'where': "metric='capture_time'",
        'rollup_select': 'time, avg(avg)',
        'rollup_group_by': 'time',
        'rollup_strategy': lambda x: sum(x)/len(x) if len(x) > 0 else 0,
        },
    'average_capture_speed_by_side': {
        'human_name': 'Capture speed by side',
        'description': 'Average capture speed',
        'select': ['{slice}', 'avg(CAST(value as REAL))', 'facet'],
        'where': "metric='capture_time'",
        'group_by': ['facet'],
        'rollup_select': 'time, avg(avg), facet',
        'rollup_group_by': 'time, facet',
        'rollup_strategy': lambda x: sum(x)/len(x)  if len(x) > 0 else 0,
        },
    'pages_per_hour_by_operator': {
        'human_name': 'Pages per hour',
        'description': 'A measure of efficiency',
        'select': ['{slice}', 'count(metric)', "strftime('%Y-%m-%d-%H',datetime(time, 'unixepoch', 'localtime'))", 'operator'],
        'where': "metric='capture_time'",
        'group_by': ["strftime('%Y-%m-%d-%H',datetime(time, 'unixepoch', 'localtime'))", 'operator'],
        'rollup_select': 'time, avg(count), operator',
        'rollup_group_by': 'time, operator',
        'rollup_strategy': lambda x: sum(x)/len(x) if len(x) > 0 else 0,
        },
    'total_books_uploaded': {
        'human_name': 'Uploads total',
        'description': 'Number of books uploaded',
        'select': ['{slice}', 'count(value)'],
        'where': "metric='state_change' and value='uploaded'",
        'rollup_select': 'time, sum(count)',
        'rollup_group_by': 'time',
        'rollup_type': int,
        },
    'total_books_downloaded': {
        'human_name': 'Downloads total',
        'description': 'Books downloaded for foldouts or corrections',
        'select': ['{slice}', 'count(value)'],
        'where': "metric='state_change' and value='downloaded'",
        'rollup_select': 'time, sum(count)',
        'rollup_group_by': 'time',
        'rollup_type': int,
    },
    'events_by_component': {
        'human_name': 'Events by component',
        'description': 'Break down app activity by subsystem',
        'select': ['{slice}', 'count(value)', 'component'],
        'group_by': ['component',],
        'rollup_select': 'time, sum(count), component',
        'rollup_group_by': 'time, component',
        'rollup_type': int,
    },
    'screen_changes': {
        'human_name': 'Screen changes',
        'description': 'Number of time a screen was changed',
        'select': ['{slice}', 'count(value)'],
        'where': "component='screen_manager'",
        'rollup_select': 'time, sum(count)',
        'rollup_group_by': 'time',
        'rollup_type': int,
    },
    'captures_by_operator': {
        'human_name': 'Pages captured by operator over time',
        'description': 'See your capture performance',
        'select': ['{slice}', 'count(value)', 'operator'],
        'group_by': ['operator',],
        'where': "metric='capture_time'",
        'rollup_select': 'time, sum(count), operator',
        'rollup_group_by': 'time, operator',
        'rollup_type': int,
        'rollup_strategy': sum,
    },
    'uploads_by_operator': {
        'human_name': 'Uploads/operator over time',
        'description': 'Total number of books uploaded by each operator',
        'select': ['{slice}', 'count(value)', 'operator'],
        'where': "metric='state_change' and value='uploaded'",
        'group_by': ['operator',],
        'rollup_select': 'time, sum(count), operator',
        'rollup_group_by': 'time, operator',
        'rollup_type': int,
        'rollup_strategy': sum,
        },
    'books_created_by_operator': {
        'human_name': 'Books created by operator',
        'description': 'Number of books created by an operator',
        'select': ['{slice}', 'count(value)', 'operator'],
        'where': "component='library' and metric='book_created'",
        'group_by': ['operator',],
        'rollup_select': 'time, sum(count), operator',
        'rollup_group_by': 'time, operator',
        'rollup_type': int,
        'rollup_strategy': sum,
        },
    'app_sessions': {
        'human_name': 'App sessions',
        'description': 'Nuber of times Scribe3 was started up',
        'select': ['{slice}', 'count(value)'],
        'where': "metric='started' and component='app'",
        'rollup_select': 'time, sum(count)',
        'rollup_group_by': 'time',
        'rollup_type': int,
        },
    'operators': {
        'human_name': 'Operators',
        'description': 'Seen operators, all time',
        'select': ["operator"],
        'group_by': ['operator'],
        'rollup_select': 'operator',
        'rollup_group_by': 'operator',
        'rollup_strategy': list,
        'rollup_type': str,
        'timeless': True,
        },
    'active_operators': {
        'human_name': 'Active operators',
        'description': 'Operators with recorded history',
        'select': ['{slice}', 'count(DISTINCT operator)'],
        'rollup_select': 'time, max(count)',
        'rollup_group_by': 'time',
        'rollup_strategy': max,
        'rollup_type': int,
        },

}

'''

INACTIVE TASKS

'tasks_ran': {
    'human_name': 'Tasks',
    'description': 'Number of tasks that ran',
    'select': ['{slice}', 'count(value)'],
    'where': "component='task_scheduler'",
    'rollup_select': 'time, sum(count)',
    'rollup_group_by': 'time',
    'rollup_type': int,
},
'tasks_by_event': {
    'human_name': 'Tasks by event',
    'description': 'Details of task subsystem',
    'select': ['{slice}', 'count(value)', 'metric'],
    'where': "component='task_scheduler'",
    'group_by': ['metric',],
    'rollup_select': 'time, sum(count), metric',
    'rollup_group_by': 'time, metric',
    'rollup_type': int,
},
'tasks_by_type': {
    'human_name': 'Tasks by type',
    'description': 'Details of task subsystem activity',
    'select': ['{slice}', 'count(value)', 'value'],
    'where': "component='task_scheduler'",
    'group_by': ['value',],
    'rollup_select': 'time, sum(count), value',
    'rollup_group_by': 'time, value',
    'rollup_type': int,
},


'''