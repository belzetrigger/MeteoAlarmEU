# moved logic of Meteo rss warning to extra class
import re
from datetime import datetime, timedelta
from time import mktime

# import sys
# sys.path
# sys.path.append('/usr/lib/python3/dist-packages')
# synology
# sys.path.append('/volume1/@appstore/py3k/usr/local/lib/python3.5/site-packages')
# windows
# sys.path.append('C:\\Program Files (x86)\\Python37-32\\Lib\\site-packages')

import feedparser
try:
    from bs4 import BeautifulSoup
except Exception as e:
    # looks like update?
    print("Could not load BeautifulSoup. {} ".format(e))

try:
    import Domoticz
except ImportError:
    import fakeDomoticz as Domoticz


class Meteo:
    # ####################################
    # Common definitions
    # maximum of length for details
    MAX_SHOWN_DETAIL_LENGTH = 80
    # show pub date of rss in name
    SHOW_DATE_IN_NAME = True

    AWT_TRANSLATION = {
        1: ["Wind", "Wind", "Wind"],
        2: ["Snow/Ice", "Schnee/Eis", "Snow/Ice"],
        3: ["ThunderStorm", "Gewitter", "ThunderStorm"],
        4: ["Fog", "Nebel", "Fog"],
        5: ["High Temp", "Hohe Temp.", "High Temp"],
        6: ["Low Temp", "Niedrige Temp.", "Low Temp"],
        7: ["Coastal Event", "Coastal Event", "Coastal Event"],
        8: ["Forestfire", "Waldbrand", "Forestfire"],
        9: ["Avalanches", "Avalanches", "Avalanches"],
        10: ["Rain", "Regen", "Rain"],
        11: ["Flood", "Flut", "Flood"],
        12: ["Rain-Flood", "Rain-Flood", "Rain-Flood"],
        99: ["No special awareness required", "Allet knorke!",
             "No special awareness required"],
        200: ["today", "Heute",
              "today"],
        201: ["Tomorrow", "Morgen",
              "tomorrow"]
    }

    # dict for switch dom language to Meteo rss stuff
    DOM_LANG_TO_METEO = {
        'en': 'english',
        'de': 'deutsch',
        'se': 'svenska'
    }

    def __init__(self, rssUrl, domLangSetting, detailSetting="detail_dom_lang",
                 iconSetting="icon_inline_detail"):
        self.rssUrl = rssUrl
        self.lastUpdate = datetime.now()
        self.debug = False
        self.error = False
        self.nextpoll = datetime.now()
        self.detailNo = True
        self.detailLang = "english"
        self.iconNo = True

        self.iconType = ''
        self.langKey = 0  # 0 = english, 1 = german, 2 = ?
        self.configure(domLangSetting, detailSetting, iconSetting)
        self.reset()
        return

    def getDayTitle(self, idx):
        '''returns the title or name for the device.
        "Today: {location} ({update time from rss})"
        Arguments:
            idx {int} -- 0 for today, 1 for tomorrow

        Returns:
            str -- the name: like "Today: {location} ({update time from rss})"
        '''
        s = ''
        if(self.hasError is True):
            s = getAwtTranslation(idx, self.langKey) + ': ERROR!!!'
        else:
            # convert from time struct to date
            dt = datetime.fromtimestamp(mktime(self.pubDate))
            # Domoticz.Debug("XXX{:%H:%M}".format(dt))
            s = getAwtTranslation(idx, self.langKey) + ': ' + self.location
            if Meteo.SHOW_DATE_IN_NAME is True and self.pubDate is not None:
                s = "{} ({:%H:%M})".format(s, dt)
        return s

    def getTodayTitle(self):
        return self.getDayTitle(200)

    def getTomorrowTitle(self):
        return self.getDayTitle(201)

    def needUpdate(self):
        '''does some of the devices need an update

        Returns:
            boolean -- if True -> please update the device in domoticz
        '''

        return self.needUpdate

    def configure(self, domLangSetting, detailSetting, iconSetting):
        '''does the configuration of this service

        Arguments:
            domLangSetting {str} -- the settings from domoticz
            detailSetting {str} -- configuration of detail from domoticz for this current hardware
            iconSetting {str} -- configuration of icons from domoticz for this current hardware
        '''

        # check details and language
        if detailSetting == 'no_detail' or len(detailSetting) <= 0:
            self.detailNo = True
            Domoticz.Debug("switched details off for status text.")
            # a bit ugly ...
            # but set detailLang matching to dom settings
            self.detailLang = getMeteoLang(domLangSetting)
            self.langKey = getLangIndex(self.detailLang)
        else:
            self.detailNo = False
            # get language
            Domoticz.Debug(
                "1#Detail turned on. Fallback-Language is: " + self.detailLang)
            # check if we should use lang from domoticz settings
            if 'detail_dom_lang' in detailSetting:
                Domoticz.Debug("1.2#Try translate lang from domoticz settings (='{}') to meteo rss conform"
                               .format(domLangSetting))
                self.detailLang = getMeteoLang(domLangSetting)
                self.langKey = getLangIndex(self.detailLang)

            else:
                self.detailLang = detailSetting
                self.langKey = getLangIndex(self.detailLang)

            Domoticz.Debug("2#Detail turned on. Language is: '{}'"
                           .format(self.detailLang))
            Domoticz.Debug("settings lang: {}, detail lang: {} key: {}"
                           .format(domLangSetting, self.detailLang,
                                   self.langKey))

        # check icon
        if iconSetting == 'icon_no' or len(iconSetting) <= 0:
            self.iconNo = True
            Domoticz.Debug("switched rss icon off.")
        else:
            self.iconNo = False
            # get type
            self.iconType = iconSetting
            Domoticz.Debug("Rss icon turned on. Type is: " + self.iconType)

    def dumpMeteoConfig(self):
        '''just print configuration and settings to log
        '''

        Domoticz.Log(
            "detailNo: {}\ndetailLang: {}\n"
            "langKey: {}\niconNo: {}\niconType:{}"
            .format(
                self.detailNo,
                self.detailLang,
                self.langKey,
                self.iconNo,
                self.iconType
            )
        )

    def reset(self):
        '''set all important fields to None
        '''

        self.location = None
        self.todayDetail = None
        self.todayLevel = None
        self.tomorrowDetail = None
        self.tomorrowLevel = None
        self.observationDate = None
        self.pubDate = None
        self.needUpdate = True
        self.resetError()

    def setError(self, error):
        '''sets the error msg and put error flag to True

        Arguments:
            error {Exception} -- the caught exception
        '''
        self.hasError = True
        self.errorMsg = error

    def resetError(self):
        '''just removes error flag and deletes last error msg
        '''
        self.hasError = False
        self.errorMsg = None

    def dumpMeteoStatus(self):
        '''just print current status to log
        '''

        Domoticz.Log(
            "##########################################\n"
            "{} ({}) :\nHeute:\t{}-{}\n\rMorgen:\t{}-{}\nneed update?:\t{}"
            "\nError?: {}\tErrorMsg: {}"
            .format(
                self.location,
                self.pubDate,
                self.todayLevel,
                self.todayDetail,
                self.tomorrowLevel,
                self.tomorrowDetail,
                self.needUpdate,
                self.hasError,
                self.errorMsg
            )
        )

    def readMeteoWarning(self):
        """tries to get rss data from Meteo and parse it.
        Values are stored on attributes.
        check self.needUpdate. if we get new data we set a flag there.

        """

        try:

            verifyBS4()

            Domoticz.Debug('Retrieve meteo weather data from ' + self.rssUrl)
            feed = feedparser.parse(self.rssUrl)
            if(feed.status != 200):
                raise Exception("did not find feed for {}".format(self.rssUrl))

            for key in feed["entries"]:
                Domoticz.Log("Gathering Data for:" + str(key["title"]))
                self.location = str(key["title"])
                # mydivs = soup.find("div", {"class": "lastUpdated"})
                if self.pubDate is None:
                    self.needUpdate = True
                elif self.pubDate == key.published_parsed:
                    self.needUpdate = False
                else:
                    self.needUpdate = True
                self.pubDate = key.published_parsed
                soup = BeautifulSoup(str(key["description"]), 'html.parser')
                Domoticz.Log("##########################\n{}\n##########################".format(self.pubDate))
                table = soup.find('table')
                rows = table.find_all('tr')
                idx = 0  # for today , tomorrow
                wrngCounter = 0  # counting warning per days
                data = ["", ""]
                alarms = ["", ""]
                awts = ["", ""]
                levels = ["0", "0"]
                highestLevel = [0, 0]
                AWTtext = ""

                for row in rows:
                    txt = str(row.get_text())

                    # -------------------
                    #  parse first row <tr><th colspan="3" align="left">Today</th></tr>
                    # set index matching to for today/tomorrow
                    if "Today" in txt:
                        idx = 0
                        wrngCounter = 0
                        Domoticz.Debug("######\nBLZ: working on todays data")
                        continue
                    elif "Tomorrow" in txt:
                        idx = 1
                        wrngCounter = 0
                        Domoticz.Debug("######\nBLZ: working on Tomorrow data")
                        continue

                    # -------------------
                    # parse 2nd row for data, warning, level, time
                    # using image as key
                    if row.img:
                        Domoticz.Debug(
                            "BLZ: working on 2nd row awt, level and time")

                        wrngCounter = wrngCounter + 1

                        if(len(data[idx]) > 0):
                            data[idx] = data[idx] + ";\r\n"

                        # find image
                        src = row.img.get('src')
                        Domoticz.Debug("BLZ ########### " + src)
                        if('wflag-l1' in src or 'wflag-l-' in src):
                            Domoticz.Debug(
                                "BLZ: No special awareness required")
                            levels[idx] = 1
                            highestLevel[idx] = 1

                            d = getAwtTranslation(99, self.langKey)

                            data[idx] = d
                            alarms[idx] = d
                            continue

                        # find image and alt tag in this row
                        # alt="awt:6 level:2">
                        # TODO alt and level can be there multiple times, better handle as array of array
                        alt = row.img.get('alt')
                        matches = re.findall(':\d*', alt)
                        # TODO: replace off : sucks ...
                        awts[idx] = str(matches[0]).replace(":", "")
                        levels[idx] = matches[1].replace(":", "")
                        Domoticz.Debug("BLZ: #{} awt {} level {} ".format(
                            wrngCounter, awts[idx], levels[idx]))
                        # From: 16.11.2018 10:51 CET Until: 19.11.2018 12:00 CET
                        # use regEx to get from/to
                        # TODO think about time/date
                        # if same day+-1, only time makes sence
                        # if for longer time, time is not so importend
                        matches = re.findall(
                            '\d{2}.\d{2}.\d{4} \d{2}:\d{2}', txt)
                        start = matches[0]
                        end = matches[1]
                        # generate offset day based on index --> just to now if today or tomorrow is relvant date
                        offset_day = timedelta(days=idx)
                        baseDate = datetime.now()
                        relevantDate = baseDate + offset_day

                        # #######################
                        # TODO
                        # nun beim ende das delta in +
                        # oder beim start als - angeben
                        # issue works on start up, but on update device causes errror (WINDOWS)
                        #####################
                        # startTime = datetime.strptime(start, '%d.%m.%Y %H:%M')
                        # endTime = datetime.strptime(end, '%d.%m.%Y %H:%M')
                        # startDelta = relevantDate.date() - startTime.date()
                        # endDelta = endTime.date() - relevantDate.date()
                        # Domoticz.Error("start: {} delta to now: {}".format(startTime, startDelta))
                        # Domoticz.Error("end: {} delta to now: {}".format(endTime, endDelta))
                        # if( startDelta.days > 0 ):
                        #   start = "{:{tfmt}} (-{}d)".format(startTime , startDelta.days, tfmt='%H:%M')
                        # else:
                        #   start ='{:{tfmt}}'.format(startTime, tfmt='%H:%M')

                        # if( endDelta.days > 0 ):
                        #   end = "{:{tfmt}} (+{}d)".format(endTime , endDelta.days, tfmt='%H:%M')
                        # else:
                        #   end = '{:{tfmt}}'.format(endTime, tfmt='%H:%M')

                        # workaround...
                        matches = re.findall(
                            r'(\d{2}).(\d{2}).(\d{4}) (\d{2}:\d{2})', txt)
                        start = ""
                        end = ""
                        startFull = ""
                        endFull = ""

                        rs = getDatesFromRSS(txt, relevantDate)
                        Domoticz.Log("result: {}".format(rs))

                        start = rs[0]
                        startFull = rs[1]
                        end = rs[2]
                        endFull = rs[3]

                        AWTtext = getAwtTranslation(awts[idx], self.langKey)

                        if len(alarms[idx]) > 1:
                            alarms[idx] = alarms[idx] + ", \r\n"

                        if(self.iconNo):
                            warnImg = ''
                        else:
                            if('detail' in self.iconType):
                                warnImg = "<img border='1' height='13' src='{}' title='{} - {}: {}'/>".format(
                                    src, startFull, endFull, "_DETAIL_")
                            else:
                                warnImg = "<img border='1' height='13' src='{}' title='{} - {}'/>".format(
                                    src, startFull, endFull)
                        alarms[idx] = "{} {} {}({}) {}-{}".format(alarms[idx],
                                                                  warnImg, AWTtext, levels[idx], start, end)
                        # data[idx]= "{} {} {}({}) {}-{}".format(data[idx],  warnImg,AWTtext, levels[idx], start,end)
                        data[idx] = "{}  {} {}({}) {}-{}  ".format(data[idx],
                                                                   warnImg, AWTtext, levels[idx], start, end)

                        # just level what for?????
                        if (levels[idx] == "5"):
                            levels[idx] = "1"

                        # check highest level
                        if(int(levels[idx]) > int(highestLevel[idx])):
                            highestLevel[idx] = int(levels[idx])

                        continue

                    # -------------------
                    # parse 3rd row for details
                    # if switched on

                    detailTxt = ''
                    # search for details
                    # only if details switched on generally or for icon
                    if(self.detailNo is False or 'detail' in self.iconType):
                        if self.detailLang in txt:
                            # all languagres in one line eg: AT deutsch: bla english: bli
                            # deutsch: Es treten oberhalb 1000 m Sturmböen mit
                            # Geschwindigkeiten zwischen 60 km/h (17m/s, 33kn, Bft 7) und 70 km/h (20m/s, 38kn, Bft 8)
                            # aus östlicher Richtung auf. In exponierten Lagen muss mit Sturmböen um 80 km/h
                            # (22m/s, 44kn, Bft 9) gerechnet werden.
                            # if( len(data[idx]) > 0 ) :
                            #  data[idx] = data[idx] + "\r\n"

                            # extract matching lang
                            # matches = re.findall('(\benglish:|\bdeutsch:|\bsvenska:)(.*)', txt)
                            for (lang, detail) in re.findall('(english:|deutsch:|svenska:)(.*)', txt):
                                # Domoticz.Debug('BLZ lang: {} \tdetail: {}'.format(lang, detail))
                                if self.detailLang in lang:
                                    # got now right entry store it and leave
                                    detailTxt = detail
                                    Domoticz.Debug('BLZ found detail {} ({})'.format(
                                        detailTxt, self.detailLang))
                                    break

                            # for m in re.finditer('(english:|deutsch:|svenska:)(.*)', txt):
                            #  Domoticz.Debug('fgffg {}'.format( m.group(2)))

                            ##
                            # take care about shown text
                            # put it in our array - should be already
                            # prefilled with data for alarm
                            # cut off if it is too long ...
                            # only first 100 chars
                            if(self.detailNo is False):
                                if(len(detailTxt) > Meteo.MAX_SHOWN_DETAIL_LENGTH):
                                    data[idx] = "{} {}...".format(
                                        data[idx], detailTxt[:Meteo.MAX_SHOWN_DETAIL_LENGTH])
                                else:
                                    data[idx] = "{} {}".format(
                                        data[idx], detailTxt)
                            ##
                            # take care about icon
                            if 'icon_inline_detail' in self.iconType:
                                # Test, put details to image
                                data[idx] = data[idx].replace(
                                    '_DETAIL_', detailTxt)
                        else:
                            Domoticz.Log(
                                "details switched ON, "
                                " but language '{}' not found."
                                .format(self.detailLang))
                    else:
                        Domoticz.Debug("details switched OFF, so just Warning")
                        # data[idx] =  "{} {}({}) ".
                        # format(  data[idx],  AWTtext, levels[idx])
                        data[idx] = alarms[idx]

                # after all lines ...
                Domoticz.Debug("BLZ: Alarm today:\t{}\ntomorrow:\t{} ".format(
                    alarms[0], alarms[1]))
                self.todayDetail = data[0]
                self.todayLevel = highestLevel[0]

                self.tomorrowDetail = data[1]
                self.tomorrowLevel = highestLevel[1]
                if(not self.detailNo):
                    Domoticz.Debug(
                        "BLZ: Txt today:\t{}\ntomorrow:\t{} "
                        .format(data[0], data[1]))

        except (Exception) as e:
            Domoticz.Error("Error: " + str(e) + " URL: " + self.rssUrl)
            self.setError(e)
            return
        self.lastUpdate = datetime.now()


