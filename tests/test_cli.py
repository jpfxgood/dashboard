from char_draw import canvas,display_list,graph
from data_sources.data_table import DataTable,Column,Cell,string_type,float_type,int_type,date_type,blank_type,format_string,format_date,format_float,format_int
from dashboard import dashboard
import curses
import curses.ascii
import os
import time
from datetime import datetime,timedelta
from dashboard_test_util import screen_size,dashboard_test_case,dt_testdir
from io import StringIO
from dashboard_cli.config import load_config

def test_cli(capsys,dt_testdir):
    with capsys.disabled():
        def main(stdscr):
            screen_size(40,100)
            stdscr.clear()
            stdscr.refresh()

            config_path = os.path.join(dt_testdir["data_path"],"test_config")
            config_template = open(config_path,"r").read()
            config_stream = StringIO(config_template%dt_testdir)

            cf = None
            try:
                time.sleep(1)
                cf = load_config(stdscr,config_stream)
                ret = cf["dashboard"].main([curses.KEY_F5])
                dashboard_test_case(stdscr,"dbc_page_1",dt_testdir["snapshot_path"],[(0,0,99,0),(0,7,99,37)])
                ret = cf["dashboard"].main([curses.KEY_NPAGE])
                dashboard_test_case(stdscr,"dbc_page_2",dt_testdir["snapshot_path"],[(0,0,99,0),(0,7,99,37)])
                ret = cf["dashboard"].main([curses.KEY_NPAGE])
                dashboard_test_case(stdscr,"dbc_page_3",dt_testdir["snapshot_path"],[(0,0,99,0),(0,7,99,37)])
                ret = cf["dashboard"].main([curses.KEY_NPAGE])
                dashboard_test_case(stdscr,"dbc_page_4",dt_testdir["snapshot_path"],[(0,0,99,0),(0,7,99,37)])
                ret = cf["dashboard"].main([curses.KEY_NPAGE])
                dashboard_test_case(stdscr,"dbc_page_5",dt_testdir["snapshot_path"],[(0,0,99,0),(0,7,99,37)])
            finally:
                if cf and "tables" in cf:
                    for d in cf["tables"]:
                        d[1].stop_refresh()

        curses.wrapper(main)
