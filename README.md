metafiend
=========

Quick and easy metainfo extraction and scrubber for many file formats. The goal here is re-use existing tools whenever possible, but to normalize their usage.

All of the work is done via Python libraries for specific file formats, or tools like Exiftool or FFMPEG.

Installation:
-------------

1. pip install pypdf openxmllib
2. (OSX) brew install exiftool ffmpeg
3. (Ubuntu) sudo apt-get install exiftool ffmpeg