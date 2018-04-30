# The Rumor Come Out: Does /u/General_Scales is Bot?

LovelyUploadBot is a python script that pulls videos from a playlist and uploads them to Reddit, whenever new videos are added. The obvious application for this bot is it's usage on a channels upload playlist, which is why it was created.

As is, the code is written to be run on the Game Grumps subreddit with the Game Grumps channel, however this should be easy to change. Should you wish to run this bot, you will need Python 3, PRAW, and the Google Python API.

Install Python 3, then run:
```
sudo pip install praw
sudo pip install --upgrade google-api-python-client
```
Additionally, you will need a Youtube API key from developers.google.com. Next, you will need to create a Reddit project for your bot, and collect its ID and Secret. More information can be found in the documentation for PRAW. This information will need to be compiled into a text file of the following format, named "keys.txt":
```
<Youtube API Key>
<Reddit ID>
<Reddit Secret>
<Reddit Agent>
<Reddit Username>
<Reddit Password>
```
Finally, you will need to edit the main function of the bot. Simply remove the lines declaring, initializing, and updating the Game Grumps/GrumpOut channel in the main function and replace them with whichever channels you wish to use.
