# plugin for displaying weather warnigs
#
# Author: belze
#
"""
MeteoAlarmEU RSS Reader Plugin

Author: Belze(2018/2019/2020), Ycahome(2017)


Version:    1.0.0: Initial Version
            1.0.1: Minor bug fixes
            1.0.2: Bug Correction
            1.3.0: switched to from bs4 import BeautifulSoup by blz
            1.3.1: add option to show details and also use highest level for alarm level if multiple entries
            1.3.2: add option to show alarm icon from rss feed and switch language
            1.3.3: add option to use language from domoticz settings
            1.4.0: moved to extra class
            1.4.1: cleaned up a bit and added comments on functions
            1.4.2: bit more stability and better handling for wrong feed url

"""
"""


<plugin key="MeteoAlarmEUX"
name="Meteo Alarm EU RSS ReaderX" author="belze & ycahome"
version="1.4.2" wikilink="" externallink="http://www.domoticz.com/forum/viewtopic.php?f=65&t=19519">
     <description>
        <h2>Meteo Alarm EU RSS Reader eXtended</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>shows warnings for today and tomorrow</li>
            <li>using domoticz alarm level to signal the risk</li>
            <li>detail level can be chosen</li>
            <li>supports english, german, partly swedish</li>
            <li>use this langauge to grab matching warning from meteo</li>
            <li>icons from meteo can be embedded</li>
            <li>meteo publish date is shown in name</li>
            <li>if problems occur eg. missing libs - devices will show it</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>today - warnings for current day</li>
            <li>tomorrow - warnings for the next day</li>
        </ul>
        <h3>Hint</h3>
        First visit -><a href="http://www.meteoalarm.eu/">
        Meteo_</a> to choose your region and get rss-Feed link
    </description>

    <params>
        <param field="Mode1" label="RSSFeed" width="400px" required="true"
        default="http://www.meteoalarm.eu/documents/rss/de/DE404.rss"/>
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
# synology
# sys.path.append('/volume1/@appstore/py3k/usr/local/lib/python3.5/site-packages')


from meteo import Meteo

# TODO
# - deeper look on from-until, sometimes until goes for a few days... in this case clock is not enough
# - langauge
#  - use langauge from dom Settings["Language"] - en,de,..
#  - if defined lang not found in rss -> english as fallback?
#  - clean up
# - more languages ..
# - icons as set?,
#  - 48png
#  - alarmtype must be integrated into alarm level, default is 0-4, eg: Alert48_22.png
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
            # check if error
            if(self.mt.hasError is True):
                txt = self.mt.errorMsg
                updateDevice(1, 4, txt, self.mt.getTodayTitle())
                updateDevice(2, 4, txt, self.mt.getTomorrowTitle())
            else:
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
#                   common functions                                        #
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
                Devices[Unit].Update(int(highestLevel), str(alarmData))
            else:
                Devices[Unit].Update(int(highestLevel), str(alarmData), Name=name)
            Domoticz.Log("BLZ: Awareness Updated to: {} value: {}".format(alarmData, highestLevel))
        else:
            Domoticz.Log("BLZ: Awareness Remains Unchanged")
    else:
        Domoticz.Error("Devices[{}] is unknown. So we cannot update it.".format(Unit))
