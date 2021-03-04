FROM ubuntu:18.04

RUN ls -lahrt
RUN apt-get update 
RUN apt-get upgrade -y
RUN apt-get install -y xorg xvfb
RUN apt-get install -y build-essential python3 python3-dev python3-pip
RUN apt-get install -y git wget
RUN apt-get install -y dpkg-sig apt-utils
RUN apt-get install -y ffmpeg libasound2-dev libsdl2-2.0-0 libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libsdl2-net-dev libsdl2-gfx-dev python3-sdl2
RUN apt-get install -y libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev libmtdev1 libgl1-mesa-dev
RUN apt-get install -y libcups2-dev libffi-dev libssl-dev libfreetype6-dev libyaml-dev exiftool

RUN python3 -m pip install --upgrade pip setuptools virtualenv

