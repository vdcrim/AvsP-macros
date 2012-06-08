# -*- coding: utf-8 -*-

"""
Overlay a clip on top of another using a mask with a prescribed shape

Requirements:
- GraMaMa AviSynth filter <http://www.wilbertdijkhof.com/>

Instructions:
This macro uses the last assigned variable as the overlay clip and 'last' 
as the overlayed. Example:

  ColorBars(pixel_type="yv12")
  alt=Invert()

becomes:

  ColorBars(pixel_type="yv12")
  alt=Invert()
  Overlay(alt, mask=GraMaMa(mode=1, a=200, b=200, rad=100, rad2=100, binarize=False).Invert(), mode="blend")

where (a, b) is the center of the mask, selected by clicking on the video 
preview.


Latest version:  https://github.com/vdcrim/avsp-macros

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

# GraMaMa parameters (actually called 'mode', 'rad', 'rad2' and 'binarize')
shape = 'Circle'
horizontal_radius = 100
vertical_radius = 100
binarize = False

# The macro uses the last assigned variable as the "overlay" clip.  If there 
# isn't any assign in the script it uses the following variable name:
clip = 'b'

# Refresh the video preview at the end
refresh_preview = True


# ------------------------------------------------------------------------------


import re

shape_list = [_('Circle'), _('Square'), _('Diamond'), _('Line'), _('Ellipse'), 
              _('Rectangle')]
options = avsp.GetTextEntry(title=_('GraMaMa mask'), 
    message=[[_('Shape'), _('Horizontal radius'), _('Vertical radius'), _('Binarize')], 
             _('Select the center of the mask after pressing OK')], 
    default=[[shape_list + [shape], horizontal_radius, vertical_radius, binarize], 0], 
    types=[['list_read_only', 'spin', 'spin', 'check'], 'sep'], 
    width=0)
if not options:
    return
for i, shape in enumerate(shape_list):
    if options[0] == shape:
        mode = i + 1
        break
rad = options[1]
rad2 = options[2]
binarize = options[3]

avs_text = avsp.GetText()
re_assign = re.compile(r'\s*(\w+)\s*=')
for line in reversed(avs_text.splitlines()):
    if re_assign.match(line):
        clip = re_assign.match(line).group(1)
        break
if avs_text.endswith('\n'):
    avsp.InsertText('last')
else:
    avsp.InsertText('\nlast')
xy = avsp.GetPixelInfo()
avs = avsp.GetWindow().currentScript
avs.SetSelection(avs.PositionFromLine(avs.GetLineCount() - 1), -1)
avs.Clear()
if xy:
    avsp.InsertText(u'Overlay({}, mask=GraMaMa(mode={}, a={}, b={}, rad={}, '
                     'rad2={}, binarize={}).Invert(), mode="blend")\n'.format(
                     clip, mode, xy[0][0], xy[0][1], rad, rad2, binarize))
    if refresh_preview:
        avsp.UpdateVideo()
