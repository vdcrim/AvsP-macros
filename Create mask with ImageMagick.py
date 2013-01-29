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


Date: 2013-01-29
Latest version:  https://github.com/vdcrim/avsp-macros

Changelog:
- AvxSynth compatibility
- fix Python 2.6 compatibility
- fix blur=0


Copyright (C) 2012, 2013  Diego Fernández Gosende <dfgosende@gmail.com>

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
import sys
import os
import os.path
import subprocess
import re

def check_executable_path(executable, check_PATH_Windows=True, check_PATH_nix=False, 
                          error_message=None):
    """Check if executable is in the 'tools' directory or its subdirectories or PATH"""
    
    def prompt_path(executable, message_prefix):
        """Prompt for a path if not found"""
        if avsp.MsgBox(_("{0}\n\nPress 'Accept' to specify a path. Alternatively copy\n"
                         "the executable to the 'tools' subdirectory.".format(message_prefix)), 
                       _('Error'), True):
            filter = _('Executable files') + ' (*.exe)|*.exe|' if os.name == 'nt' else ''
            filter = filter + _('All files') + ' (*.*)|*.*'
            executable_path = avsp.GetFilename(_('Select the {0} executable').format(executable), 
                                               filter)
            if executable_path:
                avsp.Options['{0}_path'.format(executable)] = executable_path
                return True
    
    tools_dir = avsp.GetWindow().toolsfolder
    executable_lower = executable.lower()
    for parent, dirs, files in os.walk(tools_dir):
        for file in files:
            if file.lower() in (executable_lower, executable_lower + '.exe'):
                avsp.Options['{0}_path'.format(executable)] = os.path.join(parent, file)
                return True
    if os.name == 'nt':
        if check_PATH_Windows:
            try:
                path = subprocess.check_output('for %i in ({0}) do @echo. %~$PATH:i'.
                            format(executable + '.exe'), shell=True).strip().splitlines()[0]
                if not os.path.isfile(path) and not os.path.isfile(path + '.exe'):
                    raise
            except: pass
            else:
                avsp.Options['{0}_path'.format(executable)] = path
                return True
    else:
        if check_PATH_nix:
            try:
               path = subprocess.check_output(['which', 'convert']).strip().splitlines()[0]
            except: pass
            else:
                avsp.Options['{0}_path'.format(executable)] = path
                return True
    if error_message is None:
        error_message = _("{0} not found").format(executable)
    return prompt_path(executable, error_message)

self = avsp.GetWindow()

# Check convert path
convert_path = avsp.Options.get('convert_path', '')
if not os.path.isfile(convert_path):
    if not check_executable_path('convert', False, True,
                                 _("'convert' from ImageMagick not found")):
        return
    convert_path = avsp.Options['convert_path']

# Get options
mask_path = avsp.GetScriptFilename()
if not mask_path:
    if self.version > '2.3.1':
        mask_path = avsp.GetScriptFilename(propose='image')
    else:
        mask_path = os.path.join(self.options['recentdir'], 
            self.scriptNotebook.GetPageText(self.scriptNotebook.GetSelection()).lstrip('* '))
base, ext = os.path.splitext(mask_path)
if ext in ('.avs', '.avsi'):
    mask_path = base
mask_path = mask_path + '.png' 
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
blur = ('-blur', '0x{0}'.format(blur)) if blur else None

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
version = self.version
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
avs = self.currentScript
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
       '{0}x{1}'.format(width, height), 'xc:black', '-fill', 'white', '-draw', 
       'polygon {0}'.format(' '.join(['{0},{1}'.format(x, y) for x, y in points]))]
if blur: cmd.extend(blur)
cmd.append(mask_path)
code = sys.getfilesystemencoding()
cmd = [arg.encode(code) for arg in cmd]
if os.name == 'nt':
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

# Wait for the mask to be created and insert it in the script
stdout = cmd.communicate()[0]
if cmd.returncode:
    avsp.MsgBox(_('Mask creation failed:\n' + stdout), _('Error'))
elif apply_mask:
    avsp.InsertText(u'mask={0}\nOverlay({1}, mask=mask, mode="blend")\n'
                    .format(avsp.GetSourceString(mask_path), clip))
    if refresh_preview:
        avsp.UpdateVideo()