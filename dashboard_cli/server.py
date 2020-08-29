import locale
locale.setlocale(locale.LC_ALL,"")
import sys
import os
import json
import time
from io import StringIO
from data_sources.data_table import to_json,from_json
from dashboard_cli.config import load_table

def server( options, args ):
    """ run as a data table server and respond to commands read from stdin """
    tables = {}
    try:
        while True:
            line = sys.stdin.readline()
            if line.startswith("table"):
                command,json_blob = line.strip().split(":",1)
                td = json.loads(json_blob.strip())
                tables[td["name"]] = load_table(td)
                print("loaded:%s"%(td["name"]))
            elif line.startswith("refresh"):
                command,name = line.strip().split(":",1)
                tables[name].refresh()
                table_json = StringIO()
                to_json(tables[name],table_json)
                print("%s:%s"%(name,table_json.getvalue()))
            elif line.startswith("get"):
                command,name = line.strip().split(":",1)
                table_json = StringIO()
                to_json(tables[name],table_json)
                print("%s:%s"%(name,table_json.getvalue()))
            elif line.startswith("exit"):
                break
            time.sleep(1)
    finally:
        for k in tables:
            tables[k].stop_refresh()
    return 0
