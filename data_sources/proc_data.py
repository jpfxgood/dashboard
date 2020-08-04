# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that aggregates data from system information using psutil and provides a set of data tables """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
import psutil
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized

class AverageCell(Cell):
    def __init__(self,type,value,format):
        self.type = type
        self.value = value
        self.format = format
        self.values = [ value ]

    def put_value(self,value):
        self.values.append(value)
        self.value = sum(self.values)/len(self.values)

class ProcDataTable( DataTable ):
    """ class that collects a time based aggregation of data from system process information into a data_table """
    def __init__(self,num_hours=24,bucket_hours=1,refresh_minutes=10):
        """ Initialize the ProcDataTable to collect system process information, a timespan to aggregate for, aggregation bucket in hours, a refresh interval for updating in minutes """
        self.num_hours = num_hours
        self.bucket_hours = bucket_hours
        DataTable.__init__(self,None,
            "Proc Data: for the last %d hours in %d hour buckets, refreshed every %d minutes"%(
            self.num_hours,
            self.bucket_hours,
            refresh_minutes),refresh_minutes)
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh or rebuild tables """

        current_time = datetime.now()

        column_names = [ "Time Stamps", "CPU Percent", "Load Avg",
            "Total Virtual Memory", "Available Virtual Memory",
            "Filesystem Percent Full", "Filesystem Read Bytes", "Filesystem Write Bytes",
            "Network Sent Bytes","Network Received Bytes","Network Connections" ]

        def bucket_idx( timestamp, column ):
            for idx in range(column.size()):
                if column.get(idx).get_value() >= timestamp:
                    return idx
            else:
                return -1

        def append_bucket( timestamp, column ):
            column.put(column.size(),Cell(date_type,timestamp+timedelta( hours=self.bucket_hours),format_date))
            if column.size() > self.num_hours/self.bucket_hours:
                for cn in column_names:
                    self.get_column(cn).delete(0)
            return column.size()-1

        def add_average( column_name, idx, value ):
            column = self.get_column(column_name)
            if not column.size() or idx >= column.size():
                column.put(idx, AverageCell(float_type,value,format_float))
            else:
                column.get(idx).put_value(value)

        bidx = 0
        for cn in column_names:
            if not self.has_column(cn):
                self.add_column(Column(name=cn))
            if cn == "Time Stamps":
                bidx = bucket_idx( current_time, self.get_column(cn))
                if bidx < 0:
                    bidx = append_bucket( current_time, self.get_column(cn))
            elif cn == "CPU Percent":
                add_average(cn,bidx,psutil.cpu_percent())
            elif cn == "Load Avg":
                add_average(cn,bidx,psutil.getloadavg()[2])
            elif cn == "Total Virtual Memory":
                add_average(cn,bidx,psutil.virtual_memory().total)
            elif cn == "Available Virtual Memory":
                add_average(cn,bidx,psutil.virtual_memory().available)
            elif cn == "Filesystem Percent Full":
                add_average(cn,bidx,psutil.disk_usage("/").percent)
            elif cn == "Filesystem Read Bytes":
                add_average(cn,bidx,psutil.disk_io_counters().read_bytes)
            elif cn == "Filesystem Write Bytes":
                add_average(cn,bidx,psutil.disk_io_counters().write_bytes)
            elif cn == "Network Sent Bytes":
                add_average(cn,bidx,psutil.net_io_counters().bytes_sent)
            elif cn == "Network Recieved Bytes":
                add_average(cn,bidx,psutil.net_io_counters().bytes_recv)
            elif cn == "Network Connections":
                add_average(cn,bidx,float(len(psutil.net_connections())))
        self.changed()

        DataTable.refresh(self)
