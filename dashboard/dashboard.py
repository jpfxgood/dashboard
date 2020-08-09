# Copyright 2017 James P Goodwin a package to draw graphs of data in a terminal window
""" module that implements graphs of data rendered in a terminal window """
import locale
locale.setlocale(locale.LC_ALL,"")
import curses
import curses.ascii
import sys
import os
import math
import time
from datetime import datetime
from char_draw import canvas
from char_draw import graph
from data_sources import data_table,syslog_data

class Panel:
    def __init__(self, y=-1,x=-1,height=-1,width=-1,graphs=None,parent=None):
        """ A panel is a container for a collection of graphs they fit within it's bounds """
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.graphs = graphs if graphs else []
        self.graph_layout = []
        self.parent = None
        self.pad = None
        if parent:
            self.set_parent( parent )

    def set_layout( self, y, x, height, width ):
        """ set the current layout of this panel """
        self.y = y
        self.x = x
        self.height = height
        self.width = width
        self.layout_graphs()

    def get_layout( self ):
        """ return the panel layout """
        return (self.y,self.x,self.height,self.width)

    def get_pad( self ):
        """ return this panel's pad just a passthru to the parent's pad """
        return self.pad

    def set_parent( self, parent ):
        """ set this panel to have this parent """
        self.pad = parent.get_pad()
        self.parent = parent
        self.layout_graphs()

    def add_graph( self, graph ):
        """ add a graph to this panel """
        self.graphs.append( graph )
        self.layout_graphs()

    def layout_graphs( self ):
        """ compute a rectangular layout of graphs within the panel and assign them those locations """
        self.graph_layout = []
        if self.x >= 0: # if the panel has been sized
            ngraphs = len(self.graphs)
            best_fit = None
            min_dxy = None
            for cols in range(1,ngraphs+1):
                for rows in range(1,ngraphs+1):
                    if rows*cols >= ngraphs:
                        dx = self.width//cols
                        dy = self.height//rows
                        dxy = max(dx,dy)-min(dx,dy)
                        if min_dxy == None or dxy < min_dxy:
                            min_dxy = dxy
                            best_fit = (rows,cols,dy,dx)
            rows,cols,dy,dx = best_fit
            x = 0
            y = 0
            for g in self.graphs:
                self.graph_layout.append((y,x,dy,dx))
                pad = self.get_pad()
                if pad:
                    g_pad = pad.subpad(dy,dx,y,x)
                    g_canvas = canvas.Canvas(g_pad)
                    g.set_canvas(g_canvas)
                x += dx
                if x >= self.width:
                    x = 0
                    y += dy
        return self.graph_layout

    def get_graph_layout( self ):
        """ return a list of tuples (graph,y,x,height,width) for the current layout """
        if not self.graph_layout:
            self.layout_graphs()
        ret_layout = []
        idx = 0
        for y,x,dy,dx in self.graph_layout:
            ret_layout.append((self.graphs[idx],self.y+y,self.x+x,dy,dx))
            idx += 1
        return ret_layout

    def redraw( self ):
        """ redraw the panel and all it's graphs """
        if not self.graph_layout:
            self.layout_graphs()
        if self.get_pad():
            for g in self.graphs:
                if g.is_modified():
                    g.render()

