import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from os import path

sys.path
sys.path.append('/usr/lib/python3/dist-packages')
sys.path.append('/volume1/@appstore/py3k/usr/local/lib/python3.5/site-packages')

import feedparser
from bs4 import BeautifulSoup

from meteo import Meteo


"""
MeteoAlarmEU RSS Reader Plugin

Author: Belze(2018), Ycahome(2017)


Version:    1.0.0: Initial Version
            1.0.1: Minor bug fixes
            1.0.2: Bug Correction
            1.3.0: switched to bfrom bs4 import BeautifulSoup by blz
            1.3.1: add option to show details and also use highest level for alarm level if multiple entries
            1.3.2: add option to show alarm icon from rss feed and swtich language
            1.3.3: add option to use language from domoticz settings
            1.4.0: moved to extra class
            1.4.1: cleaned up a bit and added comments on functions
"""
"""


<plugin key="MeteoAlarmEUX"
name="Meteo Alarm EU RSS ReaderX" author="belze & ycahome"
version="1.4.1" wikilink="" externallink="http://www.domoticz.com/forum/viewtopic.php?f=65&t=19519">
    <params>
        <param field="Mode1" label="RSSFeed" width="400px" required="true"
        default="http://www.meteoalarm.eu/documents/rss/gr/GR011.rss"/>
        <param field="Mode3" label="Update every x minutes" width="200px"
        required="true" default="300"/>
        <param field="Mode4" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="False" />
            </options>
        </param>
        <param field="Mode5" label="Details and Language for Status" width="200px"
        title="here you can choose if more details from rss should be shown and if so - which language to use">
            <options>
                <option label="NO_DETAIL" value="no_detail"  selected="selected"/>
                <option label="Details using domoticz lang" value="detail_dom_lang"/>
                <option label="Details in english" value="english"   />
                <option label="Details auf deutsch" value="deutsch"   />
                <option label="Details pa svenska" value="svenska"   />
            </options>
        </param>
        <param field="Mode6" label="Show Alarm Icons from RSS" width="200px">
            <options>
                <option label="NO_ICON" value="icon_no"  selected="selected"/>
                <option label="inline icon" value="icon_inline"   />
                <option label="inline icon with detail" value="icon_inline_detail"   />
            </options>
        </param>
    </params>
</plugin>
"""
# TODO
# - deeper look on from-untill, sometimes untill goes for a few days... in this case clock is not enough
# - langauge
#  - use langauge from dom Settings["Language"] - en,de,..
#  - if defined lang not found in rss -> english as fallback?
#  - clean up
# - more languages ..
# - icons as set?,
#  - 48png
#  - alarmtype must be integreted into alarm level, default is 0-4, eg: Alert48_22.png
#  - see www/app/UtilityController.js: img='<img src="images/Alert48_' + item.Level + '.png" height="48" width="48">';
#  - https://www.meteoalarm.eu/documents/rss/wflag-l4-t10.jpg
#  - https://www.meteoalarm.eu/theme/common/pictures/aw104.jpg


try:
    import Domoticz
except ImportError:
    import fakeDomoticz as Domoticz

sys.path
sys.path.append('/usr/lib/python3/dist-packages')
sys.path.append('/volume1/@appstore/py3k/usr/local/lib/python3.5/site-packages')
sys.path.append('C:\\Program Files (x86)\\Python37-32\\Lib\\site-packages')


# from unidecode import unidecode


# from unidecode import unidecode


