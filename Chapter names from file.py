# -*- coding: utf-8 -*-

"""
Replace default chapter names in Matroska chapter files with names provided 
in a specified file, one chapter name per line. All xml files in the given 
directory are processed.

Intended for use with vfr.py (http://forum.doom9.org/showthread.php?t=154535)


Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
  v1: initial release
  v2: updated prompt dialog. Needs AvsPmod 2.3.0+
  v3: fixes


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

# Default name of chapters (it can be a regular expression)
default_name = r'Chapter'

# Filename list for chapter names file search
chapters_name_filename = ['chapter names.txt', 'chapter_names.txt', 
                          'chapters.txt', 'cnames.txt', 'chapters'
                          'chapter titles.txt', 'chapter_titles.txt', 
                          'titles.txt', 'ctitles.txt', 'titles']


# ------------------------------------------------------------------------------


# run in thread
from os import listdir
from os.path import isfile, isdir, dirname, join
import re

avs = avsp.GetScriptFilename()
chapters_directory = dirname(avs)
chapters_name_filename += [name.capitalize() for name in chapters_name_filename]
for path in (join(chapters_directory, name) for name in chapters_name_filename):
    if isfile(path):
        names_file = path
        break
else:
    names_file = ''
txt_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
options = avsp.GetTextEntry(title='Chapter names from file',
                            message=['Chapter names file', 
                                     'Matroska chapter files directory'], 
                            default=[(names_file, txt_filter), chapters_directory], 
                            types=['file_open', 'dir'])
if not options:
    return
else:
    names_file, chapters_directory = options
if not isfile(names_file):
    avsp.MsgBox('Chapter names file not found:\n' + names_file)
    return
if not isdir(chapters_directory):
    avsp.MsgBox('The specified directory does not exist:\n' + chapters_directory)
    return
with open(names_file) as names_file:
    names = names_file.readlines()
xml_list = filter(lambda path: path.endswith('.xml'), listdir(chapters_directory))
re_chapter = re.compile(
  r'(^.*<ChapterString>)\s*' + default_name + r'\s*(</ChapterString>.*$)')
chapter = 0
for xml in xml_list:
    with open(join(chapters_directory, xml), 'r+') as chapter_file:
        lines = chapter_file.readlines()
        for i, line in enumerate(lines):
            res = re_chapter.search(line)
            if res:
                if len(names) < chapter + 1:
                    avsp.MsgBox('Not enough chapter names: {} titles, {} files'
                                .format(len(names), chapter + 1), 'Warning')
                    return
                lines[i] = re_chapter.sub(
                           r'\g<1>{}\g<2>'.format(names[chapter].strip()), line)
                chapter += 1
        chapter_file.seek(0)
        chapter_file.truncate()
        chapter_file.writelines(lines)
