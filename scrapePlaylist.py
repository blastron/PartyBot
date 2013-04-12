from bs4 import BeautifulSoup
import urllib2
import re

from playlist import Track, Playlist
base_url = 'http://compo.thasauce.net'

def scrapePlaylist(compoId):
    url = 'http://compo.thasauce.net/rounds/view/%s' % compoId
    soup = BeautifulSoup(urllib2.urlopen(url).read())
    
    newPlaylist = Playlist()
    for parsedTrack in [parseEntry(rawTrack) for rawTrack in soup.find_all('div', {'class': 'item'})]:
        newPlaylist.AddTrack(parsedTrack)
    return newPlaylist

def parseEntry(entry):
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