#############################################################################
#                       Data specific functions                             #
#############################################################################


# def getMeteoLangFromSettings():
#    lng = Settings["Language"]
#    return getMeteoLang(lng)


# takes the
# PARAM :domLanguage
# RETURN
#
def getMeteoLang(domLanguage):
    """translate the domoticz language from Settings["Language"] to meteo confrom.
    eg: Domoticz: de -> meteo: deutsch,
    as you see, we use the langauge own name for the language.
    because meteo rss warning is using it this way.

    Arguments:
        domLanguage {str} -- value from domoticz settings for language

    Returns:
        str -- the matching longform language that works wit meteo rss
    """

    if domLanguage in Meteo.DOM_LANG_TO_METEO:
        mLang = Meteo.DOM_LANG_TO_METEO[domLanguage]
    else:
        Domoticz.Error("Given key '{}' "
                       + "does not exist in Mapping "
                       + "from Domoticz to Meteo! "
                       .format(domLanguage))
    return mLang


def getLangIndex(meteoLang):
    """takes the langauge from meteo and convert it to keyself.
    if language is not found, we return 0 for english

    Arguments:
        meteoLang {str} -- longform of language

    Returns:
        int -- return the matching key or 0 for english as fallback
    """

    langKey = 0
    if 'svenska' in meteoLang:
        langKey = 2
    elif 'deutsch' in meteoLang:
        langKey = 1
    else:
        langKey = 0
    return langKey

