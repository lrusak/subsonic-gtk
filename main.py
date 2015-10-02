#!/usr/bin/env python3
# -*- coding: utf-8 -*

from gi.repository import Gtk, Gio, GdkPixbuf, GLib
from pysonic.libsonic import connection
import vlcpython.generated.vlc as vlc
import urllib.parse
import os
import html
import time

schema_source = Gio.SettingsSchemaSource.new_from_directory(
                os.path.expanduser("schemas"),
                Gio.SettingsSchemaSource.get_default(),
                False,
                )

schema = schema_source.lookup('apps.subsonic-gtk-py', False)
settings = Gio.Settings.new_full(schema, None, None)

class MainWindow:
    def __init__(self):
                  
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        self.eventManager = self.player.event_manager()
        self.eventManager.event_attach(vlc.EventType.MediaPlayerEndReached, self.song_is_over)
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file("subsonic-gtk.glade")
        self.builder.connect_signals(self)

        self.revealer = self.builder.get_object("navigation_menu")
        
        self.notebook = self.builder.get_object("main_view")

        self.artist_list = self.builder.get_object("artist_list")
        self.artists = self.builder.get_object("artists")
    
        self.album_list = self.builder.get_object("album_list")
        self.albums = self.builder.get_object("albums")
                
        self.song_list = self.builder.get_object("song_list")
        self.songs = self.builder.get_object("songs")
        
        self.queue_list = self.builder.get_object("queue_list")
        self.queue = self.builder.get_object("queue")
        
        self.queue_add_all_button = self.builder.get_object('button10')
        self.queue_clear_all_button = self.builder.get_object('button11')
        self.refresh_button = self.builder.get_object('button12')

        self.play_button = self.builder.get_object("button8")

        self.pause_image = Gtk.Image.new_from_icon_name('gtk-media-pause', 0)
        self.play_pause_button = self.builder.get_object('button8')
        self.play_image = self.builder.get_object('image6')
        
        self.next_button = self.builder.get_object('button9')
        
        self.now_playing_art = self.builder.get_object('image4')
        self.now_playing_label = self.builder.get_object('label12')
        
        self.status_bar = self.builder.get_object('statusbar1')
        self.context = self.status_bar.get_context_id("status")
        
        self.progress_bar = self.builder.get_object('progressbar1')
        
        self.current_track = None
        self.scrobbled = False

        self.window = self.builder.get_object("window1")
        self.window.show_all()
        
        self.reset_timer = False
        self.count = 0
        self.duration = 100
        self.timer = GLib.timeout_add(self.duration, self.tickEvent)
        
        user = settings.get_string('user')
        passwd = settings.get_string('passwd')
        server = settings.get_string('server')
        path = settings.get_string('path')
        port = settings.get_int('port')
        insecure = settings.get_boolean('insecure')
    
        try:
            self.connection = connection.Connection(server, user, passwd, port, path, 'subsonic-gtk', insecure=insecure)
            if not self.connection.ping():
                self.activate_page_settings()
        except: pass
                            
    def on_window_destroy(self, *args):
        Gtk.main_quit(*args)

    def activate_sidebar(self, *args):
        if self.revealer.get_reveal_child():
            self.revealer.set_reveal_child(False)
        else:
            self.revealer.set_reveal_child(True)

    def activate_page_home(self, *args):
        self.notebook.set_current_page(0)
        self.revealer.set_reveal_child(False)

    def activate_page_library(self, *args):
        self.notebook.set_current_page(1)
        self.revealer.set_reveal_child(False)
        self.queue_add_all_button.set_visible(False)
        self.queue_clear_all_button.set_visible(False)
        
        alphabet = self.connection.getIndexes()
        for index1,letter in enumerate(alphabet['indexes']['index']):
            if len(alphabet['indexes']['index'][index1]['artist']) > 2 or type(alphabet['indexes']['index'][index1]['artist']) is list:
                for index2,artists in enumerate(alphabet['indexes']['index'][index1]['artist']):
                    mid = int(alphabet['indexes']['index'][index1]['artist'][index2]['id'])
                    name = str(alphabet['indexes']['index'][index1]['artist'][index2]['name'])
                    self.artists.append([mid, html.unescape(name)])
            else:
                    mid = int(alphabet['indexes']['index'][index1]['artist']['id'])
                    name = str(alphabet['indexes']['index'][index1]['artist']['name'])
                    self.artists.append([mid, html.unescape(name)])
               
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("artist", renderer, text=1)
        if len(self.artist_list.get_columns()) is 0:
            self.artist_list.append_column(column)
        
    def on_artist_select(self, treeview, path, *args):
        self.albums.clear()
        row = self.artists.get_iter(path)
        mid = self.artists.get_value(row, 0)
        self.notebook.set_current_page(5)

        self.album_list.set_pixbuf_column(0)
        self.album_list.set_text_column(1)
        
        albums = self.connection.getMusicDirectory(mid)
        
        for index,album_list in enumerate(albums['directory']['child']):
            if type(albums['directory']['child']) is list:
                mid = int(albums['directory']['child'][index]['id'])
                album = str(albums['directory']['child'][index]['album'])
                coverArt = int(albums['directory']['child'][index]['coverArt'])
                stop = False
                
            else:
                mid = int(albums['directory']['child']['id'])
                album = str(albums['directory']['child']['album'])
                coverArt = int(albums['directory']['child']['coverArt'])
                stop = True
                
            image = self.connection.getCoverArt(coverArt, size=200).read()        
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image)
            loader.close()
            pixbuf = loader.get_pixbuf()
    
            self.albums.append([pixbuf, html.unescape(album), mid, coverArt])
            if stop:
                break
                
    def on_album_select(self, iconview, path):
        self.songs.clear()
        self.queue_add_all_button.set_visible(True)
        row = self.albums.get_iter(path)
        mid = self.albums.get_value(row, 2)
        self.notebook.set_current_page(6)
        
        songs = self.connection.getMusicDirectory(mid)
        for index,song_list in enumerate(songs['directory']['child']):
            self.songs.append([html.unescape(songs['directory']['child'][index]['album']), 
                               songs['directory']['child'][index]['albumId'], 
                               html.unescape(songs['directory']['child'][index]['artist']), 
                               songs['directory']['child'][index]['bitRate'], 
                               songs['directory']['child'][index]['coverArt'], 
                               songs['directory']['child'][index]['id'], 
                               songs['directory']['child'][index]['path'], 
                               songs['directory']['child'][index]['size'], 
                               html.unescape(songs['directory']['child'][index]['title']), 
                               songs['directory']['child'][index]['track']
                               ])

        track = Gtk.CellRendererText()
        title = Gtk.CellRendererText()
        artist = Gtk.CellRendererText()
        
        column = Gtk.TreeViewColumn("tracks")

        column.pack_start(track, True)
        column.pack_start(title, True)
        column.pack_start(artist, True)
        column.add_attribute(track, "text", 9)
        column.add_attribute(title, "text", 8)
        column.add_attribute(artist, "text", 2)
        
        if len(self.song_list.get_columns()) is 0:
            self.song_list.append_column(column)
            
    def add_all(self, *args):
        self.add_to_queue(None, Gtk.TreePath(0))
        
    def clear_all(self, *args):
        self.stop()
        self.queue.clear()
            
    def add_to_queue(self, treeview, path, *args):
        self.queue_add_all_button.set_visible(False)
        self.queue_clear_all_button.set_visible(True)
        self.notebook.set_current_page(7)
        
        for remove in reversed(range(path.get_indices()[0])):
            self.songs.remove(self.songs.get_iter(remove))
                        
        for row in self.songs:
            self.queue.append(row[:])
        
        track = Gtk.CellRendererText()
        title = Gtk.CellRendererText()
        artist = Gtk.CellRendererText()
        
        column = Gtk.TreeViewColumn("queue")

        column.pack_start(track, True)
        column.pack_start(title, True)
        column.pack_start(artist, True)
        
        column.add_attribute(track, "text", 9)
        column.add_attribute(title, "text", 8)
        column.add_attribute(artist, "text", 2)
        
        if len(self.queue_list.get_columns()) is 0:
            self.queue_list.append_column(column)
        
        #todo, fix when adding queue buttons
        if not self.player.is_playing():
            self.queue_list.set_cursor(Gtk.TreePath(0))
            self.now_playing(Gtk.TreePath(0))
            self.play()
        
    def play(self):
        self.eventManager = self.player.event_manager()
        self.eventManager.event_attach(vlc.EventType.MediaPlayerEndReached, self.song_is_over)
        
        if not self.player.is_playing():
            if self.player.get_state() == vlc.State.Ended:
                self.player.stop() #Restart it
            self.player.play()
    
    def stop(self):
        self.player.stop()

    def on_song_select(self, treeview, path, *args):
        self.stop()
        self.now_playing(path)
        self.play()
        self.queue_list.set_cursor(path)
        self.next_track
        
    def song_is_over(self, event):
        try:
            new_path = Gtk.TreePath(int(self.current_track.to_string()) + 1)
            self.now_playing(new_path)
            self.play()
            self.queue_list.set_cursor(new_path)
        except ValueError:
            pass
                
    def previous_track(self, *args):
        try:
            self.stop()
            new_path = Gtk.TreePath(int(self.current_track.to_string()) -1)
            self.now_playing(new_path)
            self.play()
            self.queue_list.set_cursor(new_path)
        except TypeError:
            pass
            
    def next_track(self, *args):
        try:
            self.stop()
            new_path = Gtk.TreePath(int(self.current_track.to_string()) + 1)
            self.now_playing(new_path)
            self.play()
            self.queue_list.set_cursor(new_path)
        except ValueError:
            pass

    def now_playing(self, path):
        row = self.queue.get_iter(path)
        sid = self.queue.get_value(row, 5)

        self.current_track = path
        self.scrobbled = False

        row = self.queue.get_iter(path)
        coverArt = self.queue.get_value(row, 4)
        album_label = self.queue.get_value(row, 0)

        image = self.connection.getCoverArt(coverArt, size=400).read()        
        loader = GdkPixbuf.PixbufLoader()
        loader.write(image)
        loader.close()
        pixbuf = loader.get_pixbuf()
        
        self.now_playing_art.set_from_pixbuf(pixbuf)
        self.now_playing_label.set_text(album_label)
        
        self.stream(sid)
                
    def stream(self, sid):
        self.player = self.instance.media_player_new()
        
        getVars = {'id': sid,
                   'c': 'subsonic-gtk',
                   'u': self.connection._username,
                   'p': self.connection._rawPass,
                   'v': self.connection.apiVersion
                   }

        url = self.connection._baseUrl + ':' + str(self.connection._port) + '/' + self.connection._serverPath + '/stream.view' + '?'
        song = url + urllib.parse.urlencode(getVars)
                
        self.player.set_mrl(song)
        self.play_pause_button.set_image(self.pause_image)
        
        self.connection.scrobble(sid, submission=False)

    def timer(self):
        while True:
            GLib.idle_add(self.tickEvent, i=True)
            time.sleep(0.1)

    def tickEvent(self):
        self.count += 1
        
        state = self.player.get_state()
        
        #Update the display state
        if state == vlc.State.Playing:
            self.push_message('Playing...')
        elif state == vlc.State.Stopped:
            self.push_message('Stopped...')
        elif state == vlc.State.Paused:
            self.push_message('Paused...')
        else:
            pass
        
        fraction = self.player.get_position()
        self.progress_bar.set_fraction(fraction)
        
        if self.current_track is not None:
            try:
                row = self.queue.get_iter(self.current_track)
                sid = self.queue.get_value(row, 5)
        
                if ('%.2f' % fraction) == '0.50' and not self.scrobbled:            
                    self.connection.scrobble(sid, submission=True)
                    self.scrobbled = True
                    print('scrobbled!')
            except ValueError:
                pass
                    
        return True
    
    def push_message(self, message): 
        self.status_bar.push(self.context, message)
        
    def play_pause(self, *args):
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_button.set_image(self.play_image)
        else:
            self.player.play()
            self.play_pause_button.set_image(self.pause_image)
    
    def activate_page_playlists(self, *args):
        self.notebook.set_current_page(2)
        self.revealer.set_reveal_child(False)

    def activate_page_chat(self, *args):
        self.notebook.set_current_page(3)
        self.revealer.set_reveal_child(False)
        
    def activate_page_nowPlaying(self, *args):
        self.notebook.set_current_page(7)
        self.revealer.set_reveal_child(False)
        self.queue_add_all_button.set_visible(False)
        self.queue_clear_all_button.set_visible(True)

    def activate_page_settings(self, *args):
        self.notebook.set_current_page(4)
        self.revealer.set_reveal_child(False)
        
        self.user_field = self.builder.get_object('entry2')
        self.passwd_field = self.builder.get_object('entry1')
        self.server_field = self.builder.get_object('entry3')
        self.path_field = self.builder.get_object('entry4')
        self.port_field = self.builder.get_object('entry5')
        self.insecure_field = self.builder.get_object('checkbutton1')
        
        self.user_field.set_text(settings.get_string('user'))
        self.passwd_field.set_text(settings.get_string('passwd'))
        self.server_field.set_text(settings.get_string('server'))
        self.path_field.set_text(settings.get_string('path'))
        self.port_field.set_text(str(settings.get_int('port')))
        self.insecure_field.set_active(settings.get_boolean('insecure'))
        
    def on_settings_changed(self, entry):
        settings.set_string('user', self.user_field.get_text())
        settings.set_string('passwd', self.passwd_field.get_text())
        settings.set_string('server', self.server_field.get_text())
        settings.set_string('path', self.path_field.get_text())
        settings.set_int('port', int(self.port_field.get_text()))
        settings.set_boolean('insecure', self.insecure_field.get_active())
        
        user = settings.get_string('user')
        passwd = settings.get_string('passwd')
        server = settings.get_string('server')
        path = settings.get_string('path')
        port = settings.get_int('port')
        insecure = settings.get_boolean('insecure')
        
        self.connection = connection.Connection(server, user, passwd, port, path, 'subsonic-gtk', insecure=insecure)
        
if __name__ == '__main__':
    MainWindow()
    Gtk.main() 
    