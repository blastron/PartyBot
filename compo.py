import traceback
import os
import speech
from StringIO import StringIO
from scrapePlaylist import parse_playlist
from playlist import computeNewTrackIndex
from async_downloader import Download, download_with_retries
from async_transcoder import Transcoder, transcode
from namelookup import GetPronounceableName
from urllib2 import HTTPError


class Compo:
    class State:
        Initializing, WaitingForSongDownload, AnnouncingSong, PlayingSong, UpdatingPlaylist, Complete, Error = range(7)

    song_directory = "songs/"

    def __init__(self, compo_id, irc_bot, streamer):
        self.compo_id = compo_id
        self.bot = irc_bot
        self.streamer = streamer

        self.playlist = None
        self.track_index = 0

        self.track_statuses = {}

        self.state = None
        self.queued_message = None

        self.song_download_task = None
        self.song_download_file = None
        self.song_download_filepath = None
        self.song_download_track = None

        self.song_transcode_task = None

        self.playlist_download_task = None
        self.playlist_download_stream = None

    def start(self, track_index=0):
        self.bot.irc_client.broadcast("Initializing party for %s..." % self.compo_id)

        self.state = Compo.State.Initializing
        self.track_index = track_index

        # Download the playlist. (This will kick off a song when it's done.)
        self._download_playlist()

    def update(self):
        # Churn our download/transcode threads
        if self.song_download_task and self.song_download_task.is_finished():
            # The song download task has finished.
            self._song_download_complete()

        if self.song_transcode_task and self.song_transcode_task.is_finished():
            # The song transcode task has finished.
            self._song_transcode_complete()

        if self.playlist_download_task and self.playlist_download_task.is_finished():
            # The playlist download task has finished.
            self._playlist_download_complete()

        if self.state == Compo.State.AnnouncingSong:
            if not (self.streamer.IsPlaying() or self.streamer.IsWaiting()):
                # The announcement has finished. Play the track. We're assuming that the song is already downloaded;
                #   if we've gotten through announcing the song, this SHOULD be the case.
                print "Announcement broadcast complete."
                self.state = Compo.State.PlayingSong

                current_song = self.playlist.GetTrack(self.track_index)
                self.bot.irc_client.broadcast('\x0303*** Playing "%s" by %s... ***' %
                                              (current_song.title, current_song.artist))
                self.streamer.Play(self._get_local_url_for_track(current_song))
        elif self.state == Compo.State.PlayingSong:
            if not (self.streamer.IsPlaying() or self.streamer.IsWaiting()):
                # The song has finished. If there's a message queued, play it.
                print "Song playthrough complete."
                if self.queued_message:
                    self.bot.irc_client.broadcast(self.queued_message)
                    self.queued_message = None

                # Update the playlist, so that we can ensure we're not serving stale songs.
                self.state = Compo.State.UpdatingPlaylist
                self._download_playlist()

    def _ready_current_song(self):
        if self.playlist.Length() == 0:
            self.state = Compo.State.Complete
            self.bot.irc_client.broadcast("*!* Given compo had zero songs! Aborting. *!*")
        elif self.playlist.Length() <= self.track_index:
            self.state = Compo.State.Complete
            self.bot.irc_client.broadcast("*** Party complete. Thank you to all of our participants. ***")
        else:
            # Determine if the current song is downloaded
            current_track = self.playlist.GetTrack(self.track_index)
            if current_track.id in self.track_statuses:
                if self.track_statuses[current_track.id] == "done":
                    # The current song has already been downloaded, announce it.
                    self._announce_current_song()
                elif self.track_statuses[current_track.id] == "error":
                    # We weren't able to download the current track, likely for 404 reasons.
                    self.state = Compo.State.WaitingForSongDownload
                    self.bot.irc_client.broadcast(
                        "There was an error playing the track \"%s\". This could be caused due " +
                        "to excessively long track names. Skipping...")
                    self.track_index += 1
                    self._ready_current_song()
                else:
                    # We have yet to finish downloading the current track.
                    self.state = Compo.State.WaitingForSongDownload
                    self.bot.irc_client.broadcast("Waiting for track download to finish, please stand by...")
            else:
                # The current song has not yet been seen. Kick off a download, interrupting any other downloads
                #   currently in-progress.
                self.bot.irc_client.broadcast("Downloading track, please stand by...")
                self._download_track(current_track)

    def _announce_current_song(self):
        self.state = Compo.State.AnnouncingSong

        current_song = self.playlist.GetTrack(self.track_index)
        self.bot.irc_client.broadcast(
            '\x0302*** Queueing "%s" by %s... ***' % (current_song.title, current_song.artist))

        # TODO: Move announcement to a threaded task, this can hang for about 3 seconds
        announcement = "Now playing %s by %s." % (current_song.title, GetPronounceableName(current_song.artist))
        speech.SpeakToFile(announcement, "announce.mp3")

        # Play the track.
        self.streamer.Play("announce.mp3")

        # Kick off the next song's download in the background.
        next_track_index = self.track_index + 1
        if self.playlist.Length() > next_track_index:
            # There's at least one song left, start downloading it.
            next_track = self.playlist.GetTrack(next_track_index)
            self._download_track(next_track)

    # Playlist downloading
    def _download_playlist(self):
        playlist_url = 'http://compo.thasauce.net/rounds/view/%s' % self.compo_id

        print "Downloading playlist."
        self.playlist_download_stream = StringIO()
        self.playlist_download_task = download_with_retries(playlist_url, self.playlist_download_stream, 5, 5)

    def _playlist_download_complete(self):
        status = self.playlist_download_task.get_status()
        if status == Download.Status.Success:
            print "Playlist download complete."
            playlist_html = self.playlist_download_stream.getvalue()
            playlist = parse_playlist(playlist_html)

            if self.state is Compo.State.Initializing:
                # The initial playlist has been downloaded, get the party started
                self.state = Compo.State.WaitingForSongDownload
                self.playlist = playlist
                self._ready_current_song()
            else:
                # We've finished downloading the playlist. Update it, advance the song index, and continue.
                self._update_playlist(playlist)
                self.track_index += 1
                self._ready_current_song()
        elif status is Download.Status.Timeout:
            print "Playlist download timed out."
            if self.state is Compo.State.Initializing:
                # We failed to download the initial playlist. Report an error.
                self.state = Compo.State.Error
                self.bot.irc_client.broadcast("\x0305Initialization failed: unable to reach ThaSauce servers.")
            else:
                self.bot.irc_client.broadcast(
                    "\x0305Warning: unable to reach ThaSauce servers to update playlist. Party " +
                    "may be able to continue automatically.")
                self.track_index += 1
                self._ready_current_song()
        elif status == Download.Status.Error:
            print "Playlist download failed."
            if self.state is Compo.State.Initializing:
                self.state = Compo.State.Error
                if status.exception is HTTPError:
                    if status.exception.code == 404:
                        self.bot.irc_client.broadcast("\x0305Initialization failed: party with given ID not found.")
                    else:
                        self.bot.irc_client.broadcast(
                            "\x0305Initialization failed: unrecoverable error when contacting" +
                            " ThaSauce. HTTP error code: " + str(status.exception.code))
                else:
                    self.bot.irc_client.broadcast(
                        "\x0305Initialization failed: unrecoverable error when contacting ThaSauce.")
            else:
                self.bot.irc_client.broadcast(
                    "\x0305Warning: unrecoverable error while communicating with ThaSauce to" +
                    " update playlist. Party may be able to continue automatically.")
                self.track_index += 1
                self._ready_current_song()

        # Clean up.
        self.playlist_download_task = None
        self.playlist_download_stream.close()
        self.playlist_download_stream = None

    def _update_playlist(self, updated_playlist):
        updated_track_index = computeNewTrackIndex(self.playlist, updated_playlist, self.track_index)

        self.playlist = updated_playlist
        self.track_index = updated_track_index

    # Song downloading
    def _get_local_url_for_track(self, track):
        if not os.path.exists(self.song_directory):
            os.makedirs(self.song_directory)

        return self.song_directory + track.id + ".mp3"

    def _download_track(self, track):
        source_url = track.url
        destination_path = self._get_local_url_for_track(track)

        print "Commencing download for track id %s." % track.id
        self.track_statuses[track.id] = "downloading"

        self.song_download_file = open(destination_path, "wb")
        self.song_download_filepath = destination_path
        self.song_download_task = download_with_retries(source_url, self.song_download_file, 5, 5)
        self.song_download_track = track

    def _song_download_complete(self):
        self.song_download_file.close()
        self.song_download_file = None

        status = self.song_download_task.get_status()
        if status == Download.Status.Success:
            # The file was successfully downloaded. Transcode it to the correct format.
            print "Download complete for track id %s." % self.song_download_track.id
            self.track_statuses[self.song_download_track.id] = "downloading"
            self.song_transcode_task = transcode(self.song_download_filepath)
        elif status == Download.Status.Timeout:
            # The download timed out. Stop the party and alert listeners that downloading has failed.
            print "Track download failed."
            self.state = Compo.State.Error
            self.queued_message = "\x0305Unable to reach ThaSauce servers to download the next song. Aborting party."
        elif status == Download.Status.Error:
            # The download did not succeed for an unrecoverable reason. This is likely due to a problem
            #   with the specific file or URL; skip this track and alert listeners that the song was
            #   un-downloadable.
            self.track_statuses[self.song_download_track.id] = "error"

        self.song_download_task = None

    def _song_transcode_complete(self):
        status = self.song_transcode_task.get_status()
        if status == Transcoder.Status.Done:
            print "Transcode complete for track id %s." % self.song_download_track.id
            self.track_statuses[self.song_download_track.id] = "done"
            if self.state == Compo.State.WaitingForSongDownload:
                # We were waiting for the song download to finish, either because this was the first song or because
                #   the download didn't finish before the previous track finished.
                self._announce_current_song()
            else:
                # We're not actively waiting on the song to finish downloading, so do nothing. This will get picked
                #   up in the next update cycle.
                pass
        elif status == Transcoder.Status.Error:
            self.state = Compo.State.Error
            self.queued_message = "\x0305Unable to transcode next song for playback. Aborting party."

        self.song_transcode_task = None
