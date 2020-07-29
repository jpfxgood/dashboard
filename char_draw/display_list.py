# Copyright 2017 James P Goodwin chardraw unicode curses based graphics package
""" module that implements a graphics package using block graphics on curses window """
import sys
import os
from char_draw import canvas
import curses


class Bbox:
    """ Bounding box object """
    def __init__(self, x0=0,y0=0,x1=0,y1=0):
        """ constructor, takex the bounding points of the bounding box """
        self.x0 = x0 if x0 < x1 else x1
        self.y0 = y0 if y0 < y1 else y1
        self.x1 = x1 if x1 > x0 else x0
        self.y1 = y1 if y1 > y0 else y0

    def get_size(self):
        """ return the height and width of the bounding box """
        return (self.x1-self.x0),(self.y1-self.y0)

    def get_location(self):
        """ return the location of the upper left corner of the bounding box """
        return self.x0,self.y0

    def union(self,bbox):
        """ constructs the bounding box that is the union of this bounding box and the input bbox """
        ret = Bbox( self.x0, self.y0, self.x1, self.y1 )
        ret.x0 = bbox.x0 if bbox.x0 < self.x0 else self.x0
        ret.y0 = bbox.y0 if bbox.y0 < self.y0 else self.y0
        ret.x1 = bbox.x1 if bbox.x1 > self.x1 else self.x1
        ret.y1 = bbox.y1 if bbox.y1 > self.y1 else self.y1
        return (ret)

    def __repr__(self):
        return "(%10.2f,%10.2f,%10.2f,%10.2f)"%(self.x0,self.y0,self.x1,self.y1)


class DisplayList:
    """ Base object for all display list objects """
    def __init__(self, parent = None, children = None, canvas=None):
        """ constructor, takes a parent object to be contained within and a list of children object to contain """
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = []
        # modified flag indicates if the object has been changed
        self.modified = True
        # initialize bbox
        self.bbox = None
        # set up canvas
        self.canvas = None
        self.xform = [1.0,1.0]
        self.focus = False
        if canvas:
            self.set_canvas(canvas)
        elif parent:
            self.set_canvas(parent.get_canvas())

    def set_focus( self, state  ):
        """ set focus to True or False to tell graph to render in focus mode """
        self.focus = state
        self.modified = True

    def is_focus( self ):
        """ return the current focus state """
        return self.focus

    def set_parent(self,parent):
        """ set the parent of this object """
        self.parent = parent
        self.set_canvas(parent.get_canvas())

    def get_parent(self):
        """ get the parent of this object """
        return(self.parent)

    def get_canvas(self):
        """ get the canvas for this display list """
        return self.canvas

    def set_canvas(self,canvas):
        """ set the canvas and the scaling transformation """
        self.xform = [1.0,1.0]
        self.canvas = canvas
        self.modified = True
        for c in self.children:
            c.set_canvas(canvas)

    def get_bbox(self):
        """ computes the bounding box of the display list object """
        ret = self.bbox
        if self.modified:
            ret = self.bbox = None
            for c in self.children:
                if not ret:
                    ret = c.get_bbox()
                else:
                    ret = ret.union(c.get_bbox())
            self.bbox = ret
            self.modified = False
        return (ret)

    def render(self):
        """ draw the object on the suppied canvas """
        for c in self.children:
            c.render()

    def transform(self, x, y ):
        """ apply current transform to point """
        return (x*self.xform[0], y*self.xform[1])

    def bounds(self):
        """ return the bounds of the current drawing surface """
        max_x,max_y = self.canvas.get_maxxy()
        return (0.0,0.0,max_x/self.xform[0],max_y/self.xform[1])

    def pick(self, row, col):
        """ return the topmost opject at row,col for mouse selection """
        for c in self.children:
            o = c.pick(row,col)
            if o:
                return o
        b = self.get_bbox()
        ulrow,ulcol = self.canvas.to_rowcol(*self.transform(b.x0,b.y0))
        lrrow,lrcol = self.canvas.to_rowcol(*self.transform(b.x1,b.y1))
        if row >= ulrow and row <= lrrow and col >= ulcol and col <= lrcol:
            return self
        else:
            return None

    def invalidate(self):
        """ mark this object and it's parent as invalidated """
        self.modified = True
        if self.parent:
            self.parent.invalidate()

    def is_modified(self):
        """ does this display list contain modified objects """
        modified = self.modified
        for c in self.children:
            modified = modified or c.is_modified()
        return modified

    def handle(self, event ):
        """ handle an input event, return None if handled, event if not """
        return event

    def add_child(self, child ):
        """ append a child to the list of children of this object """
        self.children.append(child)
        child.set_parent(self)
        child.set_canvas(self.get_canvas())
        self.invalidate()

    def remove_child(self, child ):
        """ remove this child from the list of children of this object """
        self.children.remove(child)
        child.set_parent(None)

    def get_children(self):
        """ return the children of this object if any """
        return self.children

    def set_children(self, children):
        """ set the children of this object to a new list of children """
        self.children = children
        for c in children:
            c.set_parent(self)
            c.set_canvas(self.get_canvas())
        self.invalidate()


