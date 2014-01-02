#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
from gtk import gdk
from gtk.gdk import threads_enter,threads_leave
import gtk
import gobject
import pango
import YoutubeConnector
import Connector
import Viewer
import Bookmarks
import threader
import threading
import traceback
import json
import zipfile
from cookielib import CookieJar
import urllib2
import webbrowser
import re
import locale
import time

class SearchBar(gtk.ToolItem):
    __gsignals__ = {
        'need-completion': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_PYOBJECT,(object,)),
        'search': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,tuple())
    }
    NO_COMLETION=['user:']
    
    def __init__(self):
        gtk.ToolItem.__init__(self)
        box = gtk.HBox()
        self.entry = gtk.Entry()
        self.entry.connect('activate', self.do_activate)
        self.entry.connect('changed',self.do_canged)
        self.completion=gtk.EntryCompletion()
        self.completion.set_model(gtk.ListStore(str))
        self.completion.set_text_column(0)
        self.completion.set_inline_selection(True)
        self.completion.set_match_func(lambda a,b,c: True)
        self.completion.connect('match_selected', self.do_match_selected)
        self.entry.set_completion(self.completion)
        label = gtk.Label('Search: ')
        box.pack_start(label, expand=False, fill=False)
        box.pack_start(self.entry, expand=True, fill=True)
        self.set_expand(True)
        self.add(box)
        self.timer=None
        
    def do_canged(self,source):
        text=source.get_text()
        if len(text)<1:
            self.timer.cancel()
            return
        for comp in self.NO_COMLETION:
            if text.startswith(comp):
                source.set_completion(None)
                return
        if not source.get_completion():
            source.set_completion(self.completion)
        if self.timer and self.timer.is_alive():
            self.timer.reset_time()
        else:
            del self.timer
            self.timer=threader.Timer(3,self.emit_need_completion,args=(source,))
            self.timer.start()
        return True
    
    def emit_need_completion(self, source):
        e=self.emit('need-completion', source.get_text())
        gobject.idle_add(self.set_completion,source,e)
        source.emit('changed')
        
    def set_completion(self, source, completion):
        model=self.completion.get_model()
        model.clear()
        for i in completion:
            model.append((i,))
        source.queue_draw()
        
    def do_match_selected(self,completion,model,it):
        text=model.get(it,0)[0]
        entry=completion.get_entry()
        entry.set_text(text)
        self.emit('search')
        
    def do_activate(self, entry):
        self.emit('search')
        
    def get_text(self):
        return self.entry.get_text()
    
    def set_text(self, text):
        return self.entry.set_text(text)
        
class ShowBox(gtk.ScrolledWindow):
    
    __gsignals__ = {
        'scroll-end-event': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
    }
    
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.widgets = []
        self.max_x = 2
        self.max_y = 4
        self.xl = 0
        self.xr = 1
        self.yu = 0
        self.yd = 1
        self.table = gtk.Table(self.max_x, self.max_y)
        self.table.set_row_spacings(3)
        self.table.set_col_spacings(3)
        self.add_with_viewport(self.table)
        self.get_vscrollbar().connect('value_changed', self.on_scroll)
        adjustment = self.get_vscrollbar().get_adjustment()
        adjustment.set_upper(100)
        self.get_vscrollbar().set_adjustment(adjustment)
    
    def show(self):
        gtk.ScrolledWindow.show(self)
        self.table.show()
    
    def add(self, widget):
        self.widgets.append(widget);
        self.table.attach(widget, self.xl, self.xr, self.yu, self.yd)
        self.xl += 1
        self.xr += 1
        if self.xr > self.max_x:
            self.xr = 1
            self.xl = 0
            self.yu += 1
            self.yd += 1
        self.check_resize()

    def clear(self):
        for child in self.widgets:
            self.table.remove(child)
            child.destroy()
        self.widgets = []
            
    def on_scroll(self, widget):
        adjustment = widget.get_adjustment()
        if(adjustment.get_value() >= adjustment.get_upper() - 
           adjustment.get_step_increment() - adjustment.get_page_increment() - 80):
            self.emit("scroll-end-event", self)

