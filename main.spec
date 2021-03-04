# -*- mode: python -*-

import os
import sys
import subprocess

from kivy.tools.packaging.pyinstaller_hooks import (
    get_deps_minimal, hookspath, runtime_hooks
)
import PIL

sys.path.append(os.getcwd())
from ia_scribe.factory_registers import Factory

block_cipher = None
used_pillow_plugins = {
    'BmpImagePlugin',
    'GifImagePlugin',
    'JpegImagePlugin',
    'Jpeg2KImagePlugin',
    'PngImagePlugin',
    'TiffImagePlugin',
    'MpoImagePlugin'
}


def filter_binaries(all_binaries):
    print('Excluding system libraries:')
    excluded_pkgs  = set()
    excluded_files = set()
    whitelist_prefixes = ('libpython3.6', 'python-')
    command = ['dpkg', '-S', None]
    stderr = open('/dev/null')
    for b in all_binaries:
        if b[-1] == 'EXTENSION':
            continue
        command[2] = b[1]
        try:
            output = subprocess.check_output(command, stderr=stderr)
            output = output.decode('utf-8')
            package = output.split(':')[0]
            if not package.startswith(whitelist_prefixes):
                excluded_pkgs.add(package)
                excluded_files.add(b[0])
                print('Excluding {} from package {}'.format(b[0], package))
        except Exception:
            pass
    stderr.close()
    print('Exe will depend on the following packages:')
    print(','.join(excluded_pkgs))
    print('')
    binaries = [x for x in all_binaries if x[0] not in excluded_files]
    return binaries


def filter_datas(all_datas):
    blacklist_prefixes = ('kivy_install/modules', 'kivy_install/data/fonts')
    excluded_datas = set()
    print('Excluding unnecessary data:')
    for item in all_datas:
        dest_path = item[0]
        if dest_path.startswith(blacklist_prefixes):
            excluded_datas.add(item)
            print('Excluding data: {}'.format(item[1]))
    print('')
    return [data for data in all_datas if data not in excluded_datas]


def find_app_hiddenimports():
    modules = set()
    for class_name in Factory.classes:
        data = Factory.classes[class_name]
        module_path = data['module']
        if module_path and module_path.startswith('ia_scribe'):
            modules.add(module_path)
    return list(modules)


def get_pillow_excludes():
    diff = set(PIL._plugins) - used_pillow_plugins
    return ['PIL.{}'.format(plugin) for plugin in diff]


deps = get_deps_minimal(window=['sdl2'],
                        image=['sdl2', 'pil'],
                        text=['sdl2'],
                        audio=['sdl2'],
                        clipboard=['sdl2'],
                        video= None,
                        camera=None,
                        spelling=None)

hiddenimports = deps['hiddenimports']
hiddenimports += find_app_hiddenimports()

# https://github.com/pypa/setuptools/issues/1963
hiddenimports.append('pkg_resources.py2_warn')

# Should be removed when Kivy/Pyinstaller fixes its import hook
hiddenimports.append('kivy.graphics.vertex')
hiddenimports.append('kivy.graphics.compiler')
hiddenimports.append('kivy.graphics.cgl_backend.cgl_gl')
hiddenimports.append('kivy.core.image.img_pil')

# Monkey patch twisted import
deps['excludes'].remove('twisted')
deps['hiddenimports'].append('twisted')

excludes = deps['excludes']
excludes += get_pillow_excludes()
excludes += [
    'PyQt4',
    'PyQt5',
    'PySide',
    'gi',
    'gobject',
    'pygments',
    'numpy',
    'kivy.extras',
    'kivy.lib.vidcore_lite',
    'kivy.gesture',
    'kivy.geometry',
    'kivy.multistroke',
    'kivy.interactive',
    'kivy.tools',
    'kivy.core.window.window_egl_rpi',
    'kivy.graphics.cgl_backend.cgl_glew',
    'kivy.graphics.cgl_backend.cgl_debug',
    'kivy.graphics.cgl_backend.cgl_mock',
    'kivy.graphics.svg',
    'kivy.graphics.tesselator'
]

a = Analysis(['main.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=[],
             hiddenimports=hiddenimports,
             hookspath=hookspath(),
             runtime_hooks=runtime_hooks(),
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

datas = filter_datas(a.datas)
datas += [('CHANGELOG.md','CHANGELOG.md', 'DATA')]
datas += [('README.md','README.md', 'DATA')]
datas += [('cli/README.md','cli/README.md', 'DATA')]
datas += Tree('extensions', prefix='extensions',)
if os.path.exists('build_number'):
    datas += [('build_number', 'build_number', 'DATA')]

binaries = filter_binaries(a.binaries)

pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=block_cipher)

# onefile mode
exe = EXE(pyz,
          a.scripts,
          binaries,
          datas,
          a.zipfiles,
          Tree('assets', prefix='assets'),
          Tree('libs', prefix='libs', excludes=['include']),
          Tree('ia_scribe', prefix='ia_scribe',
               excludes=['*.py', '*.pyc', '*.pyo']),
          exclude_binaries=False,
          name='ia-scribe',
          debug=False,
          strip=False,
          upx=True,
          console=False)

'''
# onedir mode
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='ia-scribe',
          debug=False,
          strip=False,
          upx=True,
          console=False)

coll = COLLECT(exe,
               binaries,
               datas,
               a.zipfiles,
               Tree('assets', prefix='assets'),
               Tree('libs', prefix='libs', excludes=['include']),
               Tree('ia_scribe', prefix='ia_scribe',
                    excludes=['*.py', '*.pyc', '*.pyo']),
               strip=False,
               upx=True,
               name='ia-scribe')
'''
