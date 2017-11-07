# Simple ZoneMinder API handler - more like a stub
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

import http.cookiejar, urllib.request, urllib.parse, urllib.error
import json
import logging

class ZoneMinderAPILoginError(Exception):
	def __init__(self, *args, **kwargs):
		super(ZoneMinderAPILoginError, self).__init__(*args, **kwargs)
		

class ZoneMinderAPI(object):
	def __init__(self, server, login, password):
		super(ZoneMinderAPI, self).__init__()
		self.server = server
		self.login = login
		self.password = password

		self.logger = logging.getLogger('zoneminder.ZoneMinderAPI')

		cj = http.cookiejar.CookieJar()
		self.__opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
		self.__url = 'http://{}/zm'.format(server)
	
	def __request(self, url, tries=5):
		self.logger.info('Request URL: {}, tries: {}'.format(url, tries))
		if tries == 0:
			raise ZoneMinderAPILoginError('Login tries exceed')

		try:
			url_to_open = '{}/api/{}'.format(self.__url, url)
			self.logger.debug('Opening URL: {}'.format(url_to_open))
			with self.__opener.open(url_to_open) as response:
				data = json.loads(response.read().decode())

				return data
		except urllib.error.HTTPError as e:
			self.logger.debug('Response code: {}'.format(e.code))
			if e.code == 401:
				self.logger.info('Request unauthorized, trying to login')

				self.__login()
				return self.__request(url, tries - 1)

	def __login(self):
		self.logger.info('Logging in...')
		http_data = {
			'username': self.login,
			'password': self.password,
			'action': 'login',
			'view': 'console',
		}
		url_to_open = '{}/index.php'.format(self.__url)

		self.logger.debug('Opening URL: {}'.format(url_to_open))
		with self.__opener.open(url_to_open, urllib.parse.urlencode(http_data).encode()) as response:
			data = response.read()

			if b'ZoneMinder Login' in data:
				raise ZoneMinderAPILoginError('Bad login or password')

	def get_active_monitors(self, minutes):
		data = self.__request('events/consoleEvents/{}%20minute.json/AlarmFrames%20>=:%2010.json'.format(int(minutes)))
		results = data['results']

		if isinstance(results, dict):
			return tuple(map(int, results.keys()))
		
		return ()
