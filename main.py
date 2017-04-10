from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re

import requests
import random

from datetime import datetime,timedelta
import time
#import urllib
import HTMLParser
import xbmcplugin
#import xml.etree.ElementTree as ET
#import sqlite3
import os
#import shutil
#from rpc import RPC
from types import *

plugin = Plugin()
big_list_view = False


def log(v):
     xbmc.log(repr(v))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")


def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

@plugin.route('/add_playlist')
def add_playlist():
    playlists = plugin.get_storage('playlists')
    d = xbmcgui.Dialog()
    name = d.input("Playlist Name:")
    if not name:
        return
    type = d.select("Playlist Type",["URL", "File"])
    if type == -1:
        return
    if type == 0:
        playlist = d.input("Playlist (%s) Url:" % name)
    else:
        playlist = d.browse(1, 'Playlist', 'files', '', False, False, 'special://home/')
    if playlist:
        playlists[name] = playlist
    xbmc.executebuiltin('Container.Refresh')


@plugin.route('/remove_playlist')
def remove_playlist():
    playlists = plugin.get_storage('playlists')
    playlist_list = sorted(playlists)
    d = xbmcgui.Dialog()
    which = d.select("Remove playlist",playlist_list)
    if which == -1:
        return
    playlist = playlist_list[which]
    del playlists[playlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/remove_this_playlist/<playlist>')
def remove_this_playlist(playlist):
    playlists = plugin.get_storage('playlists')
    del playlists[playlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/clear_playlists')
def clear_playlists():
    playlists = plugin.get_storage('playlists')
    playlists.clear()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/import_playlists')
def import_playlists():
    playlists = plugin.get_storage('playlists')
    f = xbmcvfs.File('special://profile/addon_data/plugin.video.playlist.player/playlists.ini','rb')
    lines = f.read().splitlines()
    for line in lines:
        playlist_url = line.split('=',1)
        if len(playlist_url) == 2:
            name = playlist_url[0]
            url = playlist_url[1]
            playlists[name] = url
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/export_playlists')
def export_playlists():
    playlists = plugin.get_storage('playlists')

    f = xbmcvfs.File('special://profile/addon_data/plugin.video.playlist.player/playlists.ini','wb')
    for name in sorted(playlists):
        url = playlists[name]
        s = "%s=%s\n" % (name,url)
        f.write(s)
    f.close()

@plugin.route('/add_channel')
def add_channel():
    channels = plugin.get_storage('channels')
    d = xbmcgui.Dialog()
    channel = d.input("Add Channel")
    if channel:
        channels[channel] = ""
    xbmc.executebuiltin('Container.Refresh')


@plugin.route('/remove_channel')
def remove_channel():
    channels = plugin.get_storage('channels')
    channel_list = sorted(channels)
    d = xbmcgui.Dialog()
    which = d.select("Remove Channel",channel_list)
    if which == -1:
        return
    channel = channel_list[which]
    del channels[channel]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/remove_this_channel/<channel>')
def remove_this_channel(channel):
    channels = plugin.get_storage('channels')
    del channels[channel]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/clear_channels')
def clear_channels():
    channels = plugin.get_storage('channels')
    channels.clear()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/import_channels')
def import_channels():
    channels = plugin.get_storage('channels')
    d = xbmcgui.Dialog()
    filename = d.browse(1, 'Import Channels', 'files', '', False, False, 'special://home/')
    if not filename:
        return
    if filename.endswith('.ini'):
        lines = xbmcvfs.File(filename,'rb').read().splitlines()
        for line in lines:
            if not line.startswith('[') and not line.startswith('#') and "=" in line:
                channel_url = line.split('=',1)
                if len(channel_url) == 2:
                    name = channel_url[0]
                    channels[name] = ""
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/stream_search/<channel>')
def stream_search(channel):
    playlists = plugin.get_storage('playlists')

    streams = {}
    for playlist in sorted(playlists.keys()):
        if playlist not in playlists:
            continue
        url = playlists[playlist]
        streams[playlist] = {}
        #try:data = requests.get(url, verify=False).content
        data = xbmcvfs.File(url,'rb').read()
        '''
        except:
            if plugin.get_setting('delete') == 'true':
                log("Delete: "+playlist)
                del playlists[playlist]
            continue
        '''
        if not data:
            continue
        matches = re.findall(r'#EXTINF:.*?,(.*?)\n(.*?)\n',data,flags=(re.DOTALL | re.MULTILINE))
        for name,url in matches:
            streams[playlist][url.strip()] = name.strip()

    channel_search = channel.lower().replace(' ','')
    stream_list = []
    for id in sorted(streams):
        files = streams[id]
        for f in sorted(files, key=lambda k: files[k]):
            label = files[f]
            label_search = label.lower().replace(' ','')
            if label_search in channel_search or channel_search in label_search:
                stream_list.append((id,f,label))
    labels = ["[%s] %s" % (x[0],x[2]) for x in stream_list]
    if plugin.get_setting('dialog') == 'true':
        d = xbmcgui.Dialog()
        which = d.select(channel, labels)
        if which == -1:
            return
        stream_name = stream_list[which][2]
        stream_link = stream_list[which][1]
        plugin.set_resolved_url(stream_link)
    else:
        items = []
        for (playlist,url,label) in sorted(stream_list, key=lambda x: (x[0],x[2])):
            context_items = []
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove playlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_this_playlist, playlist=playlist))))
            if plugin.get_setting('prefix.playlist') == 'true':
                label = "[%s] %s" % (playlist,label)
            items.append(
            {
                'label': label,
                'path': plugin.url_for('play_live',url=url, name=label, thumbnail=get_icon_path('tv')),
                'thumbnail':get_icon_path('tv'),
                'is_playable': True,
                'context_menu': context_items,
            })
        return items

