import praw # Reddit API
import time # So I don't spam google's servers and kill my data
import os
from googleapiclient.discovery import build # Youtube API
from googleapiclient.errors import HttpError # Youtube Errors

VERBOSE = True # Setting to false suppresses mundane information and most warnings.
GRUMPS_NAME = 'Game Grumps'
GRUMPS_PL = 'UU9CuvdOVfMPvKCiwdGKL3cQ' # Uploads playlist of Game Grumps YouTube channel.
GRUMPS_SUBREDDIT = 'tdasplayground' # Subreddit new videos will be submitted to.
GRUMPOUT_NAME = 'Grump Out'
GRUMPOUT_PL = 'UUAQ0o3l-H3y_n56C3yJ9EHA' # Uploads playlist for Grump Out.
VID_TITLE = 0
VID_URL = 1

def main():
    verbose('Initializing...', override=True)
    youtube, reddit = initAPIs()
    if youtube == None and reddit == None: return
    gameGrumps = Youtuber()
    grumpOut = Youtuber()
    initYoutuber(youtube, reddit, gameGrumps, GRUMPS_NAME, GRUMPS_PL, GRUMPS_SUBREDDIT)
    gameGrumps.numVids -= 1
    gameGrumps.vidList.remove('p3dMg5t0xnY')
    initYoutuber(youtube, reddit, grumpOut, GRUMPOUT_NAME, GRUMPOUT_PL, GRUMPS_SUBREDDIT)
    verbose('Done!', override=True)
    # Checks for new videos and uploads them when they appear.
    while True:
        try:
            verbose("Checking for new uploads...")
            updateYoutuber(youtube, gameGrumps)
            updateYoutuber(youtube, grumpOut)
            time.sleep(abs(60 - time.localtime(time.time()).tm_sec))
        except KeyboardInterrupt:
            verbose("Keyboard interrupt received, ending violently.", override=True)
            return
        except Exception as e:
            verbose(e, override=True)
            return

def verbose(s, override=False):
    timeStamp = "[%s]:" % (time.strftime("%I:%M:%S %p",time.localtime(time.time())))
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
        verbose(e, override=True)
        verbose("FATAL: Problem opening keys.txt! Please view the ReadMe for help.", override=True)
        return None, None
    # This gives me an object that lets me deal with youtube.
    youtube = build("youtube", "v3", developerKey=YT_API_KEY)
    # This object lets me interact with reddit.
    reddit = praw.Reddit(client_id=REDDIT_ID, client_secret=REDDIT_SECRET,\
                        user_agent=REDDIT_AGENT,\
                        username=REDDIT_USER, password=REDDIT_PASS)
    return youtube, reddit

def initYoutuber(youtube, reddit, youtuber, name, uploadPl, sub):
    youtuber.subreddit = reddit.subreddit(sub)
    youtuber.name = name
    # I use this number to track when a video is added.
    youtuber.numVids = youtube.playlistItems().list(part="snippet, ContentDetails", maxResults=3,\
                                playlistId=uploadPl).execute()['pageInfo']['totalResults']
    youtuber.pl = uploadPl
    # The video list is used later to track when a new video is uploaded.
    youtuber.vidList = initVidList(youtube, youtuber)
    youtuber.uploadQueue = set()
    verbose("Initialized channel %s." % (youtuber.name), override=True)

def initVidList(youtube, youtuber):
    # Generates a list of every upload from the given channel.
    https, pl = getPlaylistItems(youtube, youtuber)
    moreVids = True
    vidList = set()
    while moreVids:
        # Adds the video id of each video in the page to the set.
        for item in pl['items']:
            id = item['contentDetails']['videoId']
            vidList.add(id)
        # Prevents the loop from ending until we know the ID of every video.
        if len(vidList) >= youtuber.numVids: moreVids = False
        # Loads the next page if there is one.
        if 'nextPageToken' in pl.keys():
            https, pl = getPlaylistItems(youtube, youtuber, https=https, pl=pl)
        elif moreVids:
            verbose('Warning: Loop reached while generating video list!')
            https, pl = getPlaylistItems(youtube, youtuber)
    return vidList

# A decorator that ensures getPlaylistItems() will execute until it gets a response.
def ensureConnection(f):
    def g(*args, **kwargs):
        sleep = 1
        while True:
            try: return f(*args, **kwargs)
            except improperUsageError as e: raise e
            except:
                verbose("Warning! Connection error while getting playlist items!",\
                                                                    override=True)
                verbose("Retrying in %d seconds..." % (sleep), override=True)
                time.sleep(sleep)
                sleep *= 2
    return g

@ensureConnection
def getPlaylistItems(youtube, youtuber, https=None, pl=None):
    if https == None and pl == None:
        https = youtube.playlistItems().list(part="snippet, ContentDetails",\
                                        maxResults=50, playlistId=youtuber.pl)
    elif https != None and pl != None:
        https = youtube.playlistItems().list_next(https, pl)
    else:
        raise improperUsageError("getPlaylistItems() requires that either both"\
                                 + " or neither https/pl be set!")
    return https, https.execute()

def updateYoutuber(youtube, youtuber):
    getLatestVideo(youtube, youtuber)
    if youtuber.uploadQueue:
        verbose("Found new content uploaded by %s!" % (youtuber.name), override=True)
        for vid in youtuber.uploadQueue.copy():
            try:
                youtuber.subreddit.submit(title=vid[VID_TITLE], url=vid[VID_URL],\
                                          resubmit=True, send_replies=False)
                youtuber.uploadQueue.remove(vid)
                verbose('Submitted video \"%s\"' % (vid[VID_TITLE]), override=True)
            except Exception as e:
                verbose(e, override=True)
    else:
        verbose("No new uploads found for channel %s." % (youtuber.name))

def getLatestVideo(youtube, youtuber):
    # This function checks if the total number of videos in the upload playlist
    # has increased, and returns the new videos if so.
    https, pl = getPlaylistItems(youtube, youtuber)
    newNumVids = pl['pageInfo']['totalResults']
    if newNumVids <= youtuber.numVids: return False
    dVids = newNumVids - youtuber.numVids
    youtuber.numVids = newNumVids
    i = 0
    while i < dVids:
        # Searches each page of the playlist for new videos until it has found them all.
        for item in pl['items']:
            id = item['contentDetails']['videoId']
            if id not in youtuber.vidList:
                title = item['snippet']['title']
                url = "https://www.youtube.com/watch?v=%s" % (id)
                youtuber.vidList.add(id)
                youtuber.uploadQueue.add((title, url))
                i += 1
        # Loads the next page if there is one.
        if 'nextPageToken' in pl.keys():
            https, pl = getPlaylistItems(youtube, youtuber, https=https, pl=pl)
        elif i < dVids:
            verbose('Warning: Loop reached while searching for latest video!')
            https, pl = getPlaylistItems(youtube, youtuber)

class Youtuber(object): pass

class improperUsageError(Exception): pass

if __name__ == "__main__": main()
