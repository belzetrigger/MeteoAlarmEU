#!/usr/bin/env python3
#
#   simple tests the meteo

from meteo import Meteo

# Berlijn
lat_be = 52.516667
lon_be = 13.416667

rssFreudenstadt = "https://www.meteoalarm.eu/documents/rss/de/DE404.rss"
rssErz = "https://www.meteoalarm.eu/documents/rss/de/DE092.rss"
rssBerlin = "https://www.meteoalarm.eu/documents/rss/de/DE202.rss"
rssKarjala = "https://www.meteoalarm.eu/documents/rss/fi/FI001.rss"


x = Meteo(rssFreudenstadt, "de")
x.dumpMeteoConfig()
x.readMeteoWarning()
x.dumpMeteoStatus()
# just re run
x.readMeteoWarning()
x.dumpMeteoStatus()
print("tdy: " + x.getTodayTitle())
print("tmr:" + x.getTomorrowTitle())

y = Meteo(rssKarjala, "en")
y.dumpMeteoConfig()
y.readMeteoWarning()
y.dumpMeteoStatus()
print("tdy: " + y.getTodayTitle())
print("tmr:" + y.getTomorrowTitle())
