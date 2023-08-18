#!/usr/bin/env python
# -*- coding: utf-8 -*-

import conf

import caldav
import datetime
import re
import requests
#import zoneinfo

from ics import Calendar, Event

def main():
    schedule = getSchedule()
    if schedule is not None:
        events, begin, end = convIcal(schedule)
        uploadServerInfo(events, begin, end)

def getSchedule():
    ret = requests.get(conf.calInfoUrl)
    if ret.status_code == 200:
        ret.encoding = 'Shift_JIS'
        return ret.text
    return None

def convIcal(text):
    elements = text.split('<hr>')
#    tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    tz = datetime.timezone(datetime.timedelta(hours=9), name='JST')

    today = datetime.date.today()
    nowYear = int(today.year)
    year = nowYear
    nowMonth = int(today.month)
    month = nowMonth
    events = []
    calStart = None
    calEnd = None
    for element in elements:
        desc = trim(element)
        category = None

        dummyMonth = re.search('^([0-9]+)月$', desc)
        if dummyMonth:
            month = int(dummyMonth.group(1))
            if month < nowMonth:
                year = nowYear + 1
            continue

        event = Event()
        dummyTitle = re.search('/(.*)】', desc)
        if dummyTitle:
            #event.name = dummyTitle.group(1)
            #event.add('summary', dummyTitle.group(1))
            event.name = dummyTitle.group(1)
        else:
            continue
        dummyPlace = re.search('■(.*)→', desc)
        if dummyPlace:
            #event.location = dummyPlace.group(1)
            #event.add('location', dummyPlace.group(1))
            event.location = dummyPlace.group(1)
        dummyCategory = re.search('■カテゴリー：(.*)', desc)
        if dummyCategory:
            category = dummyCategory.group(1)
            if conf.calName not in category:
                continue
        else:
            continue
        startTime, endTime = getStartEndTime(desc, year, month, tz)
        event.begin = startTime
        event.end = endTime
        
        event.description = desc
        events.append(event)

        if calStart is None:
            calStart = startTime
        calEnd = endTime
    return events, calStart, calEnd

def getStartEndTime(desc, year, month, tz):
    startHour = 0
    startMin = 0
    kickoffHour = 0
    kickoffMin = 0
    dummyDay = re.search('【*([0-9]+)日/', desc)
    if dummyDay:
        day = int(dummyDay.group(1))
    dummyStartTime = re.search('集合：([0-9]+):([0-9]+)', desc)
    if dummyStartTime:
        startHour = int(dummyStartTime.group(1))
        startMin  = int(dummyStartTime.group(2))
    dummyKickoffTime = re.search('kickoff：([0-9]+):([0-9]+)', desc)
    if dummyKickoffTime:
        kickoffHour = int(dummyKickoffTime.group(1))
        kickoffMin   = int(dummyKickoffTime.group(2))
    startTime = datetime.datetime(year, month, day, startHour, startMin, tzinfo=tz)
    kickOffTime = datetime.datetime(year, month, day, kickoffHour, kickoffMin, tzinfo=tz)
    if kickOffTime.hour == 0:
        endTime = kickOffTime + datetime.timedelta(hours=24)
    else:
        endTime = kickOffTime + datetime.timedelta(hours=2)
    return startTime, endTime

def trim(data):
    data = re.sub('<br>', '\n', data)
    data = re.sub('<.+?>', '', data)
    data = re.sub('\t', '', data)
    data = re.sub('(\n)+', '\n', data)
    data = re.sub('^\n', '', data)
    return data

def uploadServerInfo(events, begin, end):
    client = caldav.DAVClient(
        url=conf.uploadUlr,
        username=conf.username,
        password=conf.password)
    principal = client.principal()
    calendars = principal.calendars()
    for cal in calendars:
        if cal.name == conf.calName:
            targetCal = cal

    # delete old events
    deleteOldEvents(targetCal, begin, end)

    # add new events
    for event in events:
        ical = Calendar()
        ical.events.add(event)
        targetCal.add_event(ical.serialize())

def deleteOldEvents(cal, begin, end):
    try:
        oldEvents = cal.date_search(start=begin, end=end, expand=True)
        for e in oldEvents:
            e.delete()
    except:
        print('err')

if __name__ == '__main__':
    main()
