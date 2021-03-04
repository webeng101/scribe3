from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import DictProperty, ObjectProperty
from kivy.uix.screenmanager import Screen

from ia_scribe.uix.components.rst.rst import RestructuredTextDocument
from ia_scribe.tasks.help_center import LoadHelpDocumentsTask

from ia_scribe import scribe_globals

Builder.load_file(join(dirname(__file__), 'help_center.kv'))

HELP_SECTIONS = [
    {'text': 'Scribe3 intro',
     'file': join(scribe_globals.APP_WORKING_DIR, 'README.md'),
     'icon': 'ia_logo_black_small.png',
     'key': 'home',
     'state': 'down',
     'group': 'help_menu',
     'color': 'transparent',
     'text_color': [0, 0, 0, 1],
     },
    {'text': 'Changelog',
     'file': join(scribe_globals.APP_WORKING_DIR, 'CHANGELOG.md'),
     'icon': 'baseline_calendar_today_black_48dp.png',
     'key': 'changelog',
     'group': 'help_menu',
     'color': 'transparent',
     'text_color': [0, 0, 0, 1],
     },
    {'text': 'CLI',
     'file': join(scribe_globals.APP_WORKING_DIR, 'cli', 'README.md'),
     'icon': 'baseline_navigate_next_black_48dp.png',
     'key': 'cli',
     'group': 'help_menu',
     'color': 'transparent',
     'text_color': [0, 0, 0, 1],
     },
]


class HelpCenterScreen(Screen):

    scribe_widget = ObjectProperty(None)
    screen_manager = ObjectProperty(None)
    task_scheduler = ObjectProperty(None)
    displayed_text = ObjectProperty('Welcome to the Scribe3 Help center\n'
                                    '===========\n'
                                    'Select an entry on the left to see the associated help topic.')
    help_section_widgets = DictProperty()

    def __init__(self, **kwargs):
        if 'task_scheduler' in kwargs:
            self.task_scheduler = kwargs['task_scheduler']
        super(HelpCenterScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self._load_help_text()
        self._update_buttons_menu(HELP_SECTIONS)
        self.ids.rv_menu.fbind('on_selection', self._on_menu_option_selection)

    def _load_help_text(self):
        task = LoadHelpDocumentsTask(
            to_load=HELP_SECTIONS,
            callback=self._load_help_text_callback,
        )
        self.task_scheduler.schedule(task)

    def _load_help_text_callback(self, task, *args):
        self.help_section_widgets = task.result

    def _update_buttons_menu(self, items):
        self.ids.rv_menu.data = items

    def _on_menu_option_selection(self,  menu, selection):
        selected = selection[0]
        self.displayed_text = self.help_section_widgets.get(selected['key'])

