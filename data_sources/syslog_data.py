# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that aggregates data from the syslog and provides a set of data tables """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized

class SyslogDataTable( DataTable ):
    """ class that collects a time based aggregation of data from the syslog into a data_table """
    def __init__(self,syslog_glob="/var/log/syslog*",num_hours=24,bucket_hours=1,refresh_minutes=10):
        """ Initialize the SyslogDataTable with a file glob pattern to collect the syslogs on this machine, a timespan to aggregate for, aggregation bucket in hours, a refresh interval for updating in minutes """
        self.syslog_glob = syslog_glob
        self.num_hours = num_hours
        self.bucket_hours = bucket_hours
        DataTable.__init__(self,None,
            "Syslog Data: %s for the last %d hours in %d hour buckets, refreshed every %d minutes"%(
            self.syslog_glob,
            self.num_hours,
            self.bucket_hours,
            refresh_minutes),refresh_minutes)
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh or rebuild tables """
        current_time = datetime.now()
        start_time = current_time - timedelta( hours = self.num_hours )
        syslog_files = glob.glob(self.syslog_glob)

        time_column = Column(name="Time Stamps")
        bucket_time = start_time
        idx = 0
        while bucket_time < current_time:
            time_column.put(idx,Cell(date_type,bucket_time,format_date))
            bucket_time = bucket_time + timedelta( hours = self.bucket_hours )
            idx += 1
        time_column.put(idx,Cell(date_type,current_time,format_date))

        def bucket_idx( timestamp ):
            if timestamp < start_time or timestamp > current_time:
                return -1

            for idx in range(time_column.size()):
                if time_column.get(idx).get_value() >= timestamp:
                    return idx
            else:
                return -1

        errors_column = Column(name="Errors by Time")
        warnings_column = Column(name="Warnings by Time")
        messages_column = Column(name="Messages by Time")

        services_column = Column(name="Services")
        errors_service_column = Column(name="Errors by Service")
        warnings_service_column = Column(name="Warnings by Service")
        messages_service_column = Column(name="Messages by Service")

        def service_idx( service ):
            for idx in range(services_column.size()):
                if services_column.get(idx).get_value() == service:
                    return idx
            else:
                return -1

        def put_or_sum( column, idx, value ):
            current_value = 0
            if idx < column.size():
                c = column.get(idx)
                if c.get_type() != blank_type:
                    current_value = int(c.get_value())
            column.put(idx,Cell(int_type,current_value+value,format_int))


        for slf in syslog_files:
            if slf.endswith(".gz"):
                slf_f = gzip.open(slf,"rt",encoding="utf-8")
            else:
                slf_f = open(slf,"r",encoding="utf-8")

            for line in slf_f:
                line = line.strip()
                m = re.match(r"(\w\w\w\s+\d+\s\d\d:\d\d:\d\d)\s[a-z0-9\-]*\s([a-zA-Z0-9\-\_\.]*)[\[\]0-9]*:\s*(.*)",line)
                if m:
                    log_date = re.sub("\s+"," ","%d "%current_time.year + m.group(1))
                    log_process = m.group(2)
                    log_message = m.group(3)
                    log_datetime = datetime.strptime(log_date,"%Y %b %d %H:%M:%S")
                    b_idx = bucket_idx( log_datetime )
                    if b_idx >= 0:
                        s_idx = service_idx( log_process )
                        if s_idx < 0:
                            s_idx = services_column.size()
                            services_column.put(s_idx,Cell(string_type,log_process,format_string))
                        put_or_sum(messages_column,b_idx,1)
                        put_or_sum(messages_service_column,s_idx,1)
                        is_error = re.search("[Ee]rror|ERROR",log_message)
                        is_warning = re.search("[Ww]arning|WARNING",log_message)
                        error_count = 0
                        warning_count = 0
                        if is_error and not is_warning:
                            error_count = 1
                        elif is_warning:
                            warning_count = 1
                        put_or_sum(errors_column,b_idx,error_count)
                        put_or_sum(errors_service_column,s_idx,error_count)
                        put_or_sum(warnings_column,b_idx,warning_count)
                        put_or_sum(warnings_service_column,s_idx,warning_count)

        columns = [time_column,errors_column,warnings_column,messages_column,services_column,
                    errors_service_column,warnings_service_column,messages_service_column]

        for c in columns:
            if self.has_column(c.get_name()):
                self.replace_column(self.map_column(c.get_name()),c)
            else:
                self.add_column(c)

        self.changed()

        DataTable.refresh(self)
