# -*- coding: utf-8 -*-

"""
Create mask with ImageMagick

The mask vertices are selected by clicking on the video preview.  If 
'apply mask to script' is selected, 'Overlay' is inserted using the 
last assigned variable as the overlay clip and 'last' as the overlayed.  

Example:

  ColorBars()
  alt = Invert()

turns into:

  ColorBars()
  alt = Invert()
  mask = ImageSource("C:\mask\path.png")
  Overlay(alt, mask=mask, mode="blend")


Requirements:
- 'convert' executable from ImageMagick <http://www.imagemagick.org>


Windows installation:

By default the executable is expected to be found in 'AvsPmod\tools' 
or one of its subdirectories.  A path will be asked for on the first 
run otherwise.

If you only need ImageMagick for this macro then do the following: 
1) download the portable static version of IM
2) extract only convert.exe
3) place it on the 'AvsPmod\tools' directory


*nix installation:

Just install ImageMagick on your system.


Latest version:  https://github.com/vdcrim/avsp-macros

Changelog:
  v1: initial release
  v2: AvxSynth compatibility


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


# ------------------------------------------------------------------------------


# run in thread
from sys import getfilesystemencoding
from os import getcwdu, walk, name
from os.path import isfile, basename, join
import subprocess
import re

# Check convert.exe path
if name == 'nt':
    convert_path = avsp.Options.get('convert_path')
    if not convert_path or not isfile(convert_path):
        avsp.Options['convert_path'] = None
        for parent, dirs, files in walk('tools'):
            for file in files:
                if file == 'convert.exe':
                    convert_path = join(getcwdu(), parent, file)
                    break
            else:
                continue
            break
        else:
            if avsp.MsgBox(_("'convert.exe' from ImageMagick not found\n\n"
                           "Press 'Accept' to specify a path. Alternatively copy\n"
                           "the executable to the 'tools' subdirectory."), 
                         _('Error'), True):
                convert_path = avsp.GetFilename(_('Select the convert.exe executable'), 
                                                _('Executable files') + ' (*.exe)|*.exe|' + 
                                                _('All files') + ' (*.*)|*.*')
                if not convert_path:
                    return
        avsp.Options['convert_path'] = convert_path
else:
    try:
        convert_path = subprocess.check_output(['which', 'convert']).splitlines()[0].strip()
    except:
        avsp.MsgBox(_("'convert' executable from ImageMagick not found"), 
                    _('Error'))
        return

# Get options
mask_path = avsp.GetScriptFilename()
if mask_path:
    mask_path = mask_path[:-4] + '.png'
while True:
    options = avsp.GetTextEntry(
            title=_('Create mask - select the vertices after pressing OK'),
            message=[_('Output path'), 
                     [_('Blur'), _('Apply mask to script'),_('Refresh preview')]
                    ], 
            default=[mask_path, [(0, 0, 65355, 1), True, True]], 
            types=['file_save', ['spin', 'check', 'check']], 
            width=350)
    if not options: return
    if options[0]: break
    if not avsp.MsgBox(_('An output path is needed'), _('Error'), True):
        return
mask_path, blur, apply_mask, refresh_preview = options
if not mask_path.endswith('.png'):
    mask_path = mask_path + '.png'
blur = ('-blur', '0x{}'.format(blur)) if blur else ('',) * 2

# Search for the overlay clip
avs_text = avsp.GetText()
if apply_mask:
    clip = 'b'
    re_assign = re.compile(r'\s*(\w+)\s*=')
    for line in reversed(avs_text.splitlines()):
        if re_assign.match(line):
            clip = re_assign.match(line).group(1)
            break

# Add 'last' at the end, just in case
if avs_text.endswith('\n'):
    avsp.InsertText('last')
else:
    avsp.InsertText('\nlast')

# Get the mask vertices
version = avsp.GetWindow().version
if version < '2.3.0':
    avsp.MsgBox(_('AvsPmod 2.3.0+ needed'), _('Error'))
    return
elif version == '2.3.0':
    points = avsp.GetPixelInfo(color=None, wait=True)
else:
    points = avsp.GetPixelInfo(color=None, wait=True, lines=True)
if not points:
    avsp.MsgBox(_('Not points selected - mask creation aborted'), _('Info'))
    return
if len(points) < 3:
    avsp.MsgBox(_('At least three points are needed'), _('Error'))
    return

width, height = avsp.GetVideoWidth(), avsp.GetVideoHeight()

# Delete 'last'
avs = avsp.GetWindow().currentScript
avs.SetSelection(avs.PositionFromLine(avs.GetLineCount() - 1), -1)
avs.Clear()

# Create the mask with ImageMagick

# - Issue 1: Python 2.x doesn't support unicode args in subprocess.Popen()
#   http://bugs.python.org/issue1759845
#   Encoding to system's locale encoding
# - Issue 2: handle inheritance issues if any of stdin, stdout or stderr 
#   but not all three are specified and the process is started under some 
#   circumstances.
#   http://www.py2exe.org/index.cgi/Py2ExeSubprocessInteractions
#   http://bugs.python.org/issue3905
#   http://bugs.python.org/issue1124861
cmd = [convert_path, '-type', 'Grayscale', '-depth', '8', '-size', 
       '{}x{}'.format(width, height), 'xc:black', '-fill', 'white', '-draw', 
       'polygon {}'.format(' '.join(['{},{}'.format(x, y) for x, y in points])),
       blur[0], blur[1], mask_path]
code = getfilesystemencoding()
cmd = [arg.encode(code) for arg in cmd]
if name == 'nt':
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    cmd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT, startupinfo=info)
else:
    cmd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT)

# Wait for the mask to be created and insert it in the script
stdout = cmd.communicate()[0]
if cmd.returncode:
    avsp.MsgBox(_('Mask creation failed:\n' + stdout), _('Error'))
elif apply_mask:
    avsp.InsertText(u'mask={}\nOverlay({}, mask=mask, mode="blend")\n'
                    .format(avsp.GetSourceString(mask_path), clip))
    if refresh_preview:
        avsp.UpdateVideo()