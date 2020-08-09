# Copyright 2017 James P Goodwin data table package to manage sparse columnar data
""" module that implements a remote data table proxy over ssh connection to the dashboard running as a table server  """
import sys
import os
import re
from datetime import datetime
import threading
import time
import csv
import json
from io import StringIO
from paramiko.client import SSHClient
import keyring
from functools import wraps
from data_sources.data_table import DataTable,Cell,Column,from_json,to_json,synchronized
from dashboard.version import __version__

def sync_connection(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.connection_lock:
            return method(self, *args, **kwargs)
    return wrapper

def sync_manager(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.manager_lock:
            return method(self, *args, **kwargs)
    return wrapper

class Connection():
    def __init__(self, owner=None, ssh_client=None, session=None, stdin=None, stdout=None, stderr=None ):
        """ provides protocol to the table server """
        self.ssh_client = ssh_client
        self.session = session
        self.clients = []
        self.stdout_lines = []
        self.stderr_lines = []
        self.owner = owner
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.connection_lock = threading.RLock()
        self.reader_lock = threading.RLock()
        self.stdout_reader_thread = threading.Thread(target=self.reader,args=(self.stdout,self.stdout_lines))
        self.stdout_reader_thread.start()
        self.stderr_reader_thread = threading.Thread(target=self.reader,args=(self.stderr,self.stderr_lines))
        self.stderr_reader_thread.start()

    def reader( self, stream, lines ):
        """ worker thread that reads from stdout and pushes data onto stdout_lines and stderr_lines """
        while not self.session.exit_status_ready():
            line = stream.readline()
            with self.reader_lock:
                lines.append(line)

        with self.reader_lock:
            lines += stream.readlines()

    @sync_connection
    def get_stdout_line( self ):
        """ fetch a line from the queue of stdout_lines """
        while True:
            with self.reader_lock:
                if len(self.stdout_lines):
                    return self.stdout_lines.pop(0)
            time.sleep(1)

    @sync_connection
    def get_stderr_line( self ):
        """ fetch a line from the queue of stderr_lines """
        while True:
            with self.reader_lock:
                if len(self.stderr_lines):
                    return self.stderr_lines.pop(0)
            time.sleep(1)

    @sync_connection
    def open( self, client ):
        """ register this client as a user of this connection """
        if client not in self.clients:
            self.clients.append(client)

    @sync_connection
    def table(self, table_def):
        """ send request to create a new remote table, returns loaded response """
        print("table:%s"%table_def,file=self.stdin,flush=True)
        return self.get_stdout_line()

    @sync_connection
    def refresh(self, table_name):
        """ send request to refresh a remote table named table_name and return response """
        print("refresh:%s"%table_name,file=self.stdin,flush=True)
        return self.get_stdout_line()

    @sync_connection
    def get(self, table_name):
        """ send request to fetch table_name and return response """
        print("get:%s"%table_name,file=self.stdin,flush=True)
        return self.get_stdout_line()

    @sync_connection
    def exit(self):
        """ terminate the server and clean up this connection """
        print("exit",file=self.stdin,flush=True)
        return ""

    @sync_connection
    def close(self,client):
        """ close this client's use of this connection """
        if client in self.clients:
            self.clients.remove(client)

class ConnectionManager():
    def __init__(self):
        """ manages connections to servers and their initial setup """
        self.connections = {}
        self.manager_lock = threading.RLock()

    def __del__(self):
        """ just in case clean up any connections """
        self.shutdown()

    @sync_manager
    def shutdown( self ):
        """ shut down the connection manager and close all the pooled connections """
        for cn in self.connections:
            self.connections[cn].exit()
            self.connections[cn].ssh_client.close()
        self.connections = {}

    @sync_manager
    def connect(self,ssh_spec,client):
        """ create a connection to a server """
        if ssh_spec in self.connections:
            connection = self.connections[ssh_spec]
            connection.open(client)
            return connection

        username,server,port = re.match(r"ssh://([a-z_][a-z0-9_-]*\${0,1})@([^:]*):{0,1}(\d*){0,1}",ssh_spec).groups()

        password = keyring.get_password(server,username)
        if not password:
            return None

        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.connect( hostname=server, port=int(port if port else 22), username=username, password=password)

        if self.setup( ssh_client ):
            session,stdin,stdout,stderror = self.start_command(ssh_client,"~/.local/bin/dashboard --server")
            connection = Connection(self,ssh_client,session,stdin,stdout,stderror)
            connection.open(client)
            self.connections[ssh_spec] = connection
            return connection

        raise Exception("Setup of remote dashboard failed")

    @sync_manager
    def start_command(self, ssh_client, command ):
        """ start a command and return a tuple with (channel,stdin,stdout,stderr) for running process """
        transport = ssh_client.get_transport()
        session = transport.open_session()
        session.exec_command(command)
        stdout = session.makefile("r",1)
        stderr = session.makefile_stderr("r",1)
        stdin = session.makefile_stdin("w",1)
        return (session,stdin,stdout,stderr)

    @sync_manager
    def run_command(self, ssh_client, command ):
        """ run a command wait for it to exit and return the output (retcode,stdout_str,stderr_str) """
        session,stdin,stdout,stderr = self.start_command(ssh_client,command)

        stderr_output = StringIO()
        stdout_output = StringIO()
        while not session.exit_status_ready():
            stdout_output.write(stdout.readline())
            stderr_output.write(stderr.readline())
        stdout_output.write("".join(stdout.readlines()))
        stderr_output.write("".join(stderr.readlines()))
        exit_status = session.recv_exit_status()
        return (exit_status,stdout_output.getvalue(),stderr_output.getvalue())

    @sync_manager
    def setup(self, ssh_client ):
        """ check to see that dashboard is installed and install it if needed """
        exit_status,stdout_str,stderr_str = self.run_command(ssh_client,"~/.local/bin/dashboard --version")
        stdout_str = stdout_str.strip()
        if stdout_str.startswith("dashboard version"):
            if stdout_str.endswith(__version__):
                return True

        exit_status,stdout_str,stderr_str = self.run_command(ssh_client,'python3 -m pip install --upgrade "terminal-dashboard==%s"'%(__version__))
        if exit_status:
            raise Exception(exit_status,stdout_str,stderr_str)

        return True


_connection_manager = None
def get_connection_manager():
    """ return the connection manager create one if it doesn't exit """
    global _connection_manager
    if not _connection_manager:
        _connection_manager = ConnectionManager()
    return _connection_manager

def shutdown_connection_manager():
    """ shut down the connection manager if it was ever started """
    global _connection_manager
    if _connection_manager:
        _connection_manager.shutdown()
        _connection_manager = None

class RemoteDataTable( DataTable ):
    def __init__(self,ssh_spec=None,table_def=None,name=None,refresh_minutes=1):
        """ accepts an ssh_spec to connect to of the form ssh://username@server_name:port_number, a json string with the definition for the remote table, the local name for this table, and the number of minutes for refresh """
        DataTable.__init__(self,None,name,refresh_minutes)
        self.ssh_spec = ssh_spec
        self.table_def = table_def
        self.connection = None
        self.refresh()

    @synchronized
    def refresh(self):
        """ create a connection to the remote dashboard table server and refresh our internal state """

        if not self.connection:
            cm = get_connection_manager()
            connection = cm.connect(self.ssh_spec,self)
            if not connection:
                return
            self.connection = connection
            response = self.connection.table(json.dumps(self.table_def))
            if not response.startswith("loaded:%s"%self.table_def["name"]):
                return

        table_data = self.connection.get(self.table_def["name"])
        name,json_blob = table_data.split(":",1)
        dt = from_json(StringIO(json_blob))

        rows,cols = dt.get_bounds()
        for idx in range(cols):
            self.replace_column(idx,dt.get_column(idx))

        self.changed()
        DataTable.refresh(self)
