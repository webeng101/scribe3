from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.uix.screenmanager import Screen

from ia_scribe.scribe_globals import NOTES_DIR
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.uix.actions.generic import ColoredYesNoActionPopupMixin
from ia_scribe.uix.actions.info import ShowInfoActionPopupMixin
from ia_scribe.update.update import UpdateManager
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.utils import restart_process

config = Scribe3Configuration()

Builder.load_file(join(dirname(__file__), 'update_screen.kv'))

ACTIONS_BY_STATE = {
    'up_to_date':
        {'icon': 'retry.png',
         'text': 'Check for update',
         'action': 'check_for_update'},
    'update_available':
        {'icon': 'baseline_cloud_download_white_48dp.png',
         'text': 'Download & install',
         'action': 'do_update', },
    'updating':
        {'icon': '',
         'text': '',},
    'updated':
        {'icon': 'done.png',
         'text': 'Restart',
         'action': 'restart_app'},
    'error':
        {'icon': 'retry.png',
         'text': 'Check for update',
         'action': 'check_for_update'},
    'unknown':
        {'icon': 'retry.png',
         'text': 'Check for update',
         'action': 'check_for_update'},
}

ACTION_NAMES = {
    'check_for_update': 'check for update',
    'do_update': 'go ahead with installing the update',
    'restart_app': 'restart the app',
                }

class UpdateWidget(Screen):
    update_status = StringProperty()
    action_button_icon = StringProperty('')
    action_button_text = StringProperty('')
    current_version = StringProperty()
    update_channel = StringProperty()
    candidate_version = StringProperty()
    build_tag = StringProperty()
    history = ListProperty()
    help_text = StringProperty()
    auto_update = BooleanProperty()

    def __init__(self, **kwargs):
        super(UpdateWidget, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)
        self.update_manager = UpdateManager()
        self.update_manager.subscribe(self._update_manager_event_handler)
        try:
            with open(join(NOTES_DIR, 'about_update_notes.txt')) as f:
                self.help_text = f.read()
        except Exception as e:
            print(e)

    def _postponed_init(self, *args):
        self.update_status = self.update_manager.get_update_status(human_readable=True)

    def _update_manager_event_handler(self, event, manager):
        Clock.schedule_once(self._update_properties)

    def _update_properties(self, *args):
        self.update_status = str(self.update_manager.get_update_status(human_readable=True))
        self.current_version = self.update_manager.current_version or '--'
        self.candidate_version = self.update_manager.update_version or '--'
        self.update_channel = self.update_manager.update_channel or '--'
        self.auto_update = config.is_true('auto_update')
        self.action_button_icon = ACTIONS_BY_STATE[self.update_manager.get_update_status()]['icon']
        self.action_button_text = ACTIONS_BY_STATE[self.update_manager.get_update_status()]['text']

    def on_auto_update(self, screen, value):
        current_val = config.is_true('auto_update')
        if value != current_val:
            config.set('auto_update', value)

    def action_button_press(self, *args):
        candidate_action = ACTIONS_BY_STATE[self.update_manager.get_update_status()]['action']
        candidate_action_hr = ACTION_NAMES[candidate_action]
        concrete_action = getattr(self, candidate_action)

        self.action = ColoredYesNoActionPopupMixin(
            action_function=concrete_action,
            title='Are you sure?',
            message='Do you want to {}?'.format(candidate_action_hr),
        )
        self.action.display()

    def do_update(self, *args):
        result = self.update_manager.do_update(task_handler_class=GenericUIHandler)
        if not result:
            message = 'No update is available at this time.'
            self.action = ShowInfoActionPopupMixin(message=message)
            self.action.display()

    def check_for_update(self, *args):
        self.update_manager.do_check_update(task_handler_class=GenericUIHandler)

    def restart_app(self, *args, **kwargs):
        restart_process()