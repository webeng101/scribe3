'''
Scribe3

The Internet Archive bookscanning software
'''

import sys
from os import environ
from os.path import join

from ia_scribe import scribe_globals

__author__     = 'Davide Semenzin'
__copyright__  = 'Copyright 2018, Internet Archive'
__credits__    = ['Raj Kumar', 'Giovani Damiola', 'Filip Radovic',
                  'Wester De Weerdt']
__maintainer__ = 'Davide Semenzin'
__email__      = 'davide@archive.org'
__status__     = scribe_globals.release_status
__date__       = scribe_globals.release_date
__version__    = scribe_globals.release_version


# Override environment variables
environ['KIVY_CLIPBOARD'] = 'sdl2'
environ['KIVY_GL_BACKEND'] = 'gl'

# Log app's build number
from ia_scribe.logger import Logger
Logger.info('Scribe3App: v{}'.format(scribe_globals.BUILD_NUMBER))

# Override Kivy 1.10 default font because Scribe app does not use it.
# This enables us to remove Roboto font from distribution
from kivy.config import Config
Config.set('kivy', 'default_font', scribe_globals.DEFAULT_FONT_FILES)


# Add resources paths
from kivy.resources import resource_add_path
if getattr(sys, 'frozen', False):
    resource_add_path(scribe_globals.APP_WORKING_DIR)
resource_add_path(scribe_globals.ASSETS_DIR)
resource_add_path(scribe_globals.IMAGES_DIR)
resource_add_path(scribe_globals.SOUNDS_DIR)


# Register app's fonts
from kivy.core.text import LabelBase
LabelBase.register(
    name='DroidSans',
    fn_regular=join(scribe_globals.FONTS_DIR, 'DroidSans.ttf'),
    fn_italic=join(scribe_globals.FONTS_DIR, 'DroidSans-Italic.ttf'),
    fn_bold=join(scribe_globals.FONTS_DIR, 'DroidSans-Bold.ttf'),
    fn_bolditalic=join(scribe_globals.FONTS_DIR, 'DroidSans-BoldItalic.ttf'))
LabelBase.register(
    name='FreeSans',
    fn_regular=join(scribe_globals.FONTS_DIR, 'FreeSans.ttf'))
LabelBase.register(
    name='FreeSansTTScribe',
    fn_regular=join(scribe_globals.FONTS_DIR, 'FreeSansTTScribe.ttf'))
LabelBase.register(
    name='CourierNewTTScribe',
    fn_regular=join(scribe_globals.FONTS_DIR, 'Courier-New.ttf'))



# Register app's widgets
import ia_scribe.factory_registers
