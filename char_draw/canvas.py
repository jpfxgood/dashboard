# Copyright 2017 James P Goodwin chardraw unicode curses based graphics package
""" module that implements a graphics package using block graphics on curses window """
import locale
locale.setlocale(locale.LC_ALL,"")
import curses
import curses.ascii
import sys
import os
import math

def log_message( message ):
    """ write out a message to debug log"""
    print(message, file=open("chardraw.log","a"))

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

    def set_win(self, win ):
        """ point this canvas at a window and initialize things, will blank out the window """
        self.win = win
        self.init_win()

    def init_win(self):
        """ initializes the window and sets up all of the defaults """
        curses.init_pair(1,curses.COLOR_GREEN,curses.COLOR_BLACK)
        curses.init_pair(2,curses.COLOR_RED,curses.COLOR_BLACK)
        curses.init_pair(3,curses.COLOR_CYAN,curses.COLOR_BLACK)
        curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)
        curses.init_pair(5,curses.COLOR_BLACK,curses.COLOR_BLACK)

        self.green = curses.color_pair(1)
        self.red = curses.color_pair(2)
        self.cyan = curses.color_pair(3)
        self.white = curses.color_pair(4)
        self.black = curses.color_pair(5)

        if self.win:
            self.max_y,self.max_x = self.win.getmaxyx()
            self.char_map = [[None] * self.max_y for i in range(self.max_x)]
            self.max_y = self.max_y * 2
            self.max_x = self.max_x * 2
        else:
            self.max_y,self.max_x = (0,0)
            self.char_map = None

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
        mask = self.to_mask[(int(x)%2)+((int(y)%2)*2)]

        if not self.char_map[col][row]:
            current_mask = 0
        else:
            current_mask = self.char_to_mask[self.char_map[col][row]]

        if set:
            self.char_map[col][row] = self.mask_to_char[ mask | current_mask ]
        else:
            self.char_map[col][row] = self.mask_to_char[ mask ^ current_mask ]

        self.win.addstr(row,col,self.char_map[col][row].encode('utf_8'),color)

    def line(self, x0, y0, x1, y1, color, put_pixel=None ):
        """ draw a line between x0,y0 and x1,y1 in color """
        x0 = int(x0)
        x1 = int(x1)
        y0 = int(y0)
        y1 = int(y1)

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if put_pixel:
                    put_pixel(x,y,color)
                else:
                    self.put_pixel(x, y, color)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if put_pixel:
                    put_pixel(x,y,color)
                else:
                    self.put_pixel(x, y, color)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        if put_pixel:
            put_pixel(x, y, color)
        else:
            self.put_pixel(x,y,color)

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

