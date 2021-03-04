import copy
import webbrowser
import xml.etree.ElementTree as et
from functools import partial
from os.path import join, dirname, exists

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.parser import parse_color
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import (Screen, SlideTransition,
                                    ScreenManagerException)
from kivy.uix.textinput import TextInput

from ia_scribe import scribe_globals
from ia_scribe.book.metadata import (get_metadata,
                                     get_collections_from_metadata)
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.scribe_globals import IMAGES_SETTINGS_DIR, NOTES_DIR
from ia_scribe.uix.behaviors.hover import HoverBehavior
from ia_scribe.uix.behaviors.tooltip import TooltipScreen
from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.form.form_inputs import SettingsSwitch, SettingsInputBox
from ia_scribe.uix.components.poppers.popups import InfoPopup
from ia_scribe.uix.screens.settings.camera_settings import CameraSettingsScreen
from ia_scribe.uix.screens.settings.metadata_collection_screen import MetadataCollectionsScreen
from ia_scribe.uix.screens.settings.update_screen import UpdateWidget
from ia_scribe.update.update import UpdateStatus
from ia_scribe.uix.widgets.c2.c2_widget import C2Widget


nm = NotificationManager()

Builder.load_file(join(dirname(__file__), 'settings_screen.kv'))

config = Scribe3Configuration()

class SettingsScreen(Screen):
    scribe_widget = ObjectProperty(None)
    current_panel = ObjectProperty(None)
    sm = ObjectProperty(None)
    screens = {}
    current_screen = StringProperty()

    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.load_screen()
        self.screen_list = ['about', 'relnotes', 'general',
                            'collections', 'camera', 'update', 'c2', ]

    def load_screen(self):
        self.screens['about'] = AboutSettingsScreen()
        self.screens['general'] = GeneralSettingsScreen()
        self.screens['camera'] = CameraSettingsScreen(about_screen=self)
        self.screens['update'] = UpdateWidget()
        self.screens['relnotes'] = RelNotesWidget()
        #self.screens['catalogs'] = CatalogsWidget()
        self.screens['collections'] = MetadataCollectionsScreen()
        self.screens['c2'] = C2Screen()

    def go_screen(self, dest_screen):
        if self.current_screen != dest_screen:
            if self.screen_list.index(self.current_screen) > self.screen_list.index(dest_screen):
                direction = 'up'
            else:
                direction = 'down'
            self.ids['sm'].transition = SlideTransition()
            self.current_screen = dest_screen
            try:
                self.ids['sm'].switch_to(self.screens[dest_screen], direction=direction)
            except ScreenManagerException:
                print('Screen is already managed...')

    def on_enter(self):
        # self.scribe_widget is None when initializing this class,
        # so we add `scribe_widget` instance here instead of constructor.
        self.screens['camera'].scribe_widget = self.scribe_widget

    def on_leave(self):
        try:
            self.ids['_widget_about'].remove_widget(self.current_panel)
        except:
            pass

    def btn_about(self):
        self.go_screen('about')

    def btn_general(self):
        self.go_screen('general')

    def btn_metadata(self):
        self.go_screen('metadata')

    def btn_camera(self):
        self.go_screen('camera')

    def btn_update(self):
        self.go_screen('update')

    def show_release_notes(self):
        self.go_screen('relnotes')

    def btn_c2(self):
        self.go_screen('c2')

    def setup_manager(self, manager):
        self.sm = manager
        if self.current_screen == '':
            self.current_screen = 'general'
            self.go_screen('about')
            # Not sure why HoverButton objects do not have their child image in __init__ function
            for widget in self.ids['tab_container'].children:
                if widget.__class__.__name__ == 'HoverButton':
                    widget.ids['_img'].on_leave()
                    if widget.info == 'about':
                        widget.on_press()

    def btn_collection(self, *args):
        self.go_screen('collections')

    def btn_calibrate(self):
        calibration_screen = self.sm.get_screen('calibration_screen')
        calibration_screen.screen_manager = self.screen_manager
        calibration_screen.scribe_widget = self.scribe_widget
        calibration_screen.target_screen = 'settings_screen'
        self.sm.transition.direction = 'left'
        self.sm.current = 'calibration_screen'
        # Move to general settings screen after displaying calibration screen.
        # After calibration, screen will return here
        self.go_screen('about')
        self.ids['btn_about'].on_press()


class MetadataLabel(Label):
    metadata_key = StringProperty(None)
    color = (0, 0, 0, 1)
    pass


