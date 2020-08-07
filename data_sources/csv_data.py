# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that reads a csv file from disk forms the result into a data table based on a column mapping """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
import keyring
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized,from_csv


class CSVDataTable( DataTable ):
    """ class that collects data from a CSV file on disk and extracts columns based on a column map of  the form [[CSV_column_name, DataTable_column_name,DataTable_type (one of _string,_int,_float,_date )],...] """
    def __init__(self, refresh_minutes=1, csv_spec = None, csv_map= None, csv_name= None ):
        """ Initialize the CSVDataTable object from the file named in csv_spec and extract the columns in the provided csv_map, name the table based on the name provided or extracted from the CSV """
        self.csv_spec = csv_spec
        self.csv_map = csv_map
        self.csv_name = csv_name
        DataTable.__init__(self,None,(csv_name if csv_name else "CSVDataTable"),refresh_minutes)
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh the table by opening the csv file and loading it into a table """
        dt = from_csv(open(self.csv_spec,"r"),self.name,self.csv_map)
        if dt:
            rows,cols = dt.get_bounds()
            for idx in range(cols):
                self.replace_column(idx,dt.get_column(idx))

            if dt.get_name():
                self.name = dt.get_name()

            self.changed()
            DataTable.refresh(self)