# takes the key from meteo and looks for defined translation
# PARAM
#  idx - based on the meteo rss awt, but its extended, so 99 works as well
#  langIndex - the index stands for postion in langauge array
#              0=english,1=deutsch,2=svenska


def getAwtTranslation(idx, langIndex):
    """
    takes the key from meteo and looks for defined translation

    Arguments:
        idx {[type]} -- key/index from meteo rss awt, but its extended, so 99 works as well
        langIndex {int} -- the index stands for postion in langauge array 0=english,1=deutsch,2=svenska

    Returns:
        str -- translated longform for given awt key
    """

    txt = idx
    if int(idx) in Meteo.AWT_TRANSLATION:
        t = Meteo.AWT_TRANSLATION[int(idx)]
        txt = t[langIndex]
    else:
        txt = idx
        Domoticz.Error(
            "BLZ: did not found key '{}' in translation list!".format(idx))
    return txt


def getDatesFromRSS(txt, relevantDate):
    """parses the txt from rss feed. Search for from to dates
    in form of dd.mm.yyyy HH:MM. If warning is relevant for the same day as
    relevant day, we return the time, otherwise the date in form dd.mm.

    Arguments:
        txt {str} -- txt from rss feed, containing the from to dates
        relevantDate {date} -- the day of the device, means today or tomorrow


    Returns:
        array -- the parsed dates as [start[0], start[1], end[0], end[1]]
                 [shortStartDate, longStartDate, shortEndDate, longEndDate]
    """
    start = ["", ""]
    end = ["", ""]
    matches = re.findall(r'(\d{2}).(\d{2}).(\d{4}) (\d{2}:\d{2})', txt)
    if(matches):
        start = getDatesFromMatch(matches[0], relevantDate)
        end = getDatesFromMatch(matches[1], relevantDate)
    result = [start[0], start[1], end[0], end[1]]
    return result


