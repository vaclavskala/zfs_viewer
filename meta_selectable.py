"""Class to inherit scrollable properties"""


class MetaSelectable:
    """Base class for selectable element"""

    def __init__(self):
        self.__is_selected = False

    def select(self):
        """Set element as enabled for scroll"""
        self.__is_selected = True

    def unselect(self):
        """Set element as disabled for scroll"""
        self.__is_selected = False

    def is_selected(self):
        """If element is selected"""
        return self.__is_selected
