from kivy.core.window import Window, WindowBase
from kivy.factory import Factory
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty

# TODO: Add attribute attach_tooltip_to to TooltipBehavior.
# When attach_tooltip_to is set in TooltipControl, it will get propagated to
# all TooltipBehavior children. This will make faster to attach/detach
# label widget displaying tooltip.


class TooltipBehavior(object):
    '''A mixin class used to display tooltip label when attribute `hovered`
    is set to True. Should be used with TooltipControl as parent widget.

    Tooltip label will be added to widget returned by method
    `get_tooltip_window`, which goes in reverse in widget tree, until first
    instance of TooltipControl is found. When control instance is found,
    tooltip label in added in `attach_tooltip_to` widget if it is set.
    Otherwise control widget's root_window is used to add label widget, but if
    root window is None then label widget won't be added at all.
    '''

    hovered = BooleanProperty(False)
    '''Indicates if this widget is hovered with mouse indicator or not.
    '''

    tooltip = StringProperty()
    '''String which is set in tooltip label.
    '''

    def __init__(self, **kwargs):
        self._tooltip_label = Factory.get('TooltipLabel')(text=self.tooltip)
        self.fbind('hovered', self._update_tooltip_label)
        self.fbind('disabled', self._update_tooltip_label)
        super(TooltipBehavior, self).__init__(**kwargs)

    def collide_mouse_pos(self, x, y):
        # Position (x, y) is in window space
        wx, wy = self.to_window(*self.pos)
        return wx <= x <= wx + self.width and wy <= y <= wy + self.height

    def get_tooltip_window(self):
        stack = [self.parent]
        while stack:
            widget = stack.pop()
            if not widget:
                return None
            if isinstance(widget, TooltipControl) and widget.attach_tooltip_to:
                return widget.attach_tooltip_to
            if isinstance(widget, TooltipScreen) and widget.attach_tooltip_to:
                return widget.attach_tooltip_to
            if isinstance(widget, WindowBase):
                return widget
            stack.append(widget.parent)

    def on_tooltip(self, widget, tooltip):
        self._tooltip_label.text = tooltip

    def _update_tooltip_label(self, *args):
        tooltip_label = self._tooltip_label
        label_parent = tooltip_label.parent
        if self.hovered and not (self.disabled or label_parent):
            window = self.get_tooltip_window()
            if window:
                self.fbind('center', self._reposition_tooltip_label)
                tooltip_label.fbind('size', self._reposition_tooltip_label)
                window.add_widget(tooltip_label)
                self._reposition_tooltip_label()
        elif (not self.hovered or self.disabled) and label_parent:
            self.funbind('center', self._reposition_tooltip_label)
            tooltip_label.funbind('size', self._reposition_tooltip_label)
            label_parent.remove_widget(tooltip_label)

    def _reposition_tooltip_label(self, *args):
        label = self._tooltip_label
        label_parent = label.parent
        center_x, top = self._to_label_parent(self.center_x, self.y, self)
        half_label_width = label.width / 2.0
        if center_x + half_label_width > label_parent.width:
            center_x = label_parent.width - half_label_width
        if center_x - half_label_width < 0:
            center_x = half_label_width
        label.center_x = center_x
        if top - label.height < 0:
            top += self.height + label.height
        label.top = top

    def _to_label_parent(self, x, y, widget):
        if widget.parent is None:
            return (x, y)
        if self._tooltip_label.parent is widget.parent:
            return widget.to_parent(x, y)
        x, y = widget.to_parent(x, y)
        return self._to_label_parent(x, y, widget.parent)


