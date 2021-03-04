import os
import shutil
import tempfile
import webbrowser
from functools import partial
from os.path import join, dirname

from kivy import Logger
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.cameras import camera_system
from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.uix.behaviors.tooltip import TooltipControl
from ia_scribe.uix.screens.calibration.widget.foldout_widget import \
    CalibrationWidgetFoldout
from ia_scribe.uix.components.file_chooser import FileChooser
from ia_scribe.uix.components.poppers.popups import ScribeLearnMorePopup, InfoPopup

Builder.load_file(join(dirname(__file__), 'calibration_widget.kv'))


class CalibrationWidget(BoxLayout):

    screen_manager = ObjectProperty(None)
    scribe_widget = ObjectProperty(None)
    callibration_screen = ObjectProperty(None)
    loading_image = StringProperty(LOADING_IMAGE)
    left_port = StringProperty()
    right_port = StringProperty()
    target_screen = ObjectProperty('capture_screen')
    target_extra = ObjectProperty(allownone=True)
    use_tooltips = BooleanProperty(False)
    """Pass this value to `use_tooltips` of every TooltipControl child widget.
    """

    def __init__(self, scribe_widget=scribe_widget, **kwargs):
        super(CalibrationWidget, self).__init__(**kwargs)
        self.scribe_widget = scribe_widget
        self.left_image = None
        self.left_thumb = None
        self.right_image = None
        self.right_thumb = None
        self.foldout_image = None
        self.foldout_thumb = None
        self.foldout_widget = None
        self.left_port = scribe_widget.cameras.get_camera_port('left')
        self.right_port = scribe_widget.cameras.get_camera_port('right')

        if scribe_widget.cameras.get_camera_port('foldout') is not None:
            self.add_foldout_widget()
        self.capture_images()
        Clock.schedule_once(self._bind_image_menus)

    def _bind_image_menus(self, *args):
        left = self.ids.left_image_menu_bar
        left.bind(on_option_select=self.on_left_image_menu_option)
        right = self.ids.right_image_menu_bar
        right.bind(on_option_select=self.on_right_image_menu_option)
        if self.foldout_widget:
            menu = self.foldout_widget.ids.image_menu_bar
            menu.bind(on_option_select=self.on_foldout_image_menu_option)

    def on_left_image_menu_option(self, menu, option):
        if option == 'view_source':
            self.show_image(self.left_image)
        elif option == 'export':
            self.start_export_filechooser(self.left_image)

    def on_right_image_menu_option(self, menu, option):
        if option == 'view_source':
            self.show_image(self.right_image)
        elif option == 'export':
            self.start_export_filechooser(self.right_image)

    def on_foldout_image_menu_option(self, menu, option):
        if option == 'view_source':
            self.show_image(self.foldout_image)
        elif option == 'export':
            self.start_export_filechooser(self.foldout_image)

    def start_export_filechooser(self, source_path):
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

    def show_image(self, path):
        try:
            firefox = webbrowser.get('firefox')
            firefox.open(path)
        except Exception:
            Logger.exception('Calibration: Unable to open image "{}"'
                             .format(path))

    def export_image(self, source, destination):
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
        except Exception:
            Logger.exception('Calibration: Unable to export image from "{}" '
                             'to "{}"'.format(source, destination))

    def add_foldout_widget(self):
        self.foldout_widget = CalibrationWidgetFoldout()
        self.foldout_widget.scribe_widget = self.scribe_widget
        self.foldout_widget.calibration_widget = self
        self.foldout_widget.ids['_foldout_spinner'].values = [self.scribe_widget.cameras.get_camera_port('left'),
                                                              self.scribe_widget.cameras.get_camera_port('right'),
                                                              self.scribe_widget.cameras.get_camera_port('foldout')]
        self.foldout_widget.ids['_foldout_spinner'].text = self.scribe_widget.cameras.get_camera_port('foldout')
        self.add_widget(self.foldout_widget)

    def capture_images(self):
        page_left = self.ids['_left_image']
        page_left.source = self.loading_image

        self.clean_temp_images()

        f = tempfile.NamedTemporaryFile(prefix='calibration',
                                        suffix='.jpg', delete=False)
        self.left_image = f.name
        f.close()

        f = tempfile.NamedTemporaryFile(prefix='calibration_thumb',
                                        suffix='.jpg', delete=False)
        self.left_thumb = f.name
        f.close()

        camera_kwargs = {
            camera_system.KEY_SIDE: 'left',
            camera_system.KEY_PATH: self.left_image,
            camera_system.KEY_THUMB_PATH: self.left_thumb,
            camera_system.KEY_IMAGE_WIDGET: page_left,
            camera_system.KEY_CALLBACK: self.show_image_callback
        }
        self.scribe_widget.left_queue.put(camera_kwargs)

        f = tempfile.NamedTemporaryFile(prefix='calibration',
                                        suffix='.jpg', delete=False)
        self.right_image = f.name
        f.close()
        f = tempfile.NamedTemporaryFile(prefix='calibration_thumb',
                                        suffix='.jpg', delete=False)
        self.right_thumb = f.name
        f.close()
        page_right = self.ids['_right_image']
        page_right.source = self.loading_image
        camera_kwargs = {
            camera_system.KEY_SIDE: 'right',
            camera_system.KEY_PATH: self.right_image,
            camera_system.KEY_THUMB_PATH: self.right_thumb,
            camera_system.KEY_IMAGE_WIDGET: page_right,
            camera_system.KEY_CALLBACK: self.show_image_callback
        }
        self.scribe_widget.right_queue.put(camera_kwargs)

        if self.scribe_widget.cameras.get_camera_port('foldout') is not None:
            if self.foldout_widget is None:
                self.add_foldout_widget()
            foldout = self.foldout_widget.ids['_foldout_image']
            foldout.source = self.loading_image

            f = tempfile.NamedTemporaryFile(prefix='calibration',
                                            suffix='.jpg', delete=False)
            self.foldout_image = f.name
            f.close()

            f = tempfile.NamedTemporaryFile(prefix='calibration_thumb',
                                            suffix='.jpg', delete=False)
            self.foldout_thumb = f.name
            f.close()
            camera_kwargs = {
                camera_system.KEY_SIDE: 'foldout',
                camera_system.KEY_PATH: self.foldout_image,
                camera_system.KEY_THUMB_PATH: self.foldout_thumb,
                camera_system.KEY_IMAGE_WIDGET: foldout,
                camera_system.KEY_CALLBACK: self.show_image_callback
            }
            self.scribe_widget.foldout_queue.put(camera_kwargs)

    def clean_temp_images(self):
        for image in (self.left_image, self.left_thumb, self.right_image, self.right_thumb, self.foldout_image,
                      self.foldout_thumb):
            if image is not None and os.path.exists(image):
                os.unlink(image)

    def show_image_callback(self, report, *args):
        """This function modifies UI elements and needs to be scheduled on the
        main thread
        """
        thumb_path = report[camera_system.KEY_THUMB_PATH]
        img_obj = report[camera_system.KEY_IMAGE_WIDGET]
        img_obj.source = thumb_path
        self.ids.box_bottons.disabled = False
        # self.check_agreement()

    def parse_gphoto_output(self, output):
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

    def swap_button(self):
        print("swapping!")
        self.scribe_widget.cameras.swap()

        #if self.scribe_widget.cameras.get_num_cameras() == 3:
        #    self.scribe_widget.cameras.set_camera('foldout',
        #                                          camera_ports['foldout'])

        self.left_port = self.scribe_widget.cameras.get_camera_port('left')
        self.right_port = self.scribe_widget.cameras.get_camera_port('right')
        print("CAPTURING AFTER SWAP WITH L = {0}, R= {1}"
              .format(self.left_port, self.right_port))
        self.ids.box_bottons.disabled = True
        self.clean_temp_images()
        self.capture_images()

    def reshoot_button(self):
        self.ids.box_bottons.disabled = True
        self.clean_temp_images()
        self.capture_images()

    def show_help_popup(self):
        popup = ScribeLearnMorePopup()
        popup.open()

    def done_button(self):
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

    def switch_foldout(self, spinner):
        text = spinner.text
        camera_ports = self.scribe_widget.cameras.camera_ports
        if text == self.scribe_widget.cameras.get_camera_port('foldout'):
            return

        if text == self.scribe_widget.cameras.get_camera_port('right'):
            #camera_ports['right'], camera_ports['foldout'] = camera_ports['foldout'], camera_ports['right']
            pass
        else:
            #camera_ports['left'], camera_ports['foldout'] = camera_ports['foldout'], camera_ports['left']
            pass

        self.left_port = self.scribe_widget.cameras.get_camera_port('left')
        self.right_port = self.scribe_widget.cameras.get_camera_port('right')

        self.clean_temp_images()
        self.capture_images()

    def exif_tag(self, tag, side):
        return "Unavailable"

    def on_use_tooltips(self, widget, use_tooltips):
        stack = self.children[:]
        while stack:
            widget = stack.pop()
            if isinstance(widget, TooltipControl):
                widget.use_tooltips = use_tooltips
            stack.extend(widget.children)
