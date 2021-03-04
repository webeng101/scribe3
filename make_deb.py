#!/usr/bin/env python
"""This script creates a signed debian repository in the directory 'apt-repo'

You must have already created a gpg key without a passphrase.
"""

import os
import shutil
import subprocess
import sys
from distutils.version import StrictVersion

import internetarchive as ia

from ia_scribe import scribe_globals

dashed_string = '*' * 32

#version = scribe_globals.release_version

command = ['git', 'describe', '--tags']
print('Check output for: {}'.format(command))
git_tag = subprocess.check_output(command).decode('utf-8').strip()
print('Git tag delta: {}'.format(git_tag))
print(dashed_string)

major_version = git_tag.split('-')[0]
build_number = git_tag.split('-')[2]
version = '{}-{}'.format(major_version, build_number)

print(dashed_string)
print('Building Scribe3 version {}'.format(version))
print(dashed_string)


current_branch = os.environ['CI_COMMIT_REF_NAME']
print(current_branch)
print(dashed_string)
with open('build_number', 'w+') as f:
    f.write(git_tag)
    f.write(os.linesep)

#deb_version = '{}.{}-{}'.format(major, minor, patch)
deb_version = version
print('Deb version: {}'.format(deb_version))

deb_dir_path = 'ia-scribe_{}'.format(deb_version)
if os.path.exists(deb_dir_path):
    shutil.rmtree(deb_dir_path)
shutil.copytree('deb_pkg', deb_dir_path)

print(dashed_string)
print('Building package with PyInstaller')
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

print('CHECKPOINT: File permissions')
subprocess.check_call(['pwd'])
subprocess.check_call(['ls', '-lahrt'])
subprocess.check_call(['chmod', '-R', '755', deb_dir_path])
print('CHECKPOINT: ---')

command = ['dpkg-deb', '--build', deb_dir_path]
print('Check call for: {}'.format(command))
subprocess.check_call(command)

repo_path = 'apt-repo'
if os.path.exists(repo_path):
    shutil.rmtree(repo_path)
os.makedirs(repo_path)

deb_path = deb_dir_path + '.deb'
shutil.move(deb_path, repo_path)

pkg_path = os.path.join(repo_path, deb_path)

command = ['dpkg-sig', '--sign', 'builder', pkg_path]
print('Check call for: {}'.format(command))
subprocess.check_call(command)

command = ['apt-ftparchive', 'packages', '.']
print('Check output for: {}, cwd={}'.format(command, repo_path))
output = subprocess.check_output(command, cwd=repo_path).decode('utf-8')
print(output)

with open(os.path.join(repo_path, 'Packages'), 'w') as f:
    f.write(output)

command = ['apt-ftparchive', 'release', repo_path]
print('Check output for: {}'.format(command))
output = subprocess.check_output(command).decode('utf-8')
print(output)

release_path = os.path.join(repo_path, 'Release')
with open(release_path, 'w') as f:
    f.write(output)

command = ['gpg', '--yes', '-abs', '-o', release_path + '.gpg', release_path]
print('Check call for: {}'.format(command))
subprocess.check_call(command)

print('Created signed package {} in repo {}'.format(pkg_path, repo_path))
if 's3' not in ia.config.get_config():
    ia_configuration = {'s3': {
                                'access': os.environ['S3_ACCESS'],
                                'secret': os.environ['S3_SECRET']
                               }
                        }
    ia_session = ia.get_session(config=ia_configuration)
else:
    ia_session = ia.get_session()

if current_branch == 'master':
    repo = ia_session.get_item('scribe-repo-autobuild')
elif current_branch.endswith(('-Release', 'alpha', 'beta',)):
    repo = ia_session.get_item('scribe-repo-autobuild-{}'.format(current_branch))
else:
    repo = ia_session.get_item('scribe-repo-autobuild-dev')

repo.upload(repo_path + '/', queue_derive=False, )
print('Uploaded to: {}'.format(repo.identifier + '/'))