class VideoWidget(gtk.Widget):
    
    __gsignals__ = {
        'clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'left-clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'middle-clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
    }
    
    def __init__(self, vid,show_description):
        gtk.Widget.__init__(self)
        self.set_can_focus(True)
        self.video = vid
        picture=vid.get_picture()
        if picture:
            loader = gdk.PixbufLoader()
            loader.write(picture)
            self.pic = loader.get_pixbuf()
            loader.close()
        else:
            self.pic=None
        #self.font=gtk.FontSelection().get_font()
        self.create_pango_context()
        #self.font_description=pango.FontDescription('')
        txt = '<b>' + self.video.get_title() + '</b>\n'
        txt += self.get_formated_duration() + ' ' + self.video.get_uploader() + ' ' + self.get_formated_uploaded()
        if show_description:
            txt+= '\n' + self.video.get_short_desc()
        else:
            #self.tooltip_widget=None
            #self.set_property('has-tooltip',True)
            #self.connect('query-tooltip',self.do_query_tooltip)
            self.set_tooltip_text(self.video.get_short_desc())
        txt = txt.replace('&', '&amp;')
        self.text_layout=self.create_pango_layout("")
        self.text_layout.set_markup(txt)
        self.text_layout.set_wrap(pango.WRAP_WORD_CHAR)
        self.text_layout.set_spacing(pango.SCALE*3)
        self.connect('button-release-event', self.on_button_release)
        self.connect('enter-notify-event', self.on_enter)
        self.connect('leave-notify-event', self.on_leave)

    def on_button_release(self, widget, event):
        _, _, x, y, _ = self.window.get_geometry()
        if event.x > x or event.y > y or event.x < 0 or event.y < 0:
            return
        self.grab_focus()
        if event.button == 1:
            self.emit('clicked', event)
        if event.button == 2:
            self.emit('middle-clicked', event)
        elif event.button == 3:
            self.emit('left-clicked', event)
    
    def on_enter(self, event, widget):
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
        
    def on_leave(self, event, widget):
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.ARROW))
        
    def do_realize(self):
        self.set_flags(self.flags() | gtk.REALIZED)
        self.window = gdk.Window(self.get_parent_window(), width=self.allocation.width,
                                  height=self.allocation.height, window_type=gdk.WINDOW_CHILD,
                                   wclass=gdk.INPUT_OUTPUT, event_mask=self.get_events() | 
                                    gdk.EXPOSURE_MASK | gdk.BUTTON_RELEASE_MASK | gdk.BUTTON_PRESS_MASK | 
                                    gdk.ENTER_NOTIFY_MASK | gdk.LEAVE_NOTIFY_MASK)
        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        
        self.gc = self.style.fg_gc[gtk.STATE_NORMAL]
        
    def do_unrealize(self):
        self.window.set_user_data(None)
        self.window.destroy()
        
    def do_size_request(self, request):
        if self.pic:
            request.height = self.pic.get_height()
            request.width = self.pic.get_width() * 2.5
            self.set_size_request(request.width, request.height)
        else:
            request.height = 60
            request.width = 120
            self.set_size_request(120,60)
            
    def do_size_allocate(self, alloc):
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*alloc)
        self.allocation=alloc
    
    def do_expose_event(self, event):
        if self.pic:
            self.window.draw_pixbuf(self.gc, self.pic, 0, 0, 0, 0 , -1, -1, gdk.RGB_DITHER_NONE, 0, 0)
            width=self.pic.get_width()
        else:
            width=5
        self.text_layout.set_width(pango.SCALE*(self.allocation.width-width))
        self.window.draw_layout(self.gc,width+5,5,self.text_layout)

    def get_video(self):
        return self.video
        
    def get_formated_duration(self):
        duration=self.video.get_duration()
        return "%i:%02i" %(duration/60,duration%60) if duration is not None else ""
    
    def get_formated_uploaded(self):
        uploaded=self.video.get_uploaded()
        return time.strftime(locale.nl_langinfo(locale.D_FMT),uploaded) if uploaded is not None else ""

class UserDir():
    def __init__(self):
        if 'win32' in sys.platform:
            self.path=os.path.join(os.path.expandvars('%appdata%'),'youtube-show')
        else:
            self.path=os.path.join(os.path.expanduser('~'),'.youtube-show')
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        elif not os.path.isdir(self.path):
            raise Exception("\"" + self.path + "\" exists but is not a directory!")
        
    def get_conf_file(self):
        return os.path.join(self.path,'youtube-show.conf')
                
    def get_file(self,f):
        return os.path.join(self.path,f)

