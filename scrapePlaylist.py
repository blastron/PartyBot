from bs4 import BeautifulSoup
import urllib2
import re

from playlist import Track, Playlist
base_url = 'http://compo.thasauce.net'


def parse_playlist(playlist_html):
    soup = BeautifulSoup(playlist_html)

    new_playlist = Playlist()
    for parsedTrack in [parse_entry(rawTrack) for rawTrack in soup.find_all('div', {'class': 'item'})]:
        new_playlist.AddTrack(parsedTrack)
    return new_playlist


def parse_entry(entry):
    # Grab some details from data attributes of item and it's children
    song_id = entry["data-id"]
    song_title = entry["data-title"]
    song_artist = entry["data-author"]

    download_link = entry.find('a', {'class': 'song-download'})
    relative_url = download_link["data-file"]
    song_url = ''.join([base_url, relative_url])
    
    # Get the song's description from the description block
    item_desc = entry.find('div', {'class': 'item_desc'})
    song_description = item_desc.get_text()

    return Track(song_id, song_title, song_artist, song_url, song_description)

if __name__ == "__main__":
    playlist = scrapePlaylist("OHC220")
    for song in playlist.tracks:
        print "----------"
        print song.id
        print song.title
        print song.artist
        print song.url
        print song.description
    print "----------"
    print "%i songs total."%(len(playlist.tracks))