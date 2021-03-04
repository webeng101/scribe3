from os.path import join, dirname

from kivy.clock import mainthread
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.logger import Logger

from ia_scribe.uix.screens.calibration.widget.calibration_widget import CalibrationWidget
from ia_scribe.uix.screens.calibration.widget.calibration_widget import CalibrationWidgetFoldout
from ia_scribe.uix.screens.calibration.widget.single_calibration_widget import SingleCalibrationWidget

Builder.load_file(join(dirname(__file__), 'calibration.kv'))


class CalibrationScreen(Screen):

    scribe_widget = ObjectProperty(None)
    screen_manager = ObjectProperty(None)
    target_screen = ObjectProperty('capture_screen')
    target_extra = ObjectProperty(allownone=True)

    def on_pre_enter(self, *args):
        # self.query_cameras()
        self.ids['_calibration_box'].clear_widgets()
        info_box = CalibrationInfoMessage()
        info_box.rescan_func = self._next_frame_query_cameras
        info_box.reload_cameras = self._next_frame_reload_cameras
        self.ids['_calibration_box'].add_widget(info_box)

    def on_leave(self, *args):
        self.target_extra = None
        for widget in self.ids['_calibration_box'].children:
            if isinstance(widget, (CalibrationWidget, SingleCalibrationWidget)):
                widget.use_tooltips = False
            elif isinstance(widget, CalibrationWidgetFoldout):
                widget.ids.image_menu_bar.use_tooltips = False

    @mainthread
    def _next_frame_query_cameras(self):
        self.query_cameras()
    @mainthread
    def _next_frame_reload_cameras(self):
        self.reload_cameras()

    def reload_cameras(self):
        Logger.info('CalibrationScreen::Reloading cameras...')
        self.scribe_widget.cameras.initialize()

    def update_property_callback(self, *args, **kwargs):
        Logger.info('CalibrationScreen::update: {}{}'.format(args, kwargs))

    def query_cameras(self):
        Logger.info("CalibrationScreen::Querying cameras")
        self.reload_cameras()
        self.ids['_calibration_box'].clear_widgets()
        num_cameras = self.scribe_widget.cameras.get_num_cameras()

        if num_cameras not in [1, 2, 3]:
            error_box = CalibrationErrorMessage()
            error_box.error_msg = 'Number of cameras: {n}\n' \
                                  'You must have one two, or three cameras connected!'.format(n=num_cameras)
            error_box.rescan_func = self.query_cameras
            self.ids['_calibration_box'].add_widget(error_box)
            return


        b_single = True if self.scribe_widget.cameras.get_num_cameras() == 1 else False
        if b_single:
            calibration_box = SingleCalibrationWidget(scribe_widget=self.scribe_widget)
            calibration_box.screen_manager = self.screen_manager
            calibration_box.callibration_screen = self
            calibration_box.target_screen = self.target_screen
            calibration_box.target_extra = self.target_extra
            calibration_box.ids.image_menu_bar.attach_tooltip_to = self
            foldout_widget = calibration_box.foldout_widget
            if foldout_widget:
                foldout_widget.ids.image_menu_bar.attach_tooltip_to = self
        else:
            calibration_box = CalibrationWidget(scribe_widget=self.scribe_widget)
            calibration_box.screen_manager = self.screen_manager
            calibration_box.callibration_screen = self
            calibration_box.target_screen = self.target_screen
            calibration_box.target_extra = self.target_extra
            calibration_box.ids.left_image_menu_bar.attach_tooltip_to = self
            calibration_box.ids.right_image_menu_bar.attach_tooltip_to = self
            foldout_widget = calibration_box.foldout_widget
            if foldout_widget:
                foldout_widget.ids.image_menu_bar.attach_tooltip_to = self
        calibration_box.use_tooltips = True
        self.ids['_calibration_box'].add_widget(calibration_box)


# CalibrationErrorMessage
# _________________________________________________________________________________________
class CalibrationErrorMessage(BoxLayout):
    error_msg = StringProperty()
    button_text = StringProperty('Scan for cameras again')
    rescan_func = ObjectProperty(None)


# CalibrationInfoMessage
# _________________________________________________________________________________________
class CalibrationInfoMessage(BoxLayout):
    rescan_func = ObjectProperty(None)
    reload_cameras = ObjectProperty(None)
