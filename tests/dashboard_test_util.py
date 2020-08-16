import curses
import pprint
import gc
import re
import subprocess

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

