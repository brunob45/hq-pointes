#!/usr/bin/env python3

import json
import os
import requests

from datetime import datetime, timedelta
from dateutil import tz
from dotenv import load_dotenv
from time import sleep


class Event:
  def from_hq(self, data):
    self.start = datetime.fromisoformat(data["datedebut"])
    self.end = datetime.fromisoformat(data["datefin"])
    self.summary = "pointe"
    return self

  def from_ha(self, data):
    self.start = datetime.fromisoformat(data["start"]["dateTime"])
    self.end = datetime.fromisoformat(data["end"]["dateTime"])
    self.summary = data["summary"]
    return self

  def __repr__(self) -> str:
    return json.dumps(self.get_data(), indent=2)

  def __eq__(self, value):
    return (
      isinstance(value, Event)
      and (self.start == value.start)
      and (self.end == value.end)
      and (self.summary == value.summary)
    )

  def get_data(self) -> dict:
    return {
      "entity_id": "calendar.hq_flex_d",
      "summary": "pointe",
      "start_date_time": self.start.isoformat(timespec="minutes"),
      "end_date_time": self.end.isoformat(timespec="minutes"),
    }


def get_ha_events(url: str, headers: dict):
  start = datetime.now()
  end = start + timedelta(days=7)

  start = start.isoformat(timespec='seconds')
  end = end.isoformat(timespec='seconds')

  url = f"{url}/api/calendars/calendar.hq_flex_d?start={start}Z&end={end}Z"
  print(url)
  response = requests.get(url, headers=headers)

  if not response.text:
    return []

  results = json.loads(response.text)
  events = [Event().from_ha(x) for x in results]
  # print(events)
  return events


def get_hq_events():
  url = "https://donnees.hydroquebec.com/api/explore/v2.1/catalog/datasets/evenements-pointe/records?where=offre%3D%22CPC-D%22&order_by=datedebut%20desc&limit=20"
  response = requests.get(url)

  if not response.text:
    return []

  results = json.loads(response.text)["results"]
  events = [Event().from_hq(x) for x in results]
  # print(events)
  return events


def create_ha_event(url: str, headers: dict, data: dict):
  url = f"{url}/api/services/calendars/create_event"
  response = requests.get(url, headers=headers, json=data)
  print(response.text)


def compare_events(url: str, headers: dict):
  NOW = datetime.now(tz=tz.tzlocal())

  events_ha = get_ha_events(HA_URL, HEADERS)
  events_hq = get_hq_events()

  for event in events_hq:
    if event.start < NOW:
      print(f'Event ignored {event}')
    elif any(event == x for x in events_ha):
      print(f'Event found {event}')
    else:
      create_ha_event(HA_URL, HEADERS, event.get_data())
      print(f'Event created {event}')



if __name__ == '__main__':
  load_dotenv()

  HA_URL = os.getenv('HA_URL')
  HEADERS = {
    "Authorization": f"Bearer {os.getenv('HA_TOKEN')}",
    "content-type": "application/json",
  }

  while True:
    compare_events(HA_URL, HEADERS)
    sleep(3600) # 1 hours in seconds

  print('done')
