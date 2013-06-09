#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading
import multiprocessing
import time

def thread_pool(target=None,args_ar=None,wait=True,maxthreads=0,callback=None):
    if maxthreads<=0: maxthreads=multiprocessing.cpu_count()*2
    threads=[]
    result=[]
    done=0
    num=0
    for args in args_ar:
        if num > maxthreads:
            for t in threads:
                t.join(10)
                if not t.isAlive():
                    threads.remove(t)
                    del t
                    done+=1
                    if callback: callback(done,len(args_ar))
                    num-=1
        t=threading.Thread(target=target,args=args)
        t.setDaemon(True)
        threads.append(t)
        t.start()
        num+=1
    if wait:
        for t in threads:
            if callback: callback(done,len(args_ar))
            t.join()
            threads.remove(t)
    return result

class Timer(threading.Thread):
    def __init__(self, timeout, callback, args=(), kwargs={}):
        threading.Thread.__init__(self)
        self.callback_args=args
        self.callback_kwargs=kwargs
        self.timeout=timeout
        self.time=0
        self.setDaemon(False)
        self.time_lock=threading.Lock()
        self.execute=threading.Event()
        self.execute.set()
        self.callback=callback
        
    def reset_time(self):
        with self.time_lock:
            self.time=0
    
    def cancel(self):
        self.execute.clear()
    
    def run(self, *args, **kwargs):
        while True:
            if not self.execute.is_set(): break
            time.sleep(0.1)
            with self.time_lock:
                self.time+=1
                if self.time>self.timeout: break
        if self.execute.is_set():
            self.callback(*self.callback_args,**self.callback_kwargs)
    
    