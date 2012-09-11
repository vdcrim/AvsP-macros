# -*- coding: utf-8 -*-

"""
Divide an Avisynth script into multiple avs according to AvsP bookmarks.  
The first and last frame are automatically added to the bookmarks if not 
already present.


Latest version:  https://github.com/vdcrim/avsp-macros
Created for http://forum.doom9.org/showthread.php?p=1568663#post1568663

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

# If True, save the new scripts to the same directory and with the same 
# name as the input avs (if exists).
use_same_avs_dir = False

# If True, save the scripts always to this location, e.g. ur"C:\Scripts", 
# using the following basename.  If basename is empty take it from the 
# input avs.  If there's not avs, prompt for a name:
use_avs_dir = False
avs_dir = ur""  
base_name = ur""


# ------------------------------------------------------------------------------


from os import makedirs
from os.path import isdir, basename, join
import codecs

bm_list = avsp.GetBookmarkList()
if not bm_list:
    avsp.MsgBox(_('There is not bookmarks'), _('Error'))
    return
avs = avsp.GetScriptFilename()
if not (use_same_avs_dir and avs):
    if use_avs_dir and avs_dir:
        if not isdir(avs_dir):
            makedirs(avs_dir)
        if not base_name:
            if avs:
                base_name = basename(avs)
            else:
                base_name = avsp.GetTextEntry(_('Introduce a basename for the new scripts'), 
                                              'avs_trim', _('Divide script'))
                if not base_name:
                    return
        avs = join(avs_dir, base_name)
    else:
        avs = avsp.GetSaveFilename(_('Select a directory and basename for the new scripts'))
        if not avs:
            return
if avs.endswith('.avs'):
    avs = avs[:-4]

bm_list.sort()
if bm_list[0] != 0:
    bm_list[:0] = [0]
frame_count = avsp.GetVideoFramecount()
if bm_list[-1] == frame_count - 1:
    bm_list[-1] = frame_count
else:
    bm_list.append(frame_count)
digits = len(str(len(bm_list) - 1))
text = avsp.GetText()
avs_list = []
for i, bm in enumerate(bm_list[:-1]):
    avs_path = u'{0}_{1:0{2}}.avs'.format(avs, i+1, digits)
    avs_list.append(avs_path)
    with codecs.open(avs_path, 'w', 'utf-8') as f:
        f.write(text + '\nTrim({0},{1})\n'.format(bm, bm_list[i+1] - 1))
return avs_list
