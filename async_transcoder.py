import threading
import os
import re


class Transcoder(threading.Thread):
    class Status:
        NotStarted, Working, Done, Error = range(4)

    def __init__(self, local_file_path):
        threading.Thread.__init__(self)

        self._local_file_path = local_file_path

        self.status_lock = threading.Lock()
        self._status = Transcoder.Status.NotStarted

    def run(self):
        self._set_status(Transcoder.Status.Working)

        # Decode mp3 to wav to get channel information from it
        os.system("lame --decode \"%s\" mono_intermediate.wav > /dev/null 2>&1" % self._local_file_path)

        # Determine number of channels to check if it's stereo or mono
        os.system("sox --i mono_intermediate.wav > sox_output.txt")
        sox_output_file = open('sox_output.txt', 'r')
        sox_output_text = sox_output_file.read()
        sox_output_file.close()
        os.system("rm sox_output.txt")
        num_channels = int(re.search('Channels       : (\d+)', sox_output_text).group(1))

        print "Detected %i channels." % num_channels

        if num_channels == 2:
            # Already stereo, transcode directly from the original
            print "Transcoding..."
            os.system(
                "lame -m j -b 160 --resample 44.1 \"%s\" intermediate.mp3 > /dev/null 2>&1" % self._local_file_path)
        else:
            # Not stereo, make it stereo and re-encode
            print "Encoding mono file as stereo..."
            os.system("sox mono_intermediate.wav -c 2 stereo_intermediate.wav")
            os.system("lame -m j -b 160 --resample 44.1 stereo_intermediate.wav intermediate.mp3 > /dev/null 2>&1")
            os.system("rm stereo_intermediate.wav")
        os.system("rm mono_intermediate.wav")

        # Move the re-encoded file back on top of the target file
        os.system("rm \"%s\"" % self._local_file_path)
        os.system("mv intermediate.mp3 \"%s\"" % self._local_file_path)

        self._set_status(Transcoder.Status.Done)

    def get_status(self):
        self.status_lock.acquire(True)

        # If this thread has crashed for an unknown reason while downloading, our status should be "error".
        if self._status is Transcoder.Status.Working and not self.isAlive():
            self._status = Transcoder.Status.Error

        status = self._status

        self.status_lock.release()
        return status

    def is_finished(self):
        return self.get_status() not in [Transcoder.Status.NotStarted, Transcoder.Status.Working]

    def _set_status(self, new_status, exception=None):
        self.status_lock.acquire(True)
        self._status = new_status
        self._exception = exception
        self.status_lock.release()


def transcode(local_file_path):
    transcoder = Transcoder(local_file_path)
    transcoder.start()

    return transcoder
