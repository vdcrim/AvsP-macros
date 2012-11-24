# -*- coding: utf-8 -*-

"""
Pipe the script in the current tab to ImageMagick as RGB24 or RGB48

To send RGB48 the script must return a fake YV12 clip containing the RGB 
data (see the Dither package docs for more info).

To send RGB24 the clip must be already RGB24.  BGR24 in fact, as that is 
the order AviSynth/AvxSynth uses.  This macro reorders the data as RGB on 
its own.


Video range

By default all the frames in the clip are sent.  Bookmarks can be used 
to delimit specific frame ranges if the corresponding option is checked.  
The first and last frame of each range must be added as bookmarks.

A warning is shown if the number of bookmarks is uneven.  If the user 
accepts then the last range goes till the end of the clip.  If the 'only 
bookmarks' option is checked but there's none all the video range is 
piped.

If the 'save every range to a subdirectory' is checked then the bookmark 
title of the starting frame of each range is used as the directory name, 
a generic name if it's not set.  The titles can be introduced in the Video 
menu -> Titled bookmarks -> Set title (manual).


Splitting   

Process all the image data in one go can be very memory/filesystem space
expensive.  Instead the frames can be sent in batches.  There's various 
dividing choices:

- Specify a frame step
- Specify a time step
- Specify a number of intervals

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


Date: 2012-11-14
Latest version:  https://github.com/vdcrim/avsp-macros

Changelog:
- remember the last used output format
- strip tags and sliders from the script before evaluating it
- add 'include only the range between bookmarks' option
- add 'when using bookmarks save every range to a subdirectory' option
- bookmarks can not longer be used as splitting points
- improve error reporting


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
    if ret[-1] != stop: ret.append(stop)
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
only_bookmarks = avsp.Options.get('only_bookmarks', False)
im_args = avsp.Options.get('im_args', '')
use_dir = avsp.Options.get('use_dir', False)
use_base = avsp.Options.get('use_base', False)
last_ext = avsp.Options.get('last_ext', '.png')
add_frame_number = avsp.Options.get('add_frame_number', True)
use_subdirs = avsp.Options.get('use_subdirs', False)
show_progress = avsp.Options.get('show_progress', True)

# Check convert path
if not os.path.isfile(convert_path):
    if not check_executable_path('convert', False, True,
                                 _("'convert' from ImageMagick not found")):
        return
    convert_path = avsp.Options['convert_path']

# Get the default output path
output_path = avs_path = avsp.GetScriptFilename()
if output_path:
    dirname, basename = os.path.split(output_path)
elif self.version > '2.3.1':
    dirname, basename = os.path.split(avsp.GetScriptFilename(propose='image'))
else:
    dirname, basename = (self.options['imagesavedir'], self.scriptNotebook.GetPageText(
                         self.scriptNotebook.GetSelection()).lstrip('* '))
if use_dir:
    dirname = avsp.Options.get('dirname', '')
if use_base:
    basename = avsp.Options.get('basename', '')
basename2, ext = os.path.splitext(basename)
if ext in ('.avs', '.avsi'):
    basename = basename2 + last_ext
else:
    basename = basename + last_ext
output_path = os.path.join(dirname, basename)

# Ask for options
while True:
    election_list = (_('specifying a frame step'),  _('specifying a time step'),
                     _('specifying a number of intervals'), election)
    options = avsp.GetTextEntry(title=_('Pipe RGB to ImageMagick'), 
        message=[_('Piping options'), 
                 _('Process frames in batches by splitting the script by...'), 
                 [_('Frame step'), _('Time step'), _('Number of intervals')], 
                 _('Include only the range between bookmarks, if any'), 
                 '', _('Output options'), 
                 _('ImageMagick processing arguments (excluding input)'), 
                 _('Choose an output directory, basename and extension'), 
                 [_('Use always this directory'), _('Use always this basename')], 
                 _('Add the padded frame number as suffix'), 
                 _('When using bookmarks, save every range to a subdirectory'), 
                 _('Show progress')], 
        default=['', election_list, 
                 [(frame_step, 1, None, 0, max(1, 10 ** (len(str(frame_step)) - 2))), 
                  time_step, (intervals, 1)], only_bookmarks, 0, '', im_args, output_path, 
                  [use_dir, use_base], add_frame_number, use_subdirs, show_progress], 
        types=['sep', 'list_read_only', ['spin', '', 'spin'], 'check', 'sep', 
               'sep', '', 'file_save', ['check', 'check'], 'check', 'check', 'check'], 
        width=300)
    if not options:
        return
    (election, frame_step, time_step, intervals, only_bookmarks, im_args, output_path, 
            use_dir, use_base, add_frame_number, use_subdirs, show_progress) = options
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
output_path, ext = os.path.splitext(output_path)
dirname, basename = os.path.split(output_path)
avsp.Options['election'] = election
avsp.Options['frame_step'] = frame_step
avsp.Options['time_step'] = time_step
avsp.Options['intervals'] = intervals
avsp.Options['only_bookmarks'] = only_bookmarks
avsp.Options['im_args'] = im_args
avsp.Options['use_dir'] = use_dir
avsp.Options['use_base'] = use_base
if use_dir:
    avsp.Options['dirname'] = dirname
if use_base:
    avsp.Options['basename'] = basename
avsp.Options['last_ext'] = ext
avsp.Options['add_frame_number'] = add_frame_number
avsp.Options['use_subdirs'] = use_subdirs
avsp.Options['show_progress'] = show_progress

# Eval script
if self.version > '2.3.1':
    text = avsp.GetText(clean=True)
else:
    text = self.getCleanText(avsp.GetText())
clip = Clip(text, avs_path)   
if clip.error is not None:
    avsp.MsgBox('\n\n'.join((_('Error loading the script'), clip.error)), _('Error'))
    return
if clip.incorrect_colorspace:
    avsp.MsgBox(_('Colorspace must be RGB24 or (fake) YV12 (RGB48)'), _('Error'))
    return

# Get the list of frame ranges
if only_bookmarks:
    bm_list = avsp.GetBookmarkList()
    if not bm_list:
        use_subdirs = False
        frame_list = ((0, clip.vi.num_frames),)
    else:
        bm_list = sorted([bm for bm in bm_list if bm < clip.vi.num_frames])
        if len(bm_list) % 2:
            if not avsp.MsgBox(_('Odd number of bookmarks'),  _('Warning'), cancel=True):
                return
            else:
                bm_list.append(clip.vi.num_frames - 1)
        frame_list = [(bm, bm_list[i+1] + 1) for (i, bm) in enumerate(bm_list) if not i % 2]
else:
    use_subdirs = False
    frame_list = ((0, clip.vi.num_frames),)

# Divide each range
if election == _('specifying a frame step'):
    step = frame_step
elif election == _('specifying a time step'):
    step = float(clip.vi.fps_numerator) / clip.vi.fps_denominator * time_step_ms / 1000
elif election == _('specifying a number of intervals'):
    total_frames = 0
    for frame_range in frame_list:
        total_frames += frame_range[1] - frame_range[0] + 1
    step = total_frames / float(intervals)
frame_list = [float_range_list(frame_range[0], frame_range[1], step) for frame_range in frame_list]

# Pipe the image data to 'convert' as RGB
#
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
total_batches = 0
if show_progress:
    for frame_range in frame_list:
        total_batches += len(frame_range) - 1
    progress = avsp.ProgressBox(2 * total_batches)
if add_frame_number:
    digits = len(str(frame_list[-1][-1] - 1))
    suffix = '-%0{0}d'.format(digits)
else:
    if not total_batches:
        for frame_range in frame_list:
            total_batches += len(frame_range) - 1
    digits = len(str(total_batches))
if use_subdirs:
    digits_frame_list = len(str(len(frame_list)))
start_batch_number = 0
frame_count = 0
for range_index, frame_list in enumerate(frame_list):
    if use_subdirs:
        title = self.bookmarkDict.get(frame_list[0])
        if not title:
            title =  _('scene_{0:0{1}}').format(range_index+1, digits_frame_list)
        dirname2 = os.path.join(dirname, title)
        if not os.path.isdir(dirname2): os.mkdir(dirname2)
        output_path = os.path.join(dirname2, basename)
    for i, frame in enumerate(frame_list[:-1]):
        i2 = i + start_batch_number
        if show_progress and not avsp.SafeCall(progress.Update, 2*i2, 
                    _('Piping batch {0}/{1}').format(i2+1, total_batches))[0]:
            break
        if add_frame_number:
            scene = frame
        else:
            suffix = '-{0:0{1}}'.format(i2+1, digits)
            if use_subdirs:
                scene = frame - frame_list[0]
            else:
                scene = frame_count
        
        # Start the pipe
        cmd = ur'"{0}" -depth {1} -size {2}x{3} rgb:- {4} -scene {5} "{6}{7}{8}"'.format(
              convert_path, clip.depth, clip.real_width, clip.real_height, im_args, 
              scene, output_path, suffix, ext).encode(encoding)
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
            for every_frame in range(frame, frame_list[i+1]):
                cmd.stdin.write(clip.raw_frame(every_frame))
            frame_count += frame_list[i+1] - frame
            cmd.stdin.close()
            if show_progress and not avsp.SafeCall(progress.Update, 2*i2+1, 
                    _('Processing batch {0}/{1}').format(i2+1, total_batches))[0]:
                cmd.terminate()
                break
            cmd.wait()
        except:
            if show_progress: avsp.SafeCall(progress.Destroy)
            try:
                if cmd.poll() is None:
                    cmd.terminate()
            except: pass
            avsp.MsgBox(cmd.stdout.read(), _('Error'))
            return
    else:
        start_batch_number += i + 1
        continue
    break
else:
    if show_progress: avsp.SafeCall(progress.Update, 2*i2+2, _('Finished'))
if show_progress: avsp.SafeCall(progress.Destroy)
