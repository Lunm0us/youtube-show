#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from YoutubeConnector import Connector, YTConnector, YTSearcher

class YoutubeConnectorTest(unittest.TestCase):
    USER='lindseystomp'
    QUERY='raspberry pi'
    AUTOCOMPLETE='raspberr'
    VID='Nfk1-XMASrk'
    
    def setUp(self):
        self.searcher = YTSearcher()
        self.connector = YTConnector()
    
    def test_user_search(self):
        q=Connector.Query(offset=1,number=10,user=self.USER)
        result = self.searcher.search(q)
        self.assertTrue(type(result)==list, 'YTSearcher.search must return a list')
        self.assertTrue(len(result)>0, 'Less than 1 result')
        
    def test_search(self):
        q=Connector.Query(offset=1,number=10,query=self.QUERY)
        result = self.searcher.search(q)
        self.assertTrue(type(result)==list, 'YTSearcher.search must return a list')
        self.assertTrue(len(result)>0, 'Less than 1 result')
          
    def test_search_related(self):
        q=Connector.Query(offset=1,number=10,vid=self.VID)
        result = self.searcher.search(q)
        self.assertTrue(type(result)==list, 'YTSearcher.search must return a list')
        self.assertTrue(len(result)>0, 'Less than 1 result')
        
        
    def test_description(self):
        desc = self.connector.get_description(self.VID)
        self.assertTrue(type(desc)==str, 'YTConnector.get_description must return a str')
        
    def test_get_url(self):
        url = self.connector.get_url_by_id(self.VID)
        self.assertRegexpMatches(url,'^https?://.*', 'YTConnector.get_url_by_id did' +
                                 ' not return a valid url: %s' % url)
        
    def test_autocompletion(self):
        compl=self.searcher.get_completions(self.AUTOCOMPLETE)
        self.assertTrue(type(compl)==list, 'YTSearcher.autocomplete must return a list')
        self.assertTrue(len(compl)>0, 'Less than 1 result')
    
    def tearDown(self):
        del self.connector
        del self.searcher

if __name__ == "__main__":
    unittest.main()