#        log_message("clip_polygon [%s] %.2f,%.2f,%.2f,%.2f %d"%(",".join([str(p) for p in points]),float(minX),float(minY),float(maxX),float(maxY),dir))

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
#            if out_points:
#                log_message("clip_polygon return [%s] %.2f,%.2f,%.2f,%.2f %d"%(",".join([str(p) for p in out_points]),float(minX),float(minY),float(maxX),float(maxY),dir))
#            else:
#                log_message("clip_polygon return None %.2f,%.2f,%.2f,%.2f %d"%(float(minX),float(minY),float(maxX),float(maxY),dir))
            return out_points if out_points else None


    def rasterize( self, points, color, put_pixel=None):
        """ sort points representing the boundary of a filled shape and rasterize by filling lines with color """
        ps = sorted(points,key=lambda x: (x[1],x[0]))
        sp = iter(ps)
        p2 = p1 = next(sp,None)
        si = 0
        last = None
        while p2:
            last = p2
            p2 = next(sp,None)
            if not p2:
                if put_pixel:
                    put_pixel(p1[0],p1[1],color)
                else:
                    self.put_pixel(p1[0],p1[1],color)
            else:
                if p2[1] == p1[1]:
                    continue
                else:
                    self.line(p1[0],p1[1],last[0],last[1],color,put_pixel)
                    p1 = p2



    def circle(self, x0, y0, radius, color, fill = False, put_pixel=None ):
        """ draw a circle centered at x0,y0 of radius radius in color """
        x0 = int(x0)
        y0 = int(y0)
        radius = int(radius)

        f = 1 - radius
        ddf_x = 1
        ddf_y = -2 * radius
        x = 0
        y = radius

        points = []
        def putpoint( xp, yp ):
            points.append((xp,yp))

        putpoint(x0, y0 + radius)
        putpoint(x0, y0 - radius)
        putpoint(x0 + radius, y0)
        putpoint(x0 - radius, y0)

        while x < y:
            if f >= 0:
                y -= 1
                ddf_y += 2
                f += ddf_y
            x += 1
            ddf_x += 2
            f += ddf_x
            putpoint(x0 + x, y0 + y)
            putpoint(x0 - x, y0 + y)
            putpoint(x0 + x, y0 - y)
            putpoint(x0 - x, y0 - y)
            putpoint(x0 + y, y0 + x)
            putpoint(x0 - y, y0 + x)
            putpoint(x0 + y, y0 - x)
            putpoint(x0 - y, y0 - x)

        if not fill:
            for x,y in points:
                if put_pixel:
                    put_pixel(x,y,color)
                else:
                    self.put_pixel(x,y,color)
        else:
            self.rasterize(points,color,put_pixel)

    def arc(self,x0,y0,radius,a0,a1,color,fill=False,put_pixel=False):
        """ draw an arc between a0 degrees to a1 degrees centered at x0,y0 with radius and color """
        def circle_point(x0,y0,a,radius):
            return (x0+math.cos(math.radians(a))*radius, y0+math.sin(math.radians(a))*radius)

        bounds = []
        for a in [0,90,180,270]:
            bounds.append(circle_point(x0,y0,a,radius))

        boxes = []
        a = a0
        qa = int(a/90)
        qa1 = int(a1/90)
        p1 = circle_point(x0,y0,a1,radius)
        while a < a1:
            p = circle_point(x0,y0,a,radius)
            if qa == qa1:
                boxes.append((min(p[0],p1[0]),min(p[1],p1[1]),max(p[0],p1[0]),max(p[1],p1[1])))
            else:
                bp = bounds[(qa+1)%4]
                boxes.append((min(p[0],bp[0]),min(p[1],bp[1]),max(p[0],bp[0]),max(p[1],bp[1])))
            qa += 1
            a = qa*90

        px0 = ax0 = x0+math.cos(math.radians(a0))*radius
        px1 = ax1 = x0+math.cos(math.radians(a1))*radius
        py0 = ay0 = y0+math.sin(math.radians(a0))*radius
        py1 = ay1 = y0+math.sin(math.radians(a1))*radius

        if ax0 > ax1:
            ax = ax1
            ax1 = ax0
            ax0 = ax

        if ay0 > ay1:
            ay = ay1
            ay1 = ay0
            ay0 = ay

        circle_points = []
        arc_points = []
        def put_circle_pixel(x,y,color):
            circle_points.append((x,y))

        def put_arc_pixel(x,y,color):
            arc_points.append((x,y))

        def dist(x1,y1,x2,y2):
            return abs(x2-x1)**2+abs(y2-y1)**2

        def inboxes(x,y,boxes):
            for b in boxes:
                if x >= b[0] and x <= b[2] and y >= b[1] and y <= b[3]:
                    return True
            return False

        min_d0 = -1.0
        min_d1 = -1.0
        rx0 = 0.0
        ry0 = 0.0
        rx1 = 0.0
        ry1 = 0.0
        self.circle(x0,y0,radius,color,False,put_circle_pixel)
        for x,y in circle_points:
            if inboxes(x,y,boxes):
                put_arc_pixel(x,y,color)
                d0 = dist(x,y,px0,py0)
                d1 = dist(x,y,px1,py1)
                if min_d0 < 0 or d0 < min_d0:
                    min_d0 = d0
                    rx0 = x
                    ry0 = y
                if min_d1 < 0 or d1 < min_d1:
                    min_d1 = d1
                    rx1 = x
                    ry1 = y
        if arc_points:
            self.line(x0,y0,rx0,ry0,color,put_arc_pixel)
            self.line(x0,y0,rx1,ry1,color,put_arc_pixel)
            if fill:
                self.rasterize(arc_points,color,put_pixel)
            else:
                for x,y in arc_points:
                    self.put_pixel(x,y,color,put_pixel)

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
        x = int(x)
        y = int(y)

        if x < 0 or x >self.max_x or y < 0 or y >self.max_y:
            return
        row,col = self.to_rowcol(x,y)
        self.win.addstr(row,col,message.encode('utf_8'),color)

    def polyline(self,points,color,put_pixel=None):
        """ draw a polyline defined by the sequence points which represent a list of (x,y) tuples in the order they should be connected in color """
        i = iter(points)
        p1 = next(i,None)
        while p1:
            p2 = next(i,None)
            if p2:
                self.line(p1[0],p1[1],p2[0],p2[1],color,put_pixel)
            else:
                if put_pixel:
                    put_pixel(p1[0],p1[1],color)
                else:
                    self.put_pixel(p1[0],p1[1],color)
            p1 = p2

    def poly_fill(self,points,color,put_pixel = None):
        """ fill a concave polygon by recursively subdividing until we get a convex polygon """
