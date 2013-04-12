from bs4 import BeautifulSoup
import urllib2
import re


def getTracker(compoId):
    scraper = CompoWebScraper(compoId)
    return CompoTracker(scraper)

class CompoTracker:
    def __init__(self, scraper):
        self.scraper = scraper
        self.songList = self.scraper.FetchSongList()
        
    def GetSong(self, position):
        return self.songList[position]
    
    def CountSongs(self):
        return len(self.songList)
    
    def UpdateSongList(self, bookmark, changeIndex=None):
        currentList = self.songList
        updatedList = self.scraper.FetchSongList()
        
        # Iterate through every song in the current list and make sure it still exists in the
        #   new list. (Entries will never be added to the middle of an existing list, only
        #   removed.) For announcement purposes, track the first change we've encountered that's
        #   past the bookmark.
        currentListIndex = 0; updatedListIndex = 0
        while currentListIndex < len(currentList):
            #if updatedListIndex >= updatedList.Length():
            #    if bookmark > updatedList.Length():
            #        bookmark = updatedList.Length()
            #    break
            if currentList[currentListIndex]['url'] != updatedList[updatedListIndex]['url']:
                # Something has been deleted from the list!
                if bookmark >= updatedListIndex:
                    # The bookmark is after the deletion, update it
                    print "updating bookmark"
                    bookmark -= 1
                    
                if updatedListIndex >= bookmark and (changeIndex == None or changeIndex > updatedListIndex):
                    # We've encountered a change after the bookmark and we either haven't seen a change or
                    #   our previously seen change is further down the list, so record this as the first
                    #   available change
                    changeIndex = updatedListIndex
                elif updatedListIndex <= bookmark and changeIndex != None and changeIndex >= updatedListIndex:
                    # The deletion is before the bookmark and we have a recorded change down the list, update it
                    changeIndex -= 1
                
                # Advance the current list, but not the updated list, since something's been deleted
                #   from the current list.
                currentListIndex += 1
            else:
                # Nothing's been deleted, advance both lists
                currentListIndex += 1
                updatedListIndex += 1
        
        # If there's still more to the updated list after scanning through the current list, there's
        #   additions to the list. If we haven't recorded a change yet, do so.
        if updatedListIndex < len(updatedList) and changeIndex == None:
            changeIndex = updatedListIndex + 1
            
        self.songList = updatedList
            
        return {
            "updatedBookmark": bookmark,
            "changeIndex": changeIndex,
        }
        
class CompoWebScraper():
    def __init__(self, compoId):
        self.compoId = compoId
    
    def FetchSongList(self):
        url = 'http://compo.thasauce.net/rounds/view/%s' % self.compoId
        soup = BeautifulSoup(urllib2.urlopen(url).read())
        return [self.ParseEntry(entry) for entry in soup.find_all('div', {'class': 'item'})]
    
    def ParseEntry(self, entry):
        # Scrape the title and artist from the item block
        item_head = entry.find('div', {'class': 'item_head'})
        song_title = item_head.contents[0].strip()
        song_artist = item_head.find('a').contents[0].strip()
        
        # Slap a regex (ugh) on the player JavaScript to grab the song URL
        script_text = entry.find('script').contents[0]
        song_url = re.search('s3\.addVariable\("file","(?P<url>.*)"\);', script_text).group('url')
        
        return {'title': song_title, 'artist': song_artist, 'url': ''.join([base_url, song_url])}
