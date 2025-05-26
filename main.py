# from micropython import const
import esp32 as esp
import uasyncio as asyncio
import machine, network, requests, time, json
import mip, micropython
from collections import deque

# Microcontroller constants
RECEIVER_PIN = const(10)

# WIFI constants
WIFI_NAME = '###'
WIFI_PASS = '###'

# Volume constants
UP = const(3)
DOWN = const(-3)
MUTE = const(0)
VOLUME_PATH = "/ipcontrol/v1/systems/current/sources/current/soundControl/volume"
PLAYBACK_PATH = "/ipcontrol/v1/groups/current/sources/current"
MUTE_PATH = PLAYBACK_PATH + "/playback/mute"
UNMUTE_PATH = PLAYBACK_PATH + "/playback/unmute"
UP_CODES = (15, 143)
DOWN_CODES = (16, 144)
MUTE_CODES = (32, 160)

# Global vars
devialet_ip = ''
own_ip_address = ''

def do_connect():
  print('\nConnecting to network...')
  wlan = network.WLAN(network.WLAN.IF_STA)
  wlan.active(True)
  if not wlan.isconnected():
    wlan.connect(WIFI_NAME, WIFI_PASS)
    while not wlan.isconnected():
        machine.idle() # save power while waiting
    print('WLAN connection succeeded!')
  else:
    print('Already connected')
  global own_ip_address
  own_ip_address = wlan.ifconfig()[0]
  print(f'my ip: {own_ip_address}')
  
do_connect()

def get_mdns():
  try:
    import mdns_client
    print('already installed mdns_client')
  except:
    mip.install("github:cbrand/micropython-mdns")
    print('installed mdns_client')
    
get_mdns()
from mdns_client import Client
from mdns_client.service_discovery.txt_discovery import TXTServiceDiscovery

def get_ir_rx():
  try:
    import ir_rx
    print('already installed ir_rx')
  except:
    mip.install("github:peterhinch/micropython_ir/ir_rx")
    print('installed ir_rx')

get_ir_rx()
from ir_rx.nec import NEC_16

####################################################################
# Everything we need should be imported by now

def get_volume():
  resp = requests.get(devialet_ip+VOLUME_PATH)
  if resp.status_code != 200:
    raise ConnectionError('Could not get volume from device')
  data = resp.json()
  return data['volume']
  
def get_mute_status():
  resp = requests.get(devialet_ip+PLAYBACK_PATH)
  if resp.status_code != 200:
    raise ConnectionError('Could not get mute status from device')
  data = resp.json()
  return data['muteState']
  
def toggle_mute_status():
  url = MUTE_PATH
  if get_mute_status() == "muted":
    url = UNMUTE_PATH
  
  resp = requests.post(devialet_ip+url)
  if resp.status_code != 200:
    raise ConnectionError('Could not change mute status on device')

def volume_set_absolute(volume):
  payload = {'volume': volume}
  payload = json.dumps(payload)
  resp = requests.post(devialet_ip+VOLUME_PATH, data=payload, headers={"Content-Type": "application/json"})
  if resp.status_code != 200:
    raise Exception('Could not set volume on device')
  print(f'volume set to: {volume}')

def volume_control(volume_change):
  if volume_change == MUTE:
    toggle_mute_status()
  else:
    current_volume = get_volume()
    new_volume = current_volume + volume_change
    # logic to keep volume between 0 and 100
    if new_volume < 0 or new_volume > 100:
      if new_volume == -DOWN or new_volume == 100+UP:
        return
      elif new_volume < 0:
        new_volume = 0
      elif new_volume > 100:
        new_volume = 100
    
    volume_set_absolute(new_volume)

def get_devialet_ip():  
  loop = asyncio.get_event_loop()
  client = Client(own_ip_address)
  discovery = TXTServiceDiscovery(client)

  services = None
  async def discover_once():
    services = await discovery.query_once("_http", "_tcp", timeout=1.0)
    print(services)
    return services
    
  while not services:
    services = loop.run_until_complete(discover_once())
    
  print(f'discovered services: {services}')

  for service in services:
    if 'phantom' in service.name.lower():
      global devialet_ip
      devialet_ip = 'http://' + list(service.ips)[0]
      print(f'devialet ip: {devialet_ip}')
  
get_devialet_ip()

print(f'starting volume: {get_volume()}')

# Actually found this is more reliable than putting the ir signals in a queue/reading from the queue in an async task
# Queueing causes hanging, not sure why, but I couldn't get that to work
# Plus because the http call (the slowest piece) is done here, it sort of debounces/rate limits itself because repeated callbacks are dropped
def ir_callback(data, addr, ctrl):
  if data in UP_CODES:
    volume_control(UP)
  elif data in DOWN_CODES:
    volume_control(DOWN)
  elif data in MUTE_CODES:
    volume_control(MUTE)

# Disable hardware timer for ESP32C3
NEC_16.Timer_id = 0
ir = NEC_16(machine.Pin(RECEIVER_PIN, machine.Pin.IN), ir_callback)

while True:
  machine.idle()
  