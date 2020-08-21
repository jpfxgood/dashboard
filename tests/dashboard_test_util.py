import curses
import pprint
import gc
import re
import os
import sys
import subprocess
from io import StringIO,BytesIO

def screen_size( rows, columns ):
    cmd = "resize -s %d %d >/dev/null 2>/dev/null"%(rows,columns)
    subprocess.Popen(cmd,shell=True)
    curses.resizeterm( rows, columns )

def read_str( win, y, x, width ):
    out_str = ''
    for ix in range(x,x+width):
        rc = win.inch(y,ix)
        out_str += chr(rc & curses.A_CHARTEXT)
    return out_str

def match_chr( win, y, x, width, match_chr ):
    for ix in range(x,x+width):
        if match_chr != (win.inch(y,ix) & (curses.A_ALTCHARSET | curses.A_CHARTEXT)):
            return False
    return True

def match_attr( win, y, x, height, width, attr ):
    for iy in range(y,y+height):
        for ix in range(x,x+width):
            rc = win.inch(iy,ix)
            cc = chr(rc & curses.A_CHARTEXT)
            r_attr = (rc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            if not (attr == r_attr) and not cc.isspace():
                return(False)
    return(True)

def match_attr_str( win, y, x, width, attr ):
    return match_attr( win, y, x, 1, width, attr)

def save_snapshot( win, to_file ):
    max_y,max_x = win.getmaxyx()
    to_file.write((max_y).to_bytes(2,byteorder='big'))
    to_file.write((max_x).to_bytes(2,byteorder='big'))
    for iy in range(max_y):
        for ix in range(max_x):
            rc = win.inch(iy,ix)
            to_file.write((rc).to_bytes(2,byteorder='big'))

def load_snapshot( from_file ):
    max_y = int.from_bytes(from_file.read(2),byteorder='big')
    max_x = int.from_bytes(from_file.read(2),byteorder='big')

    snapshot = [[ 0 for f in range(max_x)] for g in range(max_y)]

    for iy in range(max_y):
        for ix in range(max_x):
            snapshot[iy][ix] = int.from_bytes(from_file.read(2),byteorder='big')

    return (max_y,max_x,snapshot)

def compare_snapshot( win, snapshot ):
    max_y,max_x,screen = snapshot
    difference = [[0 for f in range(max_x)] for g in range(max_y)]

    has_differences = False
    for iy in range(max_y):
        for ix in range(max_x):
            rc = win.inch(iy,ix)
            r_cc = chr(rc & curses.A_CHARTEXT)
            r_attr = (rc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            sc = screen[iy][ix]
            s_cc = chr(sc & curses.A_CHARTEXT)
            s_attr = (sc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            if r_cc != s_cc:
                difference[iy][ix] = difference[iy][ix] | 1
                has_differences = True
            if r_attr != s_attr:
                difference[iy][ix] = difference[iy][ix] | 2
                has_differences = True

    return (max_y,max_x,difference,has_differences)

def view_differences( win, difference,y_offset = 0,x_offset = 0 ):
    d_max_y,d_max_x,d_screen,has_differences = difference

    for iy in range(d_max_y):
        for ix in range(d_max_x):
            s_attr = curses.A_NORMAL
            if d_screen[iy][ix] & 1:
                s_attr = s_attr | curses.A_REVERSE
            if d_screen[iy][ix] & 2:
                s_attr = s_attr | curses.A_STANDOUT
            try:
                if s_attr != curses.A_NORMAL:
                    win.chgat(iy+y_offset,ix+x_offset,1,s_attr)
            except:
                pass
    win.refresh()

def format_differences( max_y,max_x,difference,has_difference ):
    s = StringIO()
    for iy in range(max_y):
        for ix in range(max_x):
            ch = '.'
            if difference[iy][ix] & 1:
                ch = '#'
            if difference[iy][ix] & 2:
                if ch == '#':
                    ch = '@'
                else:
                    ch = '$'
            s.write(ch)
        s.write('\n')
    return s.getvalue()

def prompt( win, message ):
    l = len(message)
    try:
        pwin = curses.newwin(1,l+1,0,0)
        pwin.addstr(0,0,message)
        while True:
            pwin.move(0,0)
            pwin.refresh()
            ch = pwin.getch()
            if ch == ord('Y') or ch == ord('y'):
                return True
            if ch == ord('N') or ch == ord('n'):
                return False
    finally:
        del pwin
        win.touchwin()
        win.refresh()

def dashboard_test_case( win, name, path ):
    create = ( os.environ.get("TEST_CREATE_SNAPSHOT","False") == "True" )
    snap_shot_file = os.path.join(os.path.join(path,"tests/snapshots"),"%s.dmp"%(name))
    win.refresh()
    if os.path.exists(snap_shot_file):
        snapshot = load_snapshot( open(snap_shot_file,"rb") )
        max_y,max_x,difference,has_differences = compare_snapshot( win, snapshot )
        if has_differences:
            if create:
                backup_win = BytesIO()
                win.putwin(backup_win)
                backup_win.seek(0,0)
                overlay = curses.getwin(backup_win)
                view_differences(overlay,(max_y,max_x,difference,has_differences))
                if prompt(overlay,"Accept these differences?"):
                    del overlay
                    win.touchwin()
                    win.refresh()
                    save_snapshot(win,open(snap_shot_file,"wb"))
                    win.clear()
                    return
            assert False, "Screen differences found:\n%s"%format_differences(max_y,max_x,difference,has_differences)
    else:
        if create:
            if prompt(win,"Is this screen correct?"):
                save_snapshot(win,open(snap_shot_file,"wb"))
                win.touchwin()
                win.refresh()
                win.clear()
                return
        assert False, "No snapshot found for case %s"%name
    win.clear()

