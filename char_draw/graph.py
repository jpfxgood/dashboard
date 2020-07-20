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

def float_range(start, stop, step):
    while start < stop:
        yield float(start)
        start += step

class GraphSeries():
    """ wrapper for data series to be graphed """
    def __init__(self,data_table,coordinate):
        """ constructor takes a data table and a coordinate to choose the column """
        self.data = data_table
        self.column = coordinate


class Graph(display_list.DisplayList):
    """Graph base class for all graph types """

    def __init__(self,data_table=None,x_values=None,y_values=None,parent=None,canvas=None):
        """ base constructor for all graph types constructor takes a data_table which contains values to be graphed,
        x_values is a column reference in the data table for the xaxis values,
        y_values is a list of column references to series of numerical data to be graphed,
        parent is a reference to an enclosing display list,
        canvas is a reference to a canvas to render on """
        self.data = data_table
        self.x_values = GraphSeries(self.data, x_values)
        self.y_values = [GraphSeries(self.data, sy) for sy in y_values]
        self.initialized = False
        display_list.DisplayList.__init__(self,parent,None,canvas)

    def init(self):
        """ set internal state to default state """
        self.initialzied = False

    def get_series( self ):
        """ return list of GraphSeries objects that describe the data series to be graphed """
        return self.y_values

    def get_xvalues( self ):
        """ return the series for the x-values """
        return self.x_values

    def get_data(self):
        """ return reference to the data table """
        return self.data

class GraphElement( display_list.DisplayList ):
    """ base of all of the graph children """
    def __init__(self, parent, x=0.0, y=0.0, width=0.0, height=0.0):
        display_list.DisplayList.__init__(self,parent)
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_location( self ):
        """ return the location of the graph element """
        return (self.x,self.y)

    def get_size( self ):
        """ return the height and width of the graph element """
        return (self.width, self.height)

    def set_location( self, location ):
        """ set the location of the graph element """
        self.x,self.y = location
        self.modified = True

    def set_size( self, size ):
        """ set the size of the graph element """
        self.width,self.height = size
        self.modified = True


class GraphTitle(GraphElement):
    """ A title to be displayed on a graph """
    def __init__(self,parent,text=None):
        GraphElement.__init__(self,parent)
        self.text = text
        self.add_child(display_list.Text(0,0,self.text,self.canvas.white))

    def get_bbox(self):
        """ recompute and relayout the component and return it's bbox """
        if self.modified:
            new_children = []
            x,y = self.get_location()
            width,height = self.get_size()
            rows,cols = self.canvas.to_rowcol(width,height)
            r_height,r_width = self.canvas.from_rowcol(1,1)
            text = self.text.strip()
            while text and rows:
                prev_sidx = -1
                s_idx = -1
                while s_idx < cols:
                    prev_sidx = s_idx
                    s_idx = text.find(' ',s_idx+1)
                    if s_idx == -1:
                        break
                if prev_sidx > 0:
                    s_idx = prev_sidx
                if s_idx < 0 or s_idx > cols:
                    s_idx = cols
                new_children.append(display_list.Text(x,y,text[:s_idx],self.canvas.white))
                rows -= 1
                y += r_height
                text = text[s_idx:].lstrip()
            self.set_children(new_children)
        return GraphElement.get_bbox(self)

class GraphLegend(GraphElement):
    """ A legend to be displayed on a graph """
    def __init__(self,parent,listoftext=None):
        GraphElement.__init__(self,parent)
        self.series_labels = listoftext
        r_height,r_width = self.canvas.from_rowcol(1,1)
        x = 0
        y = 0
        for l in self.series_labels:
            self.add_child(display_list.Text(x,y,l,self.canvas.white))
            y += r_height

    def get_bbox(self):
        """ recompute and relayout the component and return it's bbox """
        if self.modified:
            new_children = []
            x,y = self.get_location()
            width,height = self.get_size()
            rows,cols = self.canvas.to_rowcol(width,height)
            r_height,r_width = self.canvas.from_rowcol(1,1)
            for text in self.series_labels:
                text = text.strip()
                while text and rows:
                    prev_sidx = -1
                    s_idx = -1
                    while s_idx < cols:
                        prev_sidx = s_idx
                        s_idx = text.find(' ',s_idx+1)
                        if s_idx == -1:
                            break

                    if prev_sidx > 0:
                        s_idx = prev_sidx
                    if s_idx < 0 or s_idx > cols:
                        s_idx = cols
                    new_children.append(display_list.Text(x,y,text[:s_idx],self.canvas.white))
                    rows -= 1
                    y += r_height
                    text = text[s_idx:].lstrip()
            self.set_children(new_children)
        return GraphElement.get_bbox(self)

class GraphXAxisTitle(GraphTitle):
    """ A title to be displayed on the x-axis """
    def __init(self,parent,text):
        GraphTitle.__init__(self,parent,text)

