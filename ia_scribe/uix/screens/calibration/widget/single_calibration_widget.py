import os
import shutil
import tempfile
import webbrowser
from functools import partial
from os.path import join, dirname

from PIL import Image
from kivy import Logger
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.cameras import camera_system
from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.uix.behaviors.tooltip import TooltipControl
from ia_scribe.uix.components.file_chooser import FileChooser
from ia_scribe.uix.components.poppers.popups import ScribeLearnMorePopup, InfoPopup
from ia_scribe.utils import convert_scandata_angle_to_thumbs_rotation
from ia_scribe.config.config import Scribe3Configuration

Builder.load_file(join(dirname(__file__), 'single_calibration_widget.kv'))


class SingleCalibrationWidget(BoxLayout):

    screen_manager = ObjectProperty(None)
    scribe_widget = ObjectProperty(None)
    callibration_screen = ObjectProperty(None)
    loading_image = StringProperty(LOADING_IMAGE)
    cam_port = StringProperty()
    target_screen = ObjectProperty('capture_screen')
    target_extra = ObjectProperty(allownone=True)

    use_tooltips = BooleanProperty(False)

    def __init__(self, scribe_widget=scribe_widget, **kwargs):
        super(SingleCalibrationWidget, self).__init__(**kwargs)
        self.scribe_widget = scribe_widget
        self.image = None
        self.thumb = None
        self.foldout_image = None
        self.foldout_thumb = None
        self.foldout_widget = None
        self.config = Scribe3Configuration()
        if scribe_widget.cameras.get_camera_port('foldout') is None:
            self.cam_port = ''
        else:
            self.cam_port = scribe_widget.cameras.get_camera_port('foldout')

        self.capture_images()
        Clock.schedule_once(self._bind_image_menus)

    def _bind_image_menus(self, *args):
        menu_bar = self.ids.image_menu_bar
        menu_bar.bind(on_option_select=self.on_image_menu_option)
        if self.foldout_widget:
            menu = self.foldout_widget.ids.image_menu_bar
            menu.bind(on_option_select=self.on_foldout_image_menu_option)

    def on_image_menu_option(self, menu, option):
        if option == 'view_source':
            self.show_image(self.image)
        elif option == 'export':
            self.start_export_filechooser(self.image)
        elif option == 'rotate':
            self.rotate_image()

    def on_foldout_image_menu_option(self, menu, option):
        if option == 'view_source':
            self.show_image(self.foldout_image)
        elif option == 'export':
            self.start_export_filechooser(self.foldout_image)

    def start_export_filechooser(self, source_path):
        if source_path is not None:
            filename = os.path.basename(source_path)
            default_path = join(os.path.expanduser('~'), filename)
            root, ext = os.path.splitext(source_path)
            filters = [
                ['{} image file'.format(ext),
                 '*{}'.format(ext.lower()),
                 '*{}'.format(ext.upper())]
            ]
            filechooser = FileChooser()
            callback = partial(self.on_file_chooser_selection, source_path)
            filechooser.bind(on_selection=callback)
            filechooser.save_file(title='Export image',
                                  icon='./images/window_icon.png',
                                  filters=filters,
                                  path=default_path)

    def on_file_chooser_selection(self, source_path, chooser, selection):
        if selection:
            destination_path = selection[0]
            root, ext = os.path.splitext(source_path)
            if not destination_path.endswith(ext):
                destination_path += ext
            self.export_image(source_path, destination_path)

    @staticmethod
    def show_image(path):
        try:
            firefox = webbrowser.get('firefox')
            firefox.open(path)
        except Exception as e:
            Logger.exception('Calibration: Unable to open image "{}", error: {}'
                             .format(path, e))

    @staticmethod
    def export_image(source, destination):
        try:
            shutil.copyfile(source, destination)
            Logger.info('Calibration: Image exported from "{}" to "{}"'
                        .format(source, destination))
        except shutil.Error:
            Logger.exception('Calibration: Image source path are the same. '
                             'Source "{}", destionation "{}"'
                             .format(source, destination))
        except IOError:
            Logger.exception('Calibration: Destination "{}" is not writable'
                             .format(destination))
        except Exception as e:
            Logger.exception('Calibration: Unable to export image from "{}" '
                             'to "{}", error: {}'.format(source, destination, e))

    def capture_images(self):
        if self.cam_port != '':
            page = self.ids['_cam_image']
            page.source = self.loading_image

            self.clean_temp_images()

            f = tempfile.NamedTemporaryFile(prefix='calibration',
                                            suffix='.jpg', delete=False)
            self.image = f.name
            f.close()

            f = tempfile.NamedTemporaryFile(prefix='calibration_thumb',
                                            suffix='.jpg', delete=False)
            self.thumb = f.name
            f.close()

            camera_kwargs = {
                camera_system.KEY_SIDE: 'foldout',
                camera_system.KEY_PATH: self.image,
                camera_system.KEY_THUMB_PATH: self.thumb,
                camera_system.KEY_IMAGE_WIDGET: page,
                camera_system.KEY_CALLBACK: self.show_image_callback
            }
            self.scribe_widget.foldout_queue.put(camera_kwargs)

    def rotate_image(self):
        Logger.info("rotate image called: ")
        angle = 90
        initial_rotation_value = self.config.get_integer('default_single_camera_rotation',180)
        rotated_value = (initial_rotation_value + angle) % 360

        self.config.set('default_single_camera_rotation', rotated_value)

        rotate_by = convert_scandata_angle_to_thumbs_rotation(
            self.config.get_integer('default_single_camera_rotation'), angle)

        image = Image.open(self.image)
        image = image.rotate(rotate_by, expand=True)
        image.save(self.thumb, 'JPEG', quality=100)
        self.ids['_cam_image'].reload()
        Logger.info('SingleCalibrationScreen: rotated preview by {} degrees to {}'
                    .format(angle, self.config.get_integer('default_single_camera_rotation')))

    def clean_temp_images(self):
        for image in (self.foldout_image, self.foldout_thumb):
            if image is not None and os.path.exists(image):
                os.unlink(image)

    def show_image_callback(self, report, *args):
        """This function modifies UI elements and needs to be scheduled on the
        main thread.
        """
        thumb_path = report[camera_system.KEY_THUMB_PATH]
        img_obj = report[camera_system.KEY_IMAGE_WIDGET]
        img_obj.source = thumb_path
        self.ids.box_bottons.disabled = False

    @staticmethod
    def parse_gphoto_output(output):
        value = ''
        for line in output.split('\n'):
            if line.startswith('Current:'):
                value = line[8:].strip()
                break
        return value

    def show_config_error(self, setting, value, current_val, side):
        popup = InfoPopup(
            title='Camera Configuration Error',
            auto_dismiss=False,
            text_ok='Retry'
        )
        popup.message = '\n\n'.join(
            ['The {}-page camera is not configured correctly.'.format(side),
             'The setting {} should be set to {},\n'
             'but it is set to {}.'.format(setting, value, current_val),
             'Note that the {}-page camera is mounted '
             'OPPOSITE the page it is capturing'.format(side)]
        )
        popup.bind(on_submit=self._on_config_error_popup_submit)
        popup.open()

    def _on_config_error_popup_submit(self, popup, *args):
        popup.dismiss()
        self.callibration_screen.query_cameras()

    def reshoot_button(self):
        self.ids.box_bottons.disabled = True
        self.clean_temp_images()
        self.capture_images()

    @staticmethod
    def show_help_popup():
        popup = ScribeLearnMorePopup()
        popup.open()

    def done_button(self):
        '''Main thread
        '''
        # self.check_camera_config()
        self.ids.box_bottons.disabled = True
        self.clean_temp_images()
        self.scribe_widget.cameras.set_calibrated()
        self.goto_target_screen()

    def goto_target_screen(self):
        screen = self.screen_manager.get_screen(self.target_screen)
        screen.target_extra = self.target_extra
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = self.target_screen

    def exif_tag(self, tag):
        return "Unavailable"

    def on_use_tooltips(self, widget, use_tooltips):
        stack = self.children[:]
        while stack:
            widget = stack.pop()
            if isinstance(widget, TooltipControl):
                widget.use_tooltips = use_tooltips
            stack.extend(widget.children)
