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
from char_draw import display_list
from char_draw import data_table

class GraphSeries():
    """ wrapper for data series to be graphed """
    def __init__(self,data_table,coordinate):
        """ constructor takes a data table and a coordinate to choose the column """
        self.data = data_table
        self.column = coordinate


class Graph(display_list.DisplayList):
    """Graph base class for all graph types """

    def __init__(self,height,width,data_table=None,x_values=None,y_values=None,parent=None,canvas=None):
        """ base constructor for all graph types constructor takes a data_table which contains values to be graphed,
        x_values is a column reference in the data table for the xaxis values,
        y_values is a list of column references to series of numerical data to be graphed,
        parent is a reference to an enclosing display list,
        canvas is a reference to a canvas to render on """
        self.height = height
        self.width = width
        self.data = data_table
        self.x_values = GraphSeries(self.data, x_values)
        self.y_values = [GraphSeries(self.data, sy) for sy in y_values]
        self.initialized = False
        display_list.DisplayList.__init__(parent,None,canvas)

    def get_series( self ):
        """ return list of GraphSeries objects that describe the data series to be graphed """
        return self.y_values

    def get_xvalues( self ):
        """ return the series for the x-values """
        return self.x_values

    def get_data(self):
        """ return reference to the data table """
        return self.data

    def get_graph_objects(self, class_name ):
        """ return list of object references matching the class name, used for applying settings changes """
        matched = []
        for child in self.get_children():
            if child.__class__.__name__ == class_name:
                matched.append(child)
        return matched


class GraphTitle(display_list.DisplayList):
    """ A title to be displayed on a graph """
    def __init__(self,parent,text=None):
        display_list.DisplayList.__init__(self,parent,None,parent.get_canvas())
        self.text = text
        self._text = display_list.Text(0,0,self.text,0)
        self.add_child(self._text)

class GraphLegend(display_list.DisplayList):
    """ A legend to be displayed on a graph """
    def __init__(self,parent,listoftext=None):
        super.__init__(parent,None,parent.get_canvas())
        self.series_labels = listoftext
        self._series_labels = []
        for l in self.series_labels:
            self._series_labels.append(display_list.Text(0,0,l,0))
            self.add_child(self._series_labels[-1])


class GraphXAxisTitle(GraphTitle):
    """ A title to be displayed on the x-axis """
    def __init(self,parent,text):
        GraphTitle.__init__(self,parent,text)

class GraphYAxisTitle(GraphTitle):
    """ A title to be displayed on the y-axis """
    def __init(self,parent,text):
        GraphTitle.__init__(self,parent,text)

class GraphXAxis(display_list.DisplayList):
    """ An X-axis to be displayed on a graph """
    def __init__(self,parent, horizontal = True):
        display_list.DisplayList.__init__(self,parent,None,parent.get_canvas())
        self.horizontal = horizontal
        self._x_axis = display_list.PolyLine([],0)
        self.add_child(self._x_axis)

class GraphYAxis(display_list.DisplayList):
    """ An X-axis to be displayed on a graph """
    def __init__(self,parent,vertical = True):
        display_list.DisplayList.__init__(self,parent,None,parent.get_canvas())
        self.vertical = vertical
        self._y_axis = display_list.PolyLine([],0)
        self.add_child(self._y_axis)

class GraphArea(display_list.DisplayList):
    """ The area behind the graph series to be displayed on a graph """
    def __init__(self,parent):
        display_list.DisplayList.__init__(self,parent,None,parent.get_canvas())
        self._area = display_list.Rect(0,0,0,0,0)
        self.add_child(self._area)

class GraphBars(display_list.DisplayList):
    """ A bar chart plot of a graph series to be displayed on a graph """
    def __init__(self,parent,series):
        self.series = series
        display_list.DisplayList.__init__(self,parent,None,parent.get_canvas())


class BarGraph(Graph):
    """BarGraph that displays a data table as a bar graph"""
    def __init__(self,height,width,data_table=None,x_values=None,y_values=None,parent=None,canvas=None):
        """ constructor takes a data_table which contains values to be graphed,
        x_values is a column reference in the data table for the xaxis values,
        y_values is a list of column references to series of numerical datat to be graphed,
        parent is a reference to an enclosing display list,
        canvas is a reference to a canvas to render on """
        Graph.__init__(self,height,width,data_table,x_values,y_values,parent,canvas)
        self.title = None
        self.legend = None
        self.x_axis_title = None
        self.y_axis_title = None
        self.x_axis = None
        self.y_axis = None
        self.chart_area = None
        self.chart_series = []
        if self.canvas:
            self.init()

    def init(self):
        """ create the children for all of the graph components """
        if not self.initialized:
            self.title = GraphTitle(self,self.get_data().get_name())
            self.legend = GraphLegend(self,self.get_data().get_names())
            self.x_axis_title = GraphXAxisTitle(self,"Y Axis")
            self.y_axis_title = GraphYAxisTitle(self,"X Axis")
            self.x_axis = GraphXAxis(self, horizontal = True )
            self.y_axis = GraphYAxis(self, vertical = True )
            self.chart_area = GraphArea(self)
            self.chart_series = [GraphBars(self,series) for series in self.get_series()]
            self.add_child(self.title)
            self.add_child(self.legend)
            self.add_child(self.x_axis_title)
            self.add_child(self.y_axis_title)
            self.add_child(self.x_axis)
            self.add_child(self.y_axis)
            self.add_child(self.chart_area)
            for cs in self.chart_series:
                self.add_child(cs)
            self.initialized = True

    def layout(self):
        """ arrange the children of the graph based on size of graph """
        if self.modified:
            pass

        pass

    def render(self):
        """ override render to force initialization and layout"""
        if self.canvas:
            self.init()
            self.layout()
            display_list.DisplayList.render(self)