class TooltipControl(object):
    '''A mixin class which used with TooltipBehavior enables displaying of
    tooltips.

    For tooltips to work parent widget must inherit TooltipControl, child
    widget must inherit TooltipBehavior and attribute `use_tooltips` must be
    set to True.

    With `use_tooltips` set to True, widget will bind with Window's mouse_pos
    property. When `mouse_pos` collides with control widget, children list
    will be searched recursively to find first TooltipBehavior child widget
    which collides with `mouse_pos` and set it's `hovered` attribute to True.
    Strong reference to hovered child widget is kept for a fast check on
    subsequent `mouse_pos` changes. When `mouse_pos` doesn't collide anymore
    with last hovered widget, it's attribute `hovered` is set to False and
    strong reference is released. If `mouse_pos` still collides with control
    widget, again children list is searched.

    Since `mouse_pos` is in window coordinate space, TooltipBehavior method
    `collide_mouse_pos` is used to check if child widget collides with
    `mouse_pos`.

    With this approach only control widgets are checked for collision with
    `mouse_pos` and then children widget, thus providing tree-like search,
    which generally provides better performance from naive case when each
    TooltipBehavior widget binds to Window's `mouse_pos`.

    **IMPORTANT**: When control widget is no longer displayed on screen or
    removed from it's parent widget, attribute `use_tooltips` must be set to
    False which will unbind method `on_window_mouse_pos` from Window's
    `mouse_pos` handler and therefore prevent memory leak.

    If attribute `attach_tooltip_to` is set to None (default) then widget
    displaying tooltip will be added to root's window, otherwise tooltip
    widget will be added to children of set widget.
    '''

    use_tooltips = BooleanProperty(False)
    '''Enable/disable displaying of tooltip labels for children widgets.
    '''

    attach_tooltip_to = ObjectProperty(None, allownone=True)
    '''Widget to add tooltip label to or None (default). If None is set then
    TooltipBehavior widget will try add label to root_window of this widget.
    '''

    def __init__(self, **kwargs):
        self._last_tooltip_widget = None
        self.fbind('use_tooltips', self._update_tooltip_widgets)
        self.fbind('disabled', self._update_tooltip_widgets)
        super(TooltipControl, self).__init__(**kwargs)

    def _update_tooltip_widgets(self, *args):
        if self.use_tooltips and not self.disabled:
            Window.bind(mouse_pos=self.on_window_mouse_pos)
            self.on_window_mouse_pos(Window, Window.mouse_pos)
        else:
            Window.unbind(mouse_pos=self.on_window_mouse_pos)
            if self._last_tooltip_widget:
                self._last_tooltip_widget.hovered = False
                self._last_tooltip_widget = None

    def on_window_mouse_pos(self, window, pos):
        last_hovered = self._last_tooltip_widget
        if last_hovered:
            if last_hovered.collide_mouse_pos(*pos):
                return
            else:
                last_hovered.hovered = False
                self._last_tooltip_widget = None
        if self.collide_mouse_pos(*pos):
            for widget in self.walk_tooltip_widgets():
                if not widget.disabled and widget.collide_mouse_pos(*pos):
                    widget.hovered = True
                    self._last_tooltip_widget = widget
                    break

    def collide_mouse_pos(self, x, y):
        # Position (x, y) is in window space
        wx, wy = self.to_window(*self.pos)
        return wx <= x <= wx + self.width and wy <= y <= wy + self.height

    def walk_tooltip_widgets(self):
        stack = self.children[:]
        while stack:
            widget = stack.pop()
            if isinstance(widget, TooltipBehavior):
                yield widget
            stack.extend(widget.children)


class TooltipScreen(object):
    '''A mixin class meant to be used in combination with Screen class to keep
    in sync :attr:`use_tooltips` with `use_tooltips` of TooltipControl widgets.
    '''

    use_tooltips = BooleanProperty(False, force_dispatch=True)
    '''This value will be synced with all child widgets which inherit from 
    :class:`TooltipControl`.
    '''

    attach_tooltip_to = ObjectProperty(None, allownone=True)
    '''Widget to add tooltip label to or None or self (default). 
    
    If None is set then TooltipBehavior widget will try add label to 
    root_window of this widget.
    '''

    def __init__(self, **kwargs):
        kwargs.setdefault('attach_tooltip_to', self)
        super(TooltipScreen, self).__init__(**kwargs)

    def on_use_tooltips(self, tooltip_parent, use_tooltips):
        for widget in self.walk_tooltip_control_widgets():
            widget.use_tooltips = use_tooltips

    def walk_tooltip_control_widgets(self):
        stack = self.children[:]
        while stack:
            widget = stack.pop()
            if isinstance(widget, TooltipControl):
                yield widget
            else:
                stack.extend(widget.children)

    def on_enter(self, *args):
        self.use_tooltips = True
        return super(TooltipScreen, self).on_enter(*args)

    def on_leave(self, *args):
        self.use_tooltips = False
        return super(TooltipScreen, self).on_leave(*args)
