# Copyright 2017 James P Goodwin data table package to manage sparse columnar data
""" module that implement a data table package to manage sparse columnar data window and refresh them automatically """
import sys
import os
from datetime import datetime
from dateutil import parser
import threading
import time
import csv
import json
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
    if d >= 1000 and d < 1000000:
        return "%.0fK"%(d/1000)
    elif d >= 1000000 and d < 1000000000:
        return "%.0fM"%(d/1000000)
    elif d >= 1000000000:
        return "%.0fG"%(d/1000000000)
    else:
        return "%.2f"%d

def format_int( d ):
    if d >= 1000 and d < 1000000:
        return "%dK"%(d//1000)
    elif d >= 1000000 and d < 1000000000:
        return "%dM"%(d//1000000)
    elif d >= 1000000000:
        return "%dG"%(d//1000000000)
    else:
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

blank_cell = Cell(blank_type,"",lambda x: "")

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
        if idx <= len(self.values):
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
        if idx < len(self.values):
            self.values[idx] = value
            return
        if idx == len(self.values):
            self.values.append(value)
            return
        elif idx > len(self.values):
            while idx >= len(self.values):
                self.values.append(blank_cell)
            self.values[idx] = value
            return

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

#   format of data table as json
#   {
#       "name" : name of the table,
#       "refresh_minutes" : refresh interval in minutes,
#       "columns" : [ array of column structures
#           {
#           "name": column name
#           "values" : [ array of cells in column
#               {
#               "type" : one of "_string","_float","_int","_date","_blank"
#               "value" : string, float, int, float for date, or "" for blank
#               },
#               ]
#           },
#           ]
#   }
def from_json( stream ):
    """ load a DataTable from a stream as JSON, return new DataTable """
    jtable = json.load(stream)
    dt = DataTable(None,jtable.get("name","JSON DataTable"),jtable.get("refresh_minutes",1))
    for c in jtable["columns"]:
        nc = Column( name = c.get("name", None) )
        for v in c["values"]:
            ct = v["type"]
            cv = v["value"]
            if ct == string_type:
                cc = Cell(string_type,cv,format_string)
            elif ct == float_type:
                cc = Cell(float_type,cv,format_float)
            elif ct == int_type:
                cc = Cell(int_type,cv,format_float)
            elif ct == date_type:
                cc = Cell(date_type,datetime.fromtimestamp(cv),format_date)
            elif ct == blank_type:
                cc = blank_cell
            nc.put(nc.size(),cc)
        dt.add_column( nc )
    return dt

def to_json( dt, stream ):
    """ write a DataTable to a stream as JSON """
    out_dict = {}
    if dt.name:
        out_dict["name"] = dt.name

    out_dict["refresh_minutes"] = dt.refresh_minutes

    columns  = []
    for idx in range(len(dt.columns)):
        dtc = dt.columns[idx]
        column = {}
        if dtc.name:
            column["name"] = dtc.name

        values = []
        for dtv in dtc.values:
            values.append( { "type":dtv.type, "value": ( dtv.value if dtv.type != date_type else dtv.get_float_value() ) } )
        column["values"] = values
        columns.append(column)

    out_dict["columns"] = columns
    json.dump(out_dict,stream)

# csv representation of a DataTable
# heading row at the top
# each column of the form: table name_column name_type names cannot contain '_" and
# types will be used to load cells can't have mixed cell types in a column
def from_csv( stream, name=None, field_map=None ):
    """ load a DataTable from a stream as CSV, return new DataTable, you can provide an override to the default parsing to provide a name and a field_map which is a list of tuples CSV_column_name,DataTable_column_name,DataTable_type it will only load columns in the column map """
    dt = None
    dr = csv.DictReader(stream)
    for drr in dr:
        for drc in drr:
            parts = drc.split("_",2)
            if not dt:
                if name:
                    dt = DataTable(name=name)
                elif not field_map and len(parts) == 3:
                    dt = DataTable(name=parts[0])
                else:
                    dt = DataTable()

            dtc = None
            dtt = None
            if field_map:
                for fm in field_map:
                    if drc == fm[0]:
                        dtc = fm[1]
                        dtt = fm[2]
                        break
            else:
                if len(parts) == 3:
                    dtc = parts[1]
                    dtt = "_"+parts[2]

            if dtc and dtt:
                if not dt.has_column(dtc):
                    dt.add_column(Column(name=dtc))
                dtcc = dt.get_column(dtc)

                drv = drr[drc]
                if drv and dtt == string_type:
                    cc = Cell(string_type,drv,format_string)
                elif drv and dtt == float_type:
                    cc = Cell(float_type,float(drv),format_float)
                elif drv and dtt == int_type:
                    cc = Cell(int_type,int(drv),format_float)
                elif drv and dtt == date_type:
                    try:
                        cc = Cell(date_type,datetime.fromtimestamp(float(drv)),format_date)
                    except:
                        cc = Cell(date_type,parser.parse(drv),format_date)
                elif not drv or dtt == blank_type:
                    cc = blank_cell
                dtcc.put(dtcc.size(),cc)
    return dt

def to_csv( dt, stream ):
    """ write a DataTable to a stream as CSV, see standard format in comments above, type for column is based on the zeroth cell """
    field_names = []
    idx = 0
    max_idx = 0
    for c in dt.columns:
        type = blank_type
        for tidx in range(c.size()):
            if c.get(tidx).type != blank_type:
                type = c.get(tidx).type
                break
        field_names.append((dt.name if dt.name else "DataTable")+"_"+(c.name if c.name else "Column %d"%idx)+type)
        idx += 1
        if c.size() > max_idx:
            max_idx = c.size()
    wcsv = csv.DictWriter(stream,field_names)
    for wcridx in range(max_idx):
        wcr = {}
        for idx in range(len(dt.columns)):
            cell = dt.columns[idx].get(wcridx)
            wcr[field_names[idx]] = (cell.get_value() if cell.type != date_type else cell.get_float_value())
        if wcridx == 0:
            wcsv.writeheader()
        wcsv.writerow(wcr)

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
        self.refresh_timestamp = None
        if columns:
            for c in columns:
                self.add_column(c)

    def get_refresh_timestamp( self ):
        """ get the time that the table was last refreshed """
        return self.refresh_timestamp

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
            time.sleep(1)

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
        if idx == len(self.columns):
            self.columns.append(column)
        else:
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
        self.refresh_timestamp = time.time()
