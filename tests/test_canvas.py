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
            stdscr.clear()
            python_path = os.path.dirname(os.path.dirname(request.fspath))
            c = canvas.Canvas(stdscr)
            max_x,max_y = c.get_maxxy()
            iy = 0
            for ix in range(8,max_x):
                c.put_pixel(ix,iy,c.red)
                iy = (iy + 1)%max_y
            dashboard_test_case(stdscr,"put_pixel",python_path)
            c.clear()
            ix = 0
            iy = 0
            for ic in range(0,min(max_x,max_y)//10):
                c.line(max_x//2,0,ix,iy,c.cyan)
                ix = (ix+15)%max_x
                iy = (iy+10)%max_y
            dashboard_test_case(stdscr,"line",python_path)
            c.clear()
            c.circle(max_x//2,max_y//2,min(max_x,max_y)//3,c.white,False)
            dashboard_test_case(stdscr,"circle_not_filled",python_path)
            c.clear()
            c.circle(max_x//2,max_y//2,min(max_x,max_y)//3,curses.color_pair(20),True)
            dashboard_test_case(stdscr,"circle_filled",python_path)
            c.clear()
            a = 0
            a1 = 23
            for ac in range(20):
                c.arc(max_x//2,max_y//2,min(max_x,max_y)//3,a,a1,c.white,False)
                a = a1
                a1 = a1 + ac*5
                if a1 > 360:
                    break
            dashboard_test_case(stdscr,"arc_not_filled",python_path)
            c.clear()
            c.arc(max_x//2,max_y//2,min(max_x,max_y)//3,120,220,curses.color_pair(20),True)
            dashboard_test_case(stdscr,"arc_filled",python_path)
            c.clear()
            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*5
                y = iy + ic*5
                c.rect(x,y,x+5,y+5,curses.color_pair(9+(ic*10)),False)
            dashboard_test_case(stdscr,"rect_not_filled",python_path)
            c.clear()
            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*5
                y = iy + ic*5
                c.rect(x,y,x+5,y+5,curses.color_pair(9+(ic*10)),True)
            dashboard_test_case(stdscr,"rect_filled",python_path)
            c.clear()
            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*5
                y = iy + ic*5
                c.textat(x,y,curses.color_pair(9+(ic*10)),"Test message %d"%ic)
            dashboard_test_case(stdscr,"textat",python_path)
            c.clear()
            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*16
                y = iy + ic*10
                c.polyline([(x,y),(x+16,y+16),(x+8,y),(x,y+16),(x+16,y+8),(x,y+8),(x+8,y+16)],curses.color_pair(9+(ic*10)))
            dashboard_test_case(stdscr,"polyline",python_path)

            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*16
                y = iy + ic*10
                c.polygon([(x,y),(x+16,y+8),(x+16,y+16),(x+8,y+16),(x,y+8)],curses.color_pair(9+(ic*10)),False)
            dashboard_test_case(stdscr,"polygon_not_filled",python_path)

            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*16
                y = iy + ic*10
                c.polygon([(x,y),(x+16,y+8),(x+16,y+16),(x+8,y+16),(x,y+8)],curses.color_pair(9+(ic*10)),True)
            dashboard_test_case(stdscr,"polygon_filled",python_path)

            ix = 0
            iy = 0
            for ic in range(0,5):
                x = ix + ic*16
                y = iy + ic*10
                c.polygon([(x,y),(x+16,y+8),(x+8,y+8),(x+8,y+16),(x,y+8)],curses.color_pair(9+(ic*10)),True)
            dashboard_test_case(stdscr,"polygon_concave_filled",python_path)

        curses.wrapper(main)
