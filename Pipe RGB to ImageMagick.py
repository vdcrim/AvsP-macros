# -*- coding: utf-8 -*-

"""
Pipe the script in the current tab to ImageMagick as RGB24 or RGB48

To send RGB48 the script must return a fake YV12 clip containing the RGB 
data (see the Dither package docs for more info).

To send RGB24 the clip must be already RGB24.  BGR24 in fact, as that is 
the order AviSynth/AvxSynth uses.  This macro reorders the data as RGB on 
its own.


Splitting   

Process all the image data in one go can be very memory/filesystem space
expensive.  Instead the frames can be sent in batches.  There's various 
dividing choices:

- Specify a frame step
- Specify a time step
- Specify a number of intervals
- Use the current AvsP bookmarks as splitting points

To create a single file for each batch (e.g. single TIFF output) be sure 
to uncheck the 'Add the padded frame number as suffix' option.  To create 
GIFs better use this other macro: 
https://github.com/vdcrim/AvsP-macros/blob/master/Create GIF with ImageMagick.py


Requirements:

- 'convert' executable from ImageMagick <http://www.imagemagick.org>

By default the executable is expected to be found in 'AvsPmod\tools' or 
one of its subdirectories.  On *nix it can also be in PATH (there's already 
a 'convert' executable on Windows).  A path will be asked for in the first 
run otherwise.

Windows note:

If you only need ImageMagick for this macro then do the following: 
1) download the portable static version of IM
2) extract only convert.exe
3) place it on the 'AvsPmod\tools' directory


Date: 2012-11-04
Latest version:  https://github.com/vdcrim/avsp-macros

Changelog:
- initial release


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

import sys
import os
import os.path
import subprocess
import shlex
import re
import ctypes

import avisynth

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


class Clip(object):
    '''Basic avs script loading class with raw output
    
    Only accepts YV12 and RGB24, and reorders the later (BGR to RGB)
    
    '''
    def __init__(self, text, filename=''):
        self.error = None
        self.incorrect_colorspace = False
        self.env = avisynth.avs_create_script_environment(3)
        curdir = os.getcwdu()
        dirname, basename = os.path.split(filename)
        if os.path.isdir(dirname):
            self.env.SetWorkingDir(dirname)
        self.file = avisynth.AVS_Value(filename)
        self.name = avisynth.AVS_Value(basename)
        self.dir = avisynth.AVS_Value(dirname)
        self.env.SetGlobalVar("$ScriptFile$", self.file)
        self.env.SetGlobalVar("$ScriptName$", self.name)
        self.env.SetGlobalVar("$ScriptDir$", self.dir)
        try:
            clip = self.env.Invoke('Eval', avisynth.AVS_Value(text), 0)
        except avisynth.AvisynthError, err:
            self.error = str(err)
            os.chdir(curdir)
            return
        self.clip = clip.AsClip(self.env)
        self.vi = self.clip.GetVideoInfo()
        if self.vi.IsYV12():
            self.depth = 16
            self.real_width = self.vi.width / 2
            self.real_height = self.vi.height / 2
        elif self.vi.IsRGB24():
            self.depth = 8
            self.real_width = self.vi.width
            self.real_height = self.vi.height
            # BGR -> RGB
            clip = avisynth.AVS_Value(self.clip)
            r = self.env.Invoke("ShowRed", clip, 0)
            b = self.env.Invoke("ShowBlue", clip, 0)
            merge_args = avisynth.AVS_Value([b, clip, r, avisynth.AVS_Value("RGB24")])
            clip = self.env.Invoke("MergeRGB", merge_args, 0)
            self.clip = self.env.Invoke("FlipVertical", clip, 0).AsClip(self.env)
        else:
            self.incorrect_colorspace = True
        os.chdir(curdir)
    
    def raw_frame(self, frame):
        '''Get a buffer of raw video data'''
        frame = self.clip.GetFrame(frame)
        total_bytes = self.vi.width * self.vi.height * self.vi.BitsPerPixel() >> 3
        buf = ctypes.create_string_buffer(total_bytes)
        write_addr = ctypes.addressof(buf)
        P_UBYTE = ctypes.POINTER(ctypes.c_ubyte)
        if self.vi.IsPlanar() and (avsp.GetWindow().version < '2.4.0' or not self.vi.IsY8()):
            for plane in (avisynth.PLANAR_Y, avisynth.PLANAR_U, avisynth.PLANAR_V):
                write_ptr = ctypes.cast(write_addr, P_UBYTE)
                self.env.BitBlt(write_ptr, frame.GetRowSize(plane), frame.GetReadPtr(plane), 
                    frame.GetPitch(plane), frame.GetRowSize(plane), frame.GetHeight(plane))
                write_addr += frame.GetRowSize(plane) * frame.GetHeight(plane)
        else:
            # Note that AviSynth uses BGR
            write_ptr = ctypes.cast(write_addr, P_UBYTE)
            self.env.BitBlt(write_ptr, frame.GetRowSize(), frame.GetReadPtr(), 
                        frame.GetPitch(), frame.GetRowSize(), frame.GetHeight())
        return buf
    
    def __del__(self):
        if hasattr(self, 'clip'):
            self.clip.Release()
        self.env.Release()


self = avsp.GetWindow()

# Load default options
convert_path = avsp.Options.get('convert_path', '')
election = avsp.Options.get('election', _('specifying a frame step'))
frame_step = avsp.Options.get('frame_step', 100)
time_step = avsp.Options.get('time_step', '0:00:05.000')
intervals = avsp.Options.get('intervals', 10)
im_args = avsp.Options.get('im_args', '')
use_dir = avsp.Options.get('use_dir', False)
use_base = avsp.Options.get('use_base', False)
add_frame_number = avsp.Options.get('add_frame_number', True)
show_progress = avsp.Options.get('show_progress', True)

# Check convert path
if not os.path.isfile(convert_path):
    convert_path = os.path.join(self.toolsfolder, 'convert.exe')
    for parent, dirs, files in os.walk(self.toolsfolder):
        for file in files:
            if file == 'convert.exe':
                convert_path = os.path.join(parent, file)
                break
        else: continue
        break
    else:
        if os.name == 'nt':
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
        else:
            try:
                convert_path = subprocess.check_output(
                                ['which', 'convert']).strip().splitlines()[0]
            except:
                if avsp.MsgBox(_("'convert' from ImageMagick not found\n\n"
                                 "Press 'Accept' to specify a path. Alternatively copy\n"
                                 "the executable to the 'tools' subdirectory."), 
                               _('Error'), True):
                    convert_path = avsp.GetFilename(_('Select the convert executable'), 
                                                    _('All files') + ' (*.*)|*.*')
                    if not convert_path:
                        return
                else: return

# Get the default output path
output_path = avs_path = avsp.GetScriptFilename()
if output_path:
    dirname, basename = os.path.split(output_path)
elif self.version > '2.3.1':
    dirname, basename = os.path.split(avsp.GetScriptoutput_path(propose='general'))
else:
    dirname, basename = (self.options['recentdir'], self.scriptNotebook.GetPageText(
                         self.scriptNotebook.GetSelection()).lstrip('* '))
if use_dir:
    dirname = avsp.Options.get('dirname', '')
if use_base:
    basename = avsp.Options.get('basename', '')
basename2, ext = os.path.splitext(basename)
if ext in ('.avs', '.avsi'):
    basename = basename2 + '.png'
elif not ext:
    basename = basename + '.png'
output_path = os.path.join(dirname, basename)

# Ask for options
while True:
    election_list = (_('specifying a frame step'),  _('specifying a time step'),
                     _('specifying a number of intervals'), _('using the current boomarks'), 
                     election)
    options = avsp.GetTextEntry(title=_('Pipe RGB to ImageMagick'), 
        message=[_('Process frames in batches by splitting the script by...'), 
                 [_('Frame step'), _('Time step'), _('Number of intervals')], 
                 _('ImageMagick processing arguments (excluding input)'), 
                 _('Choose an output directory, basename and extension'), 
                 [_('Use always this directory'), _('Use always this basename')], 
                 [_('Add the padded frame number as suffix'), _('Show progress')]], 
        default=[election_list, 
                 [(frame_step, 1, None, 0, max(1, 10 ** (len(str(frame_step)) - 2))), 
                  time_step, (intervals, 1)], im_args, output_path, 
                  [use_dir, use_base], [add_frame_number, show_progress]], 
        types=['list_read_only', ['spin', '', 'spin'], '', 'file_save', 
               ['check', 'check'], ['check', 'check']], 
        width=410)
    if not options:
        return
    (election, frame_step, time_step, intervals, im_args, output_path, use_dir, 
                            use_base, add_frame_number, show_progress) = options          
    if election == _('specifying a time step'):
        time_step_ms = parse_time(time_step)
        if not time_step_ms:
            avsp.MsgBox(_('Malformed time: ') + time_step, _('Error'))
            continue
    if output_path:
        output_path = output_path.lstrip()
        break
    elif not avsp.MsgBox(_('An output path is needed'), _('Error'), True):
        return

# Save default options
avsp.Options['convert_path'] = convert_path
avsp.Options['election'] = election
avsp.Options['frame_step'] = frame_step
avsp.Options['time_step'] = time_step
avsp.Options['intervals'] = intervals
avsp.Options['im_args'] = im_args
avsp.Options['use_dir'] = use_dir
avsp.Options['use_base'] = use_base
if use_dir:
    avsp.Options['dirname'] = os.path.dirname(output_path)
if use_base:
    avsp.Options['basename'] = os.path.basename(output_path)
avsp.Options['add_frame_number'] = add_frame_number
avsp.Options['show_progress'] = show_progress

# Eval script
clip = Clip(avsp.GetText(), avs_path)   
if clip.error is not None:
    avsp.MsgBox('\n\n'.join((_('Error loading the script'), clip.error)), _('Error'))
    return
if clip.incorrect_colorspace:
    avsp.MsgBox(_('Colorspace must be RGB24 or (fake) YV12 (RGB48)'), _('Error'))
    return

# Get the list of frames
if election == _('using the current boomarks'):
    frame_list = avsp.GetBookmarkList()
    if not frame_list:
        avsp.MsgBox(_('There is not bookmarks'), _('Error'))
        return
    frame_list.sort()
    if frame_list[0] != 0:
        frame_list[:0] = [0]
    if frame_list[-1] == clip.vi.num_frames - 1:
        frame_list[-1] = clip.vi.num_frames
    else:
        frame_list.append(clip.vi.num_frames)
else:
    if election == _('specifying a frame step'):
        step = frame_step
    elif election == _('specifying a time step'):
        step = float(clip.vi.fps_numerator) / clip.vi.fps_denominator * time_step_ms / 1000
    elif election == _('specifying a number of intervals'):
        step = clip.vi.num_frames / float(intervals)
    frame_list = float_range_list(0, clip.vi.num_frames, step)


# Pipe the image data to 'convert' as RGB

# - Issue 1: Python 2.x doesn't support unicode args in subprocess.Popen()
#   http://bugs.python.org/issue1759845
#   Encoding to system's locale encoding
# - Issue 2: handle inheritance issues if any of stdin, stdout or stderr 
#   but not all three are specified and the process is started under some 
#   circumstances.
#   http://www.py2exe.org/index.cgi/Py2ExeSubprocessInteractions
#   http://bugs.python.org/issue3905
#   http://bugs.python.org/issue1124861
encoding = sys.getfilesystemencoding()
output_path, ext = os.path.splitext(output_path)
if add_frame_number:
    digits = len(str(frame_list[-1] - 1))
    suffix = '-%0{0}d'.format(digits)
else:
    digits = len(str(len(frame_list) - 1))
if show_progress:
    progress = avsp.ProgressBox(2 * len(frame_list[:-1]) + 1)
for i, frame in enumerate(frame_list[:-1]):
    if show_progress and not progress.Update(2*i, 
                _('Piping batch {0}/{1}').format(i+1, len(frame_list[:-1])))[0]:
        break
    
    # Start the pipe
    if not add_frame_number:
        suffix = '-{0:0{1}}'.format(i+1, digits)
    cmd = ur'"{0}" -depth {1} -size {2}x{3} rgb:- {4} -scene {5} "{6}{7}{8}"'.format(
          convert_path, clip.depth, clip.real_width, clip.real_height, im_args, 
          frame, output_path, suffix, ext).encode(encoding)
    cmd = shlex.split(cmd)
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
    
    # Pipe the data and wait for the process to finish
    try:
        for frame in range(frame, frame_list[i+1]):
            cmd.stdin.write(clip.raw_frame(frame))
        cmd.stdin.close()
        if show_progress and not progress.Update(2*i+1, 
                _('Processing batch {0}/{1}').format(i+1, len(frame_list[:-1])))[0]:
            cmd.terminate()
            break
        cmd.wait()
    except IOError, er:
        avsp.MsgBox(_('Too much data! Try creating smaller batches'), _('Error'))
        break
    except Exception, err:
        try:
            if cmd.poll() is None:
                cmd.terminate()
        except: pass
        raise err
else:
    if show_progress: progress.Update(2*i+2, _('Finished'))
if show_progress: progress.Destroy()
