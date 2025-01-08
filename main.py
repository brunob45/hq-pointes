#!/usr/bin/env python3

import json
import os
import requests

from datetime import datetime, timedelta
from dateutil import tz
from dotenv import load_dotenv
from time import sleep


class Event:
  ''' event description '''

  def from_hq(self, data):
    ''' create event from Hydro-Quebec API '''

    self.start = datetime.fromisoformat(data["datedebut"])
    self.end = datetime.fromisoformat(data["datefin"])
    self.summary = "pointe"
    return self

  def from_ha(self, data):
    ''' create event from Home Assistant API '''

    self.start = datetime.fromisoformat(data["start"]["dateTime"])
    self.end = datetime.fromisoformat(data["end"]["dateTime"])
    self.summary = data["summary"]
    return self

  def __repr__(self) -> str:
    ''' text representation '''
    return json.dumps(self.get_data(), indent=2)

  def __eq__(self, value):
    ''' test if events are equal '''
    return (
      isinstance(value, Event)
      and (self.start == value.start)
      and (self.end == value.end)
      and (self.summary == value.summary)
    )

  def get_data(self) -> dict:
    ''' create the json object to create a new Home Assistant event '''
    return {
      "entity_id": "calendar.hq_flex_d",
      "summary": "pointe",
      "start_date_time": self.start.isoformat(timespec="minutes"),
      "end_date_time": self.end.isoformat(timespec="minutes"),
    }


def get_ha_events(url: str, headers: dict):
  ''' fetch events from Home Assistant '''
  start = datetime.now()
  end = start + timedelta(days=7)

  start = start.isoformat(timespec='seconds')
  end = end.isoformat(timespec='seconds')

  # https://developers.home-assistant.io/docs/api/rest
  url = f"{url}/api/calendars/calendar.hq_flex_d?start={start}Z&end={end}Z"
  print(url)
  response = requests.get(url, headers=headers)

  if response.status_code != 200:
    print(f'request to HA failed with status {response.status_code}')
    return None  # request failed
  elif not response.text:
    return []  # request succeeded but empty

  results = json.loads(response.text)
  events = [Event().from_ha(x) for x in results]
  # print(events)
  return events


def get_hq_events():
  ''' fetch events from Hydro-Quebec '''
  # https://donnees.hydroquebec.com/explore/dataset/evenements-pointe/information/
  url = "https://donnees.hydroquebec.com/api/explore/v2.1/catalog/datasets/evenements-pointe/records?where=offre%3D%22CPC-D%22&order_by=datedebut%20desc&limit=20"
  response = requests.get(url)

  if response.status_code != 200:
    print(f'request to HQ failed with status {response.status_code}')
    return None  # request failed
  if not response.text:
    return []  # request succeeded but empty

  results = json.loads(response.text)["results"]
  events = [Event().from_hq(x) for x in results]
  # print(events)
  return events


def create_ha_event(url: str, headers: dict, data: dict):
  ''' create a new event in Home Assistant '''
  # https://www.home-assistant.io/integrations/calendar/#service-calendarcreate_event
  url = f"{url}/api/services/calendar/create_event"
  response = requests.post(url, headers=headers, json=data)
  print(response.text)


def compare_events(url: str, headers: dict):
  NOW = datetime.now(tz=tz.tzlocal())

  # fetch both event lists
  events_ha = get_ha_events(HA_URL, HEADERS)
  events_hq = get_hq_events()

  if (events_ha is None) or (events_hq is None):
    return  # early return, request failed

  # for all Hydro-Quebec events
  for event in events_hq:
    if event.start < NOW:  # ignore if in the past
      print(f'Event ignored {event}')
    elif any(event == x for x in events_ha):  # compare with all HA events, ignore if already present
      print(f'Event found {event}')
    else:  # new event, create in HA
      create_ha_event(HA_URL, HEADERS, event.get_data())
      print(f'Event created {event}')


if __name__ == '__main__':
  ''' main function '''
  load_dotenv()

  # https://developers.home-assistant.io/docs/api/rest/
  HA_URL = os.getenv('HA_URL')
  HEADERS = {
    "Authorization": f"Bearer {os.getenv('HA_TOKEN')}",
    "content-type": "application/json",
  }

  while True:  # main loop
    compare_events(HA_URL, HEADERS)
    sleep(3600) # 1 hours in seconds

  print('done')
