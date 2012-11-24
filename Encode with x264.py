# -*- coding: utf-8 -*-

"""
Encode the Avisynth script in the current tab with x264.

Requirements:
- avs4x264mod: http://forum.doom9.org/showthread.php?t=162656
- x264 r2117+: http://x264.nl
    
This macro uses avs4x264mod to pipe the video data to x264. By default, 
it expects to find "avs4x264mod.exe" and "x264.exe" in the "AvsPmod\tools" 
directory or in PATH.

Features:
- CRF and 2-pass ABR encoding mode, progressive and interlaced.
- Use x264 64-bit with Avisynth 32-bit. 
- Check consistency between avs output color depth and x264 input-depth 
  parameter.
- Read x264 parameters from commentaries on the script.
- Calculate an adequate SAR from MeGUI DAR info or a specific comment in 
  the script, if present.
- Add zones parameter based on commentaries on lines with Trims.
- Search for an existing QP and timecode file in the script directory with 
  the same name as the avs.
- Alias feature for setting the YCbCr to RGB flags.
- Set "start" shell command options (process priority, start minimized).
- Not display any window while encoding and notify at the end.
- Save the x264 logs and a copy of the Avisynth script.
- Close the current tab and/or preview tabs on its right.

Anamorphic encoding:
In addition to select or introduce its value in the prompt, the video DAR 
can be specified by adding a commentary in the avs like any of the following:
  # DAR 16:9
  # DAR 1.85
MeGUI DAR info is also read if present. A proper SAR value is calculated 
from the DAR and passed to x264.

Zones:
x264 zones info can be automatically added as a parameter by including a 
commentary at the end of the affected lines with Trims, e.g:
  Trim(0,1000)++Trim(5000,7000) # zones crf=20,deblock=0:0
is incorporated to the x264 call as:
  --zones 0,1000,crf=20,deblock=0:0/5000,7000,crf=20,deblock=0:0
These Trims can be commented out.

Parameters from script:
Any x264 parameter can also be incorporated by adding a comment to the avs 
like these:
  # x264 parameters --crf 17 --aq-strength 1.2
  # additional parameters --crf 17 --aq-strength 1.2
The parameters read override the prompt defaults, or are added to "additional 
parameters" if they don't have a specific field.

See the "PREFERENCES" section below to check and customize the other features.


Date: 2012-09-11
Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163440

Changelog:
- minor changes and some cleanup
- fix "Additional parameters" field. It needed to start with a space
- improved interface with recent updates in AvsPmod
- default values can be set now from the prompt
- add 2-pass ABR mode
- add scan type option
- add DAR to the prompt. It can also be read from the avs now, like 
    "# DAR 16:9" or "# DAR 1.85"
- add Blu-ray compatible and open-GOP switches to the prompt
- x264 parameters can now be read from the avs, like 
    "# x264 parameters --crf 17 --aq-strength 1.2"
- zones can now be read from lines with Trims in the avs, like 
    "Trim(0,100) # zones crf=20"
- improve RGB / YCbCr flags alias feature
- add option to archive the encoding log and a copy of the avs
- add option to run the encoding without a window and notify at the end
- add option to close the current tab and/or preview tabs on its right
- fix Python 2.6 compatibility


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

# Save changes in script before encoding (True or False)
save_avs = True

# Additional parameters to shell command 'start'
# (see http://technet.microsoft.com/en-us/library/bb491005.aspx)
start_params = '/belownormal /min'

# Check consistency between avs output color depth and x264 input-depth 
# Asumes the use of the Dither package to export >8-bit video
check_depth = True

# Suffix list for QP file and timecode search
qp_suffix = ['.qpfile', '.qpf', '.qp']
tc_suffix = ['.otc.txt', '.tc.txt', '.timecode.txt', '.timecodes.txt', '.txt']

# Default output container
ext = '.mkv'

# Use the following alias for the RGB / YCbCr flags, in the form (colorprim, 
# transfer, colormatrix), or just use a single text string to asign the same 
# value to all three flags. To not specify some of the three values use ''
use_alias = True
csp_alias = {
    'HD': ('bt709', 'bt709', 'bt709'), 
    'SD NTSC': 'smpte170m', 
    'SD PAL': 'bt470bg'
    }

# Run the encoding with the cmd window hidden, and notify at the end
hide_cmd = False

# Keep the cmd window open when finished, if shown
keep_cmd_open = False

# Close the current tab
close_tab = False
# Close the contiguous tabs on the right without a filename
close_temp_tabs = False

# Save the log of the encoding process. Needs a Windows implementation of   
# the 'tee' command on PATH, like http://www.commandline.co.uk/mtee
# and of 'sed', like http://sed.sourceforge.net/grabbag/ssed/
# (rename them to 'tee' and 'sed')
save_log = False
x264_log_dir = ur""  #  ur""  ->  "AvsPmod\tools\x264 logs" directory

# Save a copy of the Avisynth script
save_avs_copy = False
avs_log_dir = ur""  #  ur""  ->  "AvsPmod\tools\x264 logs" directory


# ------------------------------------------------------------------------------


# run in thread
import os
import os.path
import sys
from shutil import copy2
from subprocess import Popen
import time
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

# fractions module is not bundled with AvsPmod
# best_rationals function adapted from 
# http://www.daniweb.com/software-development/python/code/223956
def best_rationals(afloat):
    """generate (num, den) where num/den is a best rational approximation 
    of the float afloat"""
    if int(afloat)-afloat == 0:
        return [int(afloat),1]
    afloat, lastnum, num = ((-afloat, -1, int(-afloat)) if afloat < 0 
                            else (afloat, 1, int(afloat)))
    lastden, den = 0, 1
    rest, quot = afloat, int(afloat)
    while True:
        rest = 1.0/(rest - quot)
        quot = int(rest)
        lastnum, num, lastden, den = (num, quot * num + lastnum, den, 
                                        quot * den + lastden)
        if abs(afloat - float(num)/den) <= 0.001:
            return num, den

# Check paths and get avs path
avs4x264mod_path = avsp.Options.get('avs4x264mod_path', '')
if not os.path.isfile(avs4x264mod_path):
    if not check_executable_path('avs4x264mod'):
        return
    avs4x264mod_path = avsp.Options['avs4x264mod_path']
x264_path = avsp.Options.get('x264_path', '')
if not os.path.isfile(x264_path):
    if not check_executable_path('x264'):
        return
    x264_path = avsp.Options['x264_path']
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
code = sys.getfilesystemencoding()
avs = avs.encode(code)

# Set the prompt default values
mode = avsp.Options.get('Mode', 'CRF') 
crf = avsp.Options.get('CRF / Bitrate', '20')
preset = avsp.Options.get('Preset', 'veryslow')
tune = avsp.Options.get('Tune', 'film')
dar = avsp.Options.get('DAR', '')
scan_type = avsp.Options.get('Scan type', 'Progressive')
input_depth = avsp.Options.get('Input color depth', '8')
input_range = avsp.Options.get('Input range', 'tv')
output_range = avsp.Options.get('Output range', 'auto')
output_csp = avsp.Options.get('Output colorspace', 'i420')
rgb_flags = avsp.Options.get('RGB / YCbCr flags', 'HD')
blu_ray = avsp.Options.get('Blu-ray compatible', False)
open_gop = avsp.Options.get('Open-GOP', False)
add_params = avsp.Options.get('Additional parameters', '')
tc_file = ur""  #    ur"" -> avs_name.tc_suffix, if exists
qp_file = ur""  #    ur"" -> avs_name.qp_suffix, if exists
output = ur""  #    ur"" -> avs_name.avs.ext

# Read DAR, add zones, check colour depth
re_dar_1 = re.compile(r'#\s*DAR\s*(\d+)\s*:\s*(\d+)', re.I)
re_dar_2 = re.compile(r'#\s*DAR\s*(\d+\.?\d*)', re.I)
megui_darx = 'global MeGUI_darx ='
megui_dary = 'global MeGUI_dary ='
darx, dary = 0, 0
re_zones_line = re.compile(r'\bTrim\s*\(\s*\d+\s*,\s*\d+\s*\)'
                            '.*#\s*zones\s*(.+)', re.I)
re_zones_trim = re.compile(r'\bTrim\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', re.I)
zones = ''
re_add_params = re.compile(
    r'#\s*(?:x264|additional|add)[\s_-]*(?:parameters|params):?\s*-+(.+?)$', re.I)
re_split_params = re.compile(r'\s+-+', re.I)
new_csp_alias = ['', '', '']
out_16_str = 'Dither_convey_yuv4xxp16_on_yvxx'  # Dither package
re_out_16 = re.compile(r'[^#]*' + out_16_str + '\(.*\)')
out_16 = False
for line in avsp.GetText().splitlines():
    if not darx or not dary:
        if re_dar_1.search(line):
            darx, dary = re_dar_1.search(line).groups()
        elif re_dar_2.search(line):
            darx, dary = re_dar_2.search(line).group(1), '1'
        else:
            if not darx:
                part = line.partition(megui_darx)
                if part[1]:
                    darx = part[2].strip()
                    continue
            if not dary:
                part = line.partition(megui_dary)
                if part[1]:
                    dary = part[2].strip()
                    continue
    
    re_match = re_zones_line.search(line)
    if re_match:
        zones_params = re_match.group(1).replace(' ', '')
        for trim in re_zones_trim.findall(line):
            zones += '{0},{1},{2}/'.format(trim[0], trim[1], zones_params)
    
    re_match = re_add_params.search(line)
    if re_match:
        params = re_split_params.split(re_match.group(1).strip())
        params = [param.split(' ',1) if len(param.split()) > 1 
                                     else [param] for param in params]
        for param in params:
            param[0] = param[0].lower()
            if param[0] == 'crf':
                mode = 'CRF'
                crf = param[1]
            elif param[0] in ('b', 'bitrate'):
                mode = '2-pass ABR'
                crf = param[1]
            elif param[0] == 'preset':
                preset = param[1].capitalize()
            elif param[0] == 'tune':
                tune = param[1].capitalize()
            elif param[0] == 'sar':
                dar = _('SAR read: ') + param[1]
            elif param[0] == 'tff':
                scan_type = 'Interlaced (top)'
            elif param[0] == 'bff':
                scan_type = 'Interlaced (bottom)'
            elif param[0] == 'fake-interlaced':
                scan_type = 'Fake interlaced'
            elif param[0] == 'pulldown':
                if param[1] == '32':
                    scan_type = 'Soft telecine (NTSC)'
                elif param[1] == 'euro':
                    scan_type = 'Soft telecine (PAL)'
                else:
                    scan_type = 'Pulldown ' + param[1]
            elif param[0] == 'input-depth':
                input_depth = param[1]
            elif param[0] == 'input-range':
                input_range = param[1].capitalize()
            elif param[0] == 'range':
                output_range = param[1].capitalize()
            elif param[0] == 'output-csp':
                output_colorspace = param[1].capitalize()
            elif param[0] == 'colorprim':
                new_csp_alias[0] = param[1].lower()
            elif param[0] == 'transfer':
                new_csp_alias[1] = param[1].lower()
            elif param[0] == 'colormatrix':
                new_csp_alias[2] = param[1].lower()
            elif param[0] == 'bluray-compat':
                blu_ray = True
            elif param[0] == 'open-gop':
                open_gop = True
            elif param[0] == 'tcfile-in':
                tc_file = param[1].strip('"')
            elif param[0] == 'qpfile':
                qp_file = param[1].strip('"')
            elif param[0] in ('o', 'output'):
                output = param[1].strip('"')
            else:
                add_params += (
                            (' -' if len(param[0]) == 1 else ' --') + param[0] +  
                            (' ' + param[1] if len(param) > 1 else ''))
    if not out_16 and re_out_16.match(line):
        out_16 = True

# Prompt for x264 parameters
avs_no_ext = os.path.splitext(avs)[0]
csp_list = ['bt709', 'smpte170m', 'bt470bg']
dar_list = ['4:3', '16:9', '1.85', '2.35', '2.39', '2.40']
scan_type_list = ['Progressive', 'Interlaced (top)', 'Interlaced (bottom)', 
               'Fake interlaced', 'Soft telecine (NTSC)', 'Soft telecine (PAL)']
if scan_type not in scan_type_list:
    scan_type_list.append(scan_type)
if any(new_csp_alias):
    csp_alias[_('Read from avs')] = new_csp_alias
    rgb_flags = _('Read from avs')
if not tc_file:
    for path in (avs_no_ext + suffix for suffix in tc_suffix):
        if os.path.isfile(path):
            tc_file = path
            break
tc_filter = (_('Text files') + ' (*.txt)|*.txt|' + _('All files') + '|*.*')
if not qp_file:
    for path in (avs_no_ext + suffix for suffix in qp_suffix):
        if os.path.isfile(path):
            qp_file = path
            break
qp_filter = (_('QP files') + ' (*.qpfile;*.qpf;*.qp)|*.qpfile;*.qpf;*.qp|' + 
             _('All files') + '|*.*')
if zones:
    add_params += ' --zones ' + zones[:-1]
if not output:
    output = avs + ext
output_filter = (_('Matroska files') + ' (*.mkv)|*.mkv|' + 
                 _('MP4 files') + ' (*.mp4)|*.mp4|' + 
                 _('Flash Video files') + ' (*.flv)|*.flv|' + 
                 _('Raw bytestream files') + ' (*.264)|*.264')
message = [[_('Mode'), _('CRF / Bitrate'), _('Preset'), _('Tune')], '', 
           [_('DAR'), _('Scan type'), _('Input color depth')], 
           [_('Input range'), _('Output range'), _('Output colorspace')], 
           [_('RGB / YCbCr flags'), _('Blu-Ray compatible'), _('Open-GOP')], 
           _('Timecodes file'), _('QP file'), 
           _('Additional parameters'), _('Save current settings as default'), '', 
           _('Output')
          ]
default = [[('CRF', '2-pass ABR', mode.capitalize()), 
            (crf, None, None, 2, 0.1 if mode.lower() == 'crf' else 100), 
            ('Ultrafast', 'Superfast', 'Veryfast', 'Faster', 'Fast', 'Medium', 
             'Slow', 'Slower', 'Veryslow', 'Placebo', preset.capitalize()), 
            ('', 'Film', 'Animation', 'Grain', 'Stillimage', tune.capitalize())
           ], '', 
           [dar_list + [':'.join([darx, dary]) if darx and dary else 
                        (dar if dar else _('Non-anamorphic'))], 
            scan_type_list + [scan_type], 
            ('8', '10', '16', input_depth)
           ], 
           [ 
            ('Auto', 'TV', 'PC', input_range), 
            ('Auto', 'TV', 'PC', output_range), 
            ('i420', 'i422', 'i444', 'RGB', output_csp)
           ], 
           [
            [''] + (csp_alias.keys() if use_alias else csp_list) + [rgb_flags], 
            blu_ray, open_gop
           ], 
           (tc_file, tc_filter), (qp_file, qp_filter), 
           add_params, False, '', (output,output_filter)
          ]        
types = [['list_read_only', 'spin', 'list_read_only', 'list_writable'], 'sep', 
         ['list_writable', 'list_read_only', 'list_read_only'],
         ['list_read_only', 'list_read_only', 'list_read_only'], 
         ['list_writable', 'check', 'check'], 
         'file_open', 'file_open', '', 'check', 'sep', 'file_save'
        ]
options = avsp.GetTextEntry(title=_('Encode with x264 - x264 parameters'),
                       message=message, default=default, types=types, width=320)
if not options:
    return

# Set the x264 parameters
mode = options[0].lower()
crf = (' --crf ' if mode == 'crf' else ' --bitrate ') + str(int(options[1])) 
preset = options[2].lower()
tune = ' --tune ' + options[3].lower() if options[3] else ''
input_depth = options[6]
dar = options[4]
if dar.startswith(_('SAR read: ')):
    sar = ' --sar ' + dar.split(' ')[-1]
elif dar in ('', _('Non-anamorphic')):
    sar = ''
else:
    try:
        darx, dary = float(dar), 1
    except ValueError:
        darx, dary = map(float, re.search( r'(\S+)\s*[:/]\s*(\S+)', dar).groups())
    if input_depth != '8': darx *= 2
    sar = ' --sar {0}:{1}'.format(*best_rationals(darx * avsp.GetVideoHeight() / 
                                                dary / avsp.GetVideoWidth()))
if options[5] == 'Progressive':
    scan_type = ''
elif options[5] == 'Interlaced (top)':
    scan_type = ' --tff'
elif options[5] == 'Interlaced (bottom)':
    scan_type = ' --bff'
elif options[5] == 'Fake interlaced':
    scan_type = ' --fake-interlaced'
elif options[5] == 'Soft telecine (NTSC)':
    scan_type = ' --pulldown 32'
elif options[5] == 'Soft telecine (PAL)':
    scan_type = ' --pulldown euro'
else:
    scan_type = ' --' + options[5].lower()
input_range = ' --input-range ' + options[7].lower()
output_range = ' --range ' + options[8].lower()
output_csp = options[9].lower()
colorprim = transfer = colormatrix = ''
rgb_flags = options[10]
if rgb_flags :
    for alias in csp_alias.keys():
        if rgb_flags.lower() == alias.lower():
            if isinstance(csp_alias[alias], basestring):
                colorprim = transfer = colormatrix = csp_alias[alias]
            else:
                colorprim, transfer, colormatrix = csp_alias[alias]
            break
    else:
        colorprim = transfer = colormatrix = rgb_flags
colorprim = ' --colorprim ' + colorprim.lower() if colorprim else ''
transfer = ' --transfer ' + transfer.lower() if transfer else ''
colormatrix = ' --colormatrix ' + colormatrix.lower() if colormatrix else ''
blu_ray = ' --bluray-compat' if options[11] else ''
open_gop = ' --open-gop' if options[12] else ''
tcfile = ' --tcfile-in "' + options[13] + '"' if options[13] else ''
qpfile = ' --qpfile "' + options[14] + '"' if options[14] else ''
add_params = options[15]
output = options[-1]

# Save options
if options[16]:
    avsp.Options['Mode'] = options[0]
    avsp.Options['CRF / Bitrate'] = options[1]
    avsp.Options['Preset'] = options[2]
    avsp.Options['Tune'] = options[3]
    avsp.Options['DAR'] = dar
    avsp.Options['Scan type'] = options[5]
    avsp.Options['Input color depth'] = options[6]
    avsp.Options['Input range'] = options[7]
    avsp.Options['Output range'] = options[8]
    avsp.Options['Output colorspace'] = options[9]
    if rgb_flags != _('Read from avs'):
        avsp.Options['RGB / YCbCr flags'] = rgb_flags
    avsp.Options['Blu-ray compatible'] = options[11]
    avsp.Options['Open-GOP'] = options[12]
    avsp.Options['Additional parameters'] = options[15]

# Check input depth parameter
if check_depth:
    if input_depth == '8' and out_16:
        avsp.MsgBox(_('Incorrect input color depth (8)'), _('Error'))
        return
    if input_depth != '8' and not out_16:
        avsp.MsgBox(_('Missing "{0}" call or incorrect input color depth')
                    .format(out_16_str), _('Error'))
        return

# Close tabs 
if close_temp_tabs:
    avsp.HideVideoWindow()
    next_tab = avsp.GetCurrentTabIndex() + 1
    while True:
        if avsp.GetScriptFilename(next_tab) == '':
            avsp.CloseTab(next_tab)
        else:
            break
if close_tab:
    avsp.HideVideoWindow()
    avsp.CloseTab()   

# Archive x264 log and Avisynth script
date_time = time.strftime('[%Y-%m-%d %H.%M.%S] ', time.localtime())
if save_log:
    x264_log_dir = x264_log_dir if x264_log_dir else os.path.join(avsp.GetWindow().toolsfolder, 'x264 logs')
    if not os.path.isdir(x264_log_dir):
        os.makedirs(x264_log_dir)
    log = (' 2>&1 | sed -u -e "/%.\+frames.\+fps.\+eta/d" | tee "' + 
        os.path.join(x264_log_dir, date_time + os.path.basename(output)).encode(code))
    log_crf = log + '.log"'
    log_pass1 = log + '.pass1.log"'
    log_pass2 = log + '.pass2.log"'
else:
    log_crf = log_pass1 = log_pass2 = ''
if save_avs_copy:
    avs_log_dir = avs_log_dir if avs_log_dir else os.path.join(avsp.GetWindow().toolsfolder, 'x264 logs')
    if not os.path.isdir(avs_log_dir):
        os.makedirs(avs_log_dir)
    copy2(avs, os.path.join(avs_log_dir.encode(code), date_time + os.path.basename(avs)))

# Start the encoding process
start = 'start ' + start_params + (' /b' if hide_cmd else '')
cmd = ' cmd ' + ('/k "' if keep_cmd_open and not hide_cmd else '/c "')
end_notice =  ' && start echo {0}"'.format(_('Encoding of "{0}" finished').format(
                        os.path.basename(output))).encode(code) if hide_cmd else '"'
args = (' "' + avs4x264mod_path + '"' + 
        ' --x264-binary "' + x264_path + '"' + 
        ' --preset ' + preset + 
        tune + 
        crf + 
        ' --demuxer raw' + 
        ' --input-depth ' + input_depth + 
        ' --output-csp ' + output_csp + 
        sar + 
        scan_type + 
        input_range + 
        output_range + 
        colorprim + 
        transfer + 
        colormatrix + 
        blu_ray +  
        open_gop +
        tcfile + 
        qpfile + 
        ' ' + add_params + 
        ' "' + avs.decode(code) + '"').encode(code)
if mode == 'crf':
    if Popen(start + cmd + args + ' --output "' + output.encode(code) + '"' +
          log_crf + end_notice, shell=True).wait():
        avsp.MsgBox(_('Shell error'), _('Error'))   
else:
    stats_file = '"{0}"'.format(avs_no_ext + '.pass1.stats')
    if Popen(start + cmd + args + ' --output NUL' + ' --stats ' + stats_file + 
          ' --pass 1' + log_pass1 + ' &&' + args + 
          ' --output "' + output.encode(code) + '"' + ' --stats ' + stats_file +
          ' --pass 2' + log_pass2 + ' && del ' + stats_file + ' ' + 
          stats_file[:-1] + '.mbtree"' + end_notice, shell=True).wait():
        avsp.MsgBox(_('Shell error'), _('Error'))
