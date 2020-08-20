from char_draw import canvas
import curses
import curses.ascii
import os
import time
from dashboard_test_util import screen_size,dashboard_test_case

def test_Canvas(request,capsys):
    with capsys.disabled():
        def main(stdscr):
            screen_size(40,100)
            python_path = os.path.dirname(os.path.dirname(request.fspath))
            c = canvas.Canvas(stdscr)
            max_x,max_y = c.get_maxxy()
            iy = 0
            for ix in range(8,max_x):
                c.put_pixel(ix,iy,c.red)
                iy = (iy + 1)%max_y
            dashboard_test_case(stdscr,"put_pixel",python_path)
            stdscr.clear()
            ix = 0
            iy = 0
            for ic in range(0,min(max_x,max_y)//10):
                c.line(max_x//2,0,ix,iy,c.cyan)
                ix = (ix+15)%max_x
                iy = (iy+10)%max_y
            dashboard_test_case(stdscr,"line",python_path)
            stdscr.clear()
            c.circle(max_x//2,max_y//2,min(max_x,max_y)//3,c.white,False)
            dashboard_test_case(stdscr,"circle_not_filled",python_path)


        curses.wrapper(main)
