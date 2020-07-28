# Copyright 2017 James P Goodwin data table package to manage sparse columnar data
""" module that implement a data table package to manage sparse columnar data window """
import sys
import os
import datetime
import threading
import time
from functools import wraps

string_type = '_string'
float_type = '_float'
int_type = '_int'
date_type = '_date'
blank_type = '_blank'

def format_string( s ):
    return str(s)

def format_date( d ):
    return d.strftime("%m/%d/%y %H:%M")

def format_float( d ):
    return "%.2f"%d

def format_int( d ):
    return "%d"%d

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

    def put_value(self,value):
        self.value = value

    def get_float_value(self):
        if self.type in [float_type,int_type]:
            return float(self.value)
        elif self.type == date_type:
            return self.value.timestamp()
        else:
            return 0.0

    def get_format(self):
        return self.format

    def set_format(self,format):
        self.format = format

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

    def delete(self,idx):
        if idx < len(self.values):
            del self.values[idx]

    def ins(self,idx,value):
        if idx < len(self.values):
            self.values.insert(idx,value)
        else:
            self.put(idx,value)

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

def synchronized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.refresh_lock:
            return method(self, *args, **kwargs)
    return wrapper

class DataTable(object):
    def __init__(self,columns=None,name=None,refresh_minutes=10):
        """ accepts a list of columns and a name for the table """
        self.listeners = []
        self.columns = []
        self.name = name
        self.cnames = {}
        self.refresh_lock = threading.RLock()
        self.refresh_minutes = refresh_minutes
        self.refresh_thread = None
        self.refresh_thread_stop = False
        if columns:
            for c in columns:
                self.add_column(c)

    def acquire_refresh_lock(self):
        """ acquire the refresh lock before reading/writing the table state """
        self.refresh_lock.acquire()

    def release_refresh_lock(self):
        """ release the refresh lock after reading/writing the table state """
        self.refresh_lock.release()

    def start_refresh( self ):
        """ Start the background refresh thread """
        self.stop_refresh()
        self.refresh_thread = threading.Thread(target=self.perform_refresh)
        self.refresh_thread.start()

    def perform_refresh( self ):
        """ Thread worker that sleeps and refreshes the data on a schedule """
        start_time = time.time()
        while not self.refresh_thread_stop:
            if time.time() - start_time >= self.refresh_minutes*60.0:
                self.refresh()
                start_time = time.time()
            time.sleep(0)

    def stop_refresh( self ):
        """ Stop the background refresh thread """
        self.refresh_thread_stop = True
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join()
        self.refresh_thread = None
        self.refresh_thread_stop = False

    def listen(self,listen_func):
        """ register for notifications when a change event is raised on this table """
        self.listeners.append(listen_func)

    def unlisten(self,listen_func):
        """ unregister for notifications when a change event is raised on this table """
        self.listeners.remove(listen_func)

    def changed(self):
        """ notify listeners that this table has been changed """
        for f in self.listeners:
            f(self)

    @synchronized
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

    @synchronized
    def get_names(self):
        """ return a list of the names of the columns in order"""
        return [c.get_name() for c in self.columns]

    @synchronized
    def get_columns(self):
        """ return the list of columns """
        return self.columns

    @synchronized
    def add_column(self,column):
        idx = len(self.columns)
        column.set_idx(idx)
        if not column.get_name():
            column.set_name("%s_%d"%(self.name,idx))
        self.columns.append(column)
        self.cnames[column.get_name()] = column
        column.set_table(self)

    @synchronized
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

    @synchronized
    def replace_column(self,idx,column):
        column.set_idx(idx)
        if not column.get_name():
            column.set_name("%s_%d"%(self.name,idx))
        self.columns[idx] = column
        self.cnames[column.get_name()] = column
        column.set_table(self)

    @synchronized
    def map_column(self, reference ):
        if type(reference) == str or type(reference) == str:
            return self.cnames[reference].get_idx()
        elif type(reference) == int:
            return reference
        else:
            raise TypeError("wrong type in mapping")

    @synchronized
    def has_column(self, reference ):
        if type(reference) == str or type(reference) == str:
            return reference in self.cnames
        elif type(reference) == int:
            return idx < len(self.columns)
        else:
            return False

    @synchronized
    def get_column(self, reference):
        return self.columns[self.map_column(reference)]

    @synchronized
    def get(self, row, reference ):
        return self.columns[self.map_column(reference)].get(row)

    @synchronized
    def put(self, row, reference, value):
        self.columns[self.map_column(reference)].put(row,value)

    @synchronized
    def refresh(self):
        """ base class method for forcing a refresh on a table """
        pass