def getDatesFromMatch(match, relevantDate):
    '''extract the dates from a performed reg ex search
    and compare with relevant date to deliver a a customized shortDate
    If warning is relevant for the same day as relevant day, we return the time,
    otherwise the date in form dd.mm.
    Arguments:
        match {regex match} -- the matches from reg ex search.
                            matches = re.findall(r'(\d{2}).(\d{2}).(\d{4}) (\d{2}:\d{2})', txt)
                            dd.mm.yyyy HH:MM
        relevantDate {date} -- the day of the device, means today or tomorrow

    Returns:
        [array] -- [shortDate, longDate]
    '''
    iDay = int(match[0])
    longDate = "{}.{}. {}".format(iDay, match[1], match[3])
    # take care about start date
    if iDay == relevantDate.date().day:
        shortDate = match[3]
    else:
        shortDate = "{}.{}.".format(iDay, match[1])
    result = [shortDate, longDate]
    return result


def verifyBS4():
    if(moduleLoaded('bs4') is False):
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            Domoticz.Error("Error import BeautifulSoup".format(e))


def moduleLoaded(modulename: str):
    if modulename not in sys.modules:
        Domoticz.Error('{} not imported'.format(modulename))
        return False
    else:
        Domoticz.Debug('{}: {}'.format(modulename, sys.modules[modulename]))
        return True
