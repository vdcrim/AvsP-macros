# -*- coding: utf-8 -*-

"""
Crop borders from the script in the current tab


Latest version: https://github.com/vdcrim/avsp-macros

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

# Set to False to not ask for settings
show_prompt = True

# Values used with show_prompt = False
samples = 10  # number of frames analyzed. Start and end of the video are skipped to avoid issues with credits
tol = 70  # tolerance (0-255)
overcrop = True # round up or down crop values because of chroma subsampling
insert = True  #  insert Crop() at the end of the script
refresh = True  # update and show if hidden the video preview


# ------------------------------------------------------------------------------


# run in thread
from collections import defaultdict
import wx

def autocrop(samples=10, tol=70, overcrop=True, insert=True, refresh=True, 
             show_prompt=False):
    """Crop borders from the script in the current tab"""
    # Get options
    if show_prompt:
        samples = avsp.Options.get('samples', samples)
        tol = avsp.Options.get('tol', tol)
        overcrop = avsp.Options.get('overcrop', overcrop)
        insert = avsp.Options.get('insert', insert)
        refresh = avsp.Options.get('refresh', refresh)
        options = avsp.GetTextEntry(
                message=[[_('Samples'), _('Tolerance'), _('Overcrop')], 
                         [_('Apply to script'), _('Update preview')]], 
                default=[[(samples, 1, 100), (tol, 0, 255), overcrop], 
                         [insert, refresh]], 
                title=_('Auto-crop'), 
                types=[['spin', 'spin', 'check'], ['check', 'check']], 
                width=200)
        if not options:
            return
        samples, tol, overcrop, insert, refresh = options
        avsp.Options['samples'] = samples
        avsp.Options['tol'] = tol
        avsp.Options['overcrop'] = overcrop
        avsp.Options['insert'] = insert
        avsp.Options['refresh'] = refresh

    # Get crop values for a number of frames
    frames = avsp.GetVideoFramecount()
    avs = avsp.GetWindow().currentScript
    left_values, top_values, right_values, bottom_values = [], [], [], []
    def float_range(start=0, end=10, step=1):
        while start < end:
            yield int(round(start))
            start += step
    frames = float_range(frames/10, 9*frames/10 - 1, 8.0*frames/(10*samples))
    progress = avsp.ProgressBox(samples, _('Analyzing frames...'), _('Auto-crop'))
    crop_values = []
    for i, frame in enumerate(frames):
        if not progress.Update(i)[0]:
            progress.Destroy()
            return
        crop_values.append(autocrop_frame(frame, tol))
    progress.Destroy()

    # Get final crop values
    final_crop_values = []
    yv12 = avs.AVI.vi.IsYV12()
    yuy2 = avs.AVI.vi.IsYUY2()
    for seq in zip(*crop_values):
        value = get_crop_value(seq)
        if value % 2 and (yv12 or yuy2 and not len(final_crop_values) % 2):
            if overcrop:
                value += 1
            else:
                value -= 1
        final_crop_values.append(value)
    if insert:
        txt = '' if avsp.GetText().endswith('\n') else '\n'
        avsp.InsertText(txt + 'Crop({0}, {1}, -{2}, -{3})'.format(*final_crop_values))
        if refresh:
            avsp.ShowVideoFrame(forceRefresh=True)
    return final_crop_values

def autocrop_frame(frame, tol=70):
    """Return crop values for a specific frame"""
    width, height = avsp.GetVideoWidth(), avsp.GetVideoHeight()
    avs = avsp.GetWindow().currentScript
    bmp = wx.EmptyBitmap(width, height)
    mdc = wx.MemoryDC()
    mdc.SelectObject(bmp)
    dc = mdc if avsp.GetWindow().version > '2.3.1' else mdc.GetHDC()
    avs.AVI.DrawFrame(frame, dc)
    img = bmp.ConvertToImage()
    top_left = img.GetRed(0, 0), img.GetGreen(0, 0), img.GetBlue(0, 0)
    bottom_right = (img.GetRed(width-1, height-1), img.GetGreen(width-1, height-1), 
                    img.GetBlue(width-1, height-1))
    top = bottom = left = right = 0
    w, h = width - 1, height - 1
    
    # top & bottom
    top_done = bottom_done = False
    for i in range(height):
        for j in range(width):
            if (not top_done and (
                    abs(img.GetRed(j, i) - top_left[0]) > tol or 
                    abs(img.GetGreen(j, i) - top_left[1]) > tol or 
                    abs(img.GetBlue(j, i) - top_left[2]) > tol)):
                top = i
                top_done = True
            if (not bottom_done and (
                    abs(img.GetRed(j, h - i) - bottom_right[0]) > tol or 
                    abs(img.GetGreen(j, h - i) - bottom_right[1]) > tol or 
                    abs(img.GetBlue(j, h - i) - bottom_right[2]) > tol)):
                bottom = i
                bottom_done = True
            if top_done and bottom_done: break
        else: continue
        break
    
    # left & right
    left_done = right_done = False
    for j in range(width):
        for i in range(height):
            if (not left_done and (
                    abs(img.GetRed(j, i) - top_left[0]) > tol or 
                    abs(img.GetGreen(j, i) - top_left[1]) > tol or 
                    abs(img.GetBlue(j, i) - top_left[2]) > tol)):
                left = j
                left_done = True
            if (not right_done and (
                    abs(img.GetRed(w - j, i) - bottom_right[0]) > tol or 
                    abs(img.GetGreen(w - j, i) - bottom_right[1]) > tol or 
                    abs(img.GetBlue(w - j, i) - bottom_right[2]) > tol)):
                right = j
                right_done = True
            if left_done and right_done: break
        else: continue
        break
    
    return left, top, right, bottom

def get_crop_value(seq):
    """Get the most repeated value on a sequence if it repeats more than 50%, 
    the minimum value otherwise"""
    d = defaultdict(int)
    for i in seq:
        d[i] += 1
    max = sorted(d.keys(), key=lambda x:-d[x])[0]
    if d[max] > len(seq) / 2:
        return max
    else:
        ret_val = max
        for value in seq:
            if value < ret_val:
                ret_val = value
        return ret_val

return autocrop(samples, tol, overcrop, insert, refresh, show_prompt)
