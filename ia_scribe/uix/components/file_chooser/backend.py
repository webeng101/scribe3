import os
import time
import subprocess as sp

from distutils.spawn import find_executable as which
from plyer.facades import FileChooser
from plyer.platforms.linux import filechooser as _fch


class CancelableFileChooser(object):

    def __init__(self, **kwargs):
        super(CancelableFileChooser, self).__init__(**kwargs)
        self.force_cancel = False
    
    def _run_command(self, cmd):
        self._process = sp.Popen(cmd, stdout=sp.PIPE)
        while True:
            ret = self._process.poll()
            if ret is not None:
                if ret == self.successretcode:
                    out = self._process.communicate()[0].strip().decode('utf-8')
                    self.selection = self._split_output(out)
                    return self.selection
                else:
                    return None
            elif self.force_cancel:
                self._process.terminate()
            time.sleep(0.1)


class ZenityFileChooser(CancelableFileChooser, _fch.ZenityFileChooser):
    pass


class KDialogFileChooser(CancelableFileChooser, _fch.KDialogFileChooser):
    pass


class YADFileChooser(CancelableFileChooser, _fch.YADFileChooser):
    pass


CHOOSERS = {
    'gnome': ZenityFileChooser,
    'kde': KDialogFileChooser,
    'yad': YADFileChooser
}


class LinuxFileChooser(FileChooser):

    desktop = None
    if str(os.environ.get("XDG_CURRENT_DESKTOP")).lower() == "kde" \
        and which("kdialog"):
        desktop = "kde"
    elif which("yad"):
        desktop = "yad"
    elif which("zenity"):
        desktop = "gnome"

    def __init__(self):
        self.chooser = None

    def _file_selection_dialog(self, desktop_override=desktop, **kwargs):
        if not desktop_override:
            desktop_override = desktop
        # This means we couldn't find any back-end
        if not desktop_override:
            raise OSError("No back-end available. Please install one.")

        chooser_cls = CHOOSERS[desktop_override]
        self.chooser = chooser_cls(**kwargs)
        selection = self.chooser.run()
        self.chooser = None
        return selection

    def cancel(self):
        if self.chooser:
            self.chooser.force_cancel = True
