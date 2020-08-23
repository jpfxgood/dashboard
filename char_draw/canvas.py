# Copyright 2017 James P Goodwin chardraw unicode curses based graphics package
""" module that implements a graphics package using block graphics on curses window """
import locale
locale.setlocale(locale.LC_ALL,"")
import curses
import curses.ascii
import sys
import os
import math

def angle_point(x0,y0,a,radius):
    return (int(x0+(1.5*math.cos(math.radians(a))*radius)), int(y0+math.sin(math.radians(a))*radius))

class Canvas:
    """ primitive drawing surface attached to a curses window """

    to_mask = { 0:1, 1:2, 2:4, 3:8 }
    mask_to_char = {
        0 :'\u2008',
        1 :'\u2598',
        2 :'\u259d',
        3 :'\u2580',
        4 :'\u2596',
        5 :'\u258c',
        6 :'\u259e',
        7 :'\u259b',
        8 :'\u2597',
        9 :'\u259a',
        10:'\u2590',
        11:'\u259c',
        12:'\u2584',
        13:'\u2599',
        14:'\u259f',
        15:'\u2588'
        }

    char_to_mask = {
        '\u2008':0 ,
        '\u2598':1 ,
        '\u259d':2 ,
        '\u2580':3 ,
        '\u2596':4 ,
        '\u258c':5 ,
        '\u259e':6 ,
        '\u259b':7 ,
        '\u2597':8 ,
        '\u259a':9 ,
        '\u2590':10,
        '\u259c':11,
        '\u2584':12,
        '\u2599':13,
        '\u259f':14,
        '\u2588':15
        }

    def __init__(self, win = None ):
        """ constructor, can be initialized with a window to draw on, otherwise window must be set later by set_window """
        self.set_win(win)

    def to_rowcol(self, x, y ):
        """ return character row col for input x,y coordinates """
        return (int(y/2),int(x/2))

    def from_rowcol(self, row, col ):
        """ return the pixel location of a character position, returns upper left pixel in matrix"""
        return (int(row)*2,int(col)*2)

    def round_text_position(self, x, y):
        """ adjust a text position so that it always ends up down and to the right if it is at a half pixel offset """
        r,c = self.to_rowcol(x,y)
        y1,x1 = self.from_rowcol(r,c)
        h,w = self.from_rowcol(1,1)
        if y1 < y:
            y = y + h/2
        if x1 < x:
            x = x + w/2
        return x, y

    def round_text_x_position(self, x):
        """ adjust a text position so that it always ends up down and to the right if it is at a half pixel offset """
        r,c = self.to_rowcol(x,0)
        y1,x1 = self.from_rowcol(r,c)
        h,w = self.from_rowcol(1,1)
        if x1 < x:
            x = x + w/2
        return x

    def round_text_y_position(self, y):
        """ adjust a text position so that it always ends up down and to the right if it is at a half pixel offset """
        r,c = self.to_rowcol(0,y)
        y1,x1 = self.from_rowcol(r,c)
        h,w = self.from_rowcol(1,1)
        if y1 < y:
            y = y + h/2
        return y

    def set_win(self, win ):
        """ point this canvas at a window and initialize things, will blank out the window """
        self.win = win
        self.init_win()

    def init_win(self):
        """ initializes the window and sets up all of the defaults """
        curses.init_pair(5,curses.COLOR_BLACK,curses.COLOR_BLACK)
        curses.init_pair(1,curses.COLOR_GREEN,curses.COLOR_BLACK)
        curses.init_pair(2,curses.COLOR_RED,curses.COLOR_BLACK)
        curses.init_pair(3,curses.COLOR_CYAN,curses.COLOR_BLACK)
        curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)

        self.green = curses.color_pair(1)
        self.red = curses.color_pair(2)
        self.cyan = curses.color_pair(3)
        self.white = curses.color_pair(4)
        self.black = curses.color_pair(5)

        if curses.can_change_color():
            self.color_min = 8
            self.color_max = 256

            red = 0
            green = 100
            blue = 20
            for c in range(self.color_min,self.color_max):
                curses.init_color(c,red,green,blue)
                red += 23
                green += 33
                blue += 53
                red = red % 1000
                green = green % 1000
                blue = blue % 1000

            for cidx in range(self.color_min,self.color_max):
                curses.init_pair(cidx,cidx,curses.COLOR_BLACK)
        else:
            self.color_min = 0
            self.color_max = 8

        if self.win:
            self.max_y,self.max_x = self.win.getmaxyx()
            self.char_map = [[None] * self.max_y for i in range(self.max_x)]
            self.max_y = self.max_y * 2
            self.max_x = self.max_x * 2
        else:
            self.max_y,self.max_x = (0,0)
            self.char_map = None

    def clear( self ):
        """ clear the entire canvas """
        self.char_map = [[None] * self.max_y for i in range(self.max_x)]

    def refresh( self ):
        """ refresh the display after drawing """
        self.win.refresh()

    def get_maxxy( self ):
        """ return the maximum number of x and y pixels that are available in this canvas """
        return (self.max_x,self.max_y)

    def put_pixel( self, x,y, color, set = True ):
        """ turn on a pixel with the color indicated """
        if x < 0 or x >= self.max_x or y < 0 or y >= self.max_y:
            return
        row,col = self.to_rowcol(x,y)
        if row >= self.max_y//2 or col >= self.max_x//2:
            return

        mask = self.to_mask[(int(x)%2)+((int(y)%2)*2)]

        if not self.char_map[col][row]:
            current_mask = 0
        else:
            current_mask = self.char_to_mask[self.char_map[col][row]]

        if set:
            self.char_map[col][row] = self.mask_to_char[ mask | current_mask ]
        else:
            self.char_map[col][row] = self.mask_to_char[ mask ^ current_mask ]
        try:
            self.win.addstr(row,col,self.char_map[col][row].encode('utf_8'),color)
        except:
            pass

    def line(self, x0, y0, x1, y1, color, put_pixel=None ):
        """ draw a line between x0,y0 and x1,y1 in color """
        def set_pixel(x,y,color):
            if put_pixel:
                put_pixel(x,y,color)
            else:
                self.put_pixel(x,y,color)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = int(x0), int(y0)
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1
        if dx > dy:
            err = dx / 2.0
            while x != int(x1):
                set_pixel(x, y,color)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != int(y1):
                set_pixel(x, y,color)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        set_pixel(x, y, color)

    def intersect( self, seg1, seg2, clip_to_seg = False ):
        """ find the intersection of two segments as tuples (x0,y0,x1,y1) returns tuple (x,y) if no intersection returns None """
        def lineform( seg ):
            """ return A, B, C for the standard line formula Ax + By = C """
            A = float(seg[1]-seg[3])
            B = float(seg[2]-seg[0])
            C = A*seg[0]+B*seg[1]
            return (A,B,C)

        l1 = lineform(seg1)
        l2 = lineform(seg2)

        det = l1[0]*l2[1] - l2[0]*l1[1]
        if det != 0:
            x = (l2[1]*l1[2] - l1[1]*l2[2])/det
            y = (l1[0]*l2[2] - l2[0]*l1[2])/det

            if clip_to_seg:
                if x >= min(seg1[0],seg1[2]) and x <= max(seg1[0],seg1[2]) and y >= min(seg1[1],seg1[3]) and y <= max(seg1[1],seg1[3]):
                    return (int(x),int(y))
            else:
                return (int(x),int(y))
        return None

    def cross_product_length( self, pA,pB,pC ):
        """ compute the cross product of AB x BC """
        BAx = float(pA[0] - pB[0])
        BAy = float(pA[1] - pB[1])
        BCx = float(pC[0] - pB[0])
        BCy = float(pC[1] - pB[1])

        return (BAx * BCy - BAy * BCx)

    def is_convex( self, points ):
        """ take a list of (x,y) tuples representing the vertecies of a polygon in order and return True if it represents a convex polygon, False otherwise """
        got_negative = False
        got_positive = False
        num_points = len(points)
        if num_points <= 3:
            return True


        min_x,min_y,max_x,max_y = self.get_bounds(points)
        if max_x-min_x <= 1.0 or max_y-min_y <= 1.0:
            return True

        for A in range(num_points):
            B = (A+1)%num_points
            C = (B+1)%num_points
            cross_product = self.cross_product_length(points[A],points[B],points[C])
            if cross_product < 0:
                got_negative = True
            elif cross_product > 0:
                got_positive = True

        return not (got_negative and got_positive)

    def get_bounds(self,points):
        """ return tuple (min_x,min_y,max_x,max_y) for list of points """
        min_x = -1
        min_y = -1
        max_x = -1
        max_y = -1
        for x,y in points:
            if min_x < 0 or x < min_x:
                min_x = x
            if min_y < 0 or y < min_y:
                min_y = y
            if max_x < 0 or x > max_x:
                max_x = x
            if max_y < 0 or y > max_y:
                max_y = y
        return (min_x,min_y,max_x,max_y)

    def clip_polygon(self, points, minX, minY, maxX, maxY, dir=-1 ):
        """ clip a polygon against the bounds exressed by minX,minY to maxX,maxY and return either None for nothing inside or the points for the polygon dir is -1 all,0=top,1=right,2=bottom,3=left """
        def inside( p, minX, minY, maxX, maxY, dir ):
            x,y = p
            if dir == 0:
                return(y >= minY)
            elif dir == 1:
                return(x < maxX)
            elif dir == 2:
                return(y < maxY)
            elif dir == 3:
                return(x >= minX)

        def intersect(sp, ep, minX, minY, maxX, maxY, dir ):
            x0,y0 = sp
            x1,y1 = ep
            s1 = (x0,y0,x1,y1)
            if dir == 0:
                s2 = (minX,minY,maxX,minY)
            elif dir == 1:
                s2 = (maxX,minY,maxX,maxY)
            elif dir == 2:
                s2 = (minX,maxY,maxX,maxY)
            elif dir == 3:
                s2 = (minX,minY,minX,maxY)
            return self.intersect(s1,s2,False)

        if dir == -1:
            for d in [0,1,2,3]:
                points = self.clip_polygon(points,minX,minY,maxX,maxY,d)
                if not points:
                    return None
            return points
        else:
            sp = points[-1]
            out_points = []
            for ep in points:
                if inside(ep,minX,minY,maxX,maxY,dir):
                    if inside(sp,minX,minY,maxX,maxY,dir):
                        out_points.append(ep)
                    else:
                        ip = intersect(sp,ep,minX,minY,maxX,maxY,dir)
                        out_points.append(ip)
                        out_points.append(ep)
                else:
                    if inside(sp,minX,minY,maxX,maxY,dir):
                        ip = intersect(sp,ep,minX,minY,maxX,maxY,dir)
                        out_points.append(ip)
                sp = ep
            return out_points if out_points else None


    def rasterize( self, points, color, put_pixel=None):
        """ sort points representing the boundary of a filled shape and rasterize by filling lines with color """
        ps = sorted(points,key=lambda x: (x[1],x[0]))
        n_points = len(ps)
        if n_points == 0:
            return
        elif n_points == 1:
            x,y = ps[0]
            if put_pixel:
                put_pixel(x,y,color)
            else:
                self.put_pixel(x,y,color)
        else:
            idx = 1
            x0,y0 = ps[0]
            x1,y1 = x0,y0
            while idx < len(ps):
                xn,yn = ps[idx]
                if yn == y0:
                    x1,y1 = xn,yn
                else:
                    if x0 == x1:
                        if put_pixel:
                            put_pixel(x0,y0,color)
                        else:
                            self.put_pixel(x0,y0,color)
                    else:
                        self.line(x0,y0,x1,y1,color,put_pixel)
                    x0,y0 = xn,yn
                    x1,y1 = x0,y0
                idx += 1
            if x0 == x1:
                if put_pixel:
                    put_pixel(x0,y0,color)
                else:
                    self.put_pixel(x0,y0,color)
            else:
                self.line(x0,y0,x1,y1,color,put_pixel)

    def circle(self, x0, y0, radius, color, fill = False, put_pixel=None ):
        """ draw a circle centered at x0,y0 of radius radius in color """
        points = []

        def circle_point( points, xc,yc,x,y ):
            points.extend([(xc+x, yc+y),(xc-x, yc+y),(xc+x, yc-y),(xc-x, yc-y),(xc+y, yc+x),(xc-y, yc+x),(xc+y, yc-x),(xc-y, yc-x)])

        x0 = int(x0)
        y0 = int(y0)
        radius = int(radius)
        x = 0
        y = radius
        d = 3 - 2 * radius
        circle_point(points,x0,y0,x,y)
        while y >= x:
            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6
            circle_point(points,x0,y0,x,y)

        for idx in range(len(points)):
            x,y = points[idx]
            x = int(((x-x0)*1.5)+x0)
            points[idx] = (x,y)

        if not fill:
            for x,y in points:
                if put_pixel:
                    put_pixel(x,y,color)
                else:
                    self.put_pixel(x,y,color)
        else:
            self.rasterize(points,color,put_pixel)

    def arc(self,x0,y0,radius,a0,a1,color,fill=False,put_pixel=None,just_points=False):
        """ draw an arc between a0 degrees to a1 degrees centered at x0,y0 with radius and color """
        points = []

        def circle_point( points, xc,yc,x,y ):
            points.extend([(xc+x, yc+y),(xc-x, yc+y),(xc+x, yc-y),(xc-x, yc-y),(xc+y, yc+x),(xc-y, yc+x),(xc+y, yc-x),(xc-y, yc-x)])

        x0 = int(x0)
        y0 = int(y0)
        radius = int(radius)
        x = 0
        y = radius
        d = 3 - 2 * radius
        circle_point(points,x0,y0,x,y)
        while y >= x:
            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6
            circle_point(points,x0,y0,x,y)

        xs,ys = angle_point(x0,y0,a0,radius+0.5)
        xe,ye = angle_point(x0,y0,a1,radius+0.5)
        xm,ym = angle_point(x0,y0,(a0+a1)/2,radius+0.5)
        x_min = min(x0,xs,xe,xm)
        y_min = min(y0,ys,ye,ym)
        x_max = max(x0,xs,xe,xm)
        y_max = max(y0,ys,ye,ym)

        # for drawing the previous one was for bounding
        xs,ys = angle_point(x0,y0,a0,radius)
        xe,ye = angle_point(x0,y0,a1,radius)

        filtered_points = []
        for x,y in points:
            px = int(((x-x0)*1.5)+x0)
            if px >= x_min and px <= x_max and y >= y_min and y <= y_max:
                angle = math.degrees(math.atan2(y-y0,x-x0))
                if angle < 0:
                    angle += 360
                if angle >= a0 and angle <= a1:
                    filtered_points.append((px,y))
        points = filtered_points

        if just_points:
            for x,y in points:
                put_pixel(x,y,color)
        else:
            if not fill:
                self.line(x0,y0,xs,ys,color,put_pixel)
                self.line(x0,y0,xe,ye,color,put_pixel)
                for x,y in points:
                    if put_pixel:
                        put_pixel(x,y,color)
                    else:
                        self.put_pixel(x,y,color)
            else:
                def add_pixel( x,y,color ):
                    points.append((x,y))
                self.line(x0,y0,xs,ys,color,add_pixel)
                self.line(x0,y0,xe,ye,color,add_pixel)
                self.rasterize(points,color,put_pixel)

    def rect(self,x0,y0,x1,y1,color,fill=False,put_pixel=None):
        """ draw a rectangle bounding x0,y0, x1,y1, in color == color optionally filling """
        x0 = int(x0)
        x1 = int(x1)
        y0 = int(y0)
        y1 = int(y1)

        if not fill:
            self.line(x0,y0,x0,y1,color)
            self.line(x0,y1,x1,y1,color)
            self.line(x1,y1,x1,y0,color)
            self.line(x1,y0,x0,y0,color)
        else:
            if y1 < y0:
                y=y0
                y0=y1
                y1 = y
            for y in range(y0,y1):
                self.line(x0,y,x1,y,color,put_pixel)

    def textat(self,x,y,color,message):
        """ draw a text message at a coordinate in the color specified """
        x,y = self.round_text_position(x,y)

        height, width = self.from_rowcol(1,len(message))

        if x < 0 or x >self.max_x or y < 0 or y >self.max_y:
            return

        if y + height > self.max_y:
            return

        if x + height > self.max_x:
            clip_height,clip_width = self.to_rowcol(1,(self.max_x-x))
            if clip_width > 0:
                message = message[:clip_width]
            else:
                return

        row,col = self.to_rowcol(x,y)
        self.win.addstr(row,col,message.encode('utf_8'),color)

    def polyline(self,points,color,put_pixel=None):
        """ draw a polyline defined by the sequence points which represent a list of (x,y) tuples in the order they should be connected in color """
        n_points = len(points)
        if n_points == 0:
            return
        elif n_points == 1:
            x,y = points[0]
            if put_pixel:
                put_pixel(x,y,color)
            else:
                self.put_pixel(x,y,color)
        else:
            for idx in range(n_points-1):
                x0,y0 = points[idx]
                x1,y1 = points[idx+1]
                self.line(x0,y0,x1,y1,color,put_pixel)

    def poly_fill(self,points,color,put_pixel = None):
        """ fill a concave polygon by recursively subdividing until we get a convex polygon """
        clips = []

        minX,minY,maxX,maxY = self.get_bounds(points)

        minX = float(minX)
        minY = float(minY)
        maxX = float(maxX)
        maxY = float(maxY)

        midX = (minX+maxX)/2.0
        midY = (minY+maxY)/2.0

        clips.append((minX,minY,midX,midY))
        clips.append((midX,minY,maxX,midY))
        clips.append((midX,midY,maxX,maxY))
        clips.append((minX,midY,midX,maxY))

        while clips:
            minX,minY,maxX,maxY = clips.pop(0)
            if int(minX)==int(maxX) or int(minY)==int(maxY):
                continue

            p = self.clip_polygon(points,minX,minY,maxX,maxY)
            if p:
                if self.is_convex(p):
                    self.polygon(p,color,True,put_pixel)
                else:
                    midX = (minX+maxX)/2.0
                    midY = (minY+maxY)/2.0
                    if midX - minX < 1.0 or midY - minY < 1.0 or maxX - midX < 1.0 or maxY - midY < 1.0:
                        continue
                    clips.append((minX,minY,midX,midY))
                    clips.append((midX,minY,maxX,midY))
                    clips.append((midX,midY,maxX,maxY))
                    clips.append((minX,midY,midX,maxY))

    def polygon(self,points,color,fill=False,put_pixel=None):
        """ draw a polygon defined by the sequence points which represent a list of (x,y) tuples in the order they should be connected in color
        the last point will be connected to the first point. polygons can be filled. """

        if not points:
            return

        convex = True
        if fill:
            convex = self.is_convex(points)

        poly_pixels = []
        def put_poly_pixel(x,y,color):
            poly_pixels.append((x,y))

        i = iter(points)
        first = p1 = next(i,None)
        while p1:
            p2 = next(i,None)
            if p2:
                last = p2
                self.line(p1[0],p1[1],p2[0],p2[1],color,put_poly_pixel)
            else:
                last = p1
                put_poly_pixel(p1[0],p1[1],color)
            p1 = p2
        self.line(first[0],first[1],last[0],last[1],color,put_poly_pixel)

        if not fill:
            for x,y in poly_pixels:
                if put_pixel:
                    put_pixel(x,y,color)
                else:
                    self.put_pixel(x,y,color)
        else:
            if convex:
                self.rasterize( poly_pixels, color, put_pixel)
            else:
                for x,y in poly_pixels:
                    if put_pixel:
                        put_pixel(x,y,color)
                    else:
                        self.put_pixel(x,y,color)
                self.poly_fill(points,color,put_pixel)
