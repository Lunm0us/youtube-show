# youtube-show

The original idea behind this programm was, to give raspberry-pi users
an alternative to watching YouTube videos in the browser. But it (should) work on any system running python with pygtk and having an
internet connection.

Another programm with the same idea behind it is [raspytube](https://github.com/bbond007/raspytube). So if you are looking for a hardware
accelerated fancy YouTube browser see there.

## Requirements 
 * python2.7
 * pygtk
 * omxplayer or another player which is capable of playing mp4/h.246 or webm/vp8
videos and can open http streams given on the command line. (omxplayer, ffplay/avplay and
vlc are known to work, mplayer and others should also work but need further configuration see [Using other players](#Using other Players))

Therefore executing
```sh
sudo apt-get install pygtk omxplayer```
to install pygtk and omxplayer, should be enough for raspberry-pi users.

## Installation
Open a terminal and go to the directory where the youtube-show files are. Then type
```sh
./pack pack
sudo ./pack install```
If you don't get an error message you should have a packed and executable version in
/usr/local/bin/youtube-show.

## Usage
Type a query into the search field and press enter (an empty query is also valid). You may
also search for videos by a special user by typing
"user:username"

If you left-click on a video you get a menu with several entries. The first "Caches" lets you decide from which YouTube-cache you want to receive the video from.
So if you have a very slow connection eventough it is usually quite fast, you might want to try a different cache server than the one specified by YouTube.

You can open your bookmarks by clicking File->Bookmarks and you can add or remove them in
the left-click menu of a video.

## Using other players
If you want to use a custom player (anything different from omxplayer, ffplay, avplay or vlc)
open the Preference dialog (File->Preferences) and enter the command to execute in the player
field but use %f for the filename. May also use %t for the video-title (e.g. window title) and %u for the user-agent that should be used in requests.
E.g. ffplay uses:
```ffplay -autoexit -window-title %t -infbuf -user-agent %u %f```

## Acknowledgements
Most of the youtube connection part was taken from [youtube-dl](https://github.com/rg3/youtube-dl)

## Issues
 * playlists are not supported yet