class Page:
    def __init__(self, window, height=-1, width=-1 ):
        """ one page of a dashboard has the parent window and it's height and width """
        self.window = window

        if height <= 0 or width <= 0:
            height,width = window.getmaxyx()
            height = height - 1

        self.height = height
        self.width = width
        self.pad = curses.newpad(height,width)
        self.position = (0,0)
        self.panels = []
        self.panel_layout = []
        self.current_panel = 0

    def get_pad( self ):
        """ return  your pad """
        return self.pad

    def add_panel( self, panel ):
        """ add a panel into the page """
        self.panels.append(panel)
        panel.set_parent(self)
        self.layout_panels()

    def move( self, row, col ):
        """ move the current scroll position to a new location """
        if row < self.height and row >= 0 and col < self.width and col >= 0:
            self.position = (row,col)
        return self.position

    def get_position( self ):
        """ get the current position """
        return self.position

    def get_size( self ):
        """ return the height and width of this page """
        return (self.height,self.width)

    def get_current_panel( self ):
        """ return the current panel """
        panel = None
        if self.panels:
            panel = self.panels[self.current_panel]
        return panel

    def next_panel( self ):
        """ move to the next panel and return that panel or None if we're at the end"""
        panel = None
        if self.panels:
            if self.current_panel+1 < len(self.panels):
                self.current_panel = self.current_panel + 1
                panel = self.panels[self.current_panel]
        return panel

    def prev_panel( self ):
        """ move to the previous panel return that panel or None if we're at the start """
        panel = None
        if self.panels:
            if self.current_panel > 0:
                self.current_panel = self.current_panel -1
                panel = self.panels[self.current_panel]
        return panel

    def first_panel( self ):
        """ move to the first panel and return that panel """
        panel = None
        if self.panels:
            self.current_panel = 0
            panel = self.panels[self.current_panel]
        return panel

    def last_panel( self ):
        """ move to the last panel and return that panel """
        panel = None
        if self.panels:
            self.current_panel = len(self.panels)-1
            panel = self.panels[self.current_panel]
        return panel

    def redraw( self ):
        """ redraw all of the panels """
        if not self.get_panel_layout():
            self.layout_panels()

        for p in self.panels:
            p.redraw()

    def layout_panels( self ):
        """ compute a rectangular layout of panels within the page and assign them those locations """
        self.panel_layout = []

        is_dynamic = False
        for g in self.panels:
            y,x,dy,dx = g.get_layout()
            if x < 0:
                is_dynamic = True

        if is_dynamic:
            npanels = len(self.panels)
            best_fit = None
            min_dxy = None
            for cols in range(1,npanels+1):
                for rows in range(1,npanels+1):
                    if rows*cols >= npanels:
                        dx = self.width//cols
                        dy = self.height//rows
                        dxy = max(dx,dy)-min(dx,dy)
                        if min_dxy == None or dxy < min_dxy:
                            min_dxy = dxy
                            best_fit = (rows,cols,dy,dx)

            rows,cols,dy,dx = best_fit
            x = 0
            y = 0

            for g in self.panels:
                self.panel_layout.append((g,y,x,dy,dx))
                g.set_layout(y,x,dy,dx)
                x += dx
                if x >= self.width:
                    x = 0
                    y += dy
        else:
            for g in self.panels:
                y,x,dy,dx = g.get_layout()
                self.panel_layout.append((g,y,x,dy,dx))

        return self.panel_layout

    def get_panel_layout( self ):
        """ return the layout for the panels, tuples are panel,y,x,height,width """
        return self.panel_layout

    def refresh( self ):
        """ refresh this page showing the current position """
        w_ymax,w_xmax = self.window.getmaxyx()
        w_ymax -= 1
        if w_ymax >= self.height and w_xmax >= self.width:
            self.pad.refresh(0,0,1,0,self.height,self.width)
        else:
            p_y,p_x = self.position
            h = min(w_ymax,self.height - p_y)
            w = min(w_xmax,self.width - p_x)
            self.pad.refresh(p_y,p_x,1,0,h-1,w-1)
            if w < w_xmax:
                for y in range(0,h):
                    try:
                        self.window.addstr(y,w,' '*(w_xmax-w))
                    except:
                        pass
            while h < w_ymax:
                try:
                    self.window.addstr(h,0,' '*(w_xmax-1))
                except:
                    pass
                h += 1

