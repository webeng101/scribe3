from os.path import join

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder

from ia_scribe import scribe_globals
from ia_scribe.detectors.reshoot_action_detector import ReShootActionDetector

kv = '''
Label:
    text: 'Press an action key...'
    font_size: '22sp'
'''


class ReShootActionDetectorApp(App):

    def __init__(self, **kwargs):
        super(ReShootActionDetectorApp, self).__init__(**kwargs)
        config_path = join(scribe_globals.DEFAULT_RESHOOT_ACTION_BINDINGS)
        self.detector = ReShootActionDetector(config_path, auto_init=True)

    def build(self):
        return Builder.load_string(kv)

    def on_start(self):
        self.detector.bind(on_action=self.on_capture_action)
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def on_key_down(self, window, keycode, scancode, codepoint=None,
                    modifiers=None, **kwargs):
        return self.detector.on_key_down(keycode, scancode, codepoint,
                                         modifiers, **kwargs)

    def on_key_up(self, window, keycode, scancode, codepoint=None,
                  modifiers=None, **kwargs):
        return self.detector.on_key_up(keycode, scancode, codepoint,
                                       modifiers, **kwargs)

    def on_capture_action(self, detector, action_name):
        self.root.text = 'Action: %s' % action_name


if __name__ == '__main__':
    ReShootActionDetectorApp().run()
