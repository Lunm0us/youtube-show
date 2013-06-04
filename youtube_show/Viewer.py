#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import re
import time
import struct
import sys
if 'linux' in sys.platform:
    import fcntl
    
class Viewer(object):
    PLAYERS = [(u'omxplayer', u'%f',),
             (u'avplay', u'-autoexit', u'-window_title', u'%t',
               u'-infbuf', (u'u', u'-user-agent', u'%u',), u'%f',),
             (u'ffplay', u'-autoexit', u'-window_title', u'%t',
               u'-infbuf', (u'u', u'-user-agent', u'%u',), u'%f'),
             (u'vlc', u'--no-video-title-show', (u'u', '--http-user-agent', u'%u'), u'%f',)]
    
    def __init__(self, player=None):
        if player:
            self.player = player
        else:
            self.find_player()
        self.running = {}
        self.last = None
        if 'linux' in sys.platform:
            self.set_nonblocking = self.set_nonblocking_unix
        elif 'win' in sys.platform:
            self.set_nonblocking = self.empty
        elif 'osx' in sys.platform:
            #should probably be the same as unix/linux
            self.set_nonblocking = self.set_nonblocking_unix
        self.fields={}
    
    def empty(self,*args,**kwargs):
        pass
    
    def set_nonblocking_unix(self, f):
        fl = fcntl.fcntl(f, fcntl.F_GETFL)
        fcntl.fcntl(f, fcntl.F_SETFL, fl | os.O_NONBLOCK)
 
    def find_player(self):
        for player in self.PLAYERS:
            if self.check_for_player(player[0]):
                self.player = player
                break
        if 'win' in sys.platform:
            for player in self.PLAYERS:
                if self.check_for_player(player[0] + '.exe'):
                    self.player=tuple(player[0].exe + x for x in player[1:])
                    break
        self.is_omxplayer = bool(re.match('.*omxplayer.*', self.player[0]))
        
    def check_for_player(self, player):
        for path in os.environ['PATH'].split(os.pathsep):
            try:
                os.stat(path + os.sep + player)
                print 'found ' + path + os.sep + player + ' as a suitable player'
                return True
            except:
                pass
        return False
    
    def stop_all(self):
        if self.is_omxplayer:
            for pid in self.running:
                self.running[pid].stdin.write('q')
            time.sleep(2)
        for pid in self.running:
            self.running[pid].terminate()
        self.last = None
        self.running = {}
    
    def stop(self, pid= -1):
        if pid > 0 and pid in self.running:
            proc = self.running[pid]
        else:
            proc = self.last
        if self.is_omxplayer:
            proc.stdin.write('q')
        else:
            proc.terminate()
        if proc == self.last:
            pid = self.last.pid
            del self.running[pid]
            self.last = None
        else:
            del self.running[pid]
            
    def communicate(self, s, pid= -1):
        if pid <= 0:
            pid = self.last.pid
        try:
            self.last.stdin.write(s)
        except Exception as e:
            print e.message
            print e.args
            self.close(pid)
    
    def view(self, url, title):
        title = title if title else url
        cmdline=self.create_cmdline(url, title)
        print cmdline
        proc = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
        self.running[proc.pid] = proc
        self.last = proc
        self.set_nonblocking(proc.stdin)
        return proc.pid
    
    def create_cmdline(self, url, title):
        cmdline=[]
        if self.is_generic:
            for part in self.player:
                if not type(part) in [str,unicode]:
                    code=part[0]
                    if code in self.fields:
                        for p in part[1:]:
                            cmdline.append(p.replace('%' + code,self.fields[code]))
                else:
                    cmdline.append(part)
            repl = lambda x: x.replace(u'%t', title).replace(u'%f', url)
            return tuple(repl(x) for x in cmdline)
        else:
            for part in self.player:
                lastindex=0
                try:
                    index=part.find(u'%',lastindex)
                    while index>-1:
                        code=part[index+1]
                        if code in self.fields:
                            repl=self.fields[code]
                        elif code=='%':
                            repl='%'
                        elif code=='t':
                            repl=title
                        elif code=='f':
                            repl=code
                        else:
                            repl=None
                        if repl:
                            part=part[:index] + repl + part[index+2:]
                            lastindex=index+len(repl)
                        else:
                            lastindex=index+1
                        index=part.find(u'%',lastindex)
                except:
                    pass
                cmdline.append(part)
        return tuple(cmdline);
        
    
    def remove(self, pid):
        if self.last and pid == self.last.pid:
            self.last = None
        proc = self.running[pid]
        try:
            proc.stdin.close()
        except:
            pass
        try:
            proc.stdout.close()
        except:
            pass
        try:
            proc.stderr.close()
        except:
            pass
        del self.running[pid]
        del proc
        
    def is_playing(self):
        playing = False
        for pid in self.running.keys():
            run = self.running[pid]
            run.poll()
            if run.returncode != None:
                self.remove(pid)
            else:
                playing = True
        return playing
        
    def get_player(self):
        return self.player
    
    def set_player(self, player):
        if player:
            if type(player) == str or type(player) == unicode:
                self.player = tuple(player.split(" "))
            else:
                self.player = player
            self.is_generic = False
        else:
            self.find_player()
            self.is_generic = True
            
    def pause(self, pid= -1):
        self.communicate(' ', pid)
    
    def seek_forward(self, pid= -1):
        self.communicate(struct.pack('<i', 0x435b), pid)
        self.communicate(struct.pack('<i', 0x5b43), pid)
        
    def seek_back(self, pid= -1):
        self.communicate(struct.pack('<i', 0x5b44), pid)
        self.communicate(struct.pack('<i', 0x445b), pid)

    def add_field(self,field,content):
        self.fields[field]=content
        
    def remove_field(self,field):
        del self.fields[field]
        
if __name__ == '__main__':
    viewer=Viewer()
    viewer.add_field('u', 'TEST')
    viewer.set_player("player %f -t%t -u %u -procent %%%%%u %% ")
    print viewer.create_cmdline('url', 'title')
