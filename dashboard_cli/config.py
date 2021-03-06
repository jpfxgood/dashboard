import locale
locale.setlocale(locale.LC_ALL,"")
import json
from dashboard.dashboard import Dashboard,Page,Panel
from char_draw.graph import LineGraph,BarGraph,PieGraph,TableGraph
from data_sources.syslog_data import SyslogDataTable
from data_sources.proc_data import ProcDataTable
from data_sources.elastic_data import ElasticsearchDataTable
from data_sources.remote_data import RemoteDataTable,shutdown_connection_manager
from data_sources.odbc_data import ODBCDataTable
from data_sources.json_data import JSONDataTable
from data_sources.csv_data import CSVDataTable
from data_sources.logs_data import LogDataTable
from data_sources.data_table import to_json,from_json
import importlib.util

data_table_plugins = {}
graph_plugins = {}

# A config file is of the form:
# {
#   "tables" : list of table objects describing the data sources to be graphed in the dashboard below
#       [
#           {
#           "name" : name to refer to this table below,
#           "type" : one of "SyslogDataTable","ProcDataTable","ElasticsearchDataTable","RemoteDataTable","ODBCDataTable","CSVDataTable","JSONDataTable","LogDataTable" ( more to come),
#           "refresh_minutes" : number of minutes to automatically refresh optional, 0 if only manual, default is 5 minutes
#           "num_hours" : number of hours of history to look at
#           "bucket_hours" : number of hours per bucket, table will have num_hours/bucket_hours entries
#           "syslog_glob" : full unix glob pattern to match syslogs for the SyslogDataTable
#           "es_index_pattern" : only for ElasticsearchDataTable, Elasticsearch index pattern wildcard to query
#           "es_query_body" : { body of the query to execute as well formed JSON Elasticsearch DSL },
#           "es_field_map" : [ array of tuples [ json_path ex "aggregations.3.buckets.key" matching the value you want, column name to append it to in the table, value type one of int,float,str,or date where date is a timestamp numerical value ]...]
#           "ssh_spec" : for the RemoteDataTable a string of the form ssh://username@hostname:port to connect to the remote system
#           "table_def" : for the RemoteDataTable one of these table definitions, defines the remote table to populate, assumes local keyring has credentials for user at hostname
#           "sql_spec" : for the ODBCDataTable, a string of the following form to specify a connection to an odbc database odbc://username@server/driver/database:port, assumes local keyring has credentials at this spec so something like 'keyring set odbc://james@localhost/myodbc8w/james:5432 james',
#           "sql_query" : for the ODBCDataTable, a sql query to execute on that database,
#           "sql_map" : for the ODBCDataTable, a list of tuples of the form [[sql_column_name,data_table_column_name],...] only these columns will be mapped into the table
#           "csv_spec" : for the CSVDataTable, path to CSV file to read,
#           "csv_map" : for the CSVDataTable, column specification of the form [["csv_column_name","data_table_column_name","type one of _int,_float,_string,_date"],...] only imports matching columns,
#           "json_spec" : for the JSONDataTable path to a JSON file to read, assumed to be in the format written by the data_sources.data_table.to_json function,
#           "log_glob" : for the LogDataTable, glob of log files to read, can include compressed logs in .gz format,
#           "log_map" : for the LogDataTable, list of line specifications of the form:
#                    [ { "line_regex" : "escaped python regex with a group per field to extract",
#                        "num_buckets" : number of buckets to aggregate in,
#                        "bucket_size" : for integer and float buckets it is just the literal size, for strings it is ignored and the last num_buckets strings will form the buckets, for dates it is the number of minutes,
#                        "bucket_type" : one of "_string","_date","_int","_float",
#                        "column_map: [ [ regex group number 1..n, "Data Table Column Name", "type as above","action, one of key,min,max,avg,sum,median,mode, count(regex), key is special and indicates the bucket key, count matches the regex and the value of the column is the number of matches in the bucket
#                       },...repeated matches with different keys can collect other aggregations and also handle different types of lines
#                    ],
#           "log_lookback" : a tuple of the number of days, hours, minutes to look back at logs [ days, hours, minutes ] all must be specified
#           },
#       ],
#   "dashboard": definition of the dashboard to present
#       {
#       "auto_tour_delay" : integer seconds or 0 for no tour,
#       "pages" : list of page objects defining pages of dashboard
#           [
#               {
#                   "height" : height in characters, optional, -1 if not provided indicating to fill initial window,
#                   "width" : width in characters, optional, -1 if not provided indicating to fill initial window,
#                   "panels" : list of panel objects defining how this page is divided up
#                       [
#                           {
#                           "y" : vertical offset in page in characters optional, -1 if not provided saying to have the container lay out the panel,
#                           "x" : horizontal offset in page in characters optional, -1 if not provided saying to have the container lay out the panel,
#                           "height" : height in characters optional, -1 if not provided saying to have the container lay out the panel,
#                           "width" : width in characters optional, -1 if not provided saying to have the container lay out the panel,
#                           "graphs" : list of graph objects to be laid out in this panel
#                               [
#                                   {
#                                   "type" : one of "LineGraph","BarGraph","PieGraph","TableGraph"
#                                   "table" : name of table from tables list above,
#                                   "xseries" : name of the column in the table that represents the x axis values or pie labels for the graph,
#                                   "yseries" : [ list of column names of series to graph against the xseries ],
#                                   "yunit" : name of the units on the Y axis Bar and Line Graph only,
#                                   "top" : for graphs that support top-n selection it defines how many top items from the columns to graph, default is 0 which graphs all values in column,
#                                   "title" : title of this graph defaults to name of data table,
#                                   "area" : for LineGraph draw this as an area chart filling under the curve, defaults to False
#                                   },
#                               ]
#                           },
#                       ]
#               },
#           ]
#       }
# }

