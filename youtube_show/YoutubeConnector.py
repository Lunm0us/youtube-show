#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import urllib2
import Connector
import json
import urllib
import urlparse
import HTMLParser
import time

class YTVideo(Connector.Video):
    URL_PROTO='https://www.youtube.com/watch?v=%id'
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.title = kwargs.get('title', None)
        self.desc = kwargs.get('desc', None)
        self.duration=kwargs.get('duration',0)
        self.uploader=kwargs.get('uploader',None)
        self.uploaded=kwargs.get('uploaded',time.gmtime(0))
        if type(self.uploaded) is tuple:
            self.uploaded=time.struct_time(self.uploaded)
        self.pic = None
    
    def get_description(self):
        return self.desc
    
    def get_short_desc(self):
        dindex = 250
        index=dindex
        if len(self.desc)>index:
            try:
                while not self.desc[index].isspace() and index>dindex/2:
                    index-=1
            finally:
                return self.desc[:index]
        else:
            return self.desc
    
    def get_title(self):
        return self.title
    
    def set_picture(self, pic):
        self.pic = pic
    
    def get_picture(self):
        return self.pic
    
    def get_id(self):
        return self.id
    
    def get_url(self):
        return YTVideo.URL_PROTO.replace('%id', self.id)
    
    def get_duration(self):
        return self.duration
    
    def get_uploader(self):
        return self.uploader

    def get_uploaded(self):
        return self.uploaded
    
class YTSearcher(Connector.Searcher):
    PROTO_VIDEO = 'https://gdata.youtube.com/feeds/api/videos?q=%s&start-index=%i&max-results=%i&v=2&alt=jsonc'
    PROTO_USER = 'https://gdata.youtube.com/feeds/api/users/%s/uploads?max-results=%i&start-index=%i&v=2&alt=jsonc'
    PROTO_RELATED = 'https://gdata.youtube.com/feeds/api/videos/%s/related?max-results=%i&start-index=%i&v=2&alt=jsonc'
    PROTO_USER_QUERY =  '&q=%s'
    PROTO_COMPLETION = 'http://google.com/complete/search?client=youtube&ds=yt&q=%s'
    
    def __init__(self, downloader=None):
        self.decoder=json.decoder.JSONDecoder()
        if downloader:
            self.downloader = downloader
        else:
            self.downloader = urllib2.build_opener()
    
    def search(self,query):
        if query.type=='user':
            return self.search_user(query.user,query.query,query.number,query.offset)
        elif query.type=='related':
            return self.search_related(query.vid,query.number,query.offset)
        else:
            return self.search_video(query.query,query.number,query.offset)
    
    def search_video(self, query, number=10, num_from=1):
        query_url=self.PROTO_VIDEO % (urllib.quote_plus(query), num_from, number)
        print query_url
        f=self.downloader.open(query_url)
        doc=f.read()
        f.close()
        data = self.decoder.decode(doc)
        return self.get_videos(data)
    
    def search_user(self,user,query,number=10,num_from=1):
        query_url=self.PROTO_USER %(user,number,num_from)
        print query_url
        if query:
            query_url+=self.PROTO_USER_QUERY % query
        doc=self.downloader.open(query_url).read()
        data=self.decoder.decode(doc)
        del doc
        return self.get_videos(data)
    
    def search_related(self,vid,number=10,num_from=1):
        query_url=self.PROTO_RELATED % (vid,number,num_from)
        print query_url
        doc=self.downloader.open(query_url).read()
        data=self.decoder.decode(doc)
        del doc
        return self.get_videos(data)
    
    def get_videos(self,data):
        try:
            data=data['data']['items']
        except:
            return []
        return [YTVideo(title=vid['title'], desc=vid['description'],
                          id=vid['id'],uploader=vid['uploader'],
                          duration=int(vid['duration']),
                          uploaded=self.parse_time_str(vid['uploaded']),) for vid in data]
    
    def parse_time_str(self, s):
        s=s.rsplit('.')[0]
        return time.strptime(s,'%Y-%m-%dT%H:%M:%S')
    
    def get_completions(self, query):
        url=self.PROTO_COMPLETION % urllib.quote_plus(query)
        try:
            data=self.downloader.open(url).read()
            data=data[data.find('(')+1:-1]
            data=json.loads(data)
            return [i[0] for i in data[1]]
        except:
            return []

