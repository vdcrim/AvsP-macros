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

There are two ways of specifying the line of the avs used:
· Parse the avs from top to bottom or vice versa, and use the first 
  line with Trims found.
· Use a line with a specific comment at the end, e.g:
  Trim(0,99)++Trim(200,499)  # ivtc


Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163653

Changelog:
  v1: initial release
  v2: support for negative second member of the Trim pair
  v3: updated prompt dialog. Needs AvsPmod 2.3.0+
      accept spaces between Trim and its parameters

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

# Avisynth script parsing order
parse_avs_top2bottom = True

# Only match the Trims line with 'label' as commentary
# e.g: Trim(0,99)++Trim(200,499)  # ivtc
use_label = False
prompt_for_label = True  # Only for use_label = True
label = 'ivtc'

# Default FPS for the video range outside of the Trims
default_fps = '24000/1001'
use_default_fps = False

# List of frame rate alias
fps_alias = {'ntsc_film': 24/1.001, 'ntsc_video': 30/1.001}


# ------------------------------------------------------------------------------


# run in thread
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

if not avsp.GetScriptFilename():
    if not avsp.SaveScript():
        return
if save_avs and not avsp.IsScriptSaved():
    avsp.SaveScript()
avs = avsp.GetScriptFilename()
if not avs:
    return

# Parse Trims
if use_label and prompt_for_label:
    label = avsp.GetTextEntry(title=_('Specify the label'), 
                        message=_('Introduce the label used in the Trims line'), 
                        default=label, width=250)  
    if not label:
        return
re_line = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\).*{0}'
                     .format('#.*' + label if use_label else ''), re.I)
re_trim = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\)', re.I)
for line in (avsp.GetText().splitlines() if parse_avs_top2bottom else 
                                        reversed(avsp.GetText().splitlines())):
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
        avsp.MsgBox(_('No Trims found with label "{0}"').format(label), _('Error'))
    else:
        avsp.MsgBox(_('No Trims found in the specified Avisynth script'), _('Error'))
    return

# Prompt for frame rate values
default = 'ntsc_film'
for i in range(len(trims) - 1):
    default += ';ntsc_film' if i%2 else ';ntsc_video'
otc = splitext(avs)[0] + '.tc.txt'
timecode_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
options = avsp.GetTextEntry(
    title=_('Create a timecode file from the {0} line with uncommented Trims')
          .format(_('first') if parse_avs_top2bottom else _('last')),
    message=[_('Set a FPS for each Trim. Alias:\n'
               'itc: input timecode file, ntsc_film: {0}, ntsc_video: {1}')
             .format(fps_alias['ntsc_film'], fps_alias['ntsc_video']), 
             _('Set a FPS to apply to the range of the video outside of the '
               'Trims.\nLeave blank to only include the range within Trims in '
               'the timecode.'), 
             _('Output timecode path')],
    default=[default, default_fps if use_default_fps else '', 
             (otc, timecode_filter)], 
    types=['', '', 'file_save'], 
    width=300)
if not options:
    return

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
