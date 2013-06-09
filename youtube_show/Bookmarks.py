#!/usr/bin/python
# -*- coding: utf-8 -*-

import YoutubeConnector
import json
try:
    import bz2
    usebz2=True
except ImportError:
    usebz2=False

class Bookmarks(object):
    def __init__(self, f):
        self.bookmarks = {}
        self.file = f
        self.decoder = json.JSONDecoder()
        self.encoder = json.JSONEncoder()
        
    def save(self):
        with open(self.file, 'w') as f:
            data=self.encoder.encode(self.bookmarks)
            if usebz2:
                data=bz2.compress(data)
            f.write(data)

    def load(self):
        try:
            with open(self.file, 'r') as f:
                data=f.read()
                if usebz2:
                    try:
                        d=bz2.decompress(data)
                        if d:
                            data=d
                    except:
                        pass
                self.bookmarks = self.decoder.decode(data)
        except:
            open(self.file,'w').close()
            
    def get_videos(self):
        videos = []
        for vid in self.bookmarks:
            videos.append(YoutubeConnector.YTVideo(id=vid,**(self.bookmarks[vid])))
        return videos
    
    def add(self, video):
        vid=video.get_id()
        isnew=True
        if vid in self.bookmarks:
            isnew=False
        self.bookmarks[vid]={'title': video.get_title(),
                             'desc': video.get_short_desc(),
                             'duration': video.get_duration(),
                             'uploader': video.get_uploader(),
                             'uploaded': tuple(video.get_uploaded()), }
        return isnew
    
    def remove(self, video):
        vid=video.get_id()
        if vid in self.bookmarks:
            del self.bookmarks[vid]
            return True
        else:
            return False

    def __contains__(self,obj):
        if type(obj)==unicode or type(obj)==str:
            vid=obj
        else:
            vid=obj.get_id()
        return vid in self.bookmarks
    
    def remove_all(self):
        self.bookmarks={}
    