class Config(dict):
    DEFAULTS={'format':'all','quality':'1080p','number-start':40,'number':10,'allow_several':False,'show_desc':True,
              'size':(-1,-1),}
    def __init__(self,f):
        dict.__init__(self)
        self.file=f
        
    def load(self):
        try:
            with open(self.file,'r') as f:
                a=json.load(f)
                for key in a:
                    self[key]=a[key]
        except:
            pass
        for key in Config.DEFAULTS:
            if not key in self:
                if key in Config.DEFAULTS:
                    self[key]=Config.DEFAULTS[key]
    
    def save(self):
        with open(self.file,'w') as f:
            json.dump(self,f)
            
    def clone(self):
        c=Config()
        c.file=self.file
        for key in self:
            c[key]=self[key]
        return c
    
class Configer(gtk.Window):
    
    __gsignals__ = {
        'config-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
   }
    
    def __init__(self,parent,config):
        gtk.Window.__init__(self)
        self.set_title("Options")
        self.connect('delete_event', self.do_delete)
        self.config=config
        self.t=gtk.Table()
        self.n=0
        def addc(a,b,af=gtk.FILL|gtk.EXPAND,bf=gtk.FILL):
            self.t.attach(a,0,1,self.n,self.n+1,af)
            self.t.attach(b,1,2,self.n,self.n+1,bf)
            self.n+=1
        
        self.format_label = gtk.Label('Format: ')
        self.format_list = gtk.ListStore(str)
        for f in YoutubeConnector.YTConnector.STR_FORMATS:
            self.format_list.append((f,))
        
        self.format_switcher = gtk.ComboBox()
        self.format_switcher.set_model(self.format_list)  
        cell = gtk.CellRendererText()
        self.format_switcher.pack_start(cell, True)
        self.format_switcher.add_attribute(cell, 'text', 0)
        
        try:
            i=YoutubeConnector.YTConnector.STR_FORMATS.index(config['format'])
            self.format_switcher.set_active(i)
        except Exception as e:
            print e
        
        self.format_switcher.show()
        self.format_label.show()
        addc(self.format_label,self.format_switcher)
        
        self.quality_label = gtk.Label('Quality: ')
        self.quality_list = gtk.ListStore(str)
        for quality in YoutubeConnector.YTConnector.STR_QUALITIES:
            self.quality_list.append((quality,))
        
        self.quality_switcher = gtk.ComboBox()
        self.quality_switcher.set_model(self.quality_list)
        cell = gtk.CellRendererText()
        self.quality_switcher.pack_start(cell, True)
        self.quality_switcher.add_attribute(cell, 'text', 0)
        
        try:
            i=YoutubeConnector.YTConnector.STR_QUALITIES.index(config['quality'])
            self.quality_switcher.set_active(i)
        except Exception as e:
            print e
        
        self.quality_switcher.show()
        self.quality_label.show()
        addc(self.quality_label,self.quality_switcher)
        
        self.playerEntry=gtk.Entry()
        if 'player' in self.config:
            self.playerEntry.set_text(self.config['player'])
        self.playerLabel=gtk.Label("Player (blank for auto): ")
        self.playerChooseButton=gtk.Button("File")
        self.playerChooseButton.connect('clicked',self.player_choose_file_callback)
        h=gtk.HBox()
        h.pack_start(self.playerEntry,gtk.FILL|gtk.EXPAND)
        h.pack_start(self.playerChooseButton,0)
        addc(self.playerLabel,h)
        
        self.userAgentEntry=gtk.Entry()
        if 'User-Agent' in self.config:
            self.userAgentEntry.set_text(self.config['User-Agent'])
        self.userAgentLabel=gtk.Label("User-Agent (blank for auto): ")
        addc(self.userAgentLabel,self.userAgentEntry)
        
        self.allow_several=gtk.CheckButton()
        self.allow_several.set_active(self.config['allow_several'])
        self.allow_several_label=gtk.Label("Allow more than one at a time: ")
        addc(self.allow_several_label,self.allow_several)
        
        self.show_desc=gtk.CheckButton()
        self.show_desc.set_active(self.config['show_desc'])
        self.show_desc_label=gtk.Label("Show description: ")
        addc(self.show_desc_label,self.show_desc)
        
        h=gtk.HBox()
        self.ok_button = gtk.Button('OK')
        self.ok_button.connect('clicked', self.do_ok)
        self.ok_button.show()
        self.cancel_button = gtk.Button('Cancel')
        self.cancel_button.connect('clicked', self.do_cancel)
        self.cancel_button.show()
        h.pack_start(self.ok_button)
        h.pack_start(self.cancel_button)
        self.t.attach(h,0,2,self.n,self.n+1)
        
        self.t.show_all()
        self.add(self.t)
        self.set_transient_for(parent)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_resizable(False)
    
    def do_delete(self, widget, event):
        pass    
    
    def player_choose_file_callback(self,widget):
        dialog=gtk.FileChooserDialog(parent=self,action=gtk.FILE_CHOOSER_ACTION_OPEN)
        dialog.add_button(gtk.STOCK_OK,gtk.RESPONSE_CLOSE)
        dialog.run()
        self.playerEntry.set_text(dialog.get_filename())
        dialog.destroy()
        
    def do_ok(self, widget):
        self.config['quality']=YoutubeConnector.YTConnector.STR_QUALITIES[self.quality_switcher.get_active()]
        self.config['format']=YoutubeConnector.YTConnector.STR_FORMATS[self.format_switcher.get_active()]
        self.config['allow_several']=self.allow_several.get_active()
        self.config['show_desc']=self.show_desc.get_active()
        if self.playerEntry.get_text() !="":
            self.config['player']=self.playerEntry.get_text()
        elif 'player' in  self.config:
            del self.config['player']
        if self.userAgentEntry.get_text() != "":
            self.config['User-Agent']=self.userAgentEntry.get_text()
        elif 'User-Agent' in self.config:
            del self.config['User-Agent']
        self.emit('config-changed',self.config)
        self.destroy()
        
    def do_cancel(self, widget):
        self.destroy()
        
