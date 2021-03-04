from os.path import join, dirname

from kivy.lang import Builder

from ia_scribe.uix.behaviors.tooltip import TooltipControl
from ia_scribe.uix.components.overlay.overlay_view import OverlayView

Builder.load_file(join(dirname(__file__), 'foldout_overlay.kv'))


class FoldoutOverlay(TooltipControl, OverlayView):

    EVENT_OPTION_SELECT = 'on_option_select'
    OPTION_DELETE = 'delete'
    OPTION_REPLACE_LEFT = 'replace_left'
    OPTION_REPLACE_RIGHT = 'replace_right'

    __events__ = (EVENT_OPTION_SELECT,)

    def on_touch_down(self, touch):
        if not self.collide_buttons(*touch.pos):
            if self.auto_dismiss:
                self.dismiss()
                return True
        super(FoldoutOverlay, self).on_touch_down(touch)
        return True

    def collide_buttons(self, x, y):
        ids = self.ids
        button = ids.left_button
        if not button.disabled and button.collide_point(x, y):
            return True
        button = ids.right_button
        if not button.disabled and button.collide_point(x, y):
            return True
        return ids.delete_button.collide_point(x, y)

    def on_option_select(self, option):
        pass