class YTConnector(Connector.Connector):
    PROTO_VIDEO = 'https://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en'
    PROTO_WEBPAGE = 'https://www.youtube.com/watch?v=%s'
    
    CACHE_RE = '(.*://)(.*)(\.c\.youtube.com/.*)'
    
    STR_FORMATS = ['all', 'mp4', 'webm']
    STR_QUALITIES = ['360p', '480p', '720p', '1080p']
    MP4_FORMATS = ['37', '22', '18', '17']
    WEBM_FORMATS = ['46','45','44','43']
    
    IMAGE_URL = 'http://i%i.ytimg.com/vi/%s/default.jpg'
    MQIMAGE_URL = 'http://i%i.ytimg.com/vi/%s/mqdefault.jpg'
    HQIMAGE_URL = 'http://i%i.ytimg.com/vi/%s/hqdefault.jpg'
    
    def __init__(self, downloader=None, cache=None):
        self.formats = self.WEBM_FORMATS + self.MP4_FORMATS
        if downloader:
            self.downloader = downloader
        else:
            self.downloader = urllib2.build_opener()
        self.cache = cache
        self.desc_parser = DescriptionParser()
    
    def set_formats(self, formats):
        self.formats = formats

    def apply_config(self,config):
        if config['quality'] in YTConnector.STR_QUALITIES:
            index = YTConnector.STR_QUALITIES.index(config['quality']) +1
        else:
            index = 0
        if config['format'] == 'webm':
            self.formats = YTConnector.WEBM_FORMATS[-index:]
        elif config['format'] == 'mp4':
            self.formats = YTConnector.MP4_FORMATS[-index:]
        else:
            self.formats = YTConnector.WEBM_FORMATS[-index:] + YTConnector.MP4_FORMATS[-index:]
        print self.formats
        
    def get_url_by_id(self, vid, cache=None):
        for el in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
            try:
                doc = self.downloader.open(self.PROTO_VIDEO % (vid,el)).read()
                elems = urlparse.parse_qs(doc)
                if 'token' in elems:
                    break; 
            except:
                raise
        if not 'token' in elems:
            if 'reason' in elems:
                x=""
                for y in elems['reason']: x+=y
                raise Connector.ConnectorException('Youtube said: ' + x)
            else:
                raise Connector.ConnectorException('Could not get the video url. Maybe the format changed. :(')
            return
        try:
            stream_map = elems['url_encoded_fmt_stream_map'][0]
            stream_map = [urlparse.parse_qs(sm)for sm in stream_map.split(',')]
            stream_map = filter(lambda stream:'itag' in stream and 'url' in stream
                                and 'sig' in stream, stream_map)
            for f in self.formats:
                for stream in stream_map:
                    if stream['itag'][0] == f:
                        url = stream['url'][0] + '&signature=' + stream['sig'][0]
                        if cache:
                            if self.cache:
                                self.cache.cache_used(cache)
                            match=re.match(self.CACHE_RE,url)
                            url=match.group(1)+cache+match.group(3)
                        else:
                            if self.cache:
                                self.cache.add(url)
                        return url
        except Exception as e:
            if 'reason' in elems:
                x=""
                for y in elems['reason']: x+=y
                raise Connector.ConnectorException('Youtube said: ' + x)
            else:
                raise Connector.ConnectorException('Error fetching the Video URL: ' + str(e) + '\n' + str(stream_map))
        return None
    
    def get_description(self,vid):
        query_url=self.PROTO_WEBPAGE % vid
        doc=self.downloader.open(query_url).read()
        exc=None
        try:
            self.desc_parser.load(doc)
        except Exception as e:
            exc=e
        desc=self.desc_parser.description
        self.desc_parser.reset()
        if len(desc)<1 and exc:
            raise exc
        return desc
        
    def get_picture_by_id(self, vid):
        try:
            for cache in range(1,5):
                f=self.downloader.open(self.IMAGE_URL % (cache, vid))
                pic = f.read()
                f.close()
                if pic:break
            return pic
        except:
            raise
        
class CacheSaver():
    CACHE_RE = '.*://(.*)\.c\.youtube.com/.*'
    
    def __init__(self, f):
        self.filename=f
        self.caches=None
        self.cache_re=re.compile(CacheSaver.CACHE_RE)
        
    def load(self):
        self.caches={}
        try:
            with open(self.filename,'r') as f:
                for cache in f:
                    cache,reputation=cache.split(' ')
                    cache=cache.strip()
                    if len(cache)>0:
                        self.caches[cache]=int(reputation)
        except:
            pass
        
    def get_caches(self):
        if not self.caches: self.load()
        return sorted(self.caches, key=lambda w:self.caches[w])
    
    def get_reputation(self, cache):
        return self.caches[cache]
    
    def cache_used(self, cache):
        if not cache in self.caches:
            self.caches[cache]=1
            return
        self.caches[cache]+=1
        if self.caches[cache]>20:
            self.caches[cache]+=1
            for cache in self.caches:
                if self.caches[cache]>1:
                    self.caches[cache]-=1
    
    def save(self):
        if self.caches:
            with open(self.filename,'w') as f:
                for cache in self.caches:
                    f.write("%s %i\n" % (cache,self.caches[cache]))
    
    def add(self, url):
        if not self.caches: self.load()
        try:
            match=self.cache_re.match(url)
            if not match: return
            cache=match.group(1)
            if not cache in self.caches:
                self.caches[cache]=0
        except:
            pass

"""
This is mainly from youtube-dl
"""
class DescriptionParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.reset()

    def handle_starttag(self, tag, attrs):
        for attr in attrs:
            if attr[0]=='id' and attr[1]=='eow-description':
                self.in_description=True
        if self.in_description:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if self.in_description and tag=='br':
            self.description+='\n'
    
    def handle_endtag(self,tag):
        if self.in_description:
            self.stack.pop()
            if len(self.stack)<1:
                self.in_description=False
    
    def handle_data(self,data):
        if self.in_description:
            self.description+=data
           
    def load(self,html):
        self.html=html
        self.feed(html)
        self.close()
    
    def reset(self):
        HTMLParser.HTMLParser.reset(self)
        self.description=""
        self.in_description=False
        self.stack=[]
        self.error_count=0
    
    def error(self,error):
        if self.error_count > 10:
            raise Connector.ConnectorException('Failed to get the description from the video web page!\nSay thanks to YouTube')
        self.rawdata = '\n'.join(self.html.split('\n')[self.getpos()[0]:])
        self.error_count += 1
        self.goahead(1)
        