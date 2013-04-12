import threading
import urllib2
import time
import os, sys, re

class Downloader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.controlLock = threading.Lock()
        self.busyLock = threading.Lock()
        
        self._busy = False
        
        self._downloadUrl = None
        self._localFileName = None
        
    def run(self):
        self._downloadUrl = None
        self._localFileName = None
        
        while True:
            self.controlLock.acquire(True)
            downloadUrl = self._downloadUrl
            localFileName = self._localFileName
            self.controlLock.release()
            
            if downloadUrl:
                self._SetBusy(True)
                print "Downloading file %s from URL %s"%(localFileName, downloadUrl)
                self._DownloadMp3(downloadUrl, localFileName)
                self._ReencodeMp3(localFileName)
                print "Download of file %s complete."%localFileName
                self._SetBusy(False)
                self._downloadUrl = None
                self._localFileName = None
            time.sleep(0.5)
        
    def DownloadAndReencodeSong(self, url, localFileName):
        self.controlLock.acquire(True)
        self._downloadUrl = url
        self._localFileName = localFileName
        self.controlLock.release()
        
    def IsDownloading(self):
        self.busyLock.acquire(True)
        busy = self._busy or self._downloadUrl != None
        self.busyLock.release()
        return busy
    
    def _SetBusy(self, setting):
        self.busyLock.acquire(True)
        self._busy = setting
        self.busyLock.release()
        
    def _DownloadMp3(self, url, localFileName):
        localFile = open(localFileName, "wb")
        localFile.write(urllib2.urlopen(url,).read())
        localFile.close()
    
    def _ReencodeMp3(self, targetFile):
        # Decode mp3 to wav to get channel information from it
        os.system("lame --decode \"%s\" mono_intermediate.wav"%targetFile)
        
        # Determine number of channels to check if it's stereo or mono
        os.system("sox --i mono_intermediate.wav > sox_output.txt")
        soxOutputFile = open('sox_output.txt', 'r')
        soxOutput = soxOutputFile.read()
        soxOutputFile.close()
        os.system("rm sox_output.txt")
        numChannels = int(re.search('Channels       : (\d+)', soxOutput).group(1))
        
        print "Detected %i channels."%numChannels
        
        if numChannels == 2:
            # Already stereo, transcode directly from the original
            print "Transcoding..."
            os.system("lame -m j -b 160 --resample 44.1 \"%s\" intermediate.mp3"%targetFile)
        else:
            # Not stereo, make it stereo and re-encode
            print "Encoding mono file as stereo..."
            os.system("sox mono_intermediate.wav -c 2 stereo_intermediate.wav")
            os.system("lame -m j -b 160 --resample 44.1 stereo_intermediate.wav intermediate.mp3")
            os.system("rm stereo_intermediate.wav")
        os.system("rm mono_intermediate.wav")
            
        # Move the re-encoded file back on top of the target file
        os.system("rm \"%s\""%targetFile)
        os.system("mv intermediate.mp3 \"%s\""%targetFile)