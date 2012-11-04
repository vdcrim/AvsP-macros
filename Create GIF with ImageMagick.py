# -*- coding: utf-8 -*-
"""
Create GIF with ImageMagick

Create a GIF from the script in the current tab. The video range can be 
optionally trimmed by adding pairs of bookmarks and selecting the 'only 
range between bookmarks' option. The GIF creation may take a while for 
long clips.

For loading/saving other formats with ImageMagick check out Wilbert's 
Immaavs AviSynth plugin <http://www.wilbertdijkhof.com>


Requirements:
- 'convert' executable from ImageMagick <http://www.imagemagick.org>


Windows installation:

By default the executable is expected to be found in 'AvsPmod\tools' 
or one of its subdirectories.  A path will be asked for in the first 
run otherwise.

If you only need ImageMagick for this macro then do the following: 
1) download the portable static version of IM
2) extract only convert.exe
3) place it on the 'AvsPmod\tools' directory


*nix installation:

Just install ImageMagick on your system.


Date: 2012-09-11
Latest version:  https://github.com/vdcrim/avsp-macros

Changelog:
- fix handle inheritance issue
- AvxSynth compatibility
- fix Python 2.6 compatibility


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
from os import getcwdu, walk, name
from os.path import isfile, splitext, basename, join
from sys import getfilesystemencoding
import subprocess
import shlex
import wx

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
            else: return
        avsp.Options['convert_path'] = convert_path
else:
    try:
        convert_path = subprocess.check_output(['which', 'convert']).splitlines()[0].strip()
    except:
        avsp.MsgBox(_("'convert' executable from ImageMagick not found"), 
                    _('Error'))
        return

# Prompt for options
speed_factor = avsp.Options.get('speed_factor', 2)
select_every = avsp.Options.get('select_every', 4)
loops = avsp.Options.get('loops', 0)
use_bm_only = avsp.Options.get('use_bm_only', True)
dither = avsp.Options.get('dither', _('Ordered + Error correction'))
optimize = avsp.Options.get('optimize', False)
add_params = avsp.Options.get('add_params', '')
notify_at_end = avsp.Options.get('notify_at_end', True)
dither_list = [_('None'), _('Riemersma'), _('Floyd-Steinberg'), _('Ordered'), 
               _('Ordered + Error correction')]
dither_cmd =  ('+dither', '-dither Riemersma', '-dither FloydSteinberg', 
               '-ordered-dither o8x8,16,16,8', '-ordered-dither o8x8,28,28,14')
dither_dict = dict(zip(dither_list, dither_cmd))
output_path = avsp.GetScriptFilename()
if output_path:
    output_path = splitext(output_path)[0] + '.gif' 
gif_filter = (_('GIF files') + ' (*.gif)|*.gif|' + _('All files') + '|*.*')
while True:
    options = avsp.GetTextEntry(
            title=_('Create GIF with ImageMagick'),
            message=[[_('Speed factor'), _('Select every'), _('Loops (0: infinite)')], 
                     _('Include only the range between bookmarks, if any'), 
                     [_('Dithering'), _('Optimize')], 
                     _('Additional parameters (applied before dithering)'),
                     [_('Save current settings as default'), _('Notify when finished')],  
                     _('Output GIF path')
                    ], 
            default=[[(speed_factor, 0, None, 2, 0.25), 
                      (select_every, 1), (loops, 0)], 
                     use_bm_only, 
                     [dither_list + [dither], optimize], 
                     add_params, [False, notify_at_end], (output_path, gif_filter)
                    ], 
            types=[['spin', 'spin', 'spin'], 'check', ['list_read_only', 'check'], 
                   '', ['check', 'check'], 'file_save'],
            width=350) 
    if not options:
        return
    elif not options[-1]:
        avsp.MsgBox(_('Missing output path'), _('Error'))
    else: break

# Set options
speed_factor = options[0]
select_every = options[1]
loops = options[2]
use_bm_only = options[3]
dither = options[4]
optimize = '-layers optimize' if options[5] else ''
add_params = options[6]
save_defaults = options[7]
notify_at_end = options[8]
output_path = options[-1]
if save_defaults:
    avsp.Options['speed_factor'] = speed_factor
    avsp.Options['select_every'] = select_every
    avsp.Options['loops'] = loops
    avsp.Options['use_bm_only'] = use_bm_only
    avsp.Options['dither'] = dither
    avsp.Options['optimize'] = bool(optimize)
    avsp.Options['add_params'] = add_params
    avsp.Options['notify_at_end'] = notify_at_end
delay = float(100) / avsp.GetVideoFramerate() * select_every / speed_factor
avs = avsp.GetWindow().currentScript
width = avsp.GetVideoWidth()
height = avsp.GetVideoHeight()
header='id=ImageMagick columns={0} rows={1}\n\f:\x1A'.format(width, height)
if use_bm_only:
    bmlist = avsp.GetBookmarkList()
    if not bmlist:
        gif_range = range(0, avsp.GetVideoFramecount(), select_every)
    else:
        if len(bmlist) % 2 and not avsp.MsgBox(_('Odd number of bookmarks'), 
                                               _('Warning'), cancel=True):
            return
        bmlist.sort()
        gif_range = []
        for i, bm in enumerate(bmlist):
            if i%2:
                gif_range.extend(range(bmlist[i-1], bm+1, select_every))
else:
    gif_range = range(0, avsp.GetVideoFramecount(), select_every)

# Pipe the image data to convert.exe as a multi-image miff file

# - Issue 1: Python 2.x doesn't support unicode args in subprocess.Popen()
#   http://bugs.python.org/issue1759845
#   Encoding to system's locale encoding
# - Issue 2: handle inheritance issues if any of stdin, stdout or stderr 
#   but not all three are specified and the process is started under some 
#   circumstances.
#   http://www.py2exe.org/index.cgi/Py2ExeSubprocessInteractions
#   http://bugs.python.org/issue3905
#   http://bugs.python.org/issue1124861
code = getfilesystemencoding()
cmd = ur'"{0}" miff:- -dispose None -loop {1} -set delay {2} {3} {4} {5} "{6}"'.format(
      convert_path, loops, delay, add_params, dither_dict[dither], optimize, 
      output_path).encode(code)
cmd = shlex.split(cmd)
if name == 'nt':
    info = subprocess.STARTUPINFO()
    try:
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
    except AttributeError:
        import _subprocess
        info.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = _subprocess.SW_HIDE
    cmd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT, startupinfo=info)
else:
    cmd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT)
try:
    for frame in gif_range:
        avsp.ShowVideoFrame(frame)
        bmp = wx.EmptyBitmap(width, height)
        mdc = wx.MemoryDC()
        mdc.SelectObject(bmp)
        dc = mdc if avsp.GetWindow().version > '2.3.1' else mdc.GetHDC()
        avs.AVI.DrawFrame(frame, dc)
        img = bmp.ConvertToImage()
        cmd.stdin.write(header + img.GetData())
    cmd.stdin.close()
    avsp.HideVideoWindow()
    if notify_at_end:
        cmd.wait()
        avsp.MsgBox(_('GIF created'), _('Info'))
except:
    if cmd.poll() is None:
        cmd.terminate()
    raise
