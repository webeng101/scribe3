import os
import shutil
from os.path import join

from concurrent import futures
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ia_scribe.uix.components.file_chooser import FileChooser
from ia_scribe.uix.components.poppers.popups import InfoPopup


class BookExport(EventDispatcher):
    '''Class handling book export process.

    :Events:
        `on_finish`:
            Dispatched from :meth:`finish` to notify that book export is
            completed or canceled.
    '''

    __events__ = ('on_finish',)

    def __init__(self, book_dir, **kwargs):
        self.book_dir = book_dir
        super(BookExport, self).__init__(**kwargs)

    def start(self, *args):
        filechooser = FileChooser()
        filechooser.bind(on_selection=self.on_directory_selection)
        filechooser.choose_dir(title='Select or create an empty directory',
                               icon='./images/window_icon.png',
                               path=join(os.path.expanduser('~'), ''))

    def on_directory_selection(self, chooser, selection):
        if selection:
            export_path = selection[0]
            if os.listdir(export_path):
                self.show_error('Directory "{}" is not empty.\n\nSelect '
                                'an empty directory.'.format(export_path))
                return
            self.export(export_path)
        else:
            self.finish()

    def export(self, export_path):
        popup = Popup(title='Exporting book', auto_dismiss=False,
                      content=Label(text='Please wait'),
                      size_hint=(None, None), size=(400, 300))
        popup.open()
        with futures.ThreadPoolExecutor(max_workers=1) as executor:
            f = executor.submit(self.copy_files, self.book_dir, export_path)
        try:
            result = f.result()
            popup.dismiss()
            if result is not None:
                self.show_error('An error occurred during export!')
            else:
                Logger.info('BookExport: Exported book from "{}" to "{}"'
                            .format(self.book_dir, export_path))
                self.finish()
        except Exception:
            Logger.exception('BookExport: Failed to export book from '
                             '"{}" to "{}"'.format(self.book_dir, export_path))
            popup.dismiss()
            self.show_error('An error occurred during export!')

    def copy_files(self, src, dst, symlinks=False, ignore=None,
                   copy_function=shutil.copy2, ignore_dangling_symlinks=False):
        '''Copied from shutil.copytree, but `os.makedirs(dst)` is not called,
        so it assumes that `dst` exists.
        '''
        names = os.listdir(src)
        if ignore is not None:
            ignored_names = ignore(src, names)
        else:
            ignored_names = set()
        errors = []
        for name in names:
            if name in ignored_names:
                continue
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    if symlinks:
                        # We can't just leave it to `copy_function` because
                        # legacy code with a custom `copy_function` may rely on
                        # copytree doing the right thing.
                        os.symlink(linkto, dstname)
                        shutil.copystat(srcname, dstname,
                                        follow_symlinks=not symlinks)
                    else:
                        # ignore dangling symlink if the flag is on
                        if not os.path.exists(
                                linkto) and ignore_dangling_symlinks:
                            continue
                        # otherwise let the copy occurs. copy2 will raise
                        # an error
                        if os.path.isdir(srcname):
                            shutil.copytree(srcname, dstname, symlinks, ignore,
                                     copy_function)
                        else:
                            copy_function(srcname, dstname)
                elif os.path.isdir(srcname):
                    shutil.copytree(srcname, dstname, symlinks, ignore,
                                    copy_function)
                else:
                    # Will raise a SpecialFileError for unsupported file types
                    copy_function(srcname, dstname)
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except shutil.Error as err:
                errors.extend(err.args[0])
            except OSError as why:
                errors.append((srcname, dstname, str(why)))
        try:
            shutil.copystat(src, dst)
        except OSError as why:
            # Copying file access times may fail on Windows
            if getattr(why, 'winerror', None) is None:
                errors.append((src, dst, str(why)))
        if errors:
            raise shutil.Error(errors)
        return dst

    def show_error(self, message):
        popup = InfoPopup(title='Export Error',
                          message=message,
                          auto_dismiss=False)
        popup.bind(on_submit=self._on_export_error_popup_submit,
                   on_dismiss=self.finish)
        popup.open()

    def _on_export_error_popup_submit(self, popup, *args):
        popup.unbind(on_dismiss=self.finish)
        popup.dismiss()
        self.start()

    def finish(self, *args):
        self.dispatch('on_finish')

    def on_finish(self):
        pass
