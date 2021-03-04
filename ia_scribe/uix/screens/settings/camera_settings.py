from os.path import join, dirname

from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import DictProperty, ObjectProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from ia_scribe.tasks.camera import PopulateCamerasPropertiesTask

Builder.load_file(join(dirname(__file__), 'camera_settings.kv'))


class CameraSettingsScreen(Screen):

    sections_widgets = DictProperty()
    about_screen = ObjectProperty(None)
    camera_config = ObjectProperty(None)


    def __init__(self, **kwargs):
        super(CameraSettingsScreen, self).__init__(**kwargs)

    def on_pre_enter(self, *args):
        self.generate_from_camera_config()

    def generate_from_camera_config(self):
        self.camera_config = self.about_screen.scribe_widget.cameras.get_current_config()
        cfilew = ConfigFileWidget()

        for (key, value) in self.camera_config.items():
            section_root = ConfigFileSectionWidget(key)
            self.sections_widgets[key] = section_root
            if value is not None:
                for k, v in value.items():
                    config_widget = ConfigFileSectionValueWidget(k, v)
                    section_root.ids['_insert'].add_widget(config_widget)
                cfilew.add_widget(section_root)

        self.ids['bl_vector'].add_widget(cfilew)

    def on_leave(self):
        self.ids['bl_vector'].clear_widgets()

    def schedule_camera_sync(self):
        self.ids['bl_vector'].clear_widgets()
        self.generate_from_camera_config()
        camera_task = PopulateCamerasPropertiesTask(camera_system=self.about_screen.scribe_widget.cameras,
                                                    scheduling_callback=self.about_screen.scribe_widget.task_scheduler.schedule,
                                                    update_callback=self.update_property_callback)
        self.about_screen.scribe_widget.task_scheduler.schedule(camera_task)

    def update_property_callback(self, side, property, value):
        section_root = self.sections_widgets[side]
        config_widget = ConfigFileSectionValueWidget(property, value)
        section_root.ids['_insert'].add_widget(config_widget)


class ConfigFileWidget(GridLayout):

    def __init__(self, **kwargs):
        super(ConfigFileWidget, self).__init__(**kwargs)


class ConfigFileSectionWidget(GridLayout):

    value = ObjectProperty(None)

    def __init__(self, value, **kwargs):
        self.value = str(value)
        super(ConfigFileSectionWidget, self).__init__(**kwargs)


class ConfigFileSectionValueWidget(GridLayout):

    key = ObjectProperty(None)
    value = ObjectProperty(None)

    def __init__(self, key, value, **kwargs):
        self.value = str(value)
        self.key = str(key)
        super(ConfigFileSectionValueWidget, self).__init__(**kwargs)
