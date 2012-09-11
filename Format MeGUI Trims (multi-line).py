# -*- coding: utf-8 -*-

"""
Reformat MeGUI generated Trims in the Avisynth script in the current 
tab, e.g:

__film = last
__t0 = __film.trim(35, 118)
__t1 = __film.trim(199, 273)
__t0 ++ __t1 

to:

v = last
v.Trim(35,118)
p1 = last
v.Trim(199,273)
p2 = last
p1 ++ p2


Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
  v1: initial release
  v2: keep the rest of the line after Trim

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

import re

re_trim = re.compile(r'trim\(\s*(\d+)\s*,\s*(\d+)\s*\)(.*)', re.IGNORECASE)
avs = avsp.GetWindow().currentScript
lines = avsp.GetText().splitlines()
start, end = 0, 0
trims = []
for i, line in enumerate(lines):
    if '__film' in line:
        if not start:
            start = avs.PositionFromLine(i)
        else:
            trims.append(re_trim.search(line).groups())
    elif start:
        end = avs.GetLineEndPosition(i)
        break
else:
    avsp.MsgBox(_('No MeGUI Trims in file'), _('Error'))
    return
avs.SetSelection(start,end)
avs.Clear()

trim_text = 'v = last\n'
clip = ''
for i, trim in enumerate(trims):
    trim_text += 'v.Trim({0},{1}){2}\np{4} = last\n'.format(trim[0], trim[1], 
                                                            trim[2], i + 1)
    clip += 'p{0} ++ '.format(i + 1)
avsp.InsertText(trim_text + clip[:-4], pos=None)
