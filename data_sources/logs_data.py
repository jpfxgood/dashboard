# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that aggregates data from a log file and provides a set of data tables """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
import statistics
from dateutil import parser
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized

format_map = { date_type : format_date, int_type : format_int, float_type : format_float, string_type : format_string }

class ActionCell(Cell):
    def __init__(self,type,value,format,action):
        Cell.__init__(type,None,format)
        self.action = action
        self.values = []
        self.put_value(value)

    def default_value(self):
        if self.type == date_type:
            return datetime.now()
        elif self.type == int_type:
            return 0
        elif self.type == float_type:
            return 0.0
        elif self.type == string_type:
            return ""

    def put_value(self,value):
        self.values.append(value)
        try:
            if self.action == "key":
                self.value = value
            elif self.action == "avg":
                self.value = statistics.mean(self.values)
            elif self.action == "mode":
                self.value = statistics.mode(self.values)
            elif self.action == "median":
                self.value = statistics.median(self.values)
            elif self.action == "min":
                self.value = min(self.values)
            elif self.action == "max":
                self.value = max(self.values)
            elif self.action == "sum":
                self.value = sum(self.values)
            elif self.action.startswith("count("):
                regex = self.action.split("(")[1].split(")")[0]
                if re.match(regex,str(value)):
                    if self.value == None:
                        self.value = self.default_value() + 1
                    else:
                        self.value += 1
        except:
            self.value = self.default_value()

class Value():
    """ structure for mapped values """
    def __init__(self,column_name,type,action,value):
        """ initialize the value structure with mapping information and value from log """
        self.column_name = column_name
        self.type = type
        self.action = action
        self.value = value

    def get_value(self):
        """ based on type return the value from the log """
        if self.type == date_type:
            try:
                return datetime.fromtimestamp(float(self.value))
            except:
                return parser.parse(self.value)
        elif self.type == int_type:
            return int(self.value)
        elif self.type == float_type:
            return float(self.value)
        elif self.type == string_type:
            return self.value
        else:
            return str(self.value)

    def to_cell(self):
        """ construct and return a cell based on type, action and value """
        return ActionCell( self.type, self.get_value(), format_map[self.type], action )

class LogDataTable( DataTable ):
    """ class that collects a time based aggregation of data from the syslog into a data_table """
    def __init__(self,log_glob=None,log_map=None,refresh_minutes=10):
        """ Initialize the LogDataTable with a file glob pattern to collect the
        matching logs on this machine, a timespan to aggregate for, aggregation
        bucket in hours, a refresh interval for updating in minutes and a
        log_map of the structure [{
            "line_regex" : "python regex with groups to match columns",
            "num_buckets" : "number of buckets for this key",
            "bucket_size" : "size of a bucket",
            "bucket_type" : "type of buckets",
            "column_map" : [
                [group_number 1..n,
                "Column Name",
                "type one of _int,_float,_string,_date",
                "action one of key,avg,min,max,count(value),mode,median"],
                ...]},...]
        the key action is special and indicates that this is the bucket key for this type of line """
        self.log_glob = log_glob
        self.log_map = log_map
        DataTable.__init__(self,None,
            "LogDataTable: %s, %d buckets, %d size, %s type, %d minutes refresh"%(
                self.log_glob,
                self.num_buckets,
                self.bucket_size,
                self.bucket_type,
                refresh_minutes),
                refresh_minutes)
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh or rebuild tables """

        def get_bucket( line_spec,value ):
            if not self.has_column(value.column_name):
                self.add_column(Column(name=value.column_name))
            bc = self.get_column(value.column_name)
            for idx in range(bc.size())
                if bc.get(idx).get_value() >= value.get_value():
                    break
            else:
                idx = bc.size()
            if idx < bc.size():
                if line_spec.bucket_type == string_type:
                    if bc.get(idx).get_value() != value.get_value():
                        bc.ins(idx,Cell(line_spec.bucket_type,value.get_value(),format_map[line_spec.bucket_type]))
                return idx
            elif idx == 0 and bc.size() > 0:
                diff = bc.get(idx).get_value() - value.get_value()
                if line_spec.bucket_type == date_type:
                    while diff > timedelta(minutes=line_spec.bucket_size):
                        new_bucket = bc.get(idx).get_value() - timedelta(minutes=line_spec.bucket_size)
                        bc.ins(idx,Cell(line_spec.bucket_type,new_bucket,format_map[line_spec.bucket_type]))
                        diff = bc.get(idx).get_value() - value.get_value()
                    return idx
                elif line_spec.bucket_type == string_type:
                    bc.ins(idx,Cell(line_spec.bucket_type,value.get_value(),format_map[line_spec.bucket_type]))
                    return idx
                else:
                    while diff > line_spec.bucket_size:
                        new_bucket = bc.get(idx).get_value() - line_spec.bucket_size
                        bc.ins(idx,Cell(line_spec.bucket_type,new_bucket,format_map[line_spec.bucket_type]))
                        diff = bc.get(idx).get_value() - value.get_value()
                    return idx
            elif idx == bc.size():
                if line_spec.bucket_type == string_type:
                    bc.put(idx,Cell(line_spec.bucket_type,value.get_value(),format_map(line_spec.bucket_type]))
                else:
                    while True:
                        if idx > 0:
                            prev_bucket = bc.get(idx-1).get_value()
                        else:
                            prev_bucket = value.get_value()
    
                        if line_spec.bucket_type == date_type:
                            new_bucket = prev_bucket + timedelta(minutes=line_spec.bucket_size)
                        else:
                            new_bucket = prev_bucket + line_spec.bucket_size
    
                        bc.put(idx,Cell(line_spec.bucket_type,new_bucket,format_map[line_spec.bucket_type]))
                        if value.get_value() < new_bucket:
                            return idx
                        idx = bc.size()

        def put_value( value, bidx ):
            if not self.has_column(value.column_name):
                self.add_column(Column(name=value.column_name))
            cc = self.get_column(value.column_name)
            if bidx < cc.size():
                cc.get(bidx).put_value(value)
            else:
                cc.put(bidx,value.to_cell())

        def prune_buckets( line_spec ):
            for group,column_name,type,action in line_spec.column_map:
                if self.has_column(value.column_name):
                    cc = self.get_column(value.column_name)
                    while cc.size() > line_spec.num_buckets:
                        cc.delete(0)

        log_files = glob.glob(self.log_glob)

        for lf in log_files:
            if lf.endswith(".gz"):
                lf_f = gzip.open(slf,"rt",encoding="utf-8")
            else:
                lf_f = open(slf,"r",encoding="utf-8")

            for line in lf_f:
                line = line.strip()
                for line_spec in self.log_map:
                    m = re.match(line_spec.line_regex,line)
                    if m:
                        values = []
                        key_idx = None
                        for group,column_name,type,action in line_spec.column_map:
                            values.append(Value( column_name, type, action, m.group(group) ))
                            if action == "key":
                                key_idx = len(values)-1
                        bidx = get_bucket(line_spec,values[key_idx])
                        for v in values:
                            if v.action != "key":
                                put_value( value, bidx )
                        prune_buckets(line_spec)

        self.changed()

        DataTable.refresh(self)
