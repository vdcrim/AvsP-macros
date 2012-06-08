# -*- coding: utf-8 -*-

"""
Apply an Avisynth script to all the JPEG files in a specified directory.
See PREFERENCES section below.


Latest version: https://github.com/vdcrim/avsp-macros
Created for http://forum.doom9.org/showthread.php?p=1552739#post1552739

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

suffix = '_new'
format = '.png'
jpg_quality = 90

# Avisynth script. Replace the input path with "in_path".
script = ur"""
ImageSource("in_path", use_DevIL=true)
"""


# ------------------------------------------------------------------------------


# run in thread
from os import listdir
from os.path import splitext, basename, join

dir_path = avsp.GetDirectory(title=_('Select a directory'))
if not dir_path:
    return
avsp.NewTab()
progress = avsp.ProgressBox(max=1000, title=_('Batch processing progress'))
paths = [join(dir_path, filename) for filename in filter(
                               lambda x: x.endswith('.jpg'), listdir(dir_path))]
for i, path in enumerate(paths):
    if not progress.Update(i*1000.0/len(paths), basename(path))[0]:
        break
    avsp.SetText(script.replace('in_path', path))
    try:
        if using_jpg_quality_no_dialog_fix:
            avsp.SaveImage(splitext(path)[0] + suffix + format, quality=jpg_quality)
        else:
            avsp.SaveImage(splitext(path)[0] + suffix + format)
    except:
        avsp.MsgBox(_('Processing failed at ') + basename(path))
        break
progress.Destroy()
avsp.HideVideoWindow()
avsp.CloseTab()