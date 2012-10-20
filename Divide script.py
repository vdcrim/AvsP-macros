# -*- coding: utf-8 -*-

"""
Split an AviSynth script into multiple trimmed avs

There's various dividing choices:
- Use the current AvsP bookmarks to delimit the Trims.  The first and 
  last frame are automatically added to the bookmarks if not already 
  present.
- Specify a frame step
- Specify a time step
- Specify a number of intervals

If 'split at the current cursor position' is set, the script is only 
evaluated until the line the cursor is on, and the Trims are inserted 
in the next line.


Latest version:  https://github.com/vdcrim/avsp-macros
Created for http://forum.doom9.org/showthread.php?p=1568663#post1568663

Changelog:
  v1: initial release
  v2: add splitting options (bookmarks are not longer necessary)
      add 'split at current position' option
      move all settings to the prompt


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

import os
import os.path
import re

import pyavs

def parse_time(time):
    ''''Parse time (string) to ms
    
    >>> parse_time('01:23:45.678')
    5025678
    >>> parse_time('01:23:45')
    '''
    splits = re.split(r'[:.]', time)
    time_list = []
    try:
        for split in splits:
            time_list.append(int(split))
    except ValueError:
        return
    if len(time_list) != 4: return
    h, m, s, ms = time_list
    ms = ms + 1000 * (s + 60 * (m + 60 * h))
    return ms

def float_range_list(start, stop, step):
    '''float range (list) with stop included'''
    ret = []
    while start < stop:
        ret.append(int(round(start)))
        start += step
    ret.append(stop)
    return ret

self = avsp.GetWindow()

# Load default options
election = avsp.Options.get('election', _('using the current boomarks'))
frame_step = avsp.Options.get('frame_step', 10000)
time_step = avsp.Options.get('time_step', '0:01:00.000')
intervals = avsp.Options.get('intervals', 10)
use_current_position = avsp.Options.get('use_current_position', False)
use_dir = avsp.Options.get('use_dir', False)
use_base = avsp.Options.get('use_base', False)

# Get the default filename
filename = avsp.GetScriptFilename()
if filename:
    dirname, basename = os.path.split(filename)
elif self.version > '2.3.1':
    dirname, basename = os.path.split(avsp.GetScriptFilename(propose='general'))
else:
    dirname, basename = (self.options['recentdir'], self.scriptNotebook.GetPageText(
                         self.scriptNotebook.GetSelection()).lstrip('* '))
if use_dir:
    dirname = avsp.Options.get('dirname', '')
if use_base:
    basename = avsp.Options.get('basename', '')
filename = os.path.join(dirname, basename)

# Ask for options
while True:
    election_list = (_('using the current boomarks'), _('specifying a frame step'), 
                     _('specifying a time step'), _('specifying a number of intervals'), 
                     election)
    options = avsp.GetTextEntry(title=_('Divide script'), 
        message=[_('Split script by...'), [_('Frame step'), _('Time step'), _('Number of intervals')], 
                 _('Split at the current cursor position'), _('Choose a directory and basename'),
                 [_('Use always this directory'), _('Use always this basename')]], 
        default=[election_list, [(frame_step, 1, None, 0, 1000), time_step, (intervals, 1)], 
                 use_current_position, filename, [use_dir, use_base]], 
        types=['list_read_only', ['spin', '', 'spin'], 'check', 'file_save', ['check', 'check']], 
        width=300)
    if not options:
        return
    election, frame_step, time_step, intervals, use_current_position, filename, use_dir, use_base = options          
    time_step_ms = parse_time(time_step)
    if not time_step_ms:
        avsp.MsgBox(_('Malformed time: '+ time_step), _('Error'))
        continue
    if filename:
        filename = filename.lstrip()
        break
    elif not avsp.MsgBox(_('An output path is needed'), _('Error'), True):
        return

# Save default options
avsp.Options['election'] = election
avsp.Options['frame_step'] = frame_step
avsp.Options['time_step'] = time_step
avsp.Options['intervals'] = intervals
avsp.Options['use_current_position'] = use_current_position
avsp.Options['use_dir'] = use_dir
avsp.Options['use_base'] = use_base
if use_dir:
    avsp.Options['dirname'] = os.path.dirname(filename)
if use_base:
    avsp.Options['basename'] = os.path.basename(filename)

# Eval script
text = avsp.GetText().encode('utf-8') # StyledTextCtrl uses utf-8 internally
if use_current_position:
    script = self.currentScript
    index = script.GetLineEndPosition(script.GetCurrentLine())
else:
    index = len(text)
clip = pyavs.AvsClip(text[:index].decode('utf-8')) # AviSynth expects mbcs
if not clip.initialized or clip.IsErrorClip():
    avsp.MsgBox(_('Error loading the script'), _('Error'))
    return
frame_count = clip.Framecount
fps = clip.Framerate
del clip

# Get the list of frames
if election == _('using the current boomarks'):
    frame_list = avsp.GetBookmarkList()
    if not frame_list:
        avsp.MsgBox(_('There is not bookmarks'), _('Error'))
        return
    frame_list.sort()
    if frame_list[0] != 0:
        frame_list[:0] = [0]
    if frame_list[-1] == frame_count - 1:
        frame_list[-1] = frame_count
    else:
        frame_list.append(frame_count)
elif election == _('specifying a frame step'):
    frame_list = float_range_list(0, frame_count, frame_step)
elif election == _('specifying a time step'):
    frame_list = float_range_list(0, frame_count, fps *  time_step_ms / 1000)
elif election == _('specifying a number of intervals'):
    frame_list = float_range_list(0, frame_count, frame_count / float(intervals))

# Save scripts
global avs_list
avs_list = []
filename2, ext = os.path.splitext(filename)
if ext in ('.avs', '.avsi'):
    filename = filename2
digits = len(str(len(frame_list) - 1))
for i, frame in enumerate(frame_list[:-1]):
    avs_path = u'{0}_{1:0{2}}.avs'.format(filename, i+1, digits)
    avs_list.append(avs_path)
    with open(avs_path, 'w') as f:
        f.write(text[:index] + '\nTrim({0},{1})'.format(frame, frame_list[i+1] - 1) + 
                text[index:])
return avs_list