def load_table( t ):
    """ load and instantiate a table based on the JSON specification t """
    if t["type"] in data_table_plugins:
        return data_table_plugins[t["type"]].load_table( t )

    refresh_minutes = t.get("refresh_minutes",1)
    syslog_glob = t.get("syslog_glob","/var/log/syslog*")
    num_hours = t.get("num_hours",24)
    bucket_hours = t.get("bucket_hours",1)
    es_index_pattern = t.get("es_index_pattern",None)
    es_query_body = t.get("es_query_body",None)
    es_field_map = t.get("es_field_map",None)
    ssh_spec = t.get("ssh_spec",None)
    table_def = t.get("table_def",None)
    sql_spec = t.get("sql_spec",None)
    sql_query = t.get("sql_query",None)
    sql_map = t.get("sql_map",None)
    csv_spec = t.get("csv_spec",None)
    csv_map = t.get("csv_map",None)
    json_spec = t.get("json_spec",None)
    log_glob = t.get("log_glob",None)
    log_map = t.get("log_map",None)
    log_lookback = t.get("log_lookback",None)
    if t["type"] == "SyslogDataTable":
        dt = SyslogDataTable(syslog_glob,num_hours,bucket_hours,refresh_minutes)
    elif t["type"] == "ProcDataTable":
        dt = ProcDataTable(num_hours,bucket_hours,refresh_minutes)
    elif t["type"] == "ElasticsearchDataTable":
        dt = ElasticsearchDataTable(refresh_minutes,es_index_pattern,es_query_body,es_field_map)
    elif t["type"] == "RemoteDataTable":
        dt = RemoteDataTable(ssh_spec,table_def,t["name"],refresh_minutes)
    elif t["type"] == "ODBCDataTable":
        dt = ODBCDataTable(refresh_minutes,sql_spec,sql_query,sql_map)
    elif t["type"] == "CSVDataTable":
        dt = CSVDataTable(refresh_minutes,csv_spec,csv_map,None)
    elif t["type"] == "JSONDataTable":
        dt = JSONDataTable( json_spec )
    elif t["type"] == "LogDataTable":
        dt = LogDataTable( log_glob, log_map, log_lookback, refresh_minutes)

    dt.start_refresh()
    return dt

def load_graph( context, g ):
    """ load a graph from the json graph definition, returns graph """
    def lookup_table( name ):
        for t in context["tables"]:
            if t[0] == name:
                return t[1]

    type = g["type"]
    if type in graph_plugins:
        return graph_plugins[type].load_graph(context,g)

    graph = None
    yunit = g.get("yunit","")
    top = g.get("top",0)
    title = g.get("title",None)
    area = g.get("area",False)
    if type == "LineGraph":
        graph = LineGraph(lookup_table(g["table"]),g["xseries"],g["yseries"],yunit,None,None,title=title,area=area)
    elif type == "BarGraph":
        graph = BarGraph(lookup_table(g["table"]),g["xseries"],g["yseries"],yunit,None,None,top,title=title)
    elif type == "PieGraph":
        graph = PieGraph(lookup_table(g["table"]),g["xseries"],g["yseries"],None,None,title=title)
    elif type == "TableGraph":
        graph = TableGraph(lookup_table(g["table"]),g["xseries"],g["yseries"],None,None,title=title)

    return graph

def load_plugin( p ):
    """ load one plugin and register it in the global tables """
    global data_table_plugins
    global graph_plugins

    spec = importlib.util.spec_from_file_location(p["module_name"],p["module_file"])
    plugin_mod = importlib.util.module_from_spec(spec)
    spec.load.exec_module(plugin_mod)
    if p["type"] == "data_table":
        data_table_plugins[p["name"]] = plugin_mod.load_table
    elif p["type"] == "graph":
        data_table_plugins[p["name"]] = plugin_mod.load_graph

    return plugin_mod

def load_config( stdscr, config_stream ):
    """ load the dashboard configuration from the options.config path and factory all the objects, returns a context with the initialized objects  """
    cf = json.load(config_stream)

    context = {}
    if "plugins" in cf:
        context["plugins"] = []
        for p in cf["plugins"]:
            plugin_mod = load_plugin(p)
            context["plugins"].append( (p,plugin_mod) )

    context["tables"] = []
    for t in cf["tables"]:
        context["tables"].append((t["name"],load_table(t)))

    df = cf["dashboard"]
    auto_tour_delay = df.get("auto_tour_delay",None)
    if auto_tour_delay != None:
        dashboard = Dashboard(stdscr,auto_tour_delay = auto_tour_delay)
    else:
        dashboard = Dashboard(stdscr)

    context["dashboard"] = dashboard
    for p in df["pages"]:
        height = p.get("height",-1)
        width  = p.get("width",-1)
        page = Page(stdscr,height=height,width=width)
        for pp in p["panels"]:
            x = pp.get("x",-1)
            y = pp.get("y",-1)
            height = pp.get("height",-1)
            width = pp.get("width",-1)
            panel = Panel(x = x, y = y, height = height, width = width )
            for g in pp["graphs"]:
                panel.add_graph(load_graph(context,g))
            page.add_panel(panel)
        dashboard.add_page(page)

    return context
