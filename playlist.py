class Track:
    def __init__(self, id, title, artist, url, description):
        self.id = id
        self.title = title
        self.artist = artist
        self.url = url
        self.description = description
    
    def __eq__(self, other):
        if isinstance(other, Track):
            return self.id == other.id
        return NotImplemented
    
    def __ne__(self, other):
        value = self.__eq__(other)
        if value == NotImplemented:
            return value
        return not value

    def __str__(self):
        return "%s - %s"%(self.artist, self.title)
        
class Playlist:
    def __init__(self):
        self.tracks = []
    
    def AddTrack(self, track):
        self.tracks.append(track)
        
    def GetTrack(self, position):
        return self.tracks[position]
    
    def Length(self):
        return len(self.tracks)
    
def computeNewTrackIndex(originalPlaylist, updatedPlaylist, currentTrackIndex):
    # Iterate through every song in the current list and make sure it still exists in the
    #   new list. (Entries will never be added to the middle of an existing list, nor
    #   will they be re-ordered, only removed from the middle or added to the end.)
    originalSweepIndex = 0; updatedSweepIndex = 0;
    while originalSweepIndex < originalPlaylist.Length():
        if updatedSweepIndex >= updatedPlaylist.Length():
            # Tracks at the end of the original playlist were deleted from the updated playlist, so
            #   we've run out of tracks! If the current track index is past the length of the updated
            #   playlist, return the length of the updated playlist.
            if currentTrackIndex > updatedPlaylist.Length():
                currentTrackIndex = updatedPlaylist.Length()
            break
        elif originalPlaylist.GetTrack(originalSweepIndex) != updatedPlaylist.GetTrack(updatedSweepIndex):
            # The song from the original playlist doesn't match the updated playlist! This can only
            #   happen if a song from the original playlist has been deleted.
            
            if currentTrackIndex > updatedSweepIndex:
                # The index of the currently playing track is past the current index, step it back
                #   so that we don't skip a song.
                currentTrackIndex -= 1
            
            # Advance the current list, but not the current list; again, we'll only ever have deleted
            #   tracks in the middle of the updated list, not new tracks.
            originalSweepIndex += 1
        else:
            # Nothing's been deleted, advance both lists
            originalSweepIndex += 1
            updatedSweepIndex += 1
    
    return currentTrackIndex

# "Unit tests" to make sure this functionality works as intended.
def runTests():
    # Check to make sure Track class functions work as intended
    def trackTest():
        testTrack = Track("id", "foo", "bar", "baz", "description")
        assert testTrack.id == "id"
        assert testTrack.title == "foo"
        assert testTrack.artist == "bar"
        assert testTrack.url == "baz"
        assert testTrack.description == "description"
        
        equalTrack = Track("equal", "track", "artist", "url", "description")
        notequalTrack = Track("notequal", "track", "artist", "url", "description")
        assert testTrack == equalTrack
        assert testTrack != notequalTrack
        assert not (testTrack != equalTrack)
        assert not (testTrack == notequalTrack)
    trackTest()
    print "Track test passed successfully."
    
    # Check to make sure Playlist class functions work as intended
    def playlistTest():
        testPlaylist = Playlist()
        assert testPlaylist.Length() == 0
        
        testTrack = Track("id", "foo", "bar", "baz", "description")
        testPlaylist.AddTrack(testTrack)
        assert testPlaylist.Length() == 1
    playlistTest()
    print "Playlist test passed successfully."
    
    # Check to make sure playlist comparison functionality works
    def playlistComparisonTest():
        originalPlaylist = Playlist()
        originalPlaylist.AddTrack(Track("a", "a", "a", "a", "a"))
        originalPlaylist.AddTrack(Track("b", "b", "b", "b", "b"))
        originalPlaylist.AddTrack(Track("c", "c", "c", "c", "c"))
        originalPlaylist.AddTrack(Track("d", "d", "d", "d", "d"))
        
        newPlaylist = Playlist()
        newPlaylist.AddTrack(Track("a", "a", "a", "a", "a"))
        newPlaylist.AddTrack(Track("c", "c", "c", "c", "c"))
        
        assert computeNewTrackIndex(originalPlaylist, newPlaylist, 0) == 0
        assert computeNewTrackIndex(originalPlaylist, newPlaylist, 1) == 1
        assert computeNewTrackIndex(originalPlaylist, newPlaylist, 2) == 1
        assert computeNewTrackIndex(originalPlaylist, newPlaylist, 3) == 2
    playlistComparisonTest()
    print "Playlist comparison test passed successfully."

if __name__ == "__main__":
    runTests()