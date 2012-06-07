# -*- coding: utf-8 -*-

"""
Insert Trims (multi-line) based on the video frame bookmarks at the 
current cursor position of the Avisynth script in the current tab.


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

trim_text = 'v = last\n'
bm_list = avsp.GetBookmarkList()
bm_list.sort()
clip = ''
for i, bm in enumerate(bm_list):
    if i%2:
        trim_text += 'v.Trim({},{})\np{} = last\n'.format(bm_list[i - 1], 
                                                        bm, i//2 + 1)
        clip += 'p{} ++ '.format(i//2 + 1)
avsp.InsertText(trim_text + clip[:-4], pos=None)
if not i%2:
    avsp.MsgBox('Odd number of bookmarks', title='Warning')
