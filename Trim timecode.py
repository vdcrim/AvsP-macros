# -*- coding: utf-8 -*-

"""
Cut a timecode file according to Trims

This macro parses the Avisynth script in the current tab for a line with 
uncommented Trims, and cuts an input timecode file accordingly so the 
timestamps match the trimmed video.

There are three ways of specifying the line of the avs used:
- Parse the avs from top to bottom (default) or vice versa, and use the 
  first line with Trims found.
- Use a line with a specific comment at the end, e.g:
  Trim(0,99)++Trim(200,499)  # tc
  It can be combined with a parsing order.
- Directly specifying the Trims line number, starting with 1.


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

# PREFERENCES

# Suffix list for automatic search of a timecode file for the prompt
tc_suffix = ['.tc.txt', '.timecode.txt', '.timecodes.txt', 'timecode', 
             'timecodes', '.txt']


#-------------------------------------------------------------------------------


from os.path import isfile, splitext  
import re


def timecode_v1_to_v2(lines, offset=0, start=0, end=None, default=24/1.001):
    """Convert a timecode v1 file to v2
    
    lines: list of lines of the timecode v1 file (excluding header)
    offset: starting time (ms)
    start:  first frame
    end:    last frame
    default:  FPS used if 'assume' line isn't present
    
    Returns the list of timecode v2 lines (str)
    
    """
    # Generate all intervals
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
    try:
        for i, inter in enumerate(inters):
            all_inters.append(inter)
            if inters[i+1][0] - inter[1] > 1:
                all_inters.append([inter[1] + 1, inters[i+1][0] - 1, default])
    except IndexError:
        if end > inters[-1][1]:
            all_inters.append([inters[-1][1] + 1, end, default])

    # v1 -> v2
    v2 = [] if offset else ['0.000\n']
    for inter in all_inters:
        ms = 1000.0 / inter[2]
        for i in range(1, inter[1] - inter[0] + 2):
            v2.append('{0:.3f}\n'.format(ms * i + offset))
        offset = float(v2[-1])
    return v2


# Get options
avs = avsp.GetScriptFilename()
if avs:
    avs_no_ext = splitext(avs)[0]
    for tc_path in (avs_no_ext + suffix for suffix in tc_suffix):
        if isfile(tc_path):
            tc_in = tc_path
            tc_out = avs_no_ext + '.otc.txt'
            break
    else:
        tc_in = tc_out = ''
else:
    tc_in = tc_out = ''
while True: 
    reversed_ = avsp.Options.get('reversed_', False)
    use_label = avsp.Options.get('use_label', False)
    label = avsp.Options.get('label', 'tc')
    use_line = avsp.Options.get('use_line', False)
    line_number = avsp.Options.get('line_number', 1)
    lines = avsp.GetText().splitlines()
    options = avsp.GetTextEntry(title=_('Trim timecode'), 
            message=[_('Input timecode'), _('Output timecode'), 
                     _('Parse script from bottom to top instead of top to bottom '
                       'for a line with Trims'),
                     [_('Use the Trims line with #label'), _('Label')],
                     [_('Specify directly a line'), _('Line number')]], 
            default=[tc_in, tc_out, reversed_, 
                     [use_label, label],
                     [use_line, (line_number, 1, len(lines))]], 
            types=['file_open', 'file_save', 'check', 'check', ['check', 'spin']])
    if not options: return
    tc_in, tc_out, reversed_, use_label, label, use_line, line_number = options
    avsp.Options['reversed_'] = reversed_
    avsp.Options['use_label'] = use_label
    avsp.Options['label'] = label
    avsp.Options['use_line'] = use_line
    avsp.Options['line_number'] = line_number
    if not tc_in or not tc_out:
        avsp.MsgBox(_('Input and output timecode paths are needed'), _('Error'))
    else:
        break

# Read Trims from script
if use_line:
    use_label = False
    lines = lines[line_number - 1:line_number]
re_line = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\).*{0}'
                     .format('#\s*' + label if use_label else ''), re.I)
re_trim = re.compile(r'^[^#]*\bTrim\s*\(\s*(\d+)\s*,\s*(-?\d+)\s*\)', re.I)
for line in reversed(lines) if reversed_ else lines:
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
        break
else:
    if use_label:
        avsp.MsgBox(_("No Trims found with label '{0}'").format(label), _('Error'))
        return
    elif use_line:
        avsp.MsgBox(_('No Trims found in the specified line: {0}')
                    .format(line_number), _('Error'))
        return
    else:
        avsp.MsgBox(_('No Trims found in the specified Avisynth script'), _('Error'))
        return
trims = [(int(trim[0]), int(trim[1]) if int(trim[1]) > 0 else int(trim[0]) - 
          int(trim[1]) - 1) for trim in reversed(trims)]

# Join contiguous Trims
new_trims = []
prev = -1
try:
    for i, trim in enumerate(trims):
        if prev == -1:
            prev = trim[0]
        if trims[i+1][0] - trim[1] != 1:
            new_trims.append((prev, trim[1]))
            prev = -1
except IndexError:
    new_trims.append((prev, trims[-1][1]))
trims = new_trims

# Read timecode file. Convert v1 -> v2
with open(tc_in) as itc:
    header = itc.readline().strip()
    if header == '# timecode format v2':
        lines = itc.readlines()
    elif header == '# timecode format v1':
        lines = timecode_v1_to_v2(itc.readlines(), 
                                  end=trims[-1][1])
    else:
        avsp.MsgBox(_('Invalid timecode file'), _('Error'))
        return
    
# Offset timestamps and save new timecode
gap = 0
prev_end = 0
new_lines = ['# timecode format v2\n', '0.000\n']
for trim in trims:
    trim_start_time = float(lines[trim[0]])
    try:
        trim_end_time = float(lines[trim[1] + 1])
    except IndexError:  # tc_v2 didn't include the last frame duration
        trim_end_time = 2 * float(lines[-1]) - float(lines[-2])
        lines.append(trim_end_time)
    gap = trim_start_time - prev_end
    prev_end = trim_end_time - gap
    new_lines.extend('{0:.3f}\n'.format(float(line) - gap) 
                         for line in lines[trim[0] + 1:trim[1] + 2])
with open(tc_out, mode='w') as otc_file: otc_file.writelines(new_lines)