class BasePlugin:

    def __init__(self):
        self.debug = False
        self.error = False
        self.nextpoll = datetime.now()
        self.detailNo = True
        self.detailLang = "english"
        self.iconNo = True

        self.iconType = ''
        self.langKey = 0  # 0 = english, 1 = german, 2 = ?

        self.rss = None
        return

    def onStart(self):
        if Parameters["Mode4"] == 'Debug':
            self.debug = True
            Domoticz.Debugging(1)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)

        Domoticz.Debug("onStart called")

        # check polling interval parameter
        try:
            temp = int(Parameters["Mode3"])
        except:
            Domoticz.Error("Invalid polling interval parameter")
        else:
            if temp < 5:
                temp = 5  # minimum polling interval
                Domoticz.Error("Specified polling interval too short: changed to 5 minutes")
            elif temp > 1440:
                temp = 1440  # maximum polling interval is 1 day
                Domoticz.Error("Specified polling interval too long: changed to 1440 minutes (1 day)")
            self.pollinterval = temp * 60
        Domoticz.Log("Using polling interval of {} seconds".format(str(self.pollinterval)))

        if Parameters["Mode4"] == 'Debug':
            self.debug = True
            Domoticz.Debugging(1)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)

        self.rssUrl = Parameters["Mode1"]

        self.mt = Meteo(self.rssUrl, Settings["Language"], Parameters["Mode5"], Parameters["Mode6"])
        if self.debug is True:
            self.mt.dumpMeteoConfig

        # Check if devices need to be created
        createDevices()

        # init with empty data
        updateDevice(1, 0, "No Data")
        updateDevice(2, 0, "No Data")

    def onStop(self):
        Domoticz.Debug("onStop called")
        Domoticz.Debugging(0)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(
            "onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onHeartbeat(self):
        now = datetime.now()
        if now >= self.nextpoll:
            self.nextpoll = now + timedelta(seconds=self.pollinterval)
            self.mt.readMeteoWarning()
            # check if
            if self.mt.needUpdate is True:
                updateDevice(1, self.mt.todayLevel, self.mt.todayDetail, self.mt.getTodayTitle())
                updateDevice(2, self.mt.tomorrowLevel, self.mt.tomorrowDetail, self.mt.getTomorrowTitle())
            Domoticz.Debug("----------------------------------------------------")


global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

#############################################################################
#                   common functions                     #
#############################################################################


# Generic helper functions


def DumpConfigToLog():
    '''just dumps the configuration to log.
    '''
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return


def parseIntValue(s):
    """Parse an int and return None if no int is given
     Arguments:
        s {str} -- string of int value
    Returns:
        int -- the value in int or None
    """
    try:
        return int(s)
    except:
        return None

#
# Parse a float and return None if no float is given
#


def parseFloatValue(s):

    try:
        return float(s)
    except:
        return None

#############################################################################
#                       Data specific functions                             #
#############################################################################


# def getMeteoLangFromSettings():
#     lng = Settings["Language"]
#     return getMeteoLang(lng)


# # takes the
# # PARAM :domLanguage
# # RETURN
# #
# def getMeteoLang(domLanguage):
#     if domLanguage in BasePlugin.DOM_LANG_TO_METEO:
#         mLang = BasePlugin.DOM_LANG_TO_METEO[domLanguage]
#     else:
#         Domoticz.Error("Given key '{}' does not exist in Mapping from Domoticz to Meteo! ".format(domLanguage))
#     return mLang


# def getLangIndex(meteoLang):
#     langKey = 0
#     if 'svenska' in meteoLang:
#         langKey = 2
#     elif 'deutsch' in meteoLang:
#         langKey = 1
#     else:
#         langKey = 0
#     return langKey

# takes the key from meteo and looks for defined translation
# PARAM
#  idx - based on the meteo rss awt, but its extended, so 99 works as well
#  langIndex - the index stands for postion in langauge array 0=english,1=deutsch,2=svenska


# def getAwtTranslation(idx, langIndex):
#     txt = idx
#     if int(idx) in BasePlugin.AWT_TRANSLATION:
#         t = BasePlugin.AWT_TRANSLATION[int(idx)]
#         txt = t[langIndex]
#     else:
#         txt = idx
#         Domoticz.Error("BLZ: did not found key '{}' in translation list!".format(idx))
#     return txt


# def getDatesFromRSS(txt, relevantDate):
#     """parses the txt from rss feed. Search for from to dates
#     in form of dd.mm.yyyy HH:MM. If warning is relevant for the same day as
#     relevant day, we retun the time, otherwise the date in form dd.mm.

#     Arguments:
#         txt {str} -- txt from rss feed, containing the from to dates
#         relevantDate {date} -- the day of the device, means today or tomorrow


#     Returns:
#         arry -- the parsed dates as [start[0], start[1], end[0], end[1]]
#                  [shortStartDate, longStartDate, shortEndDate, longEndDate]
#     """

#     start = ["", ""]
#     end = ["", ""]
#     matches = re.findall(r'(\d{2}).(\d{2}).(\d{4}) (\d{2}:\d{2})', txt)
#     if(matches):
#         start = getDatesFromMatch(matches[0], relevantDate)
#         end = getDatesFromMatch(matches[1], relevantDate)
#     result = [start[0], start[1], end[0], end[1]]
#     return result


# def getDatesFromMatch(match, relevantDate):
#     '''extract the dates from a performed reg ex search
#     and compare with relevant date to deliver a a custimzed shortDate
#     If warning is relevant for the same day as relevant day, we retun the time,
#     otherwise the date in form dd.mm.
#     Arguments:
#         match {regex match} -- the matches from reg ex search.
#                             matches = re.findall(r'(\d{2}).(\d{2}).(\d{4}) (\d{2}:\d{2})', txt)
#                             dd.mm.yyyy HH:MM
#         relevantDate {date} -- the day of the device, means today or tomorrow

#     Returns:
#         [array] -- [shortDate, longDate]
#     '''

#     iDay = int(match[0])
#     longDate = "{}.{}. {}".format(iDay, match[1], match[3])
#     # take care about start date
#     if iDay == relevantDate.date().day:
#         shortDate = match[3]
#     else:
#         shortDate = "{}.{}.".format(iDay, match[1])
#     result = [shortDate, longDate]
#     return result

#############################################################################
#                       Device specific functions                           #
#############################################################################


def createDevices():
    '''
    this creates the device for today and tomorrow, if they are not in device-list
    '''

    # create the mandatory child devices if not yet exist
    if 1 not in Devices:
        Domoticz.Device(Name="Today", Unit=1, TypeName="Alert", Used=1).Create()
        Domoticz.Log("Devices[1] created.")
    if 2 not in Devices:
        Domoticz.Device(Name="Tomorrow", Unit=2, TypeName="Alert", Used=1).Create()
        Domoticz.Log("Devices[2] created.")


#
def updateDevice(Unit, highestLevel, alarmData, name='', alwaysUpdate=False):
    '''update a device - means today or tomorrow, with given data.
    If there are changes and the device exists.
    Arguments:
        Unit {int} -- index of device, 1 = today, 2 = tomorrow
        highestLevel {[type]} -- the maximum warning level for that day, it is used to set the domoticz alarm level
        alarmData {[str]} -- data to show in that device, aka text

    Optional Arguments:
        name {str} -- optional: to set the name of that device, eg. mor info about  (default: {''})
        alwaysUpdate {bool} -- optional: to ignore current status/needs update (default: {False})
    '''

    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if (alarmData != Devices[Unit].sValue) or (int(highestLevel) != Devices[Unit].nValue or alwaysUpdate is True):
            if(len(name) <= 0):
                Devices[Unit].Update(int(highestLevel), alarmData)
            else:
                Devices[Unit].Update(int(highestLevel), alarmData, Name=name)
            Domoticz.Log("BLZ: Awareness Updated to: {} value: {}".format(alarmData, highestLevel))
        else:
            Domoticz.Log("BLZ: Awareness Remains Unchanged")
    else:
        Domoticz.Error("Devices[{}] is unknown. So we cannot update it.".format(Unit))
