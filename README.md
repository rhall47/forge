# ForGe

Forensic test image generator v2.1
Copyright Hannu Visti 2013-2015, licenced under Gnu General Public Licence

## New functionality
* Secret strategy sweep. When defining a case, either number of copies or a secret strategy sweep must be chosen. If a secret strategy sweep is chosen, the number of created images depends on the number of secret files associated to the chosen secret strategy. For example, if a secret strategy using ADS is chosen as the sweep target, and the secret strategy uses secret file group 5 and secret file group 5 has ten different secret files, exactly ten images will be created. Each image will have a different file from group 5 hidden by ADS. This allows rapid creation of images for educational purposes, where each student will be given a different secret file hidden with identical method. 

## Development information

V2.0 commit merged "webhistory" branch into master.  Webhistory is by no means a completed project but this version does not cause problems to the main application and developing them independently from this point forward serves no purpose. 
* Using this version requires linux containers (apt-get lxc)
* Previous database schema is not compatible with this version. Better start from scratch. 
* Web history part creates images with Firefox 32 caches BUT is not yet able to manage cache timeline, counters etc.

## Version upgrade note

ForGe 2.0 included changes to database scheme. If upgrading from older versions, it is advisable to drop the current database and follow installation instructions in Doc/Installation.txt to create a new database schema and populate it with initial data. 

Changes: 
* TrivialObject table now has a boolean field inuse to flag a trivial file on image already used as a cover file.
* Hiding method functions now take image as a parameter. This allows database queries and updates from hiding methods modules through Image table/class methods. 
* Added Steganography hiding method using steghide application. Steghide is not part of ForGe but must be installed separately if used (sudo apt-get install steghide).

## Overview

ForGe is a tool designed to build computer forensic test images. It was done as a MSc project for 
the University of Westminster. Its main features include:

* Web browser user interface
* Rapid batch image creation (NTFS and FAT)
* Possibility to define a scenario including trivial and hidden items on images
* Variance between images. For example, if ForGe was told to put 10-20 picture files to a directory /holiday and
  create 10 images, all these images would have random pictures pulled from repository.
* Variance in timestamps. Each trivial and hidden file can be timestamped to a specific time. Each scenario is
  given a time variance parameter in weeks. If this is set to 0, every image receives an identical timeline. If
  nonzero, a random amount of weeks up to the maximum set is added to each file on each image
* Can modify timestamps to simulate certain disk actions (move, copy, rename, delete). Not all actions are available for all file system types.
* Implements several data hiding methods: Alternate data streams, extension change, file deletion, concatenation
  of files and file slack space. 
* New data hiding methods can be easily implemented. Adding a new file system is also documented.


## Components and requirements
The application is built in Python and a helper application "chelper" in C. ForGe is guaranteed to work in the following environment but slight version deviations are not expected to cause problems. ForGe is written in Python 2.7 and does not support Python 3 syntax.

* Ubuntu 64 bit 12.04 or newer (tested in 14.04), or Debian 7. 
* Django 1.5.1 or newer. Should work on Django 1.7
* Python 2.7.3 -      Currently does not support Python 3
* Tuxera NTFS-3G 2013.1.13 or newer (the default in Ubuntu 12.04 is an older version, which does weird things to attributes of deleted files)
* Linux containers

Other Linux versions than Ubuntu are likely to work. The key element is the existence of loopback devices /dev/loopX, as they are used to mount images in process.

## Installation instructions
See file Doc/Installation.txt. An installer script exists to do most of the work with minor configuration. 

## Stuff
The tool was and still is an academic project to be used by forensic experts. It does not even try tro prevent user errors and recover from deliberate misuse. 

NTFS parser component can be of interest to other file system related projects. It parses the most complex NTFS attributes (directory structures) and allows a framework to extend upon. 

## Documentation
A simple manual and extension design notes can be found in Documentation. A quick start guide explains the image creation basics. 

## Future work
I have started work on web history and cache creation. This is still in early stages but I hope something usable comes out of it. 

### Author and contact details
Hannu Visti
<br>
hannu.visti@gmail.com

Comment, suggestions and feedback are welcome. 



