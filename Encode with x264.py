# -*- coding: utf-8 -*-

"""
Encode the Avisynth script in the current tab with x264.

Requirements:
    avs4x264mod: http://forum.doom9.org/showthread.php?t=162656
    x264 r2117+: http://x264.nl
    
This macro uses avs4x264mod to pipe the video data to x264. By 
default, it expects to find "avs4x264mod.exe" and "x264.exe" 
in the "AvsPmod\tools" directory.

Anamorphic encoding:
If MeGUI DAR info is present in the avs script, a proper SAR value 
is calculated and passed to x264.

Colorprim, transfer, colormatrix:
You can leave the RGB conversion/correction flag field blank.
The following alias are also accepted:
  bt709: HD
  smpte170m: SD NTSC
  bt470bg: SD PAL

Range:
Note that starting with x264 r2117 input range is autodetected by 
default and output range is the same as input.  The fullrange flag 
is automatically added ("fullrange" parameter no longer exists).


Latest version:     https://github.com/vdcrim/avsp-macros
Doom9 Forum thread: http://forum.doom9.org/showthread.php?t=163440

Changelog:
  v1: initial release
  v2: minor changes and some cleanup
  v3: fix "Additional parameters" field. It needed to start with a space


Copyright (C) 2011  Diego Fernández Gosende <dfgosende@gmail.com>

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

# Save changes in script before encoding.
save_avs = True

# Set custom paths, e.g. ur"D:\x264.exe"
avs4x264mod_path = ur""
x264_path = ur""

# Additional parameters to shell command 'start'
# (see http://ss64.com/nt/start.html)
start_params = '/belownormal /min'

# Check consistency between avs output color depth and x264 input-depth 
check_depth = True

# Prompt default values
from collections import OrderedDict
prompt = OrderedDict([
    ['Preset', 'veryslow'], 
    ['Tune', 'film'], 
    ['CRF', '18'], 
    ['QP file', ''], #    '' -> avs_name.qp_suffix, if exists
    ['Timecodes file', ''], #    '' -> avs_name.tc_suffix, if exists
    ['Input color depth', '16'], 
    ['Output colorspace', 'i420'], 
    ['Input range;Output range', 'auto;auto'], 
    ['RGB <--> YCbCr conversion flags (alias: HD, SD NTSC, SD PAL)', 'HD'], 
    ['Additional parameters', ''],
    ['Output', ''] #    '' -> avs_name.avs.ext
    ])

# Use open-GOP
open_gop = True

# Default output container
ext = '.mkv'

# Suffix list for QP file and timecode search
qp_suffix = ['.qpfile', '.qpf', '.qp']
tc_suffix = ['.otc.txt', '.tc.txt', '.timecode.txt', '.timecodes.txt', '.txt']

# Alias list for colorprim, transfer and colormatrix
csp_alias=[('HD', 'bt709'), ('SD NTSC', 'smpte170m'), ('SD PAL', 'bt470bg')]


# ------------------------------------------------------------------------------


from os import getcwdu
from os.path import isfile, splitext, join
from sys import getfilesystemencoding
from subprocess import Popen

# Check paths and get avs path
if avs4x264mod_path:
    if not isfile(avs4x264mod_path):
        print('Custom avs4x264mod path is invalid')
        return
elif isfile(join(getcwdu(), r'tools\avs4x264mod.exe')):
    avs4x264mod_path = join(getcwdu(), r'tools\avs4x264mod.exe')
else:
    print('avs4x264mod not found')
    return
if x264_path:
    if not isfile(x264_path):
        print('Custom x264 path is invalid')
        return
elif isfile(join(getcwdu(), r'tools\x264.exe')):
    x264_path = join(getcwdu(), r'tools\x264.exe')
else:
    print('x264 not found')
    return
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

# Prompt for x264 parameters
avs_no_ext = splitext(avs)[0]
if not prompt['QP file']:
    for path in (avs_no_ext + suffix for suffix in qp_suffix):
        if isfile(path):
            prompt['QP file'] = path
            break
if not prompt['Timecodes file']:
    for path in (avs_no_ext + suffix for suffix in tc_suffix):
        if isfile(path):
            prompt['Timecodes file'] = path
            break
if not prompt['Output']:
    prompt['Output'] = avs + ext
options = avsp.GetTextEntry(title = 'Encode with x264 - x264 parameters',
                            message = prompt.keys(), default = prompt.values())
if not options:
    return
preset = options[0]
tune = options[1]
crf = options[2]
qpfile = ' --qpfile "' + options[3] + '"' if options[3] else ''
tcfile = ' --tcfile-in "' + options[4] + '"' if options[4] else ''
input_depth = options[5]
output_csp = options[6]
range = ''
if options[7]:
    range_pair = options[7].split(';')
    if len(range_pair) == 2:
        if range_pair[0]:
            range += ' --input-range ' + range_pair[0]
        if range_pair[1]:
            range += ' --range ' + range_pair[1]
if options[8]:
    colorprim = ' --colorprim '
    transfer = ' --transfer '
    colormatrix = ' --colormatrix '
    for csp in csp_alias:
        if options[8] == csp[0]:
            colorprim += csp[1]
            transfer += csp[1]
            colormatrix += csp[1]
            break
    else:
        colorprim += options[8]
        transfer += options[8]
        colormatrix += options[8]
else:
    colorprim = ''
    transfer = ''
    colormatrix = ''
add_params = options[9]
output = options[10]
open_gop = ' --open-gop' if open_gop else ''

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

# Set SAR, reading Megui DAR if present. Check colour depth
darx_str = 'global MeGUI_darx ='
dary_str = 'global MeGUI_dary ='
darx, dary = 0, 0
out_16_str = 'Dither_convey_yuv4xxp16_on_yvxx()' # Dither package
out_16 = False
for line in avsp.GetText().splitlines():
    if not darx:
        part = line.partition(darx_str)
        if part[1]:
            darx = float(part[2])
            continue
    if not dary:
        part = line.partition(dary_str)
        if part[1]:
            dary = float(part[2])
            continue
    if line.strip() == out_16_str:
        out_16 = True
if check_depth:
    if input_depth == '8' and out_16:
        print('Incorrect input color depth (8)')
        return
    if input_depth != '8' and not out_16:
        print('Missing "{}" or incorrect input color depth'.format(out_16_str))
        return
if darx and dary:
    if input_depth == '8':
        sar = '{}:{}'.format(*best_rationals(darx * avsp.GetVideoHeight() 
                                    / dary / avsp.GetVideoWidth()))

    else:
        sar = '{}:{}'.format(*best_rationals(2 * darx * avsp.GetVideoHeight() 
                                    / dary / avsp.GetVideoWidth()))
else:
    sar = '1:1'

# Start the encoding process
args = ('start ' + start_params
	+ ' "' + avs4x264mod_path + '"' 
	+ ' "' + avs4x264mod_path + '"' 
	+ ' --x264-binary "' + x264_path + '"' 
    + ' --preset ' + preset 
    + ' --tune ' + tune 
    + ' --crf ' + crf 
    + open_gop 
    + qpfile 
    + tcfile 
    + ' --demuxer raw'
    + ' --input-depth ' + input_depth 
    + ' --output-csp ' + output_csp 
    + ' --sar ' + sar 
    + range 
    + colorprim 
    + transfer 
    + colormatrix 
    + ' ' + add_params 
    + ' --output "' + output + '" "' + avsp.GetScriptFilename() + '"')
Popen(args.encode(code), shell=True)