class Rect(DisplayList):
    """Display list object for a rectangle"""
    def __init__(self,x0,y0,x1,y1,color,fill=False,parent=None):
        """ x0,y0 upper left corner of box, x1,y1 lower right corner of box, color is color, fill=True to fill parent is parent object """
        DisplayList.__init__(self,parent,None,None)
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.color = color
        self.fill = fill
        self.bbox = None

    def get_points( self ):
        """ return the rectangle's raw points """
        return ((self.x0,self.y0),(self.x1,self.y1))

    def set_points( self, points ):
        """ set the rectangle's raw points """
        self.x0,self.y0 = points[0]
        self.x1,self.y1 = points[1]
        self.invalidate()

    def get_color( self ):
        """ return the color of the rectangle """
        return self.color

    def set_color( self, color):
        """ set the color of the rectangle """
        self.color = color
        self.invalidate()

    def get_fill( self ):
        """ return the fill state of the rectangle """
        return self.fill

    def set_fill( self, fill):
        """ set the filled state of the rectangle """
        self.fill = fill
        self.invalidate()

    def render(self):
        """ override rendering to draw the requested rectangle """
        x0,y0 = self.transform( self.x0,self.y0 )
        x1,y1 = self.transform( self.x1,self.y1 )
        self.canvas.rect(self.x0,self.y0,self.x1,self.y1,self.color,self.fill)

    def get_bbox(self):
        """ get the bounding box for the rectangle """
        ret = self.bbox
        if self.modified and self.canvas:
            x0,y0 = self.transform( self.x0,self.y0 )
            x1,y1 = self.transform( self.x1,self.y1 )
            self.bbox = ret = Bbox(x0,y0,x1,y1)
            self.modified = False
        return self.bbox

class Circle(DisplayList):
    """Display list object for a circle"""
    def __init__(self, x,y,radius,color,fill=False, parent=None):
        """ x,y center of circle, radius is the radius,color is the color of the circle, fill is true to fill the circle """
        DisplayList.__init__(self,parent,None,None)
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.fill = fill
        self.bbox = None

    def get_center( self ):
        """ return the center of the circle """
        return (self.x, self.y)

    def set_center( self, center ):
        """ set the center of the circle """
        self.x, self.y = center
        self.invalidate()

    def get_radius( self ):
        """ return the center of the circle """
        return self.radius

    def set_radius( self, radius ):
        """ set the center of the circle """
        self.radius = radius
        self.invalidate()

    def get_color( self ):
        """ return the color of the circle """
        return self.color

    def set_color( self, color):
        """ set the color of the circle """
        self.color = color
        self.invalidate()

    def get_fill( self ):
        """ return the fill state of the circle """
        return self.fill

    def set_fill( self, fill):
        """ set the filled state of the circle """
        self.fill = fill
        self.invalidate()

    def render(self):
        """ override rendering to draw the requested circle """
        cx,cy = self.transform( self.x,self.y )
        dx,dy = self.transform( self.x+self.radius, self.y )
        sr = dx-cx
        self.canvas.circle(cx,cy,sr,self.color,self.fill)

    def get_bbox(self):
        """ compute the bbox of the circle """
        ret = self.bbox
        if self.canvas and self.modified:
            cx,cy = self.transform( self.x,self.y )
            dx,dy = self.transform( self.x+self.radius, self.y )
            sr = dx-cx
            self.bbox = ret = Bbox(self.x-sr,self.y-sr,self.x+sr,self.y+sr)
            self.modified = False
        return ret


class Arc(DisplayList):
    """Display list object for an arc"""
    def __init__(self, x,y,radius,a0,a1,color,fill=False, parent=None):
        """ x,y center of arc, angles are from a0 to a1, radius is the radius,color is the color of the arc, fill is true to fill the arc """
        DisplayList.__init__(self,parent,None,None)
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.fill = fill
        self.a0 = a0
        self.a1 = a1
        self.bbox = None

    def get_angles( self ):
        """ get the start and end angles for the arc """
        return (self.a0,self.a1)

    def set_angles( self, angles ):
        """ set the start and end angles for the arc """
        self.a0, self.a1 = angles

    def get_center( self ):
        """ return the center of the arc """
        return (self.x, self.y)

    def set_center( self, center ):
        """ set the center of the arc """
        self.x, self.y = center
        self.invalidate()

    def get_radius( self ):
        """ return the center of the arc """
        return self.radius

    def set_radius( self, radius ):
        """ set the center of the arc """
        self.radius = radius
        self.invalidate()

    def get_color( self ):
        """ return the color of the arc """
        return self.color

    def set_color( self, color):
        """ set the color of the arc """
        self.color = color
        self.invalidate()

    def get_fill( self ):
        """ return the fill state of the arc """
        return self.fill

    def set_fill( self, fill):
        """ set the filled state of the arc """
        self.fill = fill
        self.invalidate()

    def render(self):
        """ override rendering to draw the requested arc """
        cx,cy = self.transform( self.x,self.y )
        dx,dy = self.transform( self.x+self.radius, self.y )
        sr = dx-cx
        self.canvas.arc(cx,cy,sr,self.a0,self.a1,self.color,self.fill)

    def get_bbox(self):
        """ get the bounding box, compute it from the arc points """
        ret = self.bbox
        if self.canvas and self.modified:
            b = Bbox(-1.0,-1.0,-1.0,-1.0)
            def update_bounds(x,y,color):
                if b.x0 < 0 or x < b.x0:
                    b.x0 = x
                if b.y0 < 0 or y < b.y0:
                    b.y0 = y
                if b.x1 < 0 or x > b.x1:
                    b.x1 = x
                if b.y1 < 0 or y > b.y1:
                    b.y1 = y
            cx,cy = self.transform( self.x,self.y )
            dx,dy = self.transform( self.x+self.radius, self.y )
            sr = dx-cx
            self.canvas.arc(cx,cy,sr,self.a0,self.a1,self.color,self.fill,update_bounds)
            self.bbox = ret = b
            self.modified = False
        return ret

