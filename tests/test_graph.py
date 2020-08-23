from char_draw import canvas,display_list,graph
from data_sources.data_table import DataTable,Column,Cell,string_type,float_type,int_type,date_type,blank_type,format_string,format_date,format_float,format_int
import curses
import curses.ascii
import os
import time
from datetime import datetime,timedelta
from dashboard_test_util import screen_size,dashboard_test_case

def test_Graph(request,capsys):
    with capsys.disabled():
        def main(stdscr):
            screen_size(40,100)
            stdscr.clear()
            python_path = os.path.dirname(os.path.dirname(request.fspath))

            c_names = ["X-Series","Pie Labels","Metric 1","Metric 2","Metric 3","Metric 4","Metric 5","Metric 6"]
            d = DataTable()
            for c in c_names:
                d.add_column(Column(name=c))

            for idx in range(0,10):
                d.put(idx,"X-Series",Cell(int_type,idx*10,format_int))
                d.put(idx,"Pie Labels",Cell(string_type,"Group %d"%idx,format_string))
                d.put(idx,"Metric 1",Cell(float_type,50.0+(idx*20),format_float))
                d.put(idx,"Metric 2",Cell(float_type,75.0+(idx*30),format_float))
                d.put(idx,"Metric 3",Cell(float_type,100.0+(idx*40),format_float))
                d.put(idx,"Metric 4",Cell(float_type,123.0+(idx*23),format_float))
                d.put(idx,"Metric 5",Cell(float_type,143+(idx*33),format_float))
                d.put(idx,"Metric 6",Cell(float_type,171+(idx*51),format_float))

            c = canvas.Canvas(stdscr)
            max_x,max_y = c.get_maxxy()

            g = graph.BarGraph(d,"X-Series",["Metric 1","Metric 3","Metric 5"],"Metric Units",None,c,0,"Basic Bar Graph")
            g.render()
            dashboard_test_case(stdscr,"gr_basic_bargraph",python_path)
            c.clear()
            g = graph.LineGraph(d,"X-Series",["Metric 2","Metric 4","Metric 6"],"Metric Units",None,c,False,"Basic Line Graph")
            g.render()
            dashboard_test_case(stdscr,"gr_basic_linegraph",python_path)
            c.clear()
            g = graph.PieGraph(d,"Pie Labels",["Metric 3"],None,c,"Basic Pie Graph")
            g.render()
            dashboard_test_case(stdscr,"gr_basic_piegraph",python_path)
            c.clear()

        curses.wrapper(main)
