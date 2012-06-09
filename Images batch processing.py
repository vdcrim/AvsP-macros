# -*- coding: utf-8 -*-

"""
Apply the Avisynth script in the current tab to all the selected input 
files in a specified directory.  Save as an image the current frame of 
the result afterwards.


Latest version: https://github.com/vdcrim/avsp-macros
Created originally for http://forum.doom9.org/showthread.php?p=1552739#post1552739

Changelog:
  v1: initial release
  v2: fix previous bad cleanup
      the script is now taken from the current tab
      not restrict the input files to only JPEG
      allow specifying a different output directory
      move all the settings to the prompt


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
from os.path import splitext, basename, join
from glob import glob

# Get defaults
in_dir = avsp.Options.get('in_dir', '')
input_list = avsp.Options.get('input_list', 'bmp;png;tif')
out_dir = avsp.Options.get('out_dir', '')
out_format = avsp.Options.get('out_format', _('Portable Network Graphics') + ' (*.png)')
suffix = avsp.Options.get('suffix', '_new')
quality = avsp.Options.get('quality', 90)
format_dict = dict([(name[0], ext) for ext, name in avsp.GetWindow().imageFormats.iteritems()])

# Prompt for options
while True:
    options = avsp.GetTextEntry(title=_('Images batch processing'), 
            message=[_('The script in the current tab will be applied to all '
                       'the input files. \nPlease replace first the input path '
                       'in your source filter with "input_path", e.g. ImageSource'
                       '("input_path")'), 
                     [_('Input files directory'), 
                      _('Semicolon-separated list of input file extensions')],
                     [_('Output directory (blank = input directory)'), 
                      _('Output format')], 
                     [_('Output files suffix'), 
                      _('Quality (JPEG only)'), 
                      _('Save current values as default')]],
            default=['', [in_dir, input_list], 
                     [out_dir, sorted(format_dict.keys()) + [out_format]], 
                     [suffix, (quality, 0, 100)]],
            types=['sep', ['dir', ''], ['dir', 'list_read_only'], 
                   ['', 'spin', 'check']],
            width=500)
    if not options:
        return
    in_dir, input_list, out_dir, out_format, suffix, quality, save_options = options
    if not in_dir:
        avsp.MsgBox(_('Select the input files directory'), _('Error'))
    else: break

# Save options
if save_options:
    avsp.Options['in_dir'] = in_dir
    avsp.Options['input_list'] = input_list
    avsp.Options['out_dir'] = out_dir
    avsp.Options['out_format'] = out_format
    avsp.Options['suffix'] = suffix
    avsp.Options['quality'] = quality

# Get input files
paths = []
for ext in input_list.split(';'):
    paths.extend(glob(join(in_dir, '*.' + ext)))
if not paths:
    avsp.MsgBox(_('No files with the given extensions in the selected input '
                  'directory'), _('Error'))
    return

# Check if the script contains the path wildcard
script = avsp.GetText()
if not '"input_path"' in script:
    avsp.MsgBox(_('Not "input_path" in the script'), _('Error'))
    return

# Process and save the input files
if not out_dir:
    out_dir = in_dir
ext = format_dict[out_format]
total = len(paths)
progress = avsp.ProgressBox(max=1000, title=_('Batch processing progress'))
for i, path in enumerate(paths):
    if not progress.Update(i*1000.0/total, basename(path))[0]:
        break
    avsp.SetText(script.replace('"input_path"', '"{}"'.format(path), 1))
    try:
        avsp.SaveImage(join(out_dir, splitext(basename(path))[0] + suffix + ext), 
                       quality=quality)
    except:
        avsp.MsgBox(_('Processing failed at ') + basename(path), _('Error'))
        break

# Clean up
progress.Destroy()
avsp.HideVideoWindow()
avsp.SetText(script)