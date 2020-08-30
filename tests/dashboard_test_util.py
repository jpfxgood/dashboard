import curses
import pprint
import gc
import re
import os
import sys
import subprocess
from io import StringIO,BytesIO
import pytest
import pyodbc
import os
import shutil
import random
from datetime import datetime,timedelta
import keyring
from elasticsearch import Elasticsearch
import shutil

def screen_size( rows, columns ):
    cmd = "resize -s %d %d >/dev/null 2>/dev/null"%(rows,columns)
    subprocess.Popen(cmd,shell=True)
    curses.resizeterm( rows, columns )

def read_str( win, y, x, width ):
    out_str = ''
    for ix in range(x,x+width):
        rc = win.inch(y,ix)
        out_str += chr(rc & curses.A_CHARTEXT)
    return out_str

def match_chr( win, y, x, width, match_chr ):
    for ix in range(x,x+width):
        if match_chr != (win.inch(y,ix) & (curses.A_ALTCHARSET | curses.A_CHARTEXT)):
            return False
    return True

def match_attr( win, y, x, height, width, attr ):
    for iy in range(y,y+height):
        for ix in range(x,x+width):
            rc = win.inch(iy,ix)
            cc = chr(rc & curses.A_CHARTEXT)
            r_attr = (rc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            if not (attr == r_attr) and not cc.isspace():
                return(False)
    return(True)

def match_attr_str( win, y, x, width, attr ):
    return match_attr( win, y, x, 1, width, attr)

def save_snapshot( win, to_file ):
    max_y,max_x = win.getmaxyx()
    to_file.write((max_y).to_bytes(2,byteorder='big'))
    to_file.write((max_x).to_bytes(2,byteorder='big'))
    for iy in range(max_y):
        for ix in range(max_x):
            rc = win.inch(iy,ix)
            to_file.write((rc).to_bytes(4,byteorder='big'))

def load_snapshot( from_file ):
    max_y = int.from_bytes(from_file.read(2),byteorder='big')
    max_x = int.from_bytes(from_file.read(2),byteorder='big')

    snapshot = [[ 0 for f in range(max_x)] for g in range(max_y)]

    for iy in range(max_y):
        for ix in range(max_x):
            snapshot[iy][ix] = int.from_bytes(from_file.read(4),byteorder='big')

    return (max_y,max_x,snapshot)

def compare_snapshot( win, snapshot, ignore=None ):
    max_y,max_x,screen = snapshot
    difference = [[0 for f in range(max_x)] for g in range(max_y)]

    has_differences = False
    for iy in range(max_y):
        for ix in range(max_x):
            if ignore:                  
                skip = False
                for x,y,x1,y1 in ignore:
                    if ix >= x and ix <= x1 and iy >= y and iy <= y1:
                        skip = True
                        break
                if skip:
                    continue
            rc = win.inch(iy,ix)
            r_cc = chr(rc & curses.A_CHARTEXT)
            r_attr = (rc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            sc = screen[iy][ix]
            s_cc = chr(sc & curses.A_CHARTEXT)
            s_attr = (sc & (curses.A_ATTRIBUTES|curses.A_COLOR))&0xFFBFFFFF
            if r_cc != s_cc:
                difference[iy][ix] = difference[iy][ix] | 1
                has_differences = True
            if r_attr != s_attr:
                difference[iy][ix] = difference[iy][ix] | 2
                has_differences = True

    return (max_y,max_x,difference,has_differences)

def view_differences( win, difference,y_offset = 0,x_offset = 0 ):
    d_max_y,d_max_x,d_screen,has_differences = difference

    for iy in range(d_max_y):
        for ix in range(d_max_x):
            s_attr = curses.A_NORMAL
            if d_screen[iy][ix] & 1:
                s_attr = s_attr | curses.A_REVERSE
            if d_screen[iy][ix] & 2:
                s_attr = s_attr | curses.A_STANDOUT
            try:
                if s_attr != curses.A_NORMAL:
                    win.chgat(iy+y_offset,ix+x_offset,1,s_attr)
            except:
                pass
    win.refresh()

def format_differences( max_y,max_x,difference,has_difference ):
    s = StringIO()
    for iy in range(max_y):
        for ix in range(max_x):
            ch = '.'
            if difference[iy][ix] & 1:
                ch = '#'
            if difference[iy][ix] & 2:
                if ch == '#':
                    ch = '@'
                else:
                    ch = '$'
            s.write(ch)
        s.write('\n')
    return s.getvalue()

def prompt( win, message ):
    l = len(message)
    try:
        pwin = curses.newwin(1,l+1,0,0)
        pwin.addstr(0,0,message)
        while True:
            pwin.move(0,0)
            pwin.refresh()
            ch = pwin.getch()
            if ch == ord('Y') or ch == ord('y'):
                return True
            if ch == ord('N') or ch == ord('n'):
                return False
    finally:
        del pwin
        win.touchwin()
        win.refresh()

def dashboard_test_case( win, name, path, ignore = None ):
    create = ( os.environ.get("TEST_CREATE_SNAPSHOT","False") == "True" )
    snap_shot_file = os.path.join(os.path.join(path,"tests/snapshots"),"%s.dmp"%(name))
    win.refresh()
    if os.path.exists(snap_shot_file):
        snapshot = load_snapshot( open(snap_shot_file,"rb") )
        max_y,max_x,difference,has_differences = compare_snapshot( win, snapshot, ignore )
        if has_differences:
            if create:
                backup_win = BytesIO()
                win.putwin(backup_win)
                backup_win.seek(0,0)
                overlay = curses.getwin(backup_win)
                view_differences(overlay,(max_y,max_x,difference,has_differences))
                if prompt(overlay,"%s:Accept these differences?"%name):
                    del overlay
                    win.touchwin()
                    win.refresh()
                    save_snapshot(win,open(snap_shot_file,"wb"))
                    win.clear()
                    return
            assert False, "%s:Screen differences found:\n%s"%(name,format_differences(max_y,max_x,difference,has_differences))
    else:
        if create:
            if prompt(win,"%s:Is this screen correct?"%name):
                save_snapshot(win,open(snap_shot_file,"wb"))
                win.touchwin()
                win.refresh()
                win.clear()
                return
        assert False, "%s:No snapshot found"%name
    win.clear()


@pytest.fixture(scope="function")
def dt_testdir(request,testdir):
    python_path = os.path.dirname(os.path.dirname(request.fspath))
    data_path = os.path.join(python_path,"tests/data")
    snapshot_path = python_path
    spreadsheet_path = os.path.join(data_path,"spreadsheet.csv")
    csv_path = os.path.join(data_path,"test_csv.csv")
    json_path = os.path.join(data_path,"test_json.json")
    syslog_path = os.path.join(str(testdir.tmpdir),"syslog")
    syslog_template_path = os.path.join(data_path,"syslog.template")

    random.seed(82520)
    start_time  = datetime.now().replace(minute=0,second=0,microsecond=0)
    timestamp = start_time
    lines = []
    for line in open(syslog_template_path,"r"):
        line = line[:20] + line[20:].replace("%","%%")
        lines.append(line%(timestamp.strftime("%b"),timestamp.day,timestamp.hour,timestamp.minute,timestamp.second))
        timestamp = timestamp - timedelta(seconds=random.randint(0,300))
    lines.sort()
    syslog_out = open(syslog_path,"w")
    for line in lines:
        print(line,file=syslog_out)
    syslog_out.flush()
    syslog_out.close()

    ssh_path = os.environ.get("SSH_PATH",None)
    ssh_config = os.environ.get("SSH_CONFIG",None)
    if ssh_config:
        shutil.copytree(ssh_config,".ssh")

    db_path = os.environ.get("ODBC_PATH",None)
    username,server,driver,database,port = re.match(r"odbc://([a-z_][a-z0-9_-]*\${0,1})@([^/]*)/([^/]*)/([^:]*):{0,1}(\d*){0,1}",db_path).groups()

    password = keyring.get_password(db_path, username)
    if not password:
        return

    conn = pyodbc.connect("DRIVER={%s};DATABASE=%s;UID=%s;PWD=%s;SERVER=%s;PORT=%s;"%(driver,database,username,password,server,port))
    assert conn != None

    random.seed()
    table_idx_name = ''
    for idx in range(8):
        table_idx_name += random.choice("abcdefghijklmnopqrstuvwxyz")

    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS %s"%table_idx_name)
    cursor.execute("CREATE TABLE %s ( service varchar (18), metric1 int, metric2 int )"%table_idx_name)
    services = ["service_a","service_b","service_c","service_d"]
    idx = 0
    for s in services:
        cursor.execute("INSERT INTO %s VALUES ( ?,?,? )"%table_idx_name,s,idx,idx+5)
        idx = idx + 1
    conn.commit()

    es = Elasticsearch()
    if es.indices.exists(table_idx_name):
        es.indices.delete(table_idx_name)
    es.indices.create(table_idx_name,{ "mappings": { "properties": { "service": { "type":"keyword" },"metric1": {"type":"long"},"metric2": {"type":"long"} }}})
    idx = 0
    for s in services:
        es.index(table_idx_name,{ "service":s,"metric1":idx,"metric2":idx+5 })
        idx = idx + 1
    es.indices.flush(table_idx_name,wait_if_ongoing=True)

    def cleanup_dt_testdir():
        conn.execute("DROP TABLE IF EXISTS %s"%table_idx_name)
        conn.commit()
        conn.close()
        if es.indices.exists(table_idx_name):
            es.indices.delete(table_idx_name)
        shutil.rmtree(".ssh")

    request.addfinalizer(cleanup_dt_testdir)

    return {"python_path" : python_path,
            "data_path" : data_path,
            "spreadsheet_path": spreadsheet_path,
            "csv_path": csv_path,
            "json_path": json_path,
            "syslog_path": syslog_path,
            "local_path": str(testdir.tmpdir),
            "start_time": start_time,
            "table_idx_name": table_idx_name,
            "odbc_path": db_path,
            "ssh_path": ssh_path,
            "snapshot_path": snapshot_path,
            "testdir" : testdir }
