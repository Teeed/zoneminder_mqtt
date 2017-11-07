#!/usr/bin/env python3
# coding: utf-8
# ZoneMinder -> MQTT - which rooms are active
#
# Copyright (C) 2017 Tadeusz Magura-Witkowski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import zm
import json
import logging
import traceback
import functools


import paho.mqtt.client as mqtt
import threading

from config import CONFIG


logger = logging.getLogger('zoneminder')
# logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


zmapi = zm.ZoneMinderAPI(CONFIG['zm']['server'], CONFIG['zm']['login'], CONFIG['zm']['password'])

def publish_zone_activity(client):
	data = {
		'5min': zmapi.get_active_monitors(5),
		'15min': zmapi.get_active_monitors(15),
		'1h': zmapi.get_active_monitors(60),
	}

	return client.publish('zm/zone_activity', json.dumps(data), retain=True)[0] == mqtt.MQTT_ERR_SUCCESS

def publish_hs_active(client):
	active = 1 if len(set(zmapi.get_active_monitors(30)) - set(CONFIG['zm']['ignored_zones'])) > 0 else 0
	return client.publish('zm/hs_active', active, retain=True)[0] == mqtt.MQTT_ERR_SUCCESS and \
			client.publish('iot/szafa', active, retain=True)[0] == mqtt.MQTT_ERR_SUCCESS

def periodic_spam(client):
	try:
		try_again = publish_hs_active(client) and publish_zone_activity(client)
	except Exception as e:
		logger.error('Exception when doing periodic spam:')
		print(traceback.format_exc())
		exit(1)

	if try_again:
		threading.Timer(60, lambda: periodic_spam(client)).start()
	else:
		logger.warning('Sending message has failed. Timer disabled.')

def on_message(client, userdata, msg):
	MAPPING = {
		'zm/zone_activity': publish_zone_activity,
		'zm/hs_active': publish_hs_active,
	}

	if msg.payload == b'?':
		MAPPING[msg.topic](client)


def on_connect(client, userdata, flags, rc):
	logger.info('Connected with result code ' + str(rc))

	client.subscribe('zm/zone_activity')
	client.subscribe('zm/hs_active')

	client.publish('zm/_sys', 'connected')

	periodic_spam(client)



client = mqtt.Client(client_id="mqtt_zm", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message

client.connect(CONFIG['mqtt']['server'], 1883, 60)

client.loop_forever()
