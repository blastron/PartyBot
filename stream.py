
import shout
import sys
import string
import time

import threading

class ShoutcastStreamer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        
        self.nextFile = None
        self.needsStop = False
        self.needsAbort = False
        
        self.controlLock = threading.Lock()
        
        self._currentlyPlaying = False
        self.playLock = threading.Lock()
        
        self._shoutcaster = shout.Shout()
        print "Initializing new shoutcast interface, using libshout version %s" % shout.version()
        
        self._shoutcaster.password = 'crypsis'
        self._shoutcaster.mount = '/partybot'
        self._shoutcaster.format = 'mp3'
        
        self._shoutcaster.name = 'PartyBot Jukebox'
        
        self._inputStream = None
        self._silenceStream = None
        
    def Play(self, filename):
        self.controlLock.acquire(True)
        self.nextFile = filename
        self.controlLock.release()
        
    def Stop(self):
        self.controlLock.acquire(True)
        self.needsStop = True
        self.controlLock.release()
        
    def Abort(self):
        self.controlLock.acquire(True)
        self.needsAbort = True
        self.controlLock.release()
        
    def IsPlaying(self):
        self.playLock.acquire(True)
        isPlaying = self._currentlyPlaying
        self.playLock.release()
        return isPlaying
    
    def IsWaiting(self):
        self.controlLock.acquire(True)
        isWaiting = self.nextFile != None
        self.controlLock.release()
        return isWaiting
        
    def run(self):
        self.nextFile = None
        self.needsStop = False
        self.needsAbort = False
        
        self._shoutcaster.open()
        
        while True:
            shouldContinue = self._TickStream()
            if not shouldContinue: break
        
        self._shoutcaster.close()
        
    def _TickStream(self):
        # Ticks the stream. Only call from within the stream thread.
        
        # Check to see if we need to abort, if so, do it
        
        # Check to see if we need to stop the currently playing song or abort the stream entirely.
        #   If we can't get the mutex don't worry about it, we'll try again in a bit.
        abort = False
        if self.controlLock.acquire(False):
            if self.needsAbort: abort = True
            else: abort = False
            
            if self.needsStop:
                self.needsStop = False
                stopPlaying = True
            else: stopPlaying = False
            self.controlLock.release()
        else: stopPlaying = False
        if abort: return False
        
        # Play the stream
        if not stopPlaying and self._inputStream: isPlaying = self._PlayFromStream(self._inputStream)
        else: isPlaying = False
        
        if not isPlaying:
            # Close the input stream if we have one
            if self._inputStream:
                self._inputStream.close()
                self._inputStream = None
                
                # Indicate that we're no longer playing
                self.playLock.acquire(True)
                self._currentlyPlaying = False
                self.playLock.release()
                
                print "Song complete, playing silence..."
            
            # Play silence to keep the station alive for this tick
            if not self._silenceStream: self._GetSilenceStream()
            silenceFinished = self._PlayFromStream(self._silenceStream)
            if silenceFinished: self._GetSilenceStream()

            # Check to see if we have a new file to read. If we can't get the mutex don't
            #   worry about it, we'll try again in a bit.
            if self.controlLock.acquire(False):
                if self.nextFile:
                    self._GetSongStream(self.nextFile)
                    self.nextFile = None
                    
                    if self._silenceStream:
                        self._silenceStream.close()
                        self._silenceStream = None
                
                    # Indicate that we've started playing
                    self.playLock.acquire(True)
                    self._currentlyPlaying = True
                    self.playLock.release()
                else:
                    self._GetSilenceStream()
                        
                self.controlLock.release()
        
        return True
            
    def _PlayFromStream(self, stream):
        # Only call from within the stream thread.
        # Returns true if we streamed data, false if we didn't because we reached EOF.
        buffer = stream.read(4096)
        if len(buffer) == 0:
            return False
        else:
            self._shoutcaster.send(buffer)
            self._shoutcaster.sync()
            return True
    
    def _GetSilenceStream(self):
        # Only call from within the stream thread.
        if self._silenceStream and not self._silenceStream.closed: self._silenceStream.close()
        self._silenceStream = open("silence.mp3")
    
    def _GetSongStream(self, filepath):
        # Only call from within the stream thread.
        if self._inputStream and not self._inputStream.closed: self._inputStream.close()
        self._inputStream = open(filepath)
        
        print "Loading song stream from file %s..." % filepath