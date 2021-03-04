#!/usr/bin/env python
"""This script creates a signed debian repository in the directory 'apt-repo'
"""

import os
import shutil
import subprocess
import sys
from distutils.version import StrictVersion

from ia_scribe import scribe_globals

version = scribe_globals.release_version

command = ['git', 'describe', '--tags']
print('Check output for: {}'.format(command))
build_number = subprocess.check_output(command).decode('utf-8').strip()
print('Build number: {}'.format(build_number))

with open('build_number', 'w+') as f:
    f.write(build_number)
    f.write(os.linesep)

v = StrictVersion(version)
major, minor, patch = v.version

deb_version = '{}.{}-{}'.format(major, minor, patch)
print('Deb version: {}'.format(deb_version))

deb_dir_path = 'ia-scribe_{}'.format(deb_version)
if os.path.exists(deb_dir_path):
    shutil.rmtree(deb_dir_path)
shutil.copytree('deb_pkg', deb_dir_path)

command = ['pyinstaller', 'main.spec', '--clean']
print('Check call for: {}'.format(command))
subprocess.check_call(command)

scribe_binary = 'dist/ia-scribe'
assert os.path.exists(scribe_binary)

binary_path = os.path.join(deb_dir_path, 'usr/local/bin')
os.makedirs(binary_path)
shutil.copy(scribe_binary, binary_path)

control_file = os.path.join(deb_dir_path, 'DEBIAN/control')
assert os.path.exists(control_file)

with open(control_file, 'a') as f:
    f.write('Version: {}'.format(deb_version))
    f.write(os.linesep)

print('Successfully built version {}'.format(build_number))
