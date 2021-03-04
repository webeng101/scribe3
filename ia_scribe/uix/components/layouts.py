from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior


class SelectableGridLayout(FocusBehavior, LayoutSelectionBehavior,
                           RecycleGridLayout):

    pass
