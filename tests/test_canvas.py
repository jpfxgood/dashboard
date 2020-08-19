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
            for ix in range(5,max_x):
                c.put_pixel(ix,iy,c.red)
                iy = (iy + 1)%max_y
            dashboard_test_case(stdscr,"put_pixel",python_path)

        curses.wrapper(main)