@plugin.route('/export_channels')
def export_channels():
    channels = plugin.get_storage('channels')

    f = xbmcvfs.File('special://profile/addon_data/plugin.video.playlist.player/channels.ini','wb')
    for channel in sorted(channels):
        url = plugin.url_for('stream_search',channel=channel)
        s = "%s=%s\n" % (channel,url)
        f.write(s)
    f.close()

@plugin.route('/channel_player')
def channel_player():
    channels = plugin.get_storage("channels")

    items = []
    for channel in sorted(channels):
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Channel', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_channel))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove Channel', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_this_channel, channel=channel))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Import Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(import_channels))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Export Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(export_channels))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Clear Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(clear_channels))))
        items.append(
        {
            'label': channel,
            'path': plugin.url_for('stream_search',channel=channel),
            'thumbnail':get_icon_path('tv'),
            'is_playable': plugin.get_setting('dialog') == 'true',
            'context_menu': context_items,
        })
    return items
    
@plugin.route('/play_live/<url>/<name>/<thumbnail>')
def play_live(url,name,thumbnail):
    html = xbmcvfs.File(url,'rb').read()
    match=re.compile('#EXT-X-STREAM-INF:.*?BANDWIDTH=([0-9]*).*?\n(.+?)\n',flags=(re.MULTILINE)).findall(html)
    max_bandwidth = plugin.get_setting('max.bandwidth')
    if max_bandwidth:
        max_bandwidth = int(max_bandwidth)*1000
    else:
        max_bandwidth = 1000000000
    for bandwidth,url in sorted(match, key=lambda x: int(x[0]), reverse=True):
        if int(bandwidth) <= max_bandwidth:
            log(url)
            item = {
                'label' : name,
                'thumbnail' : thumbnail,
                'path' : url,
                'is_playable' : True
            }
            return plugin.set_resolved_url(item)

@plugin.route('/playlist_listing/<playlist>')
def playlist_listing(playlist):
    playlists = plugin.get_storage('playlists')
    url = playlists[playlist]
    data = xbmcvfs.File(url,'rb').read()
    #data = requests.get(url, verify=False).content
    matches = re.findall(r'#EXTINF:.*,(.*?)\n(.*?)\n',data,flags=(re.MULTILINE))
    urls = {}
    for name,url in matches:
        urls[url.strip()] = name.strip()
    items = []
    for url in sorted(urls, key=lambda x: urls[x]):
        name = urls[url]
        context_items = []
        items.append(
        {
            'label': name,
            'path': plugin.url_for('play_live',url=url, name=name, thumbnail=get_icon_path('tv')),
            'thumbnail':get_icon_path('tv'),
            'is_playable': True,
        })
    return items

@plugin.route('/playlists')
def playlists():
    playlists = plugin.get_storage('playlists')
    items = []
    for playlist in sorted(playlists):
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add playlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_playlist))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove playlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_this_playlist, playlist=playlist))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Import playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(import_playlists))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Export playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(export_playlists))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Clear playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(clear_playlists))))
        items.append(
        {
            'label': playlist,
            'path': plugin.url_for('playlist_listing',playlist=playlist),
            'thumbnail':get_icon_path('tv'),
            'context_menu': context_items,
        })
    return items

@plugin.route('/')
def index():
    items = []

    context_items = []
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Playlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_playlist))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove Playlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_playlist))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Import playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(import_playlists))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Export playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(export_playlists))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Clear Playlists', 'XBMC.RunPlugin(%s)' % (plugin.url_for(clear_playlists))))
    items.append(
    {
        'label': "Playlists",
        'path': plugin.url_for('playlists'),
        'thumbnail':get_icon_path('tv'),
        'context_menu': context_items,
    })

    context_items = []
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Channel', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_channel))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove Channel', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_channel))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Import Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(import_channels))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Export Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(export_channels))))
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Clear Channels', 'XBMC.RunPlugin(%s)' % (plugin.url_for(clear_channels))))
    items.append(
    {
        'label': "Channels",
        'path': plugin.url_for('channel_player'),
        'thumbnail':get_icon_path('tv'),
        'context_menu': context_items,
    })

    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)