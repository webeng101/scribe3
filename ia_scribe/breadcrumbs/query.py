from ia_scribe.breadcrumbs.config import AGGREGATIONS, AVAILABLE_SLICES


def generate_sql(name, slice='daily', range_start=None, range_end=None, where=None):
    BASESTRING = 'SELECT {select} FROM {{db}}'
    aggregation = AGGREGATIONS[name]

    concrete_slice = AVAILABLE_SLICES[slice]
    time_slice = '''strftime(\'{concrete_slice}\',datetime(time, 'unixepoch', 'localtime') )'''.format(
        concrete_slice=concrete_slice)

    select_statement = ','.join(aggregation['select'])

    query = BASESTRING.format(select=select_statement, )

    if aggregation.get('where'):
        query += ' WHERE {}'.format(aggregation['where'])

    if range_start and range_end:
        connector = ' WHERE ' if 'WHERE' not in query else ' AND '
        query += """{connector} {row_time} >= '{range_start}' and {row_time} <= '{range_end}' """.format(
            row_time="datetime(time, 'unixepoch', 'localtime')",
            range_start=range_start,
            range_end=range_end,
            connector=connector,
        )

    if where:
        connector = ' WHERE ' if 'WHERE' not in query else ' AND '
        query += """{connector} {additional_where_clause}""".format(
            connector=connector,
            additional_where_clause=where)

    group_by_base = ' GROUP BY '

    if '{slice}' in aggregation['select']:
        group_by_base += '{slice}'

    if aggregation.get('group_by'):
        additional_group_by_clauses = ','.join(aggregation['group_by'])
        if group_by_base.endswith('BY '):
            separator = ' '
        else:
            separator = ', '
        group_by_base += separator + additional_group_by_clauses

    query += group_by_base
    return query, time_slice