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

    max_y,max_x = stdscr.getmaxyx()
    wx = max_x//2
    wy = max_y//2
    sw1 = stdscr.subwin(wy,wx,0,0)
    sw2 = stdscr.subwin(wy,wx,0,wx)
    sw3 = stdscr.subwin(wy,wx,wy,0)
    sw4 = stdscr.subwin(wy,wx,wy,wx)
    c1 = canvas.Canvas(sw1)
    c2 = canvas.Canvas(sw2)
    c3 = canvas.Canvas(sw3)
    c4 = canvas.Canvas(sw4)
    sd = syslog_data.SyslogDataTable(refresh_minutes=1)
    sd.start_refresh()
    bc1 = graph.LineGraph(sd,"Time Stamps",["Errors by Time"],None,c1)
    bc2 = graph.LineGraph(sd,"Time Stamps",["Messages by Time"],None,c2)
    bc3 = graph.LineGraph(sd,"Time Stamps",["Warnings by Time"],None,c3)
    bc4 = graph.BarGraph(sd,"Services",["Messages by Service"],None,c4,5)

    while True:
        if bc1.is_modified() or bc2.is_modified() or bc3.is_modified() or bc4.is_modified():
            bc1.render()
            bc2.render()
            bc3.render()
            bc4.render()
            c1.refresh()
            c2.refresh()
            c3.refresh()
            c4.refresh()

    return 0

if __name__ == '__main__':
    curses.wrapper(main)
