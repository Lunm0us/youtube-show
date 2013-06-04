#!/usr/bin/python
# -*- coding: utf-8 -*-

class Video():
    def __init__(self,url):
        pass
    
    def get_description(self):
        return ''
    
    def get_title(self):
        return ''
    
    def get_picture(self):
        return None
    
class Query():
    def __init__(self,*args,**kwargs):
        if len(args)>0:
            query=args[0]
            self.type=query.type
            self.query=query.query
            self.offset=query.offset
            self.number=query.number
            if self.type=='user':
                self.user=query.user
            elif self.type=='related':
                self.vid=query.vid
        else:
            if 'user' in kwargs:
                self.type='user'
                self.user=kwargs.get('user')
            elif 'vid' in kwargs:
                self.type='related'
                self.vid=kwargs.get('vid')
            else:
                self.type='video'
            self.query=kwargs.get('query',"")
            self.offset=kwargs.get('offset',1)
            self.number=kwargs.get('number',10)

class Searcher():
    def __init__(self, downloader=None):
        pass
    
    def search(self,Query):
        return []
    
class Connector():
    def __init__(self):
        pass
    
    def apply_config(self,config):
        return None
    
    def get_url_by_id(self, vid, cache= None):
        return None
    
    def get_picture_by_id(self, vid):
        return None
    
class ConnectorException(Exception):
    pass