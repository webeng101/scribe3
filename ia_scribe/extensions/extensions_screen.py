import importlib
import os
import shutil
import sys

from kivy import Logger
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty
from kivy.properties import ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from ia_scribe import scribe_globals
from ia_scribe.uix.components.overlay.overlay_view import OverlayView
from ia_scribe.uix.components.poppers.popups import InfoPopup, QuestionPopup

# Imports for modules only used by extensions, so that pyinstaller
# knows to pick them up
from ia_scribe.tasks.ui_handlers import book

Builder.load_file(os.path.join(os.path.dirname(__file__), 'extensions_screen.kv'))


MODULE_BASE = 'extensions'
MODULE_BASE_DIR = os.path.join(scribe_globals.CONFIG_DIR, MODULE_BASE)

def install_extensions():
    shutil.copytree(os.path.join(scribe_globals.APP_WORKING_DIR, 'extensions'), MODULE_BASE_DIR)

if not os.path.exists(MODULE_BASE_DIR):
    install_extensions()

sys.path.insert(0, MODULE_BASE_DIR)


class ExtensionPopup(OverlayView):

    book_path = StringProperty()
    app_panel = ObjectProperty()

    def open(self, *largs):
        super(ExtensionPopup, self).open(*largs)
        #if self._window:
        #    self.app_panel.backend.book_path = self.book_path
        #    self.app_panel.backend.init()

    def on_dismiss(self):
        super(ExtensionPopup, self).on_dismiss()
        self.app_panel.clear_widgets()
        #if self._window:
        #    self.app_panel.backend.reset()

    def close_app(self):
        self.dismiss()


class ExtensionsScreen(Screen):
    index = NumericProperty(0)
    sections = ListProperty()
    callback = ObjectProperty(None)
    extension_popup = ExtensionPopup()
    errors = set()
    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        super(ExtensionsScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)


    def _postponed_init(self, *args, **kwargs):
        try:
            with open(os.path.join(scribe_globals.NOTES_DIR, 'extensions_notes.txt')) as f:
                self.ids['lb_help'].text = f.read()
        except IOError as e:
            print(e)
        self.generate_tiles()

    def import_extension_module(self, module_name):
        try:
            mod = importlib.import_module(module_name)
            Logger.debug('Loaded extension {}'.format(module_name))
            return mod, module_name
        except Exception as e:
            Logger.error('Error loading extension {}: {}'.format(module_name, e))
            self.errors.add(module_name)
            return None, module_name

    def collect_modules(self):
        self.modules = []
        modules_names = [x for x in os.listdir(MODULE_BASE_DIR) if x.endswith('app')]
        Logger.debug('Extensions directories found: {}'.format(modules_names))
        load_result = list(map(self.import_extension_module, modules_names))
        self.modules = [x[0] for x in load_result if x[0] != None]
        ret = [x[1] for x in load_result if x[0] != None]
        return ret

    def generate_tiles(self):
        loaded_modules = self.collect_modules()
        for module in loaded_modules:
            mod = [x for x in self.modules if x.__name__ == module]
            icon = mod[0].get_icon() if hasattr(mod[0], 'get_icon') else 'images/dslr-camera.png'
            description = mod[0].get_description() if hasattr(mod[0], 'get_description') else ''
            layout = ExtensionTile(module, icon=icon, description=description)
            layout.fbind(layout.EVENT_LAUNCH_EXTENSION, self.load_extension)
            self.ids['_extensions'].add_widget(layout)

    def load_extension(self, tile_object):
        extension_name = tile_object.extension_name
        mod = [x for x in self.modules if x.__name__ == extension_name]
        if len(mod) == 1:
            try:
                app = mod[0].get_app(task_scheduler = self.task_scheduler,
                                     library = self.library)
                self.extension_popup.ids['app_panel'].add_widget(app)
                self.extension_popup.open()
            except Exception as e:
                self.show_popup('error', 'extension {} has crashed on load with error:\n\n{}'.format(extension_name, e))

    def show_popup(self, title, label):
        popup = InfoPopup(
            title=title,
            message=(label),
            auto_dismiss=False
        )
        popup.bind(on_submit=popup.dismiss)
        popup.open()

    def confirm_reinstall(self):
        msg = 'Would you like to wipe your local extensions and re-install?'
        popup = QuestionPopup(
            title='Reinstall extensions?',
            message=msg,
            auto_dismiss=False
        )

        popup.bind(on_submit=self.on_confirmed_reinstall)
        popup.open()

    def on_confirmed_reinstall(self, popup, option):
        popup.dismiss()
        if option == popup.OPTION_YES:
            if os.path.exists(MODULE_BASE_DIR):
                shutil.rmtree(MODULE_BASE_DIR)
            install_extensions()
            self.ids['_extensions'].clear_widgets()
            self.generate_tiles()




class ExtensionTile(ButtonBehavior, BoxLayout):

    extension_name = StringProperty(None)
    active_user = BooleanProperty(False)
    icon = StringProperty('extension_black.png')
    description = StringProperty('no description')
    EVENT_LAUNCH_EXTENSION = 'on_event_launch_extension'

    __events__ = (EVENT_LAUNCH_EXTENSION,)

    def __init__(self, username, active_user=False, icon=None, description=None,**kwargs):
        self.extension_name = username
        if description:
            self.description = description
        self.active_user = active_user
        super(ExtensionTile, self).__init__(**kwargs)
        if self.active_user:
            self.bgcol = ( 0, 0.5, 0, 0.7)
            self.disabled = True
        if icon:
            self.icon = icon


    def on_press(self):
        self.bgcol = (0.2, 0.65, 0.8, 1)

    def on_release(self):
        self.bgcol = (1, 1, 1, 0)
        self.dispatch(self.EVENT_LAUNCH_EXTENSION)

    def on_event_launch_extension(self):
        pass

    def on_extension_name(self, *args, **kwargs):
        print('new extension loaded', args, kwargs)

    def get_pretty_name(self):
        ret = self.description
        return str(ret)


