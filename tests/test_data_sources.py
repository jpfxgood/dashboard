from data_sources.syslog_data import SyslogDataTable
from data_sources.proc_data import ProcDataTable
from data_sources.elastic_data import ElasticsearchDataTable
from data_sources.remote_data import RemoteDataTable,shutdown_connection_manager
from data_sources.odbc_data import ODBCDataTable
from data_sources.json_data import JSONDataTable
from data_sources.csv_data import CSVDataTable
from data_sources.logs_data import LogDataTable
from data_sources.data_table import DataTable,Column,Cell,ColumnIterator,string_type,float_type,int_type,date_type,blank_type,format_string,format_date,format_float,format_int,blank_cell
import curses
import curses.ascii
import os
import time
from datetime import datetime,timedelta
from dashboard_test_util import dt_testdir

def test_Cell():
    c = Cell(string_type,"Test Value",format_string)
    assert c.get_type() == string_type
    assert c.get_format() == format_string
    assert c.get_value() == "Test Value"
    assert str(c) == "Test Value"

    c = Cell(float_type,10.53,format_float)
    assert c.get_value() == 10.53
    assert c.get_float_value() == 10.53
    assert str(c) == "10.53"

    c.put_value( 22.32 )
    c.set_format( lambda x: "$%.0f"%x )
    assert c.get_value() == 22.32
    assert c.get_float_value() == 22.32
    assert str(c) == "$22"

    c = Cell(int_type,10,format_int)
    assert c.get_value() == 10
    assert c.get_float_value() == 10.00
    assert str(c) == "10"

    c = Cell(date_type,datetime(2020,8,26,7,51,0),format_date)
    assert c.get_value() == datetime(2020,8,26,7,51,0)
    assert c.get_float_value() == datetime(2020,8,26,7,51,0).timestamp()
    assert str(c) == "08/26/20 07:51"

def test_Column():
    cc = Column(name="Test Column")
    for idx in range(0,10):
        cc.put(idx,Cell(int_type,idx,format_int))

    for idx in range(0,10):
        assert cc.get(idx).get_value() == idx

    assert cc.size() == 10
    cc.delete(5)
    assert cc.size() == 9
    assert cc.get(5).get_value() == 6
    cc.ins(8,Cell(int_type,27,format_int))
    assert cc.get(8).get_value() == 27 and cc.get(9).get_value() == 9
    assert cc.get_name() == "Test Column"
    cc.set_name("New Name")
    assert cc.get_name() == "New Name"
    cc.put(34,Cell(int_type, 100, format_int))
    assert cc.get(34).get_value() == 100
    assert cc.get(33) == blank_cell
    assert cc.size() == 35