class Dashboard:
    def __init__(self,window,pages = None, auto_tour_delay = 0):
        """ Dashboard driver that holds an array of pages, auto_tour_delay > 0 will tab around all of the graphs with this delay in seconds between each """
        self.window = window
        self.pages = pages if pages else []
        self.current_page = 0
        self.current_panel = None
        self.current_graph = 0
        self.current_graph_pos = None
        self.auto_tour_delay = auto_tour_delay

    def add_page(self, page ):
        """ add a page to this dashboard """
        self.pages.append(page)

    def get_window( self ):
        """ Get this dashboard's window """
        return self.window

    def get_current_page( self ):
        """ Get the current page """
        page = None
        if self.pages:
            page = self.pages[self.current_page]
        return page


    def reset_position( self ):
        """ Reset the tour position """
        page = self.get_current_page()
        if page:
            self.current_panel = page.first_panel()
            self.current_graph = 0
            page.move(0,0)
            self.current_graph_pos = None

    def next_page( self ):
        """ Goto the next page and return it or return None if at the end """
        page = None
        if self.pages:
            if self.current_page+1 < len(self.pages):
                self.current_page += 1
                page = self.pages[self.current_page]
                self.reset_position()
        return page

    def prev_page( self ):
        """ goto the previous page and return it or return None if at the beginning """
        page = None
        if self.pages:
            if self.current_page > 0:
                self.current_page -= 1
                page = self.pages[self.current_page]
                self.reset_position()
        return page

    def first_page( self ):
        """ goto the first page and return it or return None if no pages """
        page = None
        if self.pages:
            self.current_page = 0
            page = self.pages[self.current_page]
            self.reset_position()
        return page

    def last_page( self ):
        """ goto the last page and return it or return None if no pages """
        page = None
        if self.pages:
            self.current_page = len(self.pages)-1
            page = self.pages[self.current_page]
            self.reset_position()
        return page

    def get_current_panel( self ):
        """ get the current_panel in the current_page or None if there are none """
        panel = None
        page = self.get_current_page()
        if page:
            panel = page.get_current_panel()
        return panel

    def get_current_graph( self ):
        """ get the current graph tuple in the current_page in the current panel, None if there is none """
        graph = None
        panel = self.get_current_panel()
        if panel:
            graphs = panel.get_graph_layout()
            if graphs:
                if self.current_graph >= len(graphs):
                    self.current_graph = 0
                graph = graphs[self.current_graph]
        return graph

    def next_graph( self ):
        """ step forward to the next graph,panel,page return the graph tuple for the current graph, return None at the end """
        graph = None
        panel = self.get_current_panel()
        page = self.get_current_page()
        if panel:
            graphs = panel.get_graph_layout()
            while panel and graphs and not graph:
                if self.current_graph+1 < len(graphs):
                    self.current_graph += 1
                    graph = graphs[self.current_graph]
                else:
                    page = self.get_current_page()
                    panel = page.next_panel()
                    self.current_graph = 0
                    if not panel:
                        page = self.next_page()
                        if page:
                            graph = self.get_current_graph()
                        else:
                            return None
                    else:
                        graphs = panel.get_graph_layout()
                        graph = graphs[self.current_graph]
            if graph:
                page.move(graph[1],graph[2])

        return graph


    def main( self ):
        """ main input and redraw loop for the dashboard """
        self.window.nodelay(1)
        self.window.notimeout(0)
        self.window.timeout(1000)
        self.window.keypad(1)
        curses.curs_set(0)
        curses.raw()
        curses.mousemask( curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION )

        start_time = time.time()
        positions = []
        zoomed = False
        zoomed_canvas = None
        zoomed_graph = None
        zoomed_restore_canvas = None
        status = ""
        while True:
            ch = self.window.getch()

            if not zoomed:
                cur_graph = self.get_current_graph()
                cur_graph[0].set_focus(True)

                if ch > -1:
                    page = self.get_current_page()
                    py,px = page.get_position()

                    if ch == 27: # esc key
                        return 0
                    elif ch == 9: # tab key
                        self.next_graph()
                    elif ch == curses.KEY_NPAGE:
                        self.next_page()
                    elif ch == curses.KEY_PPAGE:
                        self.prev_page()
                    elif ch == curses.KEY_HOME:
                        self.first_page()
                    elif ch == curses.KEY_END:
                        self.last_page()
                    elif ch == curses.KEY_RIGHT:
                        page.move(py,px+1)
                    elif ch == curses.KEY_LEFT:
                        page.move(py,px-1)
                    elif ch == curses.KEY_UP:
                        page.move(py-1,px)
                    elif ch == curses.KEY_DOWN:
                        page.move(py+1,px)
                    elif ch == curses.KEY_F5:
                        for p in self.pages:
                            for pp in p.get_panel_layout():
                                for gg in pp[0].get_graph_layout():
                                    gg[0].refresh_data()
                    elif ch == curses.KEY_ENTER or ch == 10: # ENTER KEY
                        zoomed = True
                        zoomed_graph = self.get_current_graph()
                        zoomed_canvas = canvas.Canvas(self.window)
                        zoomed_restore_canvas = zoomed_graph[0].get_canvas()
                        zoomed_graph[0].set_canvas(zoomed_canvas)
                        self.window.clear()
                        continue
                    elif ch == curses.KEY_MOUSE:
                        mid, mx, my, mz, mtype = curses.getmouse()
                        max_y,max_x = self.window.getmaxyx()
                        if mtype & curses.BUTTON1_CLICKED:
                            if mx == 0 and my == 0:
                                self.first_page()
                            elif mx == 0 and my > 0:
                                self.prev_page()
                            elif mx == max_x-1 and my == max_y-1:
                                self.last_page()
                            elif mx == max_x-1 and my < max_y-1:
                                self.next_page()
                    start_time = time.time()
                    positions = []

                if self.auto_tour_delay:
                    if time.time() - start_time > (self.auto_tour_delay/4): # 4 views per graph
                        if not positions:
                            g = self.next_graph()
                            if not g:
                                self.first_page()
                                g = self.get_current_graph()
                            positions = [(g[1],g[2]),(g[1]+(g[3]//2),g[2]),(g[1]+(g[3]//2),g[2]+(g[4]//2)),(g[1],g[2]+(g[4]//2))]
                        py,px = positions.pop(0)
                        self.get_current_page().move(py,px)
                        start_time = time.time()

                if cur_graph[0] != self.get_current_graph()[0]:
                    cur_graph[0].set_focus(False)

                page = self.get_current_page()
                if page:
                    page.redraw()
                    page.refresh()

            if zoomed:
                if ch > -1:
                    if ch == 27: # esc key
                        zoomed_graph[0].set_canvas(zoomed_restore_canvas)
                        zoomed = False
                        zoomed_graph = None
                        zoomed_canvas = None
                        zoomed_restore_canvas = None

                if zoomed_graph and zoomed_graph[0].is_modified():
                    zoomed_graph[0].render()
                    self.window.refresh()

            latest_refresh = 0
            for p in self.pages:
                for pp in p.get_panel_layout():
                    for gg in pp[0].get_graph_layout():
                        latest_refresh = max(latest_refresh,gg[0].get_data().get_refresh_timestamp())

            self.window.addstr(0,0," "*len(status),curses.color_pair(1)|curses.A_REVERSE)
            status = "Page %d of %d Last Update %s%s"%(self.current_page+1,len(self.pages),datetime.fromtimestamp(latest_refresh).strftime("%A, %d. %B %Y %I:%M%p")," ZOOMED (Press Esc to Exit)" if zoomed else "")
            self.window.addstr(0,0,status,curses.color_pair(1)|curses.A_REVERSE)



def main(stdscr):
    """ test driver for the dashboard """

    sd = syslog_data.SyslogDataTable(refresh_minutes=1)
    sd.start_refresh()
    d = Dashboard(stdscr,auto_tour_delay = 5)
    p = Page(stdscr)
    height, width = p.get_size()
    pp = Panel(0,0,height,width)
    pp.add_graph(graph.LineGraph(sd,"Time Stamps",["Errors by Time"],None,None))
    pp.add_graph(graph.LineGraph(sd,"Time Stamps",["Messages by Time"],None,None))
    p.add_panel(pp)
    d.add_page(p)
    p = Page(stdscr)
    pp = Panel(0,0,height,width)
    pp.add_graph(graph.LineGraph(sd,"Time Stamps",["Warnings by Time"],None,None))
    pp.add_graph(graph.BarGraph(sd,"Services",["Messages by Service"],None,None,5))
    p.add_panel(pp)
    d.add_page(p)
    d.main()
    sd.stop_refresh()

    return 0

if __name__ == '__main__':
    curses.wrapper(main)
