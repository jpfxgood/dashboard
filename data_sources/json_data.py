# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that reads a JSON file from disk forms the result into a data table """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
import keyring
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized,from_json

class JSONDataTable( DataTable ):
    """ class that collects data from a JSON file on disk of the form written by data_sources.data_table.to_json() and updates this table with it """
    def __init__(self, json_spec = None ):
        """ Initialize the JSONDataTable object from the file named in json_spec, refresh minutes will come from the loaded json """
        self.json_spec = json_spec
        DataTable.__init__(self,None,"JSONDataTable",120)
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh the table by opening the JSON file and loading it into a table """
        dt = from_json(open(self.json_spec,"r"))
        if dt:
            rows,cols = dt.get_bounds()
            for idx in range(cols):
                self.replace_column(idx,dt.get_column(idx))

            if dt.get_name():
                self.name = dt.get_name()

            self.refresh_minutes = dt.refresh_minutes

            self.changed()
            DataTable.refresh(self)