def test_DataTable():
    column_names = ["Test Column 1","Test Column 2","Test Column 3","Test Column 4","Test Column 5" ]

    dt = DataTable(name="Test Data Table",refresh_minutes=0.0167)

    for cn in column_names:
        dt.add_column(Column(name=cn))

    for cn in column_names:
        assert dt.get_column(cn).get_name() == cn

    base_v = 0
    for cn in column_names:
        for v in range(0,10):
            dt.put(v,cn,Cell(int_type,v+base_v,format_int))
        base_v += 11

    base_v = 0
    for cn in column_names:
        for v in range(0,10):
            assert dt.get(v,cn).get_value() == v+base_v
        base_v += 11

    assert not dt.has_column("Bad Column")
    assert dt.has_column(column_names[1])
    assert dt.map_column(column_names[1]) == 1

    cols = dt.get_columns()
    for c in cols:
        assert c.get_name() in column_names
    assert len(cols) == len(column_names)

    names = dt.get_names()
    for cn in column_names:
        assert cn in names
    assert len(names) == len(column_names)

    rows,cols = dt.get_bounds()
    assert rows == 10 and cols == len(column_names)

    nc = Column(name="Test Column 2.5")
    for v in range(0,10):
        nc.put(v,Cell(int_type,v,format_int))

    dt.insert_column(2,nc)
    rows,cols = dt.get_bounds()
    assert rows == 10 and cols == len(column_names)+1
    assert dt.has_column("Test Column 2.5")
    assert dt.map_column("Test Column 2.5") == 2

    for v in range(0,10):
        assert dt.get(v,"Test Column 2.5").get_value() == v

    nc = Column(name="Test Column 2.6")
    for v in range(20,30):
        nc.put(v,Cell(int_type,v,format_int))

    dt.replace_column(2,nc)
    assert rows == 10 and cols == len(column_names)+1
    assert not dt.has_column("Test Column 2.5")
    assert dt.has_column("Test Column 2.6")
    assert dt.map_column("Test Column 2.6") == 2

    for v in range(20,30):
        assert dt.get(v,"Test Column 2.6").get_value() == v

    cl = dt.get_column("Test Column 2")
    assert cl.get_name() == "Test Column 2"

    v = 11
    for cell in ColumnIterator(cl):
        assert cell.get_value() == v
        v = v + 1

    test_DataTable.changed = False
    def change_listener(data_table):
        test_DataTable.changed = True

    dt.listen(change_listener)
    dt.changed()
    assert test_DataTable.changed
    test_DataTable.changed = False
    dt.unlisten(change_listener)
    dt.changed()
    assert not test_DataTable.changed

    dt.refresh()
    timestamp = dt.get_refresh_timestamp()

    dt.start_refresh()
    time.sleep(5)
    dt.stop_refresh()
    new_timestamp = dt.get_refresh_timestamp()

    assert timestamp != new_timestamp

def test_JSONDataTable(dt_testdir):
    jdt = JSONDataTable( dt_testdir["json_path"] )
    assert jdt.get_name() == "Syslog Data: /var/log/syslog* for the last 24 hours in 1 hour buckets, refreshed every 10 minutes"
    assert jdt.get_bounds() == (25,8)
    assert str(jdt.get(0,'Time Stamps')) == "08/05/20 10:38"
    assert str(jdt.get(24,'Time Stamps')) == "08/06/20 10:38"
    assert str(jdt.get(0,'Services')) == "metricbeat"
    assert str(jdt.get(21,'Services')) == "apport"
    assert str(jdt.get(13,'Errors by Time')) == "2.00"

def test_CSVDataTable(dt_testdir):
    cdt = CSVDataTable( 1, dt_testdir["csv_path"] )
    assert cdt.get_name() == "Syslog Data: /var/log/syslog* for the last 24 hours in 1 hour buckets, refreshed every 10 minutes"
    assert cdt.get_bounds() == (25,8)
    assert str(cdt.get(0,'Time Stamps')) == "08/05/20 10:38"
    assert str(cdt.get(24,'Time Stamps')) == "08/06/20 10:38"
    assert str(cdt.get(0,'Services')) == "metricbeat"
    assert str(cdt.get(21,'Services')) == "apport"
    assert str(cdt.get(13,'Errors by Time')) == "2.00"

def test_SyslogDataTable(dt_testdir):
    st = dt_testdir["start_time"]
    sdt = SyslogDataTable( dt_testdir["syslog_path"],start_time=[st.year,st.month,st.day,st.hour,st.minute,st.second])
    column_names = ["Time Stamps","Errors by Time","Warnings by Time","Messages by Time","Services","Errors by Service","Warnings by Service","Messages by Service" ]
    for cn in column_names:
        assert sdt.has_column(cn)
    assert sdt.get(13,"Errors by Time").get_value() == 4
    assert sdt.get(14,"Warnings by Time").get_value() == 1
    assert sdt.get(15,"Messages by Time").get_value() == 23
    assert sdt.get(0,"Services").get_value() == "systemd"
    assert sdt.get(1,"Errors by Service").get_value() == 30
    assert sdt.get(15,"Warnings by Service").get_value() == 3
    assert sdt.get(0,"Messages by Service").get_value() == 60


