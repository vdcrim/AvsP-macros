# -*- coding: utf-8 -*-

"""
Reformat MeGUI generated Trims to a single line in the Avisynth script 
in the current tab.


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

import re

re_trim = re.compile(r'trim\(\s*(\d+)\s*,\s*(\d+)\s*\)', re.IGNORECASE)
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
    avsp.MsgBox('No MeGUI Trims in file', 'Error')
    return
avs.SetSelection(start,end)
avs.Clear()

trims_text = ''
for trim in trims:
    trims_text += 'Trim({},{})++'.format(*trim)
avsp.InsertText(trims_text[:-2], pos=None)
