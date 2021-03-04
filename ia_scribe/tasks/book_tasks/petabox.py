from ia_scribe.ia_services.btserver import get_ia_session

def get_pending_catalog_tasks(identifier):
    ia_session = get_ia_session()
    item = ia_session.get_item(identifier)
    tasks = item.get_task_summary()
    tasks_list = [x for x in item.tasks if x.get('status') in ['running', 'queued']] if item.tasks else []
    return tasks['running'] + tasks['queued'], tasks_list


def get_repub_state(book):
    session = get_ia_session()
    item = session.get_item(book.identifier)
    repub_state = int(item.metadata['repub_state'])
    return repub_state