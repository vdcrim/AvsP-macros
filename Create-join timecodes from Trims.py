# -*- coding: utf-8 -*-

"""
Generate a timecode file from a line with uncommented Trims

This macro creates a new timecode from a line with uncommented Trims in 
the script from the current tab.  It's meant to be used when obtaining 
a VFR video as a result of deinterlacing/IVTC various sections of the 
video in different ways, or joining several videos of different FPS.

That timecode can then be passed to an encoder or muxer, or be used 
as the timebase for the creation of chapters and the cutting of audio 
and subtitles.

You need to specify a frame rate value for every Trim.  If a range of 
your video is already VFR, a timecode v1 or v2 can be used for that 
Trim by passing the 'itc' alias instead of a FPS value.  If timecodes 
are passed as input then the output timecode will be v2, otherwise v1.

The output timecode can span all the video range or only the trimmed 
zones.  For the former you also need to assign a FPS to the video range 
outside of the Trims.

There are three ways of specifying the line of the avs used:
- Parse the avs from top to bottom (default) or vice versa, and use the 
  first line with Trims found.
- Use a line with a specific comment at the end, e.g:
  Trim(0,99)++Trim(200,499)  # ivtc
  It can be combined with a parsing order.
- Directly specifying the Trims line number, starting with 1.


Date: 2013-01-29
Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
- support for negative last frame of Trim
- update prompt dialog
- accept spaces between Trim and its parameters
- fix error when using a single timecode
- fix Python 2.6 compatibility
- move 'ask for options' setting to the prompt
- accept selecting the Trims line by specifying directly the line number


Copyright (C) 2011-2013  Diego Fernández Gosende <dfgosende@gmail.com>

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
save_avs = False

# Default FPS for the video range outside of the Trims
default_fps = '24000/1001'
use_default_fps = False

# List of frame rate alias
fps_alias = {'ntsc_film': 24/1.001, 'ntsc_video': 30/1.001}


# ------------------------------------------------------------------------------


# run in thread
import os
from os.path import splitext, isfile
from sys import getfilesystemencoding
import re

def timecode_v1_to_v2(lines, offset=0, start=0, end=None, default=24/1.001):
    """Convert a timecode v1 file to v2
    
    lines:    list of lines of the timecode v1 file (excluding header)
    offset:   starting time (ms)
    start:    first frame
    end:      last frame
    default:  FPS used if 'assume' line isn't present
    
    Returns the list of timecode v2 lines (str, without header and '0')
    
    """
    # Generate all intervals in range (start, end)
    inters = []
    all_inters =[]
    try:
        default = float(lines[0].split()[1])
        i = 1
    except IndexError:
        i = 0
    inters = [[int(line[0]), int(line[1]), float(line[2])] for line in 
                                [line.strip().split(',') for line in lines[i:]]]
    if start < inters[0][0]:
        all_inters.append([start, inters[0][0] - 1, default])
    else:
        for i, inter in enumerate(inters):
            if inter[0] < start:
                if inter[1] > start:
                    inter[0] = start
                inters[:i] = []
    try:
        for i, inter in enumerate(inters):
            if inter[1] > end:
                if inter[0] > end:
                    break
                else:
                    inter[1] = end
                    all_inters.append(inter)
                    break
            all_inters.append(inter)
            if inters[i+1][0] - inter[1] > 1:
                all_inters.append([inter[1] + 1, inters[i+1][0] - 1, default])
    except IndexError:
        if end > inters[-1][1]:
            all_inters.append([inters[-1][1] + 1, end, default])

    # v1 -> v2
    v2 = []
    for inter in all_inters:
        ms = 1000.0 / inter[2]
        for i in range(1, inter[1] - inter[0] + 2):
            v2.append('{0:.3f}\n'.format(ms * i + offset))
        offset = float(v2[-1])
    return v2

def ask_trim_options():
    '''Prompt for the Trims line selection options'''
    reversed_ = avsp.Options.get('reversed_', False)
    use_label = avsp.Options.get('use_label', False)
    label = avsp.Options.get('label', 'ivtc')
    use_line = avsp.Options.get('use_line', False)
    line_number = avsp.Options.get('line_number', 1)
    lines = avsp.GetText().splitlines()
    options = avsp.GetTextEntry(title=_('Trims line selection options'), 
            message=[ _('Parse script from bottom to top instead of top to bottom '
                       'for a line with Trims'),
                     [_('Use the Trims line with #label'), _('Label')],
                     [_('Specify directly a line'), _('Line number')]], 
            default=[reversed_, [use_label, label],
                     [use_line, (line_number, 1, len(lines))]], 
            types=['check', 'check', ['check', 'spin']])
    if not options:
        return
    (avsp.Options['reversed_'], avsp.Options['use_label'], avsp.Options['label'], 
     avsp.Options['use_line'], avsp.Options['line_number']) = options
    return options

def parse_trims(reversed_=None, use_label=None, label='', use_line=None, line_number=1):
    '''Parse script for a Trims line'''
    lines = avsp.GetText().splitlines()
    if use_line:
        use_label = False
        lines = lines[line_number - 1:line_number]
    re_line = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\).*{0}'
                         .format('#\s*' + label if use_label else ''), re.I)
    re_trim = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\)', re.I)
    for line in (reversed(lines) if reversed_ else lines):
        if re_line.search(line):
            trims = []
            end = len(line)
            while(1):
                res = re_trim.search(line[:end])
                if res is None:
                    break
                else:
                    trims.append(res.groups())
                    end = res.start(1)
            trims = [(int(trim[0]), int(trim[1]) if int(trim[1]) > 0 else 
                       int(trim[0]) - int(trim[1]) - 1) for trim in reversed(trims)]
            break
    else:
        if use_label:
            avsp.MsgBox(_("No Trims found with label '{0}'").format(label), _('Error'))
        elif use_line:
            avsp.MsgBox(_('No Trims found in the specified line: {0}')
                        .format(line_number), _('Error'))
        else:
            avsp.MsgBox(_('No Trims found in the specified Avisynth script'), _('Error'))
        return
    return trims

self = avsp.GetWindow()

# Prompt for fps list and output timecode path
ask = ask_next = avsp.Options.get('ask', False)
if save_avs and not avsp.IsScriptSaved():
    avsp.SaveScript()
avs = avsp.GetScriptFilename()
if not avs:
    if self.version > '2.3.1':
        avs = avsp.GetScriptFilename(propose='general')
    else:
        avs = os.path.join(self.options['recentdir'], 
            self.scriptNotebook.GetPageText(self.scriptNotebook.GetSelection()).lstrip('* '))
otc, ext = os.path.splitext(avs)
if ext not in ('.avs', '.avsi'):
    otc = avs
otc = otc + '.tc.txt'
timecode_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
while True:
    if ask_next:
        options = ask_trim_options()
        if options:
            trims = parse_trims(*options)
            if not trims: continue
            ask_next = False
        else:
            return   
    else:
        trims = parse_trims()
    if not trims:
        return
    
    default = 'ntsc_film'
    for i in range(len(trims) - 1):
        default += ';ntsc_film' if i%2 else ';ntsc_video'
    options = avsp.GetTextEntry(
        title=_('Create/join timecodes from Trims'),
        message=[_('Set a FPS for each Trim. Alias:\n'
                   'itc: input timecode file, ntsc_film: {0}, ntsc_video: {1}')
                 .format(fps_alias['ntsc_film'], fps_alias['ntsc_video']), 
                 _('Set a FPS to apply to the range of the video outside of the '
                   'Trims.\nLeave blank to only include the range within Trims in '
                   'the timecode.'), 
                 _('Output timecode path'), 
                 [_('Ask for Trims line selection options'), _('Ask always')]],
        default=[default, default_fps if use_default_fps else '', 
                 (otc, timecode_filter), [ask_next, ask]], 
        types=['', '', 'file_save', ['check', 'check']], 
        width=400)
    if not options:
        return
    fps_list, default_fps, otc, ask_next, ask = options
    if default_fps: use_default_fps = True
    if ask_next: continue
    if otc: break
    else: avsp.MsgBox(_('An output path is needed'), _('Error'))
avsp.Options['ask'] = ask

# Convert FPS values to float
fps_str_list = options[0].split(';')
if len(fps_str_list) != len(trims):
    avsp.MsgBox(_('Invalid list of FPS'), _('Error'))
    return
fps_str_list.append(options[1])
fps_str_list = [fps_str.strip() for fps_str in fps_str_list]
fps_list = []
itc_list = []
for i, fps_str in enumerate(fps_str_list):  
    for alias in fps_alias:
        if fps_str == alias:
            fps_list.append(fps_alias[alias])
            break   
    else:
        if fps_str == 'itc':
            fps_list.append(fps_str)
            itc_list.append(i)
            continue
        try:
            fps_frac = [float(i) for i in re.split(r'[:/]', fps_str)]
        except ValueError:
            if i != len(fps_str_list) - 1 and fps_str != '':
                avsp.MsgBox(_('Invalid FPS value: {0}').format(fps_str), _('Error'))
                return
            fps_list.append('')
            continue
        if len(fps_frac) == 1:
            fps_list.append(fps_frac[0])
        elif len(fps_frac) == 2:
            fps_list.append(fps_frac[0] / fps_frac[1])
        else:
            avsp.MsgBox(_('Invalid FPS value'), _('Error'))
            return

# VFR input
if itc_list:
    message = []
    default = []
    types = []
    for i in itc_list:
        message.append(_('Timecode path for Trim({0},{1})').format(*trims[i]))
        default.append((splitext(avs)[0] + '.txt', timecode_filter))
        types.append('file_open')
    itc_list = avsp.GetTextEntry(
                            title=_('Introduce the path of the timecode files'), 
                            message=message, default=default, types=types)
    if not itc_list:
        return
    if len(message) == 1:
        itc_list = [itc_list]
    
    # Generate all intervals if the range outside of Trims is also included
    if fps_list[-1]:
        new_trims = []
        new_fps_list = []
        if trims[0][0] > 0:
            new_trims.append((0, trims[0][0] - 1))
            new_fps_list.append(fps_list[-1])
        for i, trim in enumerate(trims):
            new_trims.append(trim)
            new_fps_list.append(fps_list[i])
            try:
                if trims[i+1][0] - trim[1] > 1:
                    new_trims.append((trim[1] + 1, trims[i+1][0] - 1))
                    new_fps_list.append(fps_list[-1])
            except IndexError:
                new_fps_list.append(fps_list[-1])
        trims = new_trims
        fps_list = new_fps_list

    # Create new timecode v2
    new_lines = ['# timecode format v2\n', '0.000\n']
    itc_i = 0
    for i, fps in enumerate(fps_list[0:-1]):  
        if fps == 'itc':
            try:
                with open(itc_list[itc_i]) as itc:
                    itc_i += 1
                    header = itc.readline().strip()
                    if header == '# timecode format v2':
                        itc.readline()
                        lines = itc.readlines()
                        if len(lines) == trims[i][1] - trims[i][0]:
                           lines.append(2 * float(lines[-1]) - float(lines[-2]))
                    elif header == '# timecode format v1':
                        lines = timecode_v1_to_v2(itc.readlines(), 
                                                  end=trims[-1][1])
                    else:
                        avsp.MsgBox(_('Invalid timecode file'), _('Error'))
                        return
            except IOError:
                code = getfilesystemencoding()
                avsp.MsgBox(_("Input timecode file doesn't exist: {0}")
                            .format(itc_list[itc_i].encode(code)), _('Error'))
                return
            new_lines.extend(
                          ['{0:.3f}\n'.format(float(line) + float(new_lines[-1]))
                           for line in lines[:trims[i][1] - trims[i][0] + 1]])
        else:
            new_lines.extend(
                     ['{0:.3f}\n'.format(1000.0 / fps * j + float(new_lines[-1])) 
                      for j in range(1, trims[i][1] - trims[i][0] + 2)])

    with open(options[2], mode='w') as otc:
        otc.writelines(new_lines)

# CFR input
else:
    new_lines = ['# timecode format v1\n', 'assume {0}\n'.format(
                                fps_list[-1] if fps_list[-1] else 24000.0/1001)]
    if fps_list[-1]:  # All video range
        new_lines.extend('{0},{1},{2:.12g}\n'.format(trim[0], trim[1], fps_list[i]) 
                         for i, trim in enumerate(trims))
    else:  # Only Trims
        shift = trims[0][0]
        for i, trim in enumerate(trims):
            new_lines.append('{0},{1},{2:.12g}\n'.format(
                             trim[0] - shift, trim[1] - shift, fps_list[i]))
            try:
                shift += trims[i + 1][0] - trim[1] -1
            except IndexError:
                pass
    with open(options[2], mode='w') as otc:
        otc.writelines(new_lines)