class HistoryObject(object):
    def __init__(self,query, lastoffset, showbox):
        self.lastsearchoffset = lastoffset
        self.lastquery = query
        self.end_search = threading.Event()
        self.showbox = showbox

class History(list):
    def __init__(self):
        self.lock=threading.Lock()
        
    def newest(self):
        self.lock.acquire()
        try:
            e=self[len(self)-1]
        finally:
            self.lock.release()
        return e
    
    def clear(self):
        self.lock.acquire()
        try:
            for i in self:
                self.remove(i)
                del i
        finally:
            self.lock.release()
                
    def first(self):
        self.lock.acquire()
        try:
            for i in self[1:]:
                self.remove(i)
                del i
            e=self[0]
        finally:
            self.lock.release()
        return e
    
    def prev(self):
        self.lock.acquire()
        try:
            if len(self)<2:
                return self[0]
            i = self.pop()
            del i
            e = self[len(self)-1]
        finally:
            self.lock.release()
        return e
        
class DescriptionWindow(gtk.Window):
    def __init__(self,desc):
        gtk.Window.__init__(self)
        self.scroller=gtk.ScrolledWindow()
        buf=gtk.TextBuffer()
        buf.set_text(desc or "")
        self.textview=gtk.TextView(buf)
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        self.textview.set_editable(False)
        self.scroller.add(self.textview)
        self.add(self.scroller)
        self.set_position(gtk.WIN_POS_MOUSE)
        self.scroller.show_all()
        self.resize(200,400)
        