class GraphYAxisTitle(GraphTitle):
    """ A title to be displayed on the y-axis """
    def __init(self,parent,text):
        GraphTitle.__init__(self,parent,text)

class GraphXAxis(GraphElement):
    """ An X-axis to be displayed on a graph """
    def __init__(self,parent, horizontal = True):
        GraphElement.__init__(self,parent)
        self.horizontal = horizontal
        self.range_min = -1
        self.range_max = -1
        self.sx = 0
        self.values = []
        self.add_child(display_list.PolyLine([],self.canvas.green))

    def get_range( self ):
        """ return range_min, range_max, sx """
        return (self.range_min,self.range_max, self.sx)

    def get_values( self ):
        """ return vector of x (value,label) """
        return self.values

    def get_bbox( self ):
        """ compute the bounding box """
        if self.modified:
            new_children = []
            x_values = self.parent.get_xvalues()
            column = x_values.data.get_column(x_values.column)
            type = None

            for c in data_table.ColumnIterator(column):
                if not type or type == data_table.blank_type:
                    type = c.get_type()
                elif type != c.get_type():
                    type = 'mixed'

            self.values = []
            if type in [data_table.blank_type,data_table.string_type, 'mixed']:
                self.range_min = 0
                self.range_max = column.size()
                ix = 0
                for c in data_table.ColumnIterator(column):
                    self.values.append((ix,str(c)))
                    ix += 1
            else:
                self.range_min = -1
                self.range_max = -1
                for c in data_table.ColumnIterator(column):
                    value = c.get_value()
                    if self.range_min < 0 or value < self.range_min:
                        self.range_min = value
                    if self.range_max < 0 or value > self.range_max:
                        self.range_max = value
                    self.values.append((value,str(c)))

            r_height,r_width = self.canvas.from_rowcol(1,1)
            width,height = self.get_size()
            ox,oy = self.get_location()
            self.sx = width / (self.range_max-self.range_min)
            x = ox
            y = oy
            points = [(x,y)]
            labels = []
            for v,label in self.values:
                scaled_x = (v-self.range_min)*self.sx
                if ox+scaled_x >= x:
                    x = ox+scaled_x
                    points.append((x,y))
                    points.append((x,y-1))
                    points.append((x,y))
                    labels.append((x,y+r_height,label))
                    l_height,l_width = self.canvas.from_rowcol(1,len(label))
                    x += l_width
            new_children.append(display_list.PolyLine(points,self.canvas.green))
            for x,y,label in labels:
                new_children.append(display_list.Text(x,y,label,self.canvas.green))
            self.set_children(new_children)
        return GraphElement.get_bbox(self)

class GraphYAxis(GraphElement):
    """ An X-axis to be displayed on a graph """
    def __init__(self,parent,vertical = True):
        GraphElement.__init__(self,parent)
        self.vertical = vertical
        self.add_child(display_list.PolyLine([],self.canvas.green))
        self.range_min = -1
        self.range_max = -1
        self.sy = 0

    def get_range( self ):
        """ return range_min, range_max, sy """
        return (self.range_min,self.range_max, self.sy)

    def get_bbox(self):
        """ compute the bounding box """
        if self.modified:
            new_children = []
            y_values = self.parent.get_series()
            self.range_min = -1
            self.range_max = -1
            for series in y_values:
                column = series.data.get_column(series.column)
                for c in data_table.ColumnIterator(column):
                    value = c.get_value()
                    if self.range_min < 0 or value < self.range_min:
                        self.range_min = value
                    if self.range_max < 0 or value > self.range_max:
                        self.range_max = value

            r_height,r_width = self.canvas.from_rowcol(1,1)
            width,height = self.get_size()
            ox,oy = self.get_location()
            oy += (height-1)
            ox += (width-2)
            self.sy = height / (self.range_max-self.range_min)
            x = ox
            y = oy
            points = [(x,y)]
            labels = []
            for data_y in float_range(self.range_min,self.range_max,(self.range_max-self.range_min)/10):
                scaled_y = (data_y-self.range_min)*self.sy
                if oy-scaled_y <= y:
                    label = data_table.format_float(float(data_y))
                    l_height,l_width = self.canvas.from_rowcol(1,len(label))
                    y = oy-scaled_y
                    points.append((x,y))
                    points.append((x+1,y))
                    points.append((x,y))
                    labels.append((x-l_width,y,label))
                    y -= l_height
            new_children.append(display_list.PolyLine(points,self.canvas.green))
            for x,y,label in labels:
                new_children.append(display_list.Text(x,y,label,self.canvas.green))
            self.set_children(new_children)
        return GraphElement.get_bbox(self)

