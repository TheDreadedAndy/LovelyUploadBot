import praw
import os
from time import time, sleep, localtime, strftime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

VERBOSE = True # Setting to false suppresses mundane information and most warnings.
VID_TITLE = 0
VID_URL = 1
GRUMPS_NAME = 'Game Grumps'
GRUMPS_PL = 'UU9CuvdOVfMPvKCiwdGKL3cQ' # Uploads playlist of Game Grumps YouTube channel.
GRUMPS_SUBREDDIT = 'gamegrumps' # Subreddit new videos will be submitted to.
GRUMPOUT_NAME = 'Grump Out'
GRUMPOUT_PL = 'UUAQ0o3l-H3y_n56C3yJ9EHA' # Uploads playlist for Grump Out.

class Youtuber(object):
    def __init__(self, youtube, reddit, name, uploadPl, sub):
        self.subreddit = reddit.subreddit(sub)
        self.name = name
        # I use this number to track when a video is added.
        self.numVids = youtube.playlistItems().list(part="snippet, ContentDetails", maxResults=3,\
                                    playlistId=uploadPl).execute()['pageInfo']['totalResults']
        self.plID = uploadPl
        self.uploadQueue = set()
        # The video list is used later to track when a new video is uploaded.
        self.genVidList(youtube)
        verbose("Initialized channel %s." % (self.name))

    def genVidList(self, youtube):
        # Generates a list of every upload from the given channel.
        https, pl = getPlaylistItems(youtube, self.plID)
        moreVids = True
        self.vidList = set()
        while moreVids:
            # Adds the video id of each video in the page to the set.
            for item in pl['items']:
                id = item['contentDetails']['videoId']
                self.vidList.add(id)
            # Prevents the loop from ending until we know the ID of every video.
            if len(self.vidList) >= self.numVids: moreVids = False
            # Loads the next page if there is one.
            if 'nextPageToken' in pl.keys():
                https, pl = getNextPlPage(youtube, https, pl)
            elif moreVids:
                verbose('Warning: Loop reached while generating video list!', override=False)
                https, pl = getPlaylistItems(youtube, self.plID)

    def update(self, youtube):
        self.getLatestVideo(youtube)
        if self.uploadQueue:
            verbose("Found new content uploaded by %s!" % (self.name))
            for vid in self.uploadQueue.copy():
                try:
                    self.subreddit.submit(title=vid[VID_TITLE], url=vid[VID_URL],\
                                              resubmit=True, send_replies=False)
                    self.uploadQueue.remove(vid)
                    verbose('Submitted video \"%s\"' % (vid[VID_TITLE]))
                except Exception as e:
                    verbose(e)
        else: verbose("No new uploads found for channel %s." % (self.name), override=False)

    def getLatestVideo(self, youtube):
        # This function checks if the total number of videos in the upload playlist
        # has increased, and returns the new videos if so.
        https, pl = getPlaylistItems(youtube, self.plID)
        newNumVids = pl['pageInfo']['totalResults']
        if newNumVids <= self.numVids: return
        dVids = newNumVids - self.numVids
        self.numVids = newNumVids
        i = 0
        while i < dVids:
            # Searches each page of the playlist for new videos until it has found them all.
            for item in pl['items']:
                id = item['contentDetails']['videoId']
                if id not in self.vidList:
                    title = item['snippet']['title']
                    url = "https://www.youtube.com/watch?v=%s" % (id)
                    self.vidList.add(id)
                    self.uploadQueue.add((title, url))
                    i += 1
            # Loads the next page if there is one.
            if 'nextPageToken' in pl.keys():
                https, pl = getNextPlPage(youtube, https, pl)
            elif i < dVids:
                verbose('Warning: Loop reached while searching for latest video!', override=False)
                https, pl = getPlaylistItems(youtube, self.plID)

def main():
    verbose('Initializing...')
    youtube, reddit = initAPIs()
    if youtube == None and reddit == None: return
    gameGrumps = Youtuber(youtube, reddit, GRUMPS_NAME, GRUMPS_PL, GRUMPS_SUBREDDIT)
    grumpOut = Youtuber(youtube, reddit, GRUMPOUT_NAME, GRUMPOUT_PL, GRUMPS_SUBREDDIT)
    verbose('Done!')
    # Checks for new videos and uploads them when they appear.
    while True:
        try:
            verbose("Checking for new uploads...", override=False)
            gameGrumps.update(youtube)
            grumpOut.update(youtube)
            controlledSleep(20)
        except KeyboardInterrupt:
            verbose("Keyboard interrupt received, ending violently.")
            return
        except Exception as e:
            verbose(e)
            return

def verbose(s, override=True):
    timeStamp = "[%s]:" % (strftime("%I:%M:%S %p",localtime(time())))
    if VERBOSE or override: print(timeStamp, s)

def initAPIs():
    try:
        # See README for more information.
        path = os.path.dirname(os.path.abspath(__file__)) + '/keys.txt'
        with open(path, 'rt') as file:
            keys = file.read().splitlines()
            YT_API_KEY = keys[0]
            REDDIT_ID = keys[1]
            REDDIT_SECRET = keys[2]
            REDDIT_AGENT = keys[3]
            REDDIT_USER = keys[4]
            REDDIT_PASS = keys[5]
    except Exception as e:
        verbose(e)
        verbose("FATAL: Problem opening keys.txt! Please view the ReadMe for help.")
        return None, None
    # This gives me an object that lets me deal with youtube.
    youtube = build("youtube", "v3", developerKey=YT_API_KEY)
    # This object lets me interact with reddit.
    reddit = praw.Reddit(client_id=REDDIT_ID, client_secret=REDDIT_SECRET,\
                        user_agent=REDDIT_AGENT,\
                        username=REDDIT_USER, password=REDDIT_PASS)
    return youtube, reddit

# Used to determine how often the bot pings youtube. The interval must be < 60.
def controlledSleep(interval):
    timer = abs(60 - localtime(time()).tm_sec)
    while timer > interval: timer -= interval
    sleep(timer)

# A decorator that ensures the playlist functions will execute until they get a response.
def ensureConnection(f):
    def g(*args, **kwargs):
        sleep = 1
        while True:
            try:
                return f(*args, **kwargs)
            except:
                verbose("Warning! Connection error while getting playlist items!")
                verbose("Retrying in %d seconds..." % (sleep))
                time.sleep(sleep)
                sleep *= 2
    return g

@ensureConnection
def getPlaylistItems(youtube, plID):
    https = youtube.playlistItems().list(part="snippet, ContentDetails",\
                                    maxResults=50, playlistId=plID)
    return https, https.execute()

@ensureConnection
def getNextPlPage(youtube, https, pl):
    https = youtube.playlistItems().list_next(https, pl)
    return https, https.execute()

if __name__ == "__main__": main()
