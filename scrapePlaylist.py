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
    # Scrape the title and artist from the item's head block
    item_head = entry.find('div', {'class': 'item_head'})
    song_title = item_head.contents[0].strip()
    song_artist = item_head.find('a').contents[0].strip()
    
    # Slap a regex (ugh) on the player JavaScript to grab the song URL
    script_text = entry.find('script').contents[0]
    song_url = re.search('s3\.addVariable\("file","(?P<url>.*)"\);', script_text).group('url')
    
    # Get the song's ID and URL from the item's download block
    item_download = entry.find('div', {'class': 'item_download'})
    song_id = item_download.p["id"][7:]
    relative_url = item_download.find_all('a')[1]["href"]
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