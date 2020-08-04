# Copyright 2020 James P Goodwin data table package to manage sparse columnar data
""" module that does an Elasticsearch query and creates a table of data based on the response """
import locale
locale.setlocale(locale.LC_ALL,'')
import sys
import os
import glob
import gzip
import re
from elasticsearch import Elasticsearch
from datetime import datetime,timedelta
from data_sources.data_table import DataTable,Column,Cell,blank_type,string_type,float_type,int_type,date_type,format_string,format_float,format_date,format_int,synchronized

class ElasticsearchDataTable( DataTable ):
    """ class that collects data from the response to a specific elasticsearch query and populates tables based on a field map """
    def __init__(self,refresh_minutes=1,es_index_pattern=None,es_query_body=None,es_field_map=None):
        """ Initialize the ElasticsearchQueryTable pass in a refresh interval in minutes, the es_query_body dict representing the query json and the field map list of tuples [( json path, field name, field type )...]"""
        self.es_query_body = es_query_body
        self.es_field_map = es_field_map
        self.es_index_pattern = es_index_pattern
        DataTable.__init__(self,None,
            "Elasticsearch query:%s,index:%s,fieldmap:%s,refreshed every %d minutes"%(
                es_query_body,es_index_pattern,es_field_map,refresh_minutes),
            refresh_minutes)
        self.refresh()

    @synchronized
    def get_es_parameters( self ):
        """ fetch the elasticsearch parameters for this table as a tuple (es_query_body,es_field_map,es_index_pattern) """
        return (self.es_query_body,self.es_field_map,self.es_index_pattern)

    @synchronized
    def set_es_parameters( self, es_query_body,es_field_map,es_index_pattern ):
        """ set the elasticsearch parameters for this table """
        self.es_query_body = es_query_body
        self.es_field_map = es_field_map
        self.es_index_pattern = es_index_pattern
        self.refresh()

    @synchronized
    def refresh( self ):
        """ refresh or rebuild tables """

        es = Elasticsearch()

        result = es.search(index=self.es_index_pattern,body=self.es_query_body)

        def match_fields( name, result ):
            matches = []
            if isinstance(result,dict):
                for k in result:
                    full_name = (name+"." if name else "")+k
                    item = result[k]
                    for json_path,field_name,field_type  in self.es_field_map:
                        if full_name == json_path:
                            matches.append((field_name,field_type,item))
                    if isinstance(item,dict) or isinstance(item,list):
                        matches += match_fields(full_name,item)
            elif isinstance(result,list):
                for k in result:
                    matches += match_fields(name,k)
            return matches

        matches = match_fields( "",result)

        new_columns = {}
        for column_name,column_type,value in matches:
            if not column_name in new_columns:
                new_columns[column_name] = Column(name=column_name)
            c = new_columns[column_name]
            if column_type == "date":
                cc = Cell(date_type,datetime.fromtimestamp(value/1000),format_date)
            elif column_type == "int":
                cc = Cell(int_type,value,format_int)
            elif column_type == "float":
                cc = Cell(float_type,value,format_float)
            elif column_type == "str":
                cc = Cell(string_type,value,format_string)
            else:
                cc = Cell(string_type,str(value),format_string)
            c.put(c.size(),cc)

        for column_name in new_columns:
            if self.has_column(column_name):
                self.replace_column(self.map_column(column_name),new_columns[column_name])
            else:
                self.add_column(new_columns[column_name])

        self.changed()

        DataTable.refresh(self)
