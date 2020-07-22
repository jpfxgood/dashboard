# Copyright 2017 James P Goodwin a package to draw graphs of data in a terminal window
""" module that implements graphs of data rendered in a terminal window """
import locale
locale.setlocale(locale.LC_ALL,"")
import curses
import curses.ascii
import sys
import os
import math
from char_draw import canvas
from char_draw import graph
from data_sources import data_table,syslog_data
                                               

def main(stdscr):
    """ test driver for the dashboard """

    c = canvas.Canvas(stdscr)
    sd = syslog_data.SyslogDataTable(refresh_minutes=1)                                  
    sd.start_refresh()
    bc = graph.LineGraph(sd,"Time Stamps",["Errors by Time","Warnings by Time","Messages by Time"],None,c)
    
    while True:
        if bc.is_modified():
            bc.render()
            c.refresh()

    return 0

if __name__ == '__main__':
    curses.wrapper(main)

