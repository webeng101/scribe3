import shutil

from kivy.event import EventDispatcher

from ia_scribe.cameras import camera_system
from ia_scribe.scribe_globals import FAKE_IMAGE


class DummyWindow(EventDispatcher):

    __events__ = ('on_key_down', 'on_key_up')

    def on_key_down(self, keycode, scancode, codepoint=None, modifiers=None,
                    **kwargs):
        pass

    def on_key_up(self, keycode, scancode, codepoint=None, modifiers=None,
                  **kwargs):
        pass


class DummyLogger(object):

    def info(self, *args):
        pass

    def debug(self, *args):
        pass

    def error(self, *args):
        pass

    def warn(self, *args):
        pass

    warning = warn

    def exception(self, *args):
        pass


class DummyCameraSystemQueue(object):

    def __init__(self, camera_system):
        self.camera_system = camera_system

    def put(self, item, block=True, timeout=None):
        self.camera_system.simulate_capture(item)


class DummyCameras(object):

    def __init__(self, cameras_count):
        self.cameras_count = cameras_count

    def get_num_cameras(self):
        return self.cameras_count


class DummyCameraSystem(object):

    def __init__(self, cameras_count):
        self.cameras = DummyCameras(cameras_count)
        self.left_queue = DummyCameraSystemQueue(self)
        self.SINGLE_CAMERA_ROTATION = 180

    def simulate_capture(self, camera_kwargs):
        side = camera_kwargs[camera_system.KEY_SIDE]
        path = camera_kwargs[camera_system.KEY_PATH]
        thumb_path = camera_kwargs[camera_system.KEY_THUMB_PATH]
        image_widget = camera_kwargs.get(camera_system.KEY_IMAGE_WIDGET, None)
        callback = camera_kwargs[camera_system.KEY_CALLBACK]
        shutil.copy(FAKE_IMAGE, path)
        shutil.copy(FAKE_IMAGE, thumb_path)
        clock_dt = 0
        report = {
            camera_system.KEY_SIDE: side,
            camera_system.KEY_THUMB_PATH: thumb_path,
            camera_system.KEY_IMAGE_WIDGET: image_widget,
            camera_system.KEY_ERROR: None,
            camera_system.KEY_STATS: {
                'capture_time': 0,
                'thumb_time': 0
            }
        }
        extra = camera_kwargs.get(camera_system.KEY_EXTRA, None)
        if extra:
            report[camera_system.KEY_EXTRA] = extra
        callback(report, clock_dt)
