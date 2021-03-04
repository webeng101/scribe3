from ia_scribe.breadcrumbs.stats_collector import _log_event

def book_adapter(payload, event_type):
    if event_type in ['state_change', 'identifier-changed',
                      'book_update', 'book_created', 'book_deleted',
                      'reloaded_metadata', 'reloaded_scandata']:
        _log_event('library', event_type, payload.status, payload.uuid)

def config_adapter(event_type, payload):
    key, value = payload
    _log_event('config', event_type, value, key)

def screen_manager_adapter(screen_manager, current_screen):
    screen_in= screen_manager.transition.screen_in
    screen_out = screen_manager.transition.screen_in
    _log_event('screen_manager', 'screen_changed', current_screen)

def cameras_adapter(cameras, camera_ports):
    print(cameras, camera_ports)

def top_bar_adapter(top_bar, option):
    _log_event('top_bar', 'option_selected', option)

def task_scheduler(event_name, scheduler, task_info):
    task = task_info.get('task')
    facet = task.book.uuid if hasattr(task, 'book') else None
    if task is None:
        pass
    else:
        _log_event('task_scheduler', event_name, task.name, facet)

def no_op_adapter(*args ,**kwargs):
    pass