class Text(DisplayList):
    """Display list object for text"""
    def __init__(self, x,y,message,color,parent=None):
        """ x,y is the position of the first character, message is the text to display, color is the color """
        DisplayList.__init__(self,parent,None,None)
        self.x = x
        self.y = y
        self.message = message
        self.color = color
        self.bbox = None

    def get_location(self):
        """ get the text location """
        return (self.x,self.y)

    def set_location(self, location):
        """ set the text location """
        self.x, self.y = location
        self.invalidate()

    def get_message(self):
        """ get the message """
        return self.message

    def set_message(self, message):
        """ set the message """
        self.message = message
        self.invalidate()

    def get_color( self ):
        """ return the color of the text """
        return self.color

    def set_color( self, color):
        """ set the color of the text """
        self.color = color
        self.invalidate()

    def render(self):
        """ override rendering to draw the requested text """
        cx,cy = self.transform( self.x,self.y )
        self.canvas.textat(cx,cy,self.color,self.message)

    def get_bbox(self):
        """compute bounding box of text"""
        ret = self.bbox
        if self.canvas and self.modified:
            cx,cy = self.transform(self.x,self.y)
            cx,cy = self.canvas.round_text_position(cx,cy)
            ty,tx = self.canvas.from_rowcol(1,len(self.message))
            max_x,max_y = self.canvas.get_maxxy()
            cx1 = cx+tx
            cy1 = cy+ty
            if cx1 > max_x:
                cx1 = max_x
            if cy1 > max_y:
                cy1 = max_y
            self.bbox = ret = Bbox(cx,cy,cx+tx,cy+ty)
            self.modified = False
        return ret

class PolyLine(DisplayList):
    """Display list object for polyline"""
    def __init__(self,points,color,parent=None):
        """ points is a list of (x,y) tuples in order to be drawn as a polyline in color """
        self.points = points
        self.color = color
        self.bbox = None
        self.transformed_points = None
        DisplayList.__init__(self,parent,None,None)

    def get_color( self ):
        """ return the color of the polyline """
        return self.color

    def set_color( self, color):
        """ set the color of the polyline """
        self.color = color
        self.invalidate()

    def get_points(self):
        """ return a tuple of x,y tuples representing this PolyLine """
        return tuple(self.points)

    def set_points(self,points):
        """ set the points of this polyline """
        self.points = points
        self.invalidate()

    def transform_points( self ):
        """ get the transformed points """
        if not self.transformed_points or self.modified:
            t_points = []
            for x,y in self.points:
                t_points.append(self.transform(x,y))
            self.transformed_points = t_points
        return self.transformed_points

    def get_bbox( self ):
        """ get the bounding box """
        if (not self.transformed_points or self.modified) and self.canvas:
            if not self.bbox:
                self.bbox = Bbox()
            self.bbox.x0,self.bbox.y0,self.bbox.x1,self.bbox.y1 = self.canvas.get_bounds(self.transform_points())
            self.modified = False
        return self.bbox

    def render(self):
        """ override rendering to draw requested polyline """
        self.canvas.polyline(self.transform_points(),self.color)

class Polygon(PolyLine):
    """Display list object for a polygon, filled or not filled"""
    def __init__(self,points,color,fill,parent=None):
        """ points is a list of (x,y) tuples in order to be drawn as a closed polygon in color and if fill is True filled with color """
        PolyLine.__init__(self,points,color,parent)
        self.fill = fill

    def get_fill( self ):
        """ return the fill state of the arc """
        return self.fill

    def set_fill( self, fill):
        """ set the filled state of the arc """
        self.fill = fill
        self.invalidate()

    def render(self):
        """ override rendering to draw requested polygon """
        self.canvas.polygon(self.transform_points(),self.color,self.fill)