class AboutSettingsScreen(TooltipScreen, Screen):

    upload_widget = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(AboutSettingsScreen, self).__init__(**kwargs)
        try:
            with open(join(NOTES_DIR, 'about_display_notes.txt')) as f:
                self.ids['lb_help'].text = f.read()
        except IOError as e:
            print(e)

    def on_enter(self, *args):
        self.ids['lb_version'].text = scribe_globals.BUILD_NUMBER
        self.update_metadata()
        self.update_catalog()
        super(AboutSettingsScreen, self).on_enter()

    def on_leave(self, *args):
        super(AboutSettingsScreen, self).on_leave(*args)

    def update_metadata(self):
        """Update scanner metadata
        """
        config = get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)
        # Go trough all widgets
        # Since there are also "EmailTextInput" class instances,
        # let us see each widget has 'metadata_key' property
        for widget in self.ids['_metadata'].children:
            if hasattr(widget, 'metadata_key'):
                value = config.get(widget.metadata_key)
                if value is not None:
                    widget.text = text_type(value)
        # Easter egg
        if config.get('operator') == 'kristy@archive.org':
            rectangle = self.ids['_about_header'].canvas.before.children[1]
            rectangle.source = 'images/fidget.png'

    def update_catalog(self):
        """
        Update number of catalogs and collection sets
        :return:
        """
        try:
            collections = get_collections_from_metadata()
            self.ids['lb_col_num'].text = str(len(collections))
        except Exception as e:
            print('Failed to get catalogs: {}'.format(e))


class CatalogsWidget(Screen):
    catalogs = []
    conf_file = []

    def __init__(self, **kwargs):
        super(CatalogsWidget, self).__init__(**kwargs)


class RelNotesWidget(Screen):
    changelog = StringProperty()

    def __init__(self, **kwargs):
        super(RelNotesWidget, self).__init__(**kwargs)
        changelog_file = join(scribe_globals.APP_WORKING_DIR, 'CHANGELOG.md')
        with open(changelog_file, 'r') as f:
            self.changelog = f.read()

    def handle_ref(self, component, ref):
        webbrowser.open(ref)


class C2Screen(Screen):
    c2_help_text = StringProperty()

    def __init__(self, **kwargs):
        super(C2Screen, self).__init__(**kwargs)
        try:
            with open(join(NOTES_DIR, 'c2_display_notes.txt')) as f:
                self.c2_help_text = f.read()
        except IOError as e:
            print(e)


# SettingsScreen
# this class manages the "settings" view on the about UI
# Main thread
# _________________________________________________________________________________________
class GeneralSettingsScreen(Screen):

    scribe_widget = ObjectProperty(None)

    # __init__()
    # _____________________________________________________________________________________
    def __init__(self, **kwargs):
        super(GeneralSettingsScreen, self).__init__(**kwargs)

    # on_enter()
    #
    # _____________________________________________________________________________________
    def on_enter(self):
        # read scribe_config.yml
        # Check sound_delay value
        if config.get('sound_delay') is None:
            config.set('sound_delay', .1)
        if config.get('load_deleted') is None:
            config.set('load_deleted', False)

        # Get all widgets that we want to initialize
        widgets = [x for x in self.ids['_metadata'].children if isinstance(x, (SettingsSwitch, SettingsInputBox))]
        # For each, initialize
        for widget in widgets:
            # get value from  dict
            val = config.get(widget.metadata_key)
            validator = config.get_field_validator(widget.metadata_key)
            # set value to widget
            try:
                widget.set_value(val)
                if validator and isinstance(widget, SettingsInputBox):
                    widget.set_validator(validator)
            except ValueError as e:
                print('Failed to update new values - {}'.format(e))

    def set_switch(self, switch):
        """
        Callback function when the MetadataSwitch is switched.
        :param switch:
        :return:
        """
        metadata_key = switch.metadata_key
        if isinstance(switch, SettingsSwitch):
            switch = switch.ids.switch
        new_val = True if switch.active else False
        if config.get(metadata_key):
            config.set(metadata_key, new_val)

        if metadata_key == 'sound_delay':
            if self.ids['txt_sound_delay'].disabled:
                config.set('sound_delay', -1)

    def save_config(self):
        widgets = [x for x in self.ids['_metadata'].children if isinstance(x, (SettingsInputBox, SettingsSwitch))]
        # Update each
        for widget in widgets:
            val = widget.get_value()
            config.set(widget.metadata_key, val)

class HoverImage(Image, HoverBehavior):

    info = StringProperty('')
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(HoverImage, self).__init__(**kwargs)
        self.active = False
        Clock.schedule_once(self.on_leave)

    def on_enter(self, *args):
        if self.active:
            return
        img_file = join(IMAGES_SETTINGS_DIR, self.info + '-tab-hover.png')
        if exists(img_file):
            self.source = img_file
        else:
            self.source = join(IMAGES_SETTINGS_DIR, 'system-tab-hover.png')

    def on_leave(self, *args):
        if self.active:
            return
        img_file = join(IMAGES_SETTINGS_DIR, self.info + '-tab-inactive.png')
        if exists(img_file):
            self.source = img_file
        else:
            self.source = join(IMAGES_SETTINGS_DIR, 'system-tab-inactive.png')


class HoverButton(ColorButton):

    info = StringProperty('')

    def __init__(self, **kwargs):
        super(HoverButton, self).__init__(**kwargs)

    def on_press(self):
        """
        Walk through other HoverButtons and de-activate them
        """
        for btn in self.parent.children:
            if btn.__class__.__name__ == self.__class__.__name__ and btn != self:
                btn.ids['_img'].active = False
                btn.ids['_img'].on_leave()
        self.ids['_img'].active = True
        self.ids['_img'].source = join(IMAGES_SETTINGS_DIR,
                                       self.info + '-tab-active.png')