def test_LogDataTable(dt_testdir):
    ldt = LogDataTable(dt_testdir["syslog_path"],[{
            "line_regex": "(\\w\\w\\w\\s+\\d+\\s\\d\\d:\\d\\d:\\d\\d)\\s[a-z0-9\\-]*\\s([a-zA-Z0-9\\-\\_\\.]*)[\\[\\]0-9]*:\\s*(.*)",
            "num_buckets" : 24,
            "bucket_size" : 60,
            "bucket_type" : "_date",
            "column_map" : [ [ 1,"Time Stamps","_date","key" ], [3,"Starts by Time","_int","count(.*[Ss]tart.*)"], [3,"Stops by Time","_int","count(.*[Ss]top.*)"]]
            }],
            [1,0,0],
            1)
    column_names = ["Time Stamps","Starts by Time","Stops by Time"]
    for cn in column_names:
        assert ldt.has_column(cn)

    rows,cols = ldt.get_bounds()
    total_starts = 0
    total_stops = 0
    for idx in range(rows):
        total_starts += ldt.get(idx,"Starts by Time").get_float_value()
        total_stops += ldt.get(idx,"Stops by Time").get_float_value()
    assert total_starts == 38 and total_stops == 8

def test_ODBCDataTable(dt_testdir):
    odt = ODBCDataTable(1,dt_testdir["odbc_path"],"select * from %s"%dt_testdir["table_idx_name"],[["service","Service"],["metric1","First Metric"],["metric2","Second Metric"]])
    column_names = ["Service","First Metric","Second Metric"]
    for cn in column_names:
        assert odt.has_column(cn)

    services = ["service_a","service_b","service_c","service_d"]
    assert odt.get_column("Service").size() == 4
    for idx in range(4):
        service = odt.get(idx,"Service").get_value()
        v = services.index(service)
        assert odt.get(idx,"First Metric").get_value() == v and odt.get(idx,"Second Metric").get_value() == v+5

def test_ElasticsearchDataTable(dt_testdir):
    odt = ElasticsearchDataTable(1,dt_testdir["table_idx_name"],{},[["hits.hits._source.service","Service","string"],["hits.hits._source.metric1","First Metric","int"],["hits.hits._source.metric2","Second Metric","int"]])
    time.sleep(1)
    odt.refresh()

    column_names = ["Service","First Metric","Second Metric"]
    for cn in column_names:
        assert odt.has_column(cn)

    services = ["service_a","service_b","service_c","service_d"]
    assert odt.get_column("Service").size() == 4
    for idx in range(4):
        service = odt.get(idx,"Service").get_value()
        v = services.index(service)
        assert odt.get(idx,"First Metric").get_value() == v and odt.get(idx,"Second Metric").get_value() == v+5

def test_RemoteDataTable(dt_testdir):
    rdt = RemoteDataTable(dt_testdir["ssh_path"],{"name": "syslog", "type": "SyslogDataTable", "refresh_minutes": 1},"Remote Table",0.0833)

    try:
        column_names = ["Time Stamps","Errors by Time","Warnings by Time","Messages by Time","Services","Errors by Service","Warnings by Service","Messages by Service" ]
        for cn in column_names:
            assert rdt.has_column(cn)

        rows,cols = rdt.get_bounds()
        non_blank = False
        for row in range(rows):
            for col in range(cols):
                if rdt.get(row,col) != blank_cell:
                    non_blank = True
                    break
            if non_blank:
                break

        assert non_blank
    finally:
        shutdown_connection_manager()

def test_ProcDataTable():
    pdt = ProcDataTable(1,1/60,1/60)
    column_names = [ "Time Stamps", "CPU Percent", "Load Avg",
        "Total Virtual Memory", "Available Virtual Memory",
        "Filesystem Percent Full", "Filesystem Read Bytes", "Filesystem Write Bytes",
        "Network Sent Bytes","Network Received Bytes","Network Connections" ]

    for cn in column_names:
        assert pdt.has_column(cn)
        
    time.sleep(1)
    pdt.refresh()

    for cn in column_names:
        assert pdt.get(0,cn) != blank_cell
