from char_draw import canvas,display_list
from char_draw.canvas import angle_point
import curses
import curses.ascii
import os
import time
from dashboard_test_util import screen_size,dashboard_test_case

def test_DisplayList(request,capsys):
    with capsys.disabled():
        def main(stdscr):
            screen_size(40,100)
            stdscr.clear()
            python_path = os.path.dirname(os.path.dirname(request.fspath))
            c = canvas.Canvas(stdscr)
            max_x,max_y = c.get_maxxy()
            d = display_list.DisplayList(canvas=c)
            r = 1
            for ix in range(5):
                for iy in range(5):
                    x = ix * 11
                    y = iy * 11
                    d.add_child(display_list.Rect(x,y,x+10,y+10,curses.color_pair(8+r*5),True))
                    r = r + 1
            d.render()
            dashboard_test_case(stdscr,"dl_rect",python_path)
            c.clear()
            r = 1
            for ix in range(5):
                for iy in range(5):
                    x = 65 + (ix * (11*1.5)) + 5
                    y = (iy * 11) + 5
                    d.add_child(display_list.Circle(x,y,5,curses.color_pair(8+r*5),True))
                    r = r + 1
            d.render()
            dashboard_test_case(stdscr,"dl_circle",python_path)
            c.clear()
            a = 0
            ia = [20,15,40,110,45,25,80,25]
            r = 1
            for ac in ia:
                d.add_child(display_list.Arc(100,40,40,a,a+ac,curses.color_pair(8*r*5),True))
                a = a + ac
                r = r +1
            d.render()
            dashboard_test_case(stdscr,"dl_arc",python_path)
            c.clear()
            r = 0
            for ix in range(5):
                for iy in range(5):
                    d.add_child(display_list.Text(ix*10,(iy*10)+(ix*2),"Text %d,%d"%(ix,iy),curses.color_pair(8*r*5)))
                    r = r + 1
            d.render()
            dashboard_test_case(stdscr,"dl_text",python_path)
            c.clear()

            points = []
            for a in range(0,360,72):
                points.append(angle_point(0,0,a,20))
                points.append(angle_point(0,0,a+36,10))
            points.append(points[0])

            r = 50
            d.add_child(display_list.PolyLine([(x+100,y+40) for x,y in points],curses.color_pair(8+r*8)))
            d.render()
            dashboard_test_case(stdscr,"dl_polyline",python_path)
            c.clear()
            r += 25
            d.add_child(display_list.Polygon([(x+102,y+42) for x,y in points],curses.color_pair(8+r*8),True))
            d.render()
            dashboard_test_case(stdscr,"dl_polygon",python_path)
            c.clear()

        curses.wrapper(main)
