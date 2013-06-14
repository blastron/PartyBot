from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, task

import re

import stream, speech, downloader
import urllib2
from scrapePlaylist import scrapePlaylist
from playlist import computeNewTrackIndex
from namelookup import GetPronounceableName

import datetime

class PartyBot(irc.IRCClient):
    nickname = "partybot"
    
    def __init__(self):
        self.isJoined = False
        
        self.streamer = stream.ShoutcastStreamer()
        self.streamer.start()
        
        self.downloader = downloader.Downloader()
        self.downloader.start()
        
        self.compoId = None
        self.playlist = None
        
        self.currentIndex = 0
        self.nextSong = None
        
        self.localFileIndex = {}
        
        self.ticker = task.LoopingCall(self.handleTick)
        self.startTicker()
        
        self.queueAnnounceTimer = None
        
        self.nextStep = None
        self.lastStepTime = None
        self.timeUntilNextStep = 0
        
        self.scheduledCompoId = None
        self.scheduledCompoStart = None
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        print "Connection established."

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print "Connection lost."
        
    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        self.Broadcast("Partybot online.")

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        print "Channel %s joined." % channel
        self.isJoined = True

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        if not user:
            return
        
        user = user.split('!', 1)[0]
        
        if channel == self.nickname:
            # This is a private message
            print "Received private message from %s: %s" % (user, msg)
            
            # Handle command
            parsedCommand = msg.split(' ')
            command = parsedCommand[0].lower()
            if len(parsedCommand) > 1: arguments = parsedCommand[1:]
            else: arguments = []
            if command == "loadparty":
                if len(arguments) == 1:
                    compo = arguments[0]
                    self.LoadCompo(compo)
                elif len(arguments) == 2:
                    compo = arguments[0]
                    index = int(arguments[1])
                    self.LoadCompo(compo, index)
                else:
                    self.BroadcastPrivate(user, "USAGE: LOADPARTY compo# [startIndex]")
                    return
            elif command == "start":
                if self.playlist != None:
                    self.StartCompo()
                else:
                    self.BroadcastPrivate(user, "No composition currently loaded.")
            elif command == "stop":
                self.Broadcast('\x0305*!* Pausing party... *!*')
                self.StopCompo()
            elif command == "skip":
                self.Broadcast('\x0305*!* Skipping track... *!*')
                self.SkipTrack()
            elif command == "say":
                if len(arguments) > 0:
                    self.Broadcast(' '.join(arguments))
                else:
                    self.BroadcastPrivate(user, "USAGE: SAY message")
            elif command == "scheduleparty":
                if len(arguments) == 3:
                    try:
                        self.scheduledCompoStart = datetime.datetime.strptime("%s %s"%(arguments[1], arguments[2]), "%m/%d/%Y %H:%M")
                    except:
                        self.BroadcastPrivate(user, "Error: Unable to parse.")
                        self.BroadcastPrivate(user, "USAGE: SCHEDULEPARTY compo# MM/DD/YYYY HH:MM (times are in 24-hour UTC)")
                        return
                    
                    self.scheduledCompoId = arguments[0]
                    self.BroadcastPrivate(user, "Party schedule complete.")
                else:
                    self.BroadcastPrivate(user, "USAGE: SCHEDULEPARTY compo# MM/DD/YYYY HH:MM (times are in 24-hour UTC)")
            else:
                self.BroadcastPrivate(user, "Unrecognized command: %s" % command)
    
    # Update loop
    def handleTick(self):
        if self.isJoined:
            self.TickCompo()
    
    def startTicker(self):
        self.ticker.start(0.1)
    
    def stopTicker(self):
        self.ticker.stop()
        
    # IRC interactions
    def Broadcast(self, text):
        self.BroadcastPrivate(self.factory.channel, text)
    
    def BroadcastPrivate(self, recipient, text):
        print "Broadcasting to %s: %s" % (recipient, text)
        self.msg(recipient, ''.join(['\x02', text]).encode("utf-8"))
        
    # Download interactions
    def StartSongDownload(self, song):
        self.nextSong = song
        
        localFileName = "songs/" + song.url[song.url.rindex('/') + 1:]
        localFileName = re.sub('["]', '', localFileName)
        self.localFileIndex[song.id] = localFileName
        
        self.downloader.DownloadAndReencodeSong(song.url, localFileName)
    
    # Control functions
    def AnnounceQueue(self):
        currentSong = self.playlist.GetTrack(self.currentIndex)
        self.Broadcast('\x0302*** Queueing "%s" by %s... ***' % (currentSong.title, currentSong.artist))
        self.nextStep = "queue"
        self.timeUntilNextStep = 0
        self.queueAnnounceTimer = datetime.datetime.now()
    
    def QueueCurrentSong(self):
        currentSong = self.playlist.GetTrack(self.currentIndex)
        
        if self.nextSong == None or self.nextSong != currentSong:
            print "Cached song is out of date or missing, downloading..."
            self.StartSongDownload(currentSong)
            self.nextStep = "queue"
        elif self.downloader.IsDownloading():
            self.nextStep = "queue"
        else:
            self.nextStep = "announce"
            self.timeUntilNextStep = max(0, 5 - (datetime.datetime.now() - self.queueAnnounceTimer).seconds)
        
    def AnnounceCurrentSong(self):
        currentSong = self.playlist.GetTrack(self.currentIndex)
        print "Announcing %s..." % currentSong.title
        
        announceText = "Now playing %s by %s." % (currentSong.title, GetPronounceableName(currentSong.artist))
        
        speech.SpeakToFile(announceText, "announce.mp3")
        self.streamer.Play("announce.mp3")
        
        self.nextStep = "announceWait"
        self.timeUntilNextStep = 1
        
    def WaitForAnnounce(self):
        if not self.streamer.IsPlaying() and not self.streamer.IsWaiting():
            self.nextStep = "play"
            self.timeUntilNextStep = 0
        else:
            self.nextStep = "announceWait"
        
    def PlayCurrentSong(self):
        currentSong = self.playlist.GetTrack(self.currentIndex)
        
        self.Broadcast('\x0303*** Playing "%s" by %s... ***' % (currentSong.title, currentSong.artist))
        print "Playing %s..." % currentSong.title
        self.streamer.Play(self.localFileIndex[currentSong.id])
        
        self.nextStep = "playWait"
        self.timeUntilNextStep = 1
        
        # Start the next song caching
        if self.currentIndex + 1 < self.playlist.Length():
            nextSong = self.playlist.GetTrack(self.currentIndex + 1)
            self.StartSongDownload(nextSong)
    
    def WaitForCurrentSong(self):
        if not self.streamer.IsPlaying() and not self.streamer.IsWaiting():
            self.nextStep = "advance"
            self.timeUntilNextStep = 0
        else:
            self.nextStep = "playWait"
    
    def AdvanceCurrentSong(self):
        self.currentIndex += 1
        
        # Update the song list
        newPlaylist = scrapePlaylist(self.compoId)
        self.currentIndex = computeNewTrackIndex(self.playlist, newPlaylist, self.currentIndex)
        self.playlist = newPlaylist
        
        if self.currentIndex >= self.playlist.Length():
            # Announce end of compo
            print "Compo over"
            self.Broadcast('*** Party complete. Thank you to all of our participants. ***')
            self.StopCompo()
        else:
            # Advance the song
            self.nextStep = "announceQueue"
            self.timeUntilNextStep = 0
            
    def LoadCompo(self, compoId, index=0):
        self.compoId = compoId
        
        if self.playlist:
            # We already have a playlist (and maybe a party), let's kill everything
            self.streamer.Stop()
        
        self.currentIndex = index
        self.playlist = scrapePlaylist(self.compoId)
        
        self.Broadcast('Party matrix engaged, ready for compo %s.' % compoId)
    
    def StartCompo(self):
        self.nextStep = "broadcastStream"
        self.lastStepTime = datetime.datetime.now()
        self.timeUntilNextStep = 2
        
        self.Broadcast('*** Preparing to commence party. ***')
    
    def StopCompo(self):
        self.nextStep = None
        if self.streamer.IsPlaying(): self.streamer.Stop()
    
    def SkipTrack(self):
        self.nextStep = "advance"
        if self.streamer.IsPlaying(): self.streamer.Stop()
    
    def BroadcastStreamUrl(self):
        externalIP = urllib2.urlopen('http://icanhazip.com/').read().rstrip()
        self.Broadcast("*** Jukebox is online. Feel free to listen in at http://%s:8000/partybot.m3u or follow along manually. ***"%externalIP)
        
        self.nextStep = "announceStart"
        self.timeUntilNextStep = 10
    
    def AnnounceStart(self):
        self.Broadcast("*** Commencing party. ***")
        self.nextStep = "announceQueue"
        self.timeUntilNextStep = 3
    
    def TickCompo(self):
        if self.nextStep != None:
            if not self.lastStepTime or (self.lastStepTime + datetime.timedelta(seconds=self.timeUntilNextStep)) <= datetime.datetime.now():
                self.lastStepTime = datetime.datetime.now()
                nextStep = self.nextStep
                self.nextStep = None
                
                if nextStep == "broadcastStream":
                    self.BroadcastStreamUrl()
                elif nextStep == "announceStart":
                    self.AnnounceStart()
                elif nextStep == "announceQueue":
                    self.AnnounceQueue()
                elif nextStep == "queue":
                    self.QueueCurrentSong()
                elif nextStep == "announce":
                    self.AnnounceCurrentSong()
                elif nextStep == "announceWait":
                    self.WaitForAnnounce()
                elif nextStep == "play":
                    self.PlayCurrentSong()
                elif nextStep == "playWait":
                    self.WaitForCurrentSong()
                elif nextStep == "advance":
                    self.AdvanceCurrentSong()
                else:
                    print "ERROR: UNRECOGNIZED STATE"
        elif self.scheduledCompoId != None:
            if self.scheduledCompoStart < datetime.datetime.utcnow():
                self.LoadCompo(self.scheduledCompoId)
                self.StartCompo()
                
                self.scheduledCompoId = None
                self.scheduledCompoStart = None

class PartyBotFactory(protocol.ClientFactory):
    def __init__(self, channel):
        self.channel = channel

    def buildProtocol(self, addr):
        p = PartyBot()
        p.factory = self
        return p

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()
