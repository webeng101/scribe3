#!/usr/bin/env bash

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential python3 python3-dev python3-pip git wget dpkg-sig libgl1-mesa-dev
sudo apt-get install -y ffmpeg libsdl2-2.0-0 libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libsdl2-net-dev libsdl2-gfx-dev python3-sdl2
sudo apt-get install -y libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev libmtdev1
sudo apt-get install -y libcups2-dev libffi-dev libssl-dev libfreetype6-dev libyaml-dev  exiftool

sudo pip3 install --upgrade pip

sudo python3 -m pip install --upgrade --user pip setuptools virtualenv
#sudo pip3 install Cython==0.25.2
sudo pip3 install --upgrade -r ${1:-.}/requirements.txt --ignore-installed
