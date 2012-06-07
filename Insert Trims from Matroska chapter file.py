
"""
Insert Trims in an Avisynth script from a Matroska chapter file

This macro takes a Matroska chapter file, gets the starting time 
of every chapter, and generates a line of Trims in which every Trim's 
starting frame corresponds to a starting time, and the end frame is 
next Trim's starting time - 1.

This can be useful to redo a previously non-ordered chapters encode to 
ordered, if the original avs is no longer available.

The FPS of the video is needed. It can be obtained from the avs or 
introduced directly. Currently only constant frame rate is supported. 

A chapter file is automatically searched for in the same directory as 
the Avisynth script (see 'preferences' section). A path is asked if it 
can't be found.


Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
  v1: initial release


Copyright (C) 2012  Diego Fernández Gosende <dfgosende@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along 
with this program.  If not, see <http://www.gnu.org/licenses/gpl-2.0.html>.

"""

# PREFERENCES

# Suffix list for automatic chapter file search
chapters_suffix = ['_Chapters.xml', '.chapters.xml', '.xml']

# Ask for a FPS intead of get it from the avs
ask_fps = False


# ------------------------------------------------------------------------------


import re
from os.path import splitext, isfile

def time2ms(time):
    time_split = [int(i) for i in re_split.search(time).groups()]
    return ((time_split[0] * 60 + time_split[1]) * 60 + time_split[2]) *1000 + time_split[3] / 10**6

# Get chapter file path
if not avsp.GetScriptFilename():
    if not avsp.SaveScript():
        return
avs = avsp.GetScriptFilename()
if not avs:
    return
for path in (splitext(avs)[0] + suffix for suffix in chapters_suffix):
    if isfile(path):
        chapters_path = path
        break
else:
    chapters_path = avsp.GetFilename('Choose the Matroska chapter file', '*.xml')
    if not chapters_path:
        return

# Get every starting Trim time (ms)
re_chapters = re.compile(ur'^.*<ChapterTimeStart>\s*(\d+:\d+:\d+.\d+\s*)</ChapterTimeStart>.*$')
re_split = re.compile(ur'(\d+):(\d+):(\d+).(\d+)')
if ask_fps:
    fps = avsp.GetTextEntry(title='Specify the FPS', 
                            message='Introduce the frame rate of the video:')
    if fps:
        fps = int(fps)
    else:
        return
else:
    fps = avsp.GetVideoFramerate()
chapters_ms = []
with open(chapters_path) as file:
    for line in file:
        chapter = re_chapters.search(line)
        if chapter:
            chapters_ms.append(time2ms(chapter.group(1)))

# Convert ms to frame number and insert the Trims
trims = 'Trim('
i, j = 0, 0
while True:
    if 1000 / fps * i >= chapters_ms[j]:
        if abs(1000 / fps * i - chapters_ms[j]) < abs(1000 / fps * (i - 1) - chapters_ms[j]):
            trims += '{})++Trim({},'.format(i - 1, i)
        else:
            trims += '{})++Trim({},'.format(i - 2, i - 1)
        if j + 1 == len(chapters_ms):
            break
        j += 1
    i += 1
avsp.InsertText(trims.partition('++')[2] + str(avsp.GetVideoFramecount() - 1) + ')', pos=None)
