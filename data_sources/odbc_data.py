# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that performs a sql query on an odbc database and forms the result into a data table """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
import pyodbc
import keyring
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized


class ODBCDataTable( DataTable ):
    """ class that collects data from the response to a specific sql query on an odbc connected database and populates tables based on a field map """
    def __init__(self,refresh_minutes=1,sql_spec=None,sql_query=None,sql_map=None):
        """ Initalize the ODBCDataTable object pass in a sql_spec to connect to the database of the form odbc://user@server/driver/database:port, a sql_query to be executed, and a field map of the form [[sql_column_name, data_table_column_name],..] indicating the columns to collect from the result """
        self.sql_spec = sql_spec
        self.sql_query = sql_query
        self.sql_map = sql_map
        DataTable.__init__(self,None,
            "ODBCDataTable query:%s,database:%s,fieldmap:%s,refreshed every %d minutes"%(
            sql_query,sql_spec,sql_map,refresh_minutes),
            refresh_minutes)

        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh the table from the query """
        username,server,driver,database,port = re.match(r"odbc://([a-z_][a-z0-9_-]*\${0,1})@([^/]*)/([^/]*)/([^:]*):{0,1}(\d*){0,1}",self.sql_spec).groups()

        password = keyring.get_password(self.sql_spec, username)
        if not password:
            return

        conn = pyodbc.connect("DRIVER={%s};DATABASE=%s;UID=%s;PWD=%s;SERVER=%s;PORT=%s;"%(driver,database,username,password,server,port))
        if not conn:
            return

        result = conn.execute(self.sql_query)

        for row in result:
            for sql_column,data_column in self.sql_map:
                value = getattr(row,sql_column)
                if not self.has_column(data_column):
                    self.add_column(Column(name=data_column))
                c = self.get_column(data_column)
                if isinstance(value,datetime):
                    cc = Cell(date_type,value,format_date)
                elif isinstance(value,int):
                    cc = Cell(int_type,value,format_int)
                elif isinstance(value,float):
                    cc = Cell(float_type,value,format_float)
                elif isinstance(value,str):
                    cc = Cell(string_type,value,format_string)
                else:
                    cc = Cell(string_type,str(value),format_string)
                c.put(c.size(),cc)

        self.changed()
        DataTable.refresh(self)
