import atexit
import time
import re
import os
import logging
import sys
import io
from collections import deque, namedtuple
from itertools import ifilter, imap

import Skype4Py
from signal import *
import csv
import operator


class UrlRecord(namedtuple('UrlRecord', ['ts', 'msg_id', 'url'])):
    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        ts, msg_id, url = iterable
        return super(UrlRecord, cls)._make((float(ts), int(msg_id), url.encode('utf-8')), new, len)

    def __new__(cls, ts, msg_id, url):
        return super(UrlRecord, cls).__new__(cls, float(ts), int(msg_id), url.encode('utf-8'))



DEBUG = True


if DEBUG:
    logging.basicConfig(level=logging.INFO)

log = logging.getLogger()

TARGET_CHAT_NAME = '#vitus_by/$eug.kirillov;eb6e6e15b266d634'
TARGET_RE = re.compile('https?:[^\s$]+\.(?:gif|jpe?g|png)', re.IGNORECASE)
OUTPUT_FILENAME='urls.csv'

MAX_HISTORY_LOOKBACK = 500
CSV_ESTIMATED_LINE_LENGTH = 500

PID='bot.run'



def write(it):
    #it = [[f.decode('utf-8') for f in r] for r in it]
    it = list(it)
    log.info("Writing %s records" % len(it))
    with open(OUTPUT_FILENAME, 'a') as f:
        csv.writer(f).writerows(it)


class SkypeBot(object):
    def __init__(self):

        self.latest_ts = 0

        self.history = None

        self.set_state_from_logfile(OUTPUT_FILENAME, MAX_HISTORY_LOOKBACK, CSV_ESTIMATED_LINE_LENGTH)

        self.is_history_read = False

        self.skype = Skype4Py.Skype(Events=self)
        self.skype.FriendlyName = "Skype Bot"
        self.skype.Attach()


    def set_state_from_logfile(self, csv_filename, num_lines, line_size):
        log.info("Reading logfile...")
        _latest_ts = 0
        _history = []
        fsize = os.path.getsize(csv_filename)
        if fsize:
            _seek = min(num_lines*line_size, fsize)
            with open(csv_filename, 'rb') as f:
                f.seek(-_seek, io.SEEK_END)
                queue = deque(csv.reader(f), num_lines)
                _latest_ts = queue[-1][0]
                _history = imap(operator.methodcaller("decode", "utf-8"), imap(operator.itemgetter(2), queue))

        self.latest_ts = float(_latest_ts)

        self.history = deque(_history, MAX_HISTORY_LOOKBACK)
        log.info("Restored history size: %s" % len(self.history))


    def AttachmentStatus(self, status):
        if status == Skype4Py.apiAttachAvailable:
            self.skype.Attach()

        if not self.is_history_read:
            self.is_history_read = True
            out = filter(lambda x: float(x[0]) >= self.latest_ts and x[2] not in self.history, self.read_skype_history())
            out.sort(key=operator.attrgetter('ts'))
            if out:
                write(out)
            log.info("Wrote %s items from skype history" % len(out))

    def read_skype_history(self):
        log.info("Reading skype history...")
        for msg in self.skype.Chat(TARGET_CHAT_NAME).Messages:
            matches = TARGET_RE.findall(msg.Body)
            if matches:
                for match in matches:
                    yield UrlRecord(msg.Timestamp, msg.Id, unicode(match))

    def MessageStatus(self, msg, status):
        out = []
        if status == Skype4Py.cmsReceived:
            if msg.Chat.Type in (Skype4Py.chatTypeDialog, Skype4Py.chatTypeLegacyDialog, Skype4Py.chatTypeMultiChat) and msg.Chat.Name == TARGET_CHAT_NAME:
                for match in TARGET_RE.findall(msg.Body):
                    print type(match)
                    if match not in self.history:
                        self.history.append(match)
                        out.append(UrlRecord(msg.Timestamp, msg.Id, match))
                    else:
                        log.info("Skip url as duplicate: %s" % match)
                if out:
                    write(out)



def create_pid():
    if True or not DEBUG:
        if os.path.isfile(PID):
            raise RuntimeError("Program is already running. Or PID file is obsolete?")
        else:
            open(PID, 'a').close()

def remove_pid(*args):
    log.info("Exiting...")
    try:
        os.remove(PID)
    except (OSError, WindowsError):
        pass
    sys.exit(0)

if __name__ == "__main__":
    create_pid()
    atexit.register(remove_pid)
    for sig in (SIGINT, SIGTERM):
        signal(sig, remove_pid)



    bot = SkypeBot()

    while True:
        time.sleep(1.0)
