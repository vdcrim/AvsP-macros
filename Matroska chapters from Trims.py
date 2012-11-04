# -*- coding: utf-8 -*-

"""
Generate Matroska chapters from Avisynth Trims.
Additionally cut audio and text subtitles to match the trimmed video.

Requirements:

- vfr.py (for chapters, qpfile, and audio)
      http://forum.doom9.org/showthread.php?t=154535
- MKVToolNix (for vfr.py, only required for templates and audio)
      http://www.bunkus.org/videotools/mkvtoolnix/
- TrimSubs.py (for trimmed timecodes and subtitles)
      http://forum.doom9.org/showthread.php?t=163653
- PySubs 0.1.1 (for TrimSubs.py, if not using it as an executable)
      http://pypi.python.org/pypi/pysubs
- Python 3.2 (if not using both vfr and TrimSubs as executables)
      http://python.org/


Description:

This macro is a wrapper for vfr.py and TrimSubs.py.  It parses the 
Avisynth script in the current tab for a line with uncommented Trims, 
and based on them generates a Matroska chapter file and a QP file to 
be used with x264.  The chapter file can be customized through the use 
of a template (see vfr.py documentation).  By using a template, the 
chapters can be ordered (ordered chapters, ordered editions).

There are two ways of specifying the line of the avs used:
- Parse the avs from top to bottom or vice versa, and use the first 
  line with Trims found.
- Use a line with a specific comment at the end, e.g:
  Trim(0,99)++Trim(200,499)  # cuts

A frame rate or timecode file (v1 or v2) is required, except for MicroDVD 
subtitles. All other fields are optional.  The macro attempts to find 
valid default values for all parameters.  If a timecode is supplied, a 
new trimmed timecode v2 file is also generated.

Audio and text subtitle files can be cut to match the trimmed video.
The audio cutting is lossless.

Supported formats:
- Audio: as MKVToolNix does (hint: a lot).
- Subtitles: ASS, SSA, SRT, SUB (MicroDVD).

Ouput filenames (ext: original extension of the input file):
  Chapters:   avs_name.xml (mkv) or avs_name.chapters.txt (ogm)
  QP file:    avs_name.qpfile
  Timecode:   input_timecode_name.otc.ext
  Audio:      input_audio_name.cut.mka
  Subtitles:  input_subtitle_name.cut.ext


Installation instructions:

Place this script in your "AvsPmod\macros" directory.  By default, 
vfr.py and TrimSubs.py are expected to be found on "AvsPmod\tools", 
subdirectories also valid.  Set a custom path in the "preferences" 
section of this file otherwise.

If any of these two Python scripts isn't in stand-alone executable 
form, you will need to get installed Python 3.2 as well.

Some of the features in vfr.py require MKVToolNix.  You must do one 
of the following:
- Install or extract MKVToolNix to a directory in your PATH.
- Install or extract MKVToolNix to any directory and set a custom
  path in the first lines of vfr.py.

If your copy of TrimSubs.py isn't a stand-alone executable, you'll 
also neeed PySubs.  Do one of the following:
- Install PySubs with the Windows installer.
- Extract the contents of the source package to any directory, and put 
  TrimSubs.py inside.  You can then move the directory to "AvsPmod\tools" 
  if you want.


Date: 2012-06-08
Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
- add custom parsing order and label feature. Needs vfr.py 0.8.6.1+
- update prompt dialog


Copyright (C) 2011, 2012  Diego Fernández Gosende <dfgosende@gmail.com>

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

# Save the avs script before starting
save_avs = True

# Set custom paths, e.g. ur"D:\vfr.py". Python is not required if using 
# executables. vfr and TrimSubs path must include the right extension
python_path = ur"python32"
vfr_path = ur""
trimsubs_path = ur""

# Avisynth script default parsing order
parse_avs_top2bottom = False

# Only match the Trims line with 'label' as commentary
# e.g: Trim(0,99)++Trim(200,499)  # cuts
use_a_label_as_default = False
default_label = 'cuts'

# Set to False to use a default fps in the dialog box 
# (avoids refreshing the avs script)
fps_from_avs = True
fps_default = '24000/1001'

# Suffix list for automatic timecode file search
tc_suffix = ['.tc.txt', '.timecode.txt', '.timecodes.txt', 'timecode', 
             'timecodes', '.txt']

# Filename list for automatic template file search
template_list = ['template.txt', 'template']

# Set the subtitle file encoding. Only needed when it's neither a 
# Unicode encoding nor the system's locale encoding.
# See http://docs.python.org/library/codecs.html#standard-encodings
encoding = ''

# Generate OGM chapters instead of Matroska
ogm_chapters = False

# If this is set to True, the cmd windows won't close when the tasks 
# are finished
keep_cmd_open = True


#-------------------------------------------------------------------------------


# run in thread
from os import getcwdu, walk
from os.path import isfile, splitext, dirname, join
from sys import getfilesystemencoding
from subprocess import Popen

# Check paths
if vfr_path:
    if isfile(vfr_path):
        if vfr_path.endswith('.py'):
            vfr_path = python_path + '" "' + vfr_path
    else:
        avsp.MsgBox(_('Custom vfr.py path is invalid:\n') + vfr_path, _('Error'))
        return
if trimsubs_path:
    if isfile(trimsubs_path):
        if trimsubs_path.endswith('.py'):
            trimsubs_path = python_path + '" "' + trimsubs_path
    else:
        avsp.MsgBox(_('Custom TrimSubs.py path is invalid:\n') + trimsubs_path, 
                    _('Error'))
        return
if not vfr_path or not trimsubs_path:
    for parent, dirs, files in walk('tools'):
        for file in files:
            if not vfr_path:
                if file == 'vfr.py':
                    vfr_path = python_path + '" "' + join(getcwdu(), 
                                                          parent, file)
                    if trimsubs_path:
                        break
                    else:
                        continue
                if file == 'vfr.exe':
                    vfr_path = join(getcwdu(), parent, file)
                    if trimsubs_path:
                        break
                    else:
                        continue
            if not trimsubs_path:
                if file == 'TrimSubs.py':
                    trimsubs_path = python_path + '" "' + join(getcwdu(), 
                                                               parent, file)
                    if vfr_path:
                        break
                    else:
                        continue
                if file == 'TrimSubs.exe':
                    trimsubs_path = join(getcwdu(), parent, file)
                    if vfr_path:
                        break
                    else:
                        continue
        else:
            continue
        break
    else:
        if not vfr_path:
            avsp.MsgBox(_('vfr.py not found'), _('Error'))
        if not trimsubs_path:
            avsp.MsgBox(_('TrimSubs.py not found'), _('Error'))
        return

# Set the prompt default values
if not avsp.GetScriptFilename():
    if not avsp.SaveScript():
        return
if save_avs and not avsp.IsScriptSaved():
    avsp.SaveScript()
avs = avsp.GetScriptFilename()
if not avs:
    return
# Python 2.x doesn't support unicode args in subprocess.Popen()
# http://bugs.python.org/issue1759845
# Encoding to system's locale encoding
code = getfilesystemencoding()
avs = avs.encode(code)
avs_no_ext = splitext(avs)[0]
parsing_order = _('Top to bottom') if parse_avs_top2bottom else _('Bottom to top')
label = default_label if use_a_label_as_default else ''
for path in (avs_no_ext + ext for ext in tc_suffix):
    if isfile(path):
        fps = path
        break
else:
    if fps_from_avs:
        fps = str(avsp.GetVideoFramerate())
    else:
        fps = fps_default
if not ogm_chapters:
    for path in (join(dirname(avs),name) for name in template_list): 
        if isfile(path):
            template = path
            break
    else:
        template = ''
else:
    template = ''
def suffix_generator(list, suffix, max=4):
    for item in list:
        yield item
    for n in range(max):
        for item in list:
            yield suffix + str(n) + item
audio_ext = ['.flac', '.dts', '.ac3', '.ogg', '.m4a', '.aac', '.mp3', '.mp2', 
             '.wav', '.mka', '.webma', '.thd', '.eac3', '.truehd', '']
for path in (avs_no_ext + suffix for suffix in suffix_generator(audio_ext, '_Track')):
    if isfile(path):
        audio = path
        break
else:
    audio = ''
sub_ext = ['.ass', '.ssa', '.srt', '.sub']
for path in (avs_no_ext + suffix for suffix in suffix_generator(sub_ext, '_Track')):
    if isfile(path):
        subtitles = path
        break
else:
    subtitles = ''
timecode_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
template_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
subs_filter = (_('Subtitle files') + ' (*.ass;*.ssa;*.srt;*.sub)|*.ass;*.ssa;*.srt;*.sub|' + 
               _('All files') + '|*.*')

# Prompt for parameters
options = avsp.GetTextEntry(
      title=_('Matroska chapters from Trims - parameters for vfr and TrimSubs'),
      message=[[_('Avisynth script parsing order for\nsetting the line with Trims used'), 
                _('Only take a line with Trims into account\nif it ends with this commentary...')], 
               _('Frame rate or timecode file (v1 or v2)'), 
               _('Template file'), _('Audio file'), _('Subtitle file'), 
               _('Additional parameters for vfr.py')],
      default=[[(_('Top to bottom'), _('Bottom to top'), _(parsing_order)), label], 
               (fps, timecode_filter), (template, template_filter), audio, 
               (subtitles, subs_filter), ''], 
      types=['list_read_only', 'file_save', 'file_open', 'file_open', 'file_open'], 
      width=300)
if not options:
    return

# Set parameters
order = '' if options[0] == _('Top to bottom') else ' --reverse'
label = ' --label ' + options[1].strip() if options[1] else ''
fps = options[2]
if fps:
    if isfile(fps):
        fps = ' --fps "' + fps + '"'
        otc = ' --otc'
    else:
        fps = ' --fps ' + fps
        otc = ''
else:
    avsp.MsgBox(_('A frame rate value or timecode file is required'), _('Error'))
    return
template = ' --template "' + options[3] + '"' if options[3] else ''
audio = ' --input "' + options[4] + '" --merge --remove' if options[4] else ''
subtitles = ' --input "' + options[5] + '"' if options[5] else ''
if encoding:
    encoding = ' --encoding ' + encoding
chapters = ' --chapters "' + avs_no_ext.decode(code)
chapters += '.chapters.txt"' if ogm_chapters else '.xml"'

# Start processes
cmd = 'cmd /k' if keep_cmd_open else 'cmd /c'
vfr_args = (cmd + ' ""' + vfr_path + '"'
    + ' --verbose' 
    + ' "' + avs.decode(code) + '"'
    + order
    + label
    + chapters
    + template
    + fps
    + audio 
    + ' ' + options[6]
    + '"')
Popen(vfr_args.encode(code))
if subtitles or otc:
    order = ' --reversed' if order else ''
    trimsubs_args = (cmd + ' ""' + trimsubs_path + '"'
        + ' --verbose' 
        + ' "' + avs.decode(code) + '"'
        + order
        + label
        + subtitles 
        + encoding 
        + fps 
        + otc 
        + '"')
    Popen(trimsubs_args.encode(code))
