# Scribe3 [![pipeline status](https://git.archive.org/ia-books/scribe3/badges/master/pipeline.svg)](https://git.archive.org/ia-books/scribe3/commits/master)
## The Internet Archive's book scanning software


1. [Overview](#1-overview) 
    1. [Features](#11-features) 
2. [Requirements](#2-requirements)
3. [Quick Start](#3-quick-start)
4. [Environment](#4-configuration)
   1. [Running](#41-running)
   2. [Virtualenv](#42-virtualenv)
   3. [VagrantBox](#43-vagrant-box)
   4. [Libraries](#44-libraries)
   5. [Debian package](#45-debian-package)
5. [Configuration](#5-Configuration)
   1. [Initial Setup](#51-initial-setup) 
   2. [Metadata](#53-metadata) 
   3. [Collection sets](#53-collection-sets)
   4. [Catalogs](#54-catalogs)
   5. [Cameras](#55-cameras)
   6. [Other](#56-other)
6. [Links](#6-links)
7. [Contacts](#7-contacts)
8. [Acknowledgements](#8-acknowledgements)

## 1. Overview
Scribe3 is the software the powers book scanning at the Internet Archive (IA). 
In the main operating mode, it runs as a GUI app on Scribe scanning stations 
and allows the user to efficiently and reliably digitize books to IA. 

In particular, as the first user-facing component of the Scribe platform, Scribe3 has a few key responsibilities: 
- **Handle peripherals**: cameras, barcode scanners, printers, contact switches, etc
- **Manage the book lifecycle** from creation to upload, to deletion. Allow station-to-station transfer, as well as correcting books after they've been scanned.   
- **Support book scanning workflows**: retrieve, validate and edit metadata, capture images, send books to other stations for scanning of large formats, support correcting items, support idiosyncratic workflows (there can be big differences in how different centers operate)
- **Interact with IA backend** services: upload/download of items, interactions with cluster RePublisher, metadata API, corrections API, telemetry APIs to name a few.
- **Measure all the things**: Scribe3 collects a large array of metrics to measure and manage all aspects of book scanning, from efficiency and yield to errors and usage patterns.
- Provide a **productive user interface**: have all the necessary tools to perform a task immediately available and ordered in a logical and consistent fashion, inform the user of what is going on but try to hide complexity and treat user input as a scarce resource.
- **Be performant**: be deliberate about managing available resources, including network bandwidth, disk space, and CPU. Ensure shooting speed is high, experience is snappy and computations are executed deterministically.
- **Be reliable**: with an install base of more than 180 stations across 30+ scanning centers all over the world, users rely on Scribe3 to take more than half a million pictures and upload thousands of books and hundreds of terabytes every day.  
- **Handle errors and self-recover**: Scribe3 interacts with many systems, all which may and do fail routinely, and tries as much as possible not to let these situations limit the user in what they can do.
- Be a **good IA citizen**: treat the resources of IA as scarce, do not waste and do not leave around waste.  

The Scribe scanning platform also includes components for telemetry with `iabdash`, 
command and control capabilities with [`scribe3-server`](https://git.archive.org/ia-books/scribe3-server),
analytics/reporting tools such as the [`books dashboard`](https://books-dashboard.archive.org/),  
[`bookinfo`](https://git.archive.org/ia-books/book-info), 
[`ingestion-adapters`](https://git.archive.org/davide/ingestion-adapters), 
the `btserver` and [`daemon`](https://git.archive.org/ia-books/scribe-daemon) systems, 
the [`corrections`](https://git.archive.org/ia-books/corrections-api) system (which is integrated 
in cluster RePublisher as well as [`web RePublisher`](https://git.archive.org/ia-books/republisher).

### 1.1 Key features
- Handle up to 9999 pages per book, and thousands of books per station.
- Handle 1 (for foldout stations), 
2 (for full-frame and table-top scribes) and 
3 (for tabletop scribes with foldout arm) cameras (see [Cameras](#55-cameras) for supported models) 
- Load and edit book metadata from myriad sources: MARCs via Z39.50
 catalogs registered with IA, OpenLibrary, preloaded identifiers, manual input, etc.
- Support affordances for mass digitization: do-we-want-it workflows, 
acceptance/rejection, slip printing; also provide strong guarantees that all items will be accounted for.  
- Support downloading and correcting books, as well as sending books around from one station to another.
- Import/export images and books, support importing image stacks as books (e.g. sheetfed scanning).
- Extensible: supports extensions as drop-in apps.
- APIs: python API, Web API, CLI, C2...
- Fully featured task execution system.
- Configurable sophisticated book state machine model.
- Standalone stats collection and analysis framework.
- Run in headless mode.

## 2. Environment
- Scribe3 is designed to support the [Table Top Scribe](https://archive.org/details/tabletopscribesystem) book scanner,
 Full Frame Scribes and Folio stations for both internal and external scanning centers. 
- Scribe3 is mostly used as a GUI application. Its native execution environment is 64bits (x64) Ubuntu 18.02.3 LTS.
- Scribe3 uses Archive.org as a backend through its [S3-like](https://archive.org/help/abouts3.txt) API, 
through the IABDASH metrics system, the BTSERVER items system for corrections - as well as Cluster Republisher. 
- [gphoto2](http://www.gphoto.org/) is used to interface with cameras. 
It's free software [LGPL license](https://www.gnu.org/licenses/lgpl-3.0.en.html).


## 3. Quick start

To start, first, clone the repository (please note that you must have *Cython 0.20.1*, *python-apt* and *numpy* globally installed. See [Running](#41-running)):

        git clone git@git.archive.org:ia-books/scribe3.git
        cd scribe3

If you wish to use a [vagrantbox](https://markup.herokuapp.com/#5-vagrant-box) just type:

        vagrant up
        vagrant ssh  
        cd /scribe3
        
Before installing the python requirements, it's a good idea to use a [*virtualenv*](http://docs.python-guide.org/en/latest/dev/virtuale$
        
        # You will need --sytem-site-packages if you have Cython, 
        # python-apt and Pygame installed system-wide. 

        virtualenv --system-site-packages venv
        source venv/bin/activate

install then the requirements:

        pip install -r requirements.txt

run Scribe3 executing this command in a graphic terminal:

        python scribe.py


## 4. Environment
This section describes how to install the necessary dependencies to run Scribe3. 

### 4.1 Running
The following instructions apply to a system-wide installation. 

Start from an Ubuntu 14.04.05 LTS i686 image

        sudo apt-get update
        sudo apt-get upgrade

Install the dependencies you'll need to compile Cython

        sudo apt-get install build-essential python-dev python-pip python-apt git python-virtualenv libffi-dev libssl-dev cups libcups2-dev

If you plan on installing pygame in virtualenv, please see the notes in section 5.1
before installing pygame as follows

        sudo apt-get build-dep python-pygame
        sudo apt-get install python-pygame
        
Install *Cython 0.20.1* and *numpy* :

        sudo pip install numpy
        sudo pip install Cython==0.20.1

Then follow the steps in section [3](#3)):

### 4.2 Virtualenv
If you want to run scribe from within a **virtualenv**, you have to consider that
*Cython 0.20.1* is an hard requirement for this software to execute and must be installed
system-wide. 

It is however possible to install *kivy* inside virtualenv. Instructions refer 
to those [provided by kivy](http://kivy.org/docs/installation/installation-linux.html#installation-in-a-virtual-environment-with-system-site-packages). 

        # Initialize virtualenv
        virtualenv -p python2.7 --system-site-packages venv
        
Note on ***pygame***: Please note that *Pygame* is more easily installed from apt and not included in the *pip*requirements file. This is because there seem to be some [issues](https://bitbucket.org/pygame/pygame/issue/140/pip-install-pygame-fails-on-ubuntu-1204) and hurdles with installing *pygame* within a virtualenv. Should you want to install it with *pip*, you should note that the package is not present in *pypy* and you need to install it from [bitbucket](https://bitbucket.org/pygame/pygame)) by following [these instructions](http://askubuntu.com/questions/299950/how-do-i-install-pygame-in-virtualenv/299965#299965) or use [this script](https://gist.github.com/brousch/6395214#file-install_pygame-sh-L4). 

Activate your virtualenv before running as above:

        source venv/bin/activate

### 4.3 Vagrant box

Use box-cutter/ubuntu1404-desktop as a base image. You can use the `Vagrantfile` in the repository or generate a new one using:
        
        vagrant init box-cutter/ubuntu1404-desktop

run the VM with:

        vagrant up

and then follow the instructions in the [quick start](#3-quick-start).

### 4.4 Libraries

* This project uses the [*Kivy framework*](http://kivy.org/#home). You can use this Vagrantfile to bootstrap
a development environment: https://github.com/rajbot/kivy_pyinstaller_linux_example

* A `gphoto` directory is also included that contains *libgphoto2* with Nikon J3 support,
built from the svn repo at commit r14922 (available in this [git-svn mirror](https://github.com/rajbot/gphoto))

### 4.4 Debian package
Scribe3 is distributed to scancenters through a [debian ppa](https://archive.org/download/scribe-repo-internal). In order to build the debian package, the `./make_deb.py` script is used. This process has additional dependencies (PyInstaller version 2.1, Kivy version 1.8.1, the GPG Keys for dpkg-sig, privs on IA ppa items). 

## 5. Configuration
Scribe3 requires a minimum amount of configuration to work. The following is necessary: 
* An archive.org account with privs for the collections you intend to upload to (for developers, that's `booksgrouptest`), as well as privs for `iabooks-btserver`
* Values for the following item metadata fields: `contributor`, `sponsor` and `scanningcenter` (if these are not set properly, they will cause redrows at billing time.)

### 5.1 Initial setup
The initial setup consists of three phases: 
* Login to archive.org
* Metadata setup
* Collections and collection sets setup

The `scanner` field should be in the form `[scanner_name].[scancenter].archive.org`; this is important because upon first run, Scribe3 will create an item with this hostname as an identifier, and will register it with IABDASH. If the account you logged in with is not priv'd for `iabooks-btserver`, this registration will fail and you will not be able to use corrections.

### 5.2 Metadata

Metadata that will be appended to every book uploaded can be configured in the "Metadata" options panel. In case of preloaded items, only `scanner` and `operator` values are updated upon upload.

### 5.3 Collection sets

There's no good way to say this: a collection set is a preset set of collections. It's often the case that you'll want your item to belong to more than one collection; Scribe3 operates on collections set. Collection set selection is mandatory for scanning non-preloaded items. 

### 5.4 Catalogs

Catalogs are being introduced in v1.30 as part of the MARC feature which allows querying IA MARC sources over our z39.50 through [Jude's api](http://www-judec.archive.org/book/marc/get_marc.php). This feature is available for preloaded items only.

### 5.5 Cameras
Scribe3 currently supports the following makers and models:

|  Maker |  Model |  gphoto2  | libgphoto2 |  Typical system |
|---|---|---|---|---|
| Nikon |  J3-5 | 2.5.4.1  | 0.10.0 | Old Internal TTS |
| Sony | Alpha 6000 | 2.5.10  | 0.12.0   | Internal TTS | 
| Sony | Alpha 6300  |2.5.10  | 0.12.0   | New TTS | 
| Sony | Alpha 7rII  |2.5.10  | 0.12.0   | FADGI TTS | 
| Canon | EOS 5D Mark II  |2.5.10  | 0.12.0   | Internal FFS | 


### 5.6 Other

- label printer
- barcode scanner
- MARC
- DWWI
- Update


## 6. Links

- [Documentation](https://wiki.archive.org/twiki/bin/view/BooksGroup/Scribe3Software)
- [Manual](https://wiki.archive.org/twiki/bin/view/BooksGroup/Scribe3Usage)
- [Testing and rollout](https://wiki.archive.org/twiki/bin/view/BooksGroup/Scribe3TestingRollout)
- [Internal PPA](https://archive.org/download/scribe-repo-internal)
- [External PPA](https://archive.org/download/scribe-repo-external)
- [IABDASH](https://iabooks.archive.org/dashboard/#/)


## 7. Contacts 

 - [Davide Semenzin](https://git.archive.org/davide) - `davide@archive.org`

## 8. Acknowledgements

*Version 3*, this version, was originally written by [Raj Kumar](https://github.com/rajbot) - <rkumar@archive.org>.

*Version 2* was a web app written by Steve Sisney and then Dan Hitt.

*Version 1* was written in Java by Mark Johnson.