class GraphArea(GraphElement):
    """ The area behind the graph series to be displayed on a graph """
    def __init__(self,parent):
        GraphElement.__init__(self,parent)
        self.add_child(display_list.Rect(0,0,0,0,self.canvas.white))

    def get_bbox(self):
        """ compute the bounding box """
        if self.modified:
            new_children = []
            x,y = self.get_location()
            width,height = self.get_size()
            new_children.append(display_list.Rect(x,y,x+width,y+height,self.canvas.white))
            self.set_children(new_children)
        return GraphElement.get_bbox(self)

class GraphBars(GraphElement):
    """ A bar chart plot of a graph series to be displayed on a graph """
    def __init__(self,parent,series,x_axis,y_axis):
        self.series = series
        self.x_axis = x_axis
        self.y_axis = y_axis
        GraphElement.__init__(self,parent)

    def get_bbox(self):
        """ compute the bounding box """
        if self.modified:
            new_children = []
            x_min,x_max,x_scale = self.x_axis.get_range()
            y_min,y_max,y_scale = self.y_axis.get_range()
            x_values = self.x_axis.get_values()
            x,y = self.get_location()
            width,height = self.get_size()
            y = y+height

            column = self.series.data.get_column(self.series.column)
            idx = 0
            for c in data_table.ColumnIterator(column):
                y_value = c.get_value()
                x_value = x_values[idx][0]
                scaled_x = (x_value-x_min)*x_scale
                scaled_y = (y_value-y_min)*y_scale
                new_children.append(display_list.Rect(x+scaled_x,y,x+scaled_x+5,y-scaled_y,self.canvas.cyan))
            self.set_children(new_children)

        return GraphElement.get_bbox(self)

class BarGraph(Graph):
    """BarGraph that displays a data table as a bar graph"""
    def __init__(self,data_table=None,x_values=None,y_values=None,parent=None,canvas=None):
        """ constructor takes a data_table which contains values to be graphed,
        x_values is a column reference in the data table for the xaxis values,
        y_values is a list of column references to series of numerical data to be graphed,
        parent is a reference to an enclosing display list,
        canvas is a reference to a canvas to render on """
        Graph.__init__(self,data_table,x_values,y_values,parent,canvas)
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
            self.chart_series = [GraphBars(self,series,self.x_axis,self.y_axis) for series in self.get_series()]
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

    def get_bbox(self):
        """ arrange the children of the graph based on size of graph """

        if self.modified:
            min_x,min_y,max_x,max_y = self.bounds()

            width = (max_x-min_x) - 4
            height = (max_y-min_y) - 4

            x = 2
            y = 2
            self.title.set_location((x,y))
            self.title.set_size((width,height*0.18))
            y = y + height*0.18
            self.legend.set_location((x,y))
            self.legend.set_size((width,height*0.18))
            y = y + height*0.18
            self.y_axis_title.set_location((x,y+height*0.20))
            self.y_axis_title.set_size((width*0.10,height*0.20))
            self.y_axis.set_location((x+(width*0.10),y))
            self.y_axis.set_size((width*0.10,height*0.40))
            self.chart_area.set_location((x+(width*0.20),y))
            self.chart_area.set_size((width*.96,height*0.40))
            for cs in self.chart_series:
                cs.set_location((x+(width*0.20),y))
                cs.set_size((width*0.96,height*0.40))
            y += height*0.40
            self.x_axis.set_location((x+(width*0.20),y))
            self.x_axis.set_size((width*0.96,height*0.12))
            y += height*0.12
            self.x_axis_title.set_location((x+(width*0.20),y))
            self.x_axis_title.set_size((width*0.96,height*0.12))

        return Graph.get_bbox(self)

    def render(self):
        """ override render to force initialization and layout"""
        if self.canvas:
            self.init()
            self.get_bbox()
            display_list.DisplayList.render(self)

def main(stdscr):
    """ test driver for the chardraw """
    curses.init_pair(1,curses.COLOR_GREEN,curses.COLOR_BLACK)
    curses.init_pair(2,curses.COLOR_RED,curses.COLOR_BLACK)
    curses.init_pair(3,curses.COLOR_CYAN,curses.COLOR_BLACK)
    curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)

    stdscr.getch()

    d = data_table.DataTable(name="SimpleBarChart")
    cx = data_table.Column(name="X values")
    for x in range(0,200):
        cx.put(x,data_table.Cell(data_table.float_type,float(x),data_table.format_float))
    cy = data_table.Column(name="Y values")
    for y in range(0,200):
        cy.put(y,data_table.Cell(data_table.float_type,float(y+200),data_table.format_float))

    d.add_column(cx)
    d.add_column(cy)

    c = canvas.Canvas(stdscr)
    bc = BarGraph(d,"X values",["Y values"],None,c)
    bc.render()
    c.refresh()

    stdscr.getch()

    return 0

if __name__ == '__main__':
    curses.wrapper(main)
