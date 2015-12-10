import urllib2
import socket

import threading

from sys import stdout
from copy import copy

base_headers = {"User-Agent": "partybot"}
chunk_size = 256


class Download(threading.Thread):
    class Status:
        NotStarted, Working, Success, Timeout, Error = range(5)

    def __init__(self, download_url, output_file, timeout, num_retries):
        threading.Thread.__init__(self)

        self._download_url = download_url
        self._output_file = output_file
        self._timeout = timeout
        self._num_retries = num_retries

        self.status_lock = threading.Lock()
        self._status = Download.Status.NotStarted
        self.exception = None

    def run(self):
        self._set_status(Download.Status.Working)

        remaining_retries = self._num_retries + 1

        # Attempt to open the socket, retrying if the connection times out
        bytes_read = 0
        while remaining_retries > 0 or self._num_retries == -1:
            remaining_retries -= 1

            headers = copy(base_headers)
            headers["Range"] = "bytes=%i-" % bytes_read
            request = urllib2.Request(self._download_url, None, headers)

            # Attempt to open the request socket. This will either succeed, timeout (at which point we continue if we
            #   still have retries, returning otherwise), or fail entirely (at which point we return).
            try:
                response = urllib2.urlopen(request, None, self._timeout)
            except socket.timeout as timeout_error:
                if remaining_retries > 0:
                    print "Socket request timed out, retrying (%i retries left)..." % remaining_retries
                    continue
                else:
                    print "Socket request timed out, aborting."
                    self._set_status(Download.Status.Timeout, timeout_error)
                    return
            except urllib2.HTTPError as error:
                print "HTTP error %i, aborting." % error.code
                self._set_status(Download.Status.Error, error)
                return
            except urllib2.URLError as error:
                print "Unable to handle URL, aborting. Error: " + str(error)
                self._set_status(Download.Status.Error, error)
                return

            # Socket was opened successfully. Get the content length.
            content_length_string = response.info().getheader("Content-Length")
            if content_length_string:
                content_length = int()
                print "Downloading %i bytes, starting at byte %i..." % (content_length, bytes_read)
            else:
                content_length = 0

            # Begin download.
            try:
                while True:
                    data = response.read(chunk_size)
                    if not data:
                        # We've reached the end of the file. Success!
                        stdout.write(" download complete.\n")
                        stdout.flush()
                        self._set_status(Download.Status.Success)
                        return
                    else:
                        bytes_read += len(data)
                        self._output_file.write(data)

                        stdout.write("\r - Downloaded %i bytes out of %i..." % (bytes_read, content_length))
                        stdout.flush()

            except socket.timeout as timeout_error:
                if remaining_retries > 0:
                    print "Download hung at %i bytes out of %i, retrying (%i retries left)..." % \
                          (bytes_read, content_length, remaining_retries)
                    continue
                else:
                    print "Download hung, aborting."
                    self._set_status(Download.Status.Timeout, timeout_error)
                    return
            except Exception as error:
                print "Unexpected exception while downloading file: " + str(error) + ". Aborting."
                self._set_status(Download.Status.Error, error)
                return

    def get_status(self):
        self.status_lock.acquire(True)

        # If this thread has crashed for an unknown reason while downloading, our status should be "error".
        if self._status is Download.Status.Working and not self.isAlive():
            self._status = Download.Status.Error

        status = self._status

        self.status_lock.release()
        return status

    def is_finished(self):
        return self.get_status() not in [Download.Status.NotStarted, Download.Status.Working]

    def _set_status(self, new_status, exception=None):
        self.status_lock.acquire(True)
        self._status = new_status
        self._exception = exception
        self.status_lock.release()


def download_with_retries(url, target_file, timeout, retries):
    """ Downloads data from a URL to a file-like object
    :param url: The URL to connect to
    :param target_file: A file-like object to which data should be written.
    :param timeout: The time to wait for an operation to complete before we give up.
    :param retries: Number of times to retry. Use -1 if you want to retry indefinitely.
    :return: A Download object representing the background I/O happening
    """
    downloader = Download(url, target_file, timeout, retries)
    downloader.start()

    return downloader


if __name__ == "__main__":
    with open("workfile", "w") as test_file:
        download_with_retries("http://httpbin.org/delay/1", 2, 3, test_file)
