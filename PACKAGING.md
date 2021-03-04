Instructions for installing Kivy 1.9.1 and packaging of Scribe app
-------------------------------------------------------------------

Ensure that pygame is uninstalled by running:

```bash
sudo apt-get remove python-pygame
```

Install Kivy 1.10 system dependencies:

```bash
sudo apt-get install -y \
    build-essential \
    python \
    python-dev \
    git \
    libav-tools \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev
```

Install project's system dependencies:

```bash
sudo apt-get install -y \
    libcups2-dev \
    libffi-dev \
    libssl-dev \
    libfreetype6-dev \
    libyaml-dev \
    libmtdev1
```

Install and upgrade pip (skip if pip is already installed):
```bash
wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py && rm get-pip.py 
sudo pip install --upgrade pip
```

Install Cython:
```bash
sudo pip install Cython==0.25.2
```

Install package requirements:
```bash
sudo pip install --upgrade -r requirements.txt
```

Package the app by running:
```bash
pyinstaller scribe_new.spec
```
Packaged version of app will be located in `dist` directory.
