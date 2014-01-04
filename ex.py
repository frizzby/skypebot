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


class UrlRecord(namedtuple('UrlRecord', ['ts', 'msg_id', 'url'])):
    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        ts, msg_id, url = iterable
        return super(UrlRecord, cls)._make((float(ts), int(msg_id), url), new, len)


DEBUG = True


if DEBUG:
    logging.basicConfig(level=logging.INFO)

log = logging.getLogger()

TARGET_CHAT_NAME = '#vitus_by/$eug.kirillov;eb6e6e15b266d634'
TARGET_RE = re.compile('https?:[^\s$]+')
OUTPUT_FILENAME='urls.csv'

PID='bot.run'


def get_last_row(csv_filename):
    fsize = os.path.getsize(csv_filename)
    if fsize:
        _seek = min(50*1024, fsize)
        with open(csv_filename, 'rb') as f:
            f.seek(-_seek, io.SEEK_END)
            return UrlRecord._make(deque(csv.reader(f), 1)[0])
    else:
        return None, None, None


class SkypeBot(object):
    def __init__(self):

        self.latest_ts, self.latest_id, _ = get_last_row(OUTPUT_FILENAME)

        self.skype = Skype4Py.Skype(Events=self)
        self.skype.FriendlyName = "Skype Bot"
        self.skype.Attach()


    def AttachmentStatus(self, status):
        if status == Skype4Py.apiAttachAvailable:
            self.skype.Attach()

        for item in imap(UrlRecord._make, ifilter(lambda x: float(x[0])>=self.latest_ts, self.read_history())):
            print item.ts, item.url


    def read_history(self):
        for msg in self.skype.Chat(TARGET_CHAT_NAME).Messages:
            matches = TARGET_RE.findall(msg.Body)
            if matches:
                for match in matches:
                    yield msg.Timestamp, msg.Id, match

        print "FURA"

    #def MessageStatus(self, msg, status):
    #
    #    if status == Skype4Py.cmsReceived:
    #        if msg.Chat.Type in (Skype4Py.chatTypeDialog, Skype4Py.chatTypeLegacyDialog):
    #            print msg.Body, msg.Chat.Type
    #            for regexp, target in self.commands.items():
    #                match = re.match(regexp, msg.Body, re.IGNORECASE)
    #                if match:
    #                    msg.MarkAsSeen()
    #                    reply = target(self, *match.groups())
    #                    if reply:
    #                        msg.Chat.SendMessage(reply)
    #                    break



def create_pid():
    if not DEBUG:
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
