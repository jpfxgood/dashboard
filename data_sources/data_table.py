# Copyright 2017 James P Goodwin data table package to manage sparse columnar data
""" module that implement a data table package to manage sparse columnar data window """
import sys
import os
import datetime

class Cell(object):
    def __init__(self,type,value,format):
        self.type = type
        self.value = value
        self.format = format

    def __str__(self):
        return self.format(self.value)

    def get_type(self):
        return self.type

    def get_value(self):
        return self.value

    def get_format(self):
        return self.format

    def set_format(self,format):
        self.format = format

string_type = '_string'
float_type = '_float'
int_type = '_int'
date_type = '_date'
blank_type = '_blank'
blank_cell = Cell(blank_type,None,lambda x: "")

class ColumnIterator(object):
    def __init__(self,column):
        self.column = column
        self.idx = 0
        self.limit = column.size()

    def __iter__(self):
        return self

    def __next__(self):
        if self.idx >= self.limit:
            raise StopIteration
        ret = self.column.get(self.idx)
        self.idx += 1
        return ret


class Column(object):
    def __init__(self,values=None,idx=0,name=None,table=None):
        """ accept a list of Cell objects, a column index, and a column name, and a table to be a part of """
        self.values = values if values else []
        self.idx = 0
        self.name = name
        self.table = table

    def size(self):
        """ get the size of this column """
        return len(self.values)

    def get(self,idx):
        """ get the cell at index idx in column """
        if idx < len(self.values):
            return self.values[idx]
        else:
            return blank_cell

    def put(self,idx,value):
        """ put a Cell value at index idx in column """
        while idx >= len(self.values):
            self.values.append(blank_cell)
        self.values[idx] = value

    def get_name(self):
        return self.name

    def set_name(self,name):
        self.name = name

    def get_idx(self):
        return self.idx

    def set_idx(self,idx):
        self.idx = idx

    def get_table(self):
        return self.table

    def set_table(self,table):
        self.table = table

blank_column = Column()

class DataTable(object):
    def __init__(self,columns=None,name=None):
        """ accepts a list of columns and a name for the table """
        self.columns = []
        self.name = name
        self.cnames = {}
        if columns:
            for c in columns:
                self.add_column(c)

    def get_bounds(self):
        """ return a tuple (rows,cols) where rows is the maximum number of rows and cols is the maximum number of cols """
        cols = len(self.columns)
        rows = -1
        for c in self.columns:
            size = c.size()
            if rows < 0 or size > rows:
                rows = size
        return (rows,cols)

    def get_name(self):
        """ return the name of the table """
        return self.name

    def get_names(self):
        """ return a list of the names of the columns in order"""
        return [c.get_name() for c in self.columns]

    def get_columns(self):
        """ return the list of columns """
        return self.columns

    def add_column(self,column):
        idx = len(self.columns)
        column.set_idx(idx)
        if not column.get_name():
            column.set_name("%s_%d"%(self.name,idx))
        self.columns.append(column)
        self.cnames[column.get_name()] = column
        column.set_table(self)

    def insert_column(self,idx,column):
        while idx > len(self.columns):
            self.add_column(blank_column)
        if idx == len(self.columns):
            self.add_column(column)
        else:
            if not column.get_name():
                column.set_name("%s_%d"%(self.name,idx))
            self.columns.insert(idx,column)
            self.cnames[column.get_name()] = column
            column.set_table(self)
            while idx < len(self.columns):
                if column.get_name() == "%s_%d"%(self.name,idx-1):
                    column.set_name("%s_%d"%(self.name,idx))
                    self.cnames[column.get_name()] = column
                self.columns[idx].set_idx(idx)
                idx += 1

    def replace_column(self,idx,column):
        column.set_idx(idx)
        if not column.get_name():
            column.set_name("%s_%d"%(self.name,idx))
        self.columns[idx] = column
        self.cnames[column.get_name()] = column
        column.set_table(self)

    def map_column(self, reference ):
        if type(reference) == str or type(reference) == str:
            return self.cnames[reference].get_idx()
        elif type(reference) == int:
            return reference
        else:
            raise TypeError("wrong type in mapping")

    def has_column(self, reference ):
        if type(reference) == str or type(reference) == str:
            return reference in self.cnames
        elif type(reference) == int:
            return idx < len(self.columns)
        else:
            return False

    def get_column(self, reference):
        return self.columns[self.map_column(reference)]

    def get(self, row, reference ):
        return self.columns[self.map_column(reference)].get(row)

    def put(self, row, reference, value):
        self.columns[self.map_column(reference)].put(row,value)

def format_string( s ):
    return str(s)

def format_date( d ):
    return d.strftime("%m/%d/%y %H:%M")

def format_float( d ):
    return "%.2f"%d

def format_int( d ):
    return "%d"%d

def main():
    """ test driver for this module """
    d = DataTable(name="TestTable")
    c = Column(name="Strings")
    for s in range(0,25):
        c.put(s,Cell(string_type,"String_%d"%s, format_string))
    c1 = Column(name="Floats")
    for s in range(0,25):
        c1.put(s,Cell(float_type,float(s*0.25), format_float))
    c2 = Column(name="Dates")
    for s in range(5,20):
        c2.put(s,Cell(date_type,datetime.datetime.now(), format_date))

    d.add_column(c)
    d.add_column(c1)
    d.add_column(c2)

    def print_table(dt):
        rows,cols = dt.get_bounds()

        sys.stdout.write(",".join(dt.get_names()))
        sys.stdout.write("\n")
        for r in range(rows):
            for c in range(cols):
                sys.stdout.write(str(dt.get(r,c)))
                if c+1 < cols:
                    sys.stdout.write(",")
            sys.stdout.write("\n")
        sys.stdout.write("\n")

    print_table(d)

    c3 = Column(name="Ints")
    for s in range(3,21):
        c3.put(s,Cell(int_type,s,format_int))

    d.insert_column(2,c3)

    print_table(d)


if __name__ == '__main__':
    main()