#        log_message("poly_fill() [%s]"%(",".join([str(p) for p in points])))
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

#        log_message("polygon() [%s] convex=%s"%(",".join([str(p) for p in points]),str(convex)))

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

def main(stdscr):
    """ test driver for the chardraw """
    curses.init_pair(1,curses.COLOR_GREEN,curses.COLOR_BLACK)
    curses.init_pair(2,curses.COLOR_RED,curses.COLOR_BLACK)
    curses.init_pair(3,curses.COLOR_CYAN,curses.COLOR_BLACK)
    curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)

    c = Canvas(stdscr)
#    log_message("Intersection (%d,%d)"%c.intersect((10,10,50,10),(20,5,20,15)))
#    log_message("Convex %s"%str(c.is_convex([(50,50),(55,55),(55,60),(50,60),(40,55)])))
#    log_message("Convex %s"%str(c.is_convex([(50,50),(55,55),(55,60),(50,60),(40,55),(45,57)])))
#    c.put_pixel(0,0,c.green)
#    c.put_pixel(1,1,c.green)
#    c.put_pixel(2,2,c.green)
#    c.put_pixel(2,3,c.green)
#    c.put_pixel(3,2,c.green)
#    c.line(0,0,24,30,c.red)
#    c.line(24,30,100,10,c.red)
#    c.line(24,30,18,20,c.red)
#    c.line(24,30,18,100,c.red)
#    c.circle(20,20,10,c.cyan,False)
#    c.circle(40,40,10,c.white,True)
#    c.rect(50,50,60,60,c.green,False)
#    c.rect(50,40,60,50,c.red,True)
#    c.textat(50,40,c.white,"Red Square")
#    c.arc(50,50,20,10.0,290.0,c.green,True)
#    c.arc(50,50,20,288.0,360.0,c.white,True)
#    c.arc(50,50,20,10.0,50.0,c.cyan,False)
#    c.arc(50,50,20,50.0,120.0,c.red,False)
#    c.polygon([(20,20),(25,25),(25,30),(20,30)],c.cyan,False)
    c.polygon([(50,50),(55,55),(55,60),(50,60),(40,55)],c.red,True)
#    p = [(50,50),(55,55),(55,60),(50,60),(40,55),(45,57)]
#    k = [(x*2-50,y*2-50) for x,y in p]
#    l = [(x+100,y) for x,y in k]
#    c.polygon(k,c.red,False)
#    c.polygon(l,c.green,True)
    c.refresh()
    eval(input())

if __name__ == '__main__':
    curses.wrapper(main)
