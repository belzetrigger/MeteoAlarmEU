# MeteoAlarmEU
 [![Plugin version](https://img.shields.io/badge/version-1.4.2-red.svg)]()

Domoticz plugin that get data from MeteoAlarm RSS data from MeteoAlarm.eu site

Original project 
and forum link: http://www.domoticz.com/forum/viewtopic.php?f=65&t=19519&hilit=MeteoAlarmEU
And also got a lot ideas from ffes [domoticz-buienradar](https://github.com/ffes/domoticz-buienradar/)

![settings](https://github.com/belzetrigger/domoticz-MeteoAlarmEU/raw/master/resources/unit_en_ml_warnings.PNG)

## Summary
This is a virtual hardware plugin that adds information about extreme weather from [meteoalarm.eu](http://www.meteoalarm.eu/) to your [Domoticz](https://www.domoticz.com/) interface. Therefore it will generate two new alert sensors showing latest warnings. One for today and another one for tomorrow.

As this is a european meteorological service it only works in Europe. And you also shoud check [meteoalarm.eu](http://www.meteoalarm.eu/about.php?lang=en_UK) if your country is participating. 

This plugin is open source.


## Installation and Setup
- a running Domoticz, tested with 4.10038 and 2020.1
- Python 3
- install needed python moduls:
  - beautifullsoup bs4
  - feedparser
  - you can use `sudo pip3 install -r requirements.txt` 
- clone project
    - go to `domoticz/plugins` directory 
    - clone the project
        ```bash
        cd domoticz/plugins
        git clone https://github.com/belzetrigger/domoticz-MeteoAlarmEU.git
        ```
- or just download, unzip and copy to `domoticz/plugins` 
- no need on Raspbian for sys path adaption if using sudo for pip3
- some extra work for Windows or Synology, make sure downloaded modules are in path eg. site-packages python paths or change in plugin.py / fritzHelper.py path
  - example adaption:
    ```bash
    import sys
    sys.path
    sys.path.append('/usr/lib/python3/dist-packages')
    # for synology python3 from community
    # sys.path.append('/volume1/@appstore/python3/lib/python3.5/site-packages')
    # for synology sys.path.append('/volume1/@appstore/py3k/usr/local/lib/python3.5/site-packages')
    # for windows check if installed packages as admin or user...
    # sys.path.append('C:\\Program Files (x86)\\Python37-32\\Lib\\site-packages')
    ```
- restart Domoticz service
- Now go to **Setup**, **Hardware** in your Domoticz interface. There add
**MeteoAlarmEU**.
### Settings
![settings](https://github.com/belzetrigger/domoticz-MeteoAlarmEU/raw/master/resources/settings.PNG)

    - RSSFeed:
        -  go to [meteoalarm.eu](http://www.meteoalarm.eu/?lang=en_UK)
        -  select your country
        -  select your region
        -  on upper right corner click on orange rss symbol
        -  copy url, should look like https://www.meteoalarm.eu/documents/rss/fi/FI001.rss
        -  paste into settings
    -  Update:  time to wait till next poll
    -  Debug: if True, the log will be hold a lot more output.
    -  Details and Language:
        -  NO_Detail
        -  Details Domoticz Languag: - just grab the language from domoticz and use it
        -  Details in english - ignore domoticz settings, just search for english details 
        -  Details auf deutsch - ignore domoticz settings, just search for german details 
        -  Details pa svenska - ignore domoticz settings, just search for swedish details 
    -  Show Alarm Icon:
        -  NO_ICON: We do not show the warning image from meteo rss feed
        -  inline icon: we show the little alarm icon from meteo
        -  inline icon with detail: we show the icon and also add the warning text as tool tip


## Bugs and ToDos
1. Inline images reference to meteo for example https://www.meteoalarm.eu/documents/rss/wflag-l2-t2.jpg  This means if client does not have access, it will be blank.
2. Think about how to use warning in the domoticz systems. For example do something with the blinds on strong wind, or stop/delay watering the garden if ..

## State
In development. 
Improve
- make languages, more flexible
- add more languages
Testing 
 - test with other themes
 - test with other languages
 
## How it Works in details
Takes the rss feed from meteo and scans it for:
- today / tomorrow: to know which device must be updated
- icons: 
    - to get the type of warning and alarm level
    - to use the same url on the device text to show image 
- keep the worst alarm level per day and use it for Domoticz alarm sensor
- updateDate aka 'publish Date' of feed: to know if there is a change, and so devices should be updated too
- language in warning message. because content is like [language]: blabla
Collect all those data per day and puts it on domoticz alarm devices

## Developing
Based on https://github.com/ffes/domoticz-buienradar/ there are
 -  `fakeDomoticz.py` - used to run it outside of Domoticz
 -  `testMeteo.py` it's the entry point for tests

## ChangeLog
1.0.0: Initial Version
1.0.1: Minor bug fixes
1.0.2: Bug Correction
1.3.0: switched to from bs4 import BeautifulSoup by blz
1.3.1: add option to show details and also use highest level for alarm level if multiple entries
1.3.2: add option to show alarm icon from rss feed and switch language
1.3.3: add option to use language from domoticz settings
1.4.0: moved to extra class
1.4.1: cleaned up a bit and added comments on functions
1.4.2: bit more stability and better handling for wrong feed url