class MainWindow(object):
    
    STOCK_BOOKMARK="youtube_show-bookmark"
    
    def __init__(self):
        threads_enter()
        gobject.type_register(VideoWidget)
        gobject.type_register(ShowBox)
        gobject.type_register(Configer)
        gobject.type_register(DescriptionWindow)
        gobject.type_register(SearchBar)
        
        locale.setlocale(locale.LC_ALL,locale.getdefaultlocale())
        
        factory=gtk.IconFactory()
        try:
            f=self.get_resource('pixmaps/bookmark.png')
            loader=gtk.gdk.PixbufLoader()
            loader.write(f.read())
            f.close()
            factory.add(self.STOCK_BOOKMARK,gtk.IconSet(loader.get_pixbuf()))
            loader.close()
        except:
            raise
        factory.add_default()
        gtk.stock_add(((self.STOCK_BOOKMARK, "_Bookmarks", gtk.gdk.CONTROL_MASK, gtk.gdk.keyval_from_name('B'), "youtube-show",),))
        
        self.userDir=UserDir()
        self.config=Config(self.userDir.get_conf_file())
        self.config.load()
        self.bookmarks=Bookmarks.Bookmarks(self.userDir.get_file('bookmarks'))
        self.bookmarks.load()
        self.caches=YoutubeConnector.CacheSaver(self.userDir.get_file('caches.txt'))

        self.cookies=CookieJar()
        self.downloader=urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookies))
        self.ytsearcher = YoutubeConnector.YTSearcher(self.downloader)
        self.ytconnector = YoutubeConnector.YTConnector(self.downloader, self.caches)
        
        self.searching = threading.Event()
        self.is_fullscreen=False
        self.history=History()
        
        self.viewer = Viewer.Viewer()
        self.win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        if not self.win:
            raise RuntimeError()
        self.win.connect('delete_event', self.cleanup)
        self.win.connect('destroy', self.destroy)
        self.win.connect('key_press_event', self.on_key_press)
        self.win.connect_object('window-state-event', self.on_window_state_change,self)

        self.build_menu_bar()
        
        self.build_tool_bar()
        self.showbox = ShowBox()
        self.showbox.connect('scroll-end-event', self.do_next_search)
        self.showbox.show()
        self.statusbar = gtk.Statusbar()
        self.statusbar.show()
        self.progressbar = gtk.ProgressBar()
        self.statusbar.add(self.progressbar)
        
        self.align = gtk.VBox()
        self.align.pack_start(self.menubar, expand=False, fill=True)
        self.align.pack_start(self.toolbar, expand=False, fill=True)
        self.align.pack_start(self.showbox, expand=True, fill=True)
        self.align.pack_start(self.statusbar, expand=False, fill=True)

        self.statusbar.push(1, 'Ready')
        self.apply_config()
        self.align.show()
        self.win.add(self.align)
        self.win.set_title("youtube-show")
    
        theme=gtk.icon_theme_get_for_screen(gtk.gdk.screen_get_default())
        try:
            icon=theme.load_icon('youtube_show',48,0)
            self.win.set_icon(icon)
        except:
            try:
                with self.get_resource('pixmaps/youtube-show.png') as iconfile:
                    loader=gdk.PixbufLoader()
                    loader.write(iconfile.read())
                    self.win.set_icon(loader.get_pixbuf())
                    loader.close()
            except:
                pass
        
        w,h=self.config['size']
        if w>-1 and h>-1:
            self.win.resize(w,h)
        else:
            self.win.resize(500, 600)
        self.win.show()
        threads_leave()
        
    def get_resource(self,resource):
        zipname=os.path.split(__file__)[0]
        if os.path.isfile(zipname):
            f=zipfile.ZipFile(zipname,'r')
            rfile=f.open(resource,'r')
            f.close()
            return rfile
        else:
            return open(os.path.join(zipname,os.path.join('..',resource)))
                        
    def build_menu_bar(self):
        self.menubar = gtk.MenuBar()
        f = gtk.MenuItem('File')
        self.menubar.append(f)
        fmenu = gtk.Menu()
        f.set_submenu(fmenu)
        i = gtk.ImageMenuItem(self.STOCK_BOOKMARK)
        i.connect('activate', self.do_show_bookmarks)
        fmenu.append(i)
        i = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        i.connect('activate', self.do_configure)
        fmenu.append(i)
        i = gtk.MenuItem('Update bookmark data')
        i.connect('activate', self.do_update_bookmarks)
        fmenu.append(i)
        i = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        i.connect('activate', self.cleanup)
        fmenu.append(i)
        f = gtk.MenuItem("Help")
        fmenu = gtk.Menu()
        self.menubar.append(f)
        f.set_submenu(fmenu)
        i = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        i.connect('activate', self.do_show_about_dialog)
        fmenu.append(i)
        self.menubar.show_all()
        
    def build_tool_bar(self):
        self.toolbar = gtk.Toolbar()
        self.first_button=gtk.ToolButton(gtk.STOCK_GOTO_FIRST)
        self.first_button.connect('clicked',self.do_go_first)
        self.first_button.set_sensitive(False)
        self.toolbar.insert(self.first_button, -1)
        self.prev_button=gtk.ToolButton(gtk.STOCK_GO_BACK)
        self.prev_button.connect('clicked',self.do_go_prev)
        self.prev_button.set_sensitive(False)
        self.toolbar.insert(self.prev_button, -1)
        self.searcher = SearchBar()
        self.searcher.connect('need-completion',self.do_get_completion)
        self.searcher.connect('search', self.do_search)
        self.toolbar.insert(self.searcher,-1)
        self.toolbar.show_all()
        
    def cleanup(self, *args):
        self.win.unfullscreen()
        self.caches.save()
        self.bookmarks.load(merge=True)
        self.bookmarks.save()
        self.config['size']=self.win.get_size()
        self.config.save()
        gtk.main_quit()
        return False
    
    def destroy(self, widget):
        pass
    
    def replace_showbox(self,new):
        self.showbox.hide_all()
        self.align.remove(self.showbox)
        self.align.pack_start(new, expand=True, fill=True)
        self.align.reorder_child(new,2)
        self.showbox=new
        self.showbox.show_all()
    
    def searcher_callback(self, number, of):
        gobject.idle_add(self.status, 'fetching ' + str(number) + '/' + str(of))
        gobject.idle_add(self.progressbar.set_fraction, float(number) / float(of))
        gobject.idle_add(self.progressbar.set_text, str(float(number) / float(of) * 100) + '%')
    
    def do_search_thread(self,query,end_search=None):
        try:
            results = self.ytsearcher.search(query)
            if len(results)>0:
                self.build_widgets(results)
            else:
                self.history.newest().end_search.set()  
        except urllib2.URLError as e:
            gobject.idle_add(self.show_error_dialog,"Error", e.reason)
        finally:
            if end_search:
                end_search()
    
    def end_search(self):
        self.searching.clear()
        gobject.idle_add(self.progressbar.hide)
        gobject.idle_add(self.status, 'Finished')
    
    def build_widgets(self, results):
        videos = [(r,)for r in results]
        threader.thread_pool(target=self.get_image, args_ar=videos, callback=self.searcher_callback)
        for r in results:
            vw = VideoWidget(r,self.config['show_desc'])
            vw.connect('clicked', self.do_open_video)
            vw.connect('left-clicked', self.show_video_menu)
            vw.connect('middle-clicked', self.do_search_related)
            vw.show()
            gobject.idle_add(self.showbox.add, vw)
                    
    def do_search(self, entry):
        if self.searching.is_set():
            return
        self.searching.set()
        self.history.clear()
        self.prev_button.set_sensitive(False)
        self.first_button.set_sensitive(False)
        s=entry.get_text().strip()
        r=re.match(r'user:([\w\-]*) ?(.*)',s)
        if r and r.lastindex==2:
            user=r.group(1)
            s=None if len(r.group(1).strip())==0 else r.group(2)
            query=Connector.Query(offset=1,number=self.config['number-start'],query=s,user=user)
        else:
            query=Connector.Query(offset=1,number=self.config['number-start'],query=s)
        hobj=HistoryObject(query,self.config['number-start']+1,self.showbox)
        self.history.append(hobj)
        self.search(query)
        
    def do_search_related(self,widget,event):
        video=widget.get_video()
        query=Connector.Query(vid=video.get_id(), offset=1,number=self.config['number-start'])
        showbox = ShowBox()
        showbox.connect('scroll-end-event', self.do_next_search)
        hobj=HistoryObject(query,self.config['number-start']+1,showbox)
        self.replace_showbox(showbox)
        self.history.append(hobj)
        self.search(query)
        self.first_button.set_sensitive(True)
        self.prev_button.set_sensitive(True)
        
    def search(self, query):
        self.showbox.clear()
        self.showbox.handler_unblock_by_func(self.do_next_search)
        self.progressbar.show()
        t = threading.Thread(target=self.do_search_thread, args=(query,self.end_search,))
        t.start()
        
    def do_next_search(self, widget, a):
        hobj=self.history.newest()
        if self.searching.is_set() or hobj.end_search.is_set():
            return
        self.searching.set()
        self.progressbar.show()
        hobj=self.history.newest()
        hobj.lastquery.offset=hobj.lastsearchoffset
        hobj.lastsearchoffset += self.config['number']
        hobj.lastquery.number=self.config['number']
        t = threading.Thread(target=self.do_search_thread, args=(hobj.lastquery,self.end_search))
        t.start()
        
    def do_show_bookmarks(self,widget):
        self.showbox.clear()
        self.showbox.handler_block_by_func(self.do_next_search)
        results = self.bookmarks.get_videos()
        if len(results)>0:
            self.build_widgets(results)
            
    def do_show_about_dialog(self, widget):
        dialog = gtk.AboutDialog()
        try:
            import version
            dialog.set_version(version.VERSION + " on branch " + version.BRANCH)
        except ImportError:
            dialog.set_version("unknown version")
        dialog.set_program_name("youtube-show")
        dialog.set_website("http://github.com/Lunm0us/youtube-show")
        dialog.set_authors(["Lunm0us <blue.gene@web.de>"])
        dialog.set_logo(self.win.get_icon())
        dialog.set_icon(self.win.get_icon())
        dialog.run()
        dialog.destroy()

    def show_video_menu(self, widget, event):
        video = widget.get_video()
        menu = gtk.Menu()
        menu.widget=widget
        caches=gtk.Menu()
        for cache in reversed(self.caches.get_caches()):
            item = gtk.MenuItem(cache)
            item.connect('button-press-event', self.do_open_video_ext,video, cache)
            caches.append(item)
        item=gtk.MenuItem('Cache')
        item.set_submenu(caches)
        menu.append(item)
        item = gtk.MenuItem('Copy direct URL')
        item.connect('activate', self.do_copy_video_url, video)
        menu.append(item)
        item = gtk.MenuItem('Copy URL')
        item.connect('activate',self.do_copy_url, video)
        menu.append(item)
        item = gtk.MenuItem('Open browser')
        item.connect('activate',self.do_open_browser, video)
        menu.append(item)
        item =  gtk.MenuItem('Show Description')
        item.connect('activate',self.do_show_description,video)
        menu.append(item)
        vid=widget.get_video().get_id()
        if vid in self.bookmarks:
            s='Remove Bookmark'
        else:
            s='Bookmark'
        item = gtk.MenuItem(s)
        item.connect('activate',self.do_bookmark, video)
        menu.append(item)
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)

    def get_image(self, video):
            video.set_picture(self.ytconnector.get_picture_by_id(video.get_id()))
    
    def do_open_video(self, widget, event):
        play = self.config['allow_several'] or not self.viewer.is_playing()
        if play:
            self.win.grab_focus()
            url = self.get_video_url(widget.get_video())
            if not url:
                return
            try:
                self.viewer.view(url,widget.get_video().get_title())
            except Exception as e:
                self.show_error_dialog('Player Error', unicode(e))
        else:
            self.status('There is still a player running (if not press \'q\')')
    
    def do_open_video_ext(self, widget, event ,video, cache):
        play = self.config['allow_several'] or not self.viewer.is_playing()
        if play:
            url = self.get_video_url(video,cache)
            if not url:
                return
            self.viewer.view(url,video.get_title())
        else:
            self.status('There is still a player running (if not press \'q\')')

    def do_copy_video_url(self, widget, video):
        url = self.get_video_url(video)
        if not url:
            return
        clipboard = gtk.Clipboard()
        clipboard.set_text(url)
        del clipboard
        
    def do_copy_url(self, widget, video):
        url = video.get_url()
        clipboard = gtk.Clipboard()
        clipboard.set_text(url)
        del clipboard
        
    def do_open_browser(self, widget, video):
        url = video.get_url()
        webbrowser.open(url)
    
    def do_show_description(self, widget, video):
        vid = video.get_id()
        title = video.get_title()
        try:
            desc = self.ytconnector.get_description(vid)
            w,h = self.win.get_size()
            win = DescriptionWindow(desc)
            win.resize(int(w/2),int(h/2))
            win.set_title(title)
            win.show()
        except Connector.ConnectorException as e:
            self.show_error_dialog("Could not get video description", e.message)
    
    def do_bookmark(self, widget, video):
        if video.get_id() in self.bookmarks:
            self.bookmarks.remove(video)
        else:
            self.bookmarks.add(video)
    
    def do_configure(self, *args):
        win = Configer(self.win,self.config)
        win.connect('config-changed',self.config_changed_callback)
        win.show()
        
    def do_go_first(self,widget):
        if len(self.history)<2:
            return
        hobj = self.history.first()
        self.restore_search(hobj)
        sensitive = len(self.history)>1
        self.first_button.set_sensitive(sensitive)
        self.prev_button.set_sensitive(sensitive)
    
    def do_go_prev(self,widget):
        if len(self.history)<2:
            return
        hobj = self.history.prev()
        self.restore_search(hobj)
        sensitive = len(self.history)>1
        self.first_button.set_sensitive(sensitive)
        self.prev_button.set_sensitive(sensitive)
    
    def do_update_bookmarks(self,widget):
        vids = []
        for bookmark in self.bookmarks.get_videos():
            query = Connector.Query(query=str(bookmark.get_id()),offset=1,number=1)
            vids.append(self.ytsearcher.search(query)[0])
        for vid in vids:
            self.bookmarks.add(vid)
    
    def do_get_completion(self, source, txt):
        comps=self.ytsearcher.get_completions(txt)
        return comps
        
    def restore_search(self,hobj):
        self.replace_showbox(hobj.showbox)
    
    def status(self, text, prio=1):
        self.statusbar.push(prio, text)
        
    def on_key_press(self,widget,event):
        if event.keyval==gtk.keysyms.F11:
            self.toggle_fullscreen()
        if self.viewer.is_playing():
            if event.keyval==gtk.keysyms.q or event.keyval==gtk.keysyms.Q:
                if event.state & gtk.gdk.CONTROL_MASK:
                    self.viewer.stop_all()
                else:
                    self.viewer.stop()
            elif event.keyval==gtk.keysyms.Left:
                self.viewer.seek_back()
            elif event.keyval==gtk.keysyms.Right:
                self.viewer.seek_forward()
            elif event.keyval==gtk.keysyms.p or event.keyval== gtk.keysyms.space:
                self.viewer.pause()
            elif event.keyval==gtk.keysyms.Up:
                self.viewer.seek_forward_fast()
            elif event.keyval==gtk.keysyms.Down:
                self.viewer.seek_back_fast()
            else:
                self.viewer.communicate(unichr(gtk.gdk.keyval_to_unicode(event.keyval)))
    
    def config_changed_callback(self,widget,config):
        self.config=config
        self.config.save()
        self.apply_config()
    
    def apply_config(self):
        config=self.config
        self.ytconnector.apply_config(config)
        if 'player' in config:
            self.viewer.set_player(config['player'])
        else:
            self.viewer.set_player(None)
        if 'User-Agent' in config:
            useragent=config['User-Agent']
        else:
            useragent='Mozilla/5.0'
        self.downloader.addheaders=[('User-Agent',useragent)]
        self.viewer.add_field('u', useragent)
    
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.win.unfullscreen()
            self.is_fullscreen=False
        else:
            self.win.fullscreen()
            self.is_fullscreen=True

    def on_window_state_change(self, win,event):
        self.is_fullscreen = bool(gtk.gdk.WINDOW_STATE_FULLSCREEN & event.new_window_state)

    def get_video_url(self,vw,chache=None):
        try:
            url = self.ytconnector.get_url_by_id(vw.get_id(),chache)
        except Connector.ConnectorException as e:
            msg=e.message
            msg=msg.replace('<br/>','\n')
            while msg:
                i=msg.find('<')
                if i<0: break
                j=msg.find('>',i)
                msg=msg[0:i] + msg[j+1:]
            self.show_error_dialog('Could not get video URL','Could not get the video url:\n'+msg)
            return None
        return url
    
    def show_error_dialog(self,title,msg):
        label = gtk.Label(msg)
        label.set_line_wrap(True)
        dialog = gtk.Dialog(title,
                           None,
                           gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                           (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.vbox.pack_start(label)
        label.show()
        dialog.run()
        dialog.destroy()
    
    def main(self):
        gtk.main()

def main():
    try:
        gobject.threads_init()
        win = MainWindow()
        win.main()
    except Exception:
        label = gtk.Label('An Error occured:\n'+ traceback.format_exc())
        dialog = gtk.Dialog("Error",
                           None,
                           gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                           (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.vbox.pack_start(label)
        label.show()
        dialog.run()
        dialog.destroy()
        raise

if __name__ == '__main__':
    main()
