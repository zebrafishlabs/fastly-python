#!/usr/bin/python

# Author: Chris Zacharias (chris@imgix.com)
# Copyright (c) 2012, Zebrafish Labs Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 	Redistributions of source code must retain the above copyright notice,
# 	this list of conditions and the following disclaimer.
# 
# 	Redistributions in binary form must reproduce the above copyright notice,
# 	this list of conditions and the following disclaimer in the documentation 
# 	and/or other materials provided with the distribution.
# 	
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

import httplib2
import urllib
import re
import json
from datetime import datetime

FASTLY_SCHEME = "https"
FASTLY_HOST = "api.fastly.com"

FASTLY_SESSION_REGEX = re.compile("(fastly\.session=[^;]+);")

class FastlyRoles(object):
	USER = "user"
	BILLING = "billing"
	ENGINEER = "engineer"
	SUPERUSER = "superuser"


class FastlyCacheSettingsAction(object):
	CACHE = "cache"
	PASS = "pass"
	RESTART = "restart"


class FastlyConditionType(object):
	RESPONSE="response"
	CACHE="cache"
	REQUEST="request"
	FETCH="fetch"


class FastlyHeaderAction(object):
	SET="set"
	APPEND="append"
	DELETE="delete"
	REGEX="regex"
	REGEX_ALL="regex_repeat"


class FastlyHeaderType(object):
	RESPONSE="response"
	FETCH="fetch"
	CACHE="cache"
	REQUEST="request"


class FastlyRequestSettingAction(object):
	LOOKUP="lookup"
	PASS="pass"


class FastlyForwardedForAction(object):
	CLEAR="clear"
	LEAVE="leave"
	APPEND="append"
	APPEND_ALL="append_all"
	OVERWRITE="overwrite"


class FastlyStatsType(object):
	ALL="all"
	DAILY="daily"
	HOURLY="hourly"
	MINUTELY="minutely"


class FastlyDirectorType(object):
	RANDOM=1
	ROUNDROBIN=2
	HASH=3
	CLIENT=4


class FastlyConnection(object):
	def __init__(self, api_key):
		self._session = None
		self._api_key = api_key
		self._fully_authed = False

	@property
	def fully_authed(self):
		return self._fully_authed


	def login(self, user, password):
		body = self._formdata({
			"user": user,
			"password": password,
		}, ["user", "password"])
		content = self._fetch("/login", method="POST", body=body)
		self._fully_authed = True
		return FastlySession(self, content)


	def list_backends(self, service_id, version_number):
		"""List all backends for a particular service and version."""

		content = self._fetch("/service/%s/version/%d/backend" % (service_id, version_number))
		return map(lambda x: FastlyBackend(self, x), content)


	def create_backend(self, 
		service_id,
		version_number, 
		name, 
		address,
		use_ssl=False,
		port=80,
		connect_timeout=1000,
		first_byte_timeout=15000,
		between_bytes_timeout=10000,
		error_threshold=0,
		max_conn=20,
		weight=100,
		auto_loadbalance=False,
		shield=None,
		request_condition=None,
		healthcheck=None,
		comment=None):
		"""Create a backend for a particular service and version."""
		body = self._formdata({
			"name": name,
			"address": address,
			"use_ssl": use_ssl,
			"port": port,
			"connect_timeout": connect_timeout,
			"first_byte_timeout": first_byte_timeout,
			"between_bytes_timeout": between_bytes_timeout,
			"error_threshold": error_threshold,
			"max_conn": max_conn,
			"weight": weight,
			"auto_loadbalance": auto_loadbalance,
			"shield": shield,
			"request_condition": request_condition,
			"healthcheck": healthcheck,
			"comment": comment,
		}, FastlyBackend.FIELDS)
		content = self._fetch("/service/%s/version/%d/backend" % (service_id, version_number), method="POST", body=body)
		return FastlyBackend(self, content)


	def get_backend(self, service_id, version_number, name):
		"""Get the backend for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name))
		return FastlyBackend(self, content)


	def update_backend(self, service_id, version_number, name_key, **kwargs):
		"""Update the backend for a particular service and version."""
		body = self._formdata(kwargs, FastlyBackend.FIELDS)
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyBackend(self, content)


	def delete_backend(self, service_id, version_number, name):
		"""Delete the backend for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def check_backends(self, service_id, version_number):
		"""Performs a health check against each backend in version. If the backend has a specific type of healthcheck, that one is performed, otherwise a HEAD request to / is performed. The first item is the details on the Backend itself. The second item is details of the specific HTTP request performed as a health check. The third item is the response details."""
		content = self._fetch("/service/%s/version/%d/backend/check_all" % (service_id, version_number))
		# TODO: Use a strong-typed class for output?
		return content


	def list_cache_settings(self, service_id, version_number):
		"""Get a list of all cache settings for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/cache_settings" % (service_id, version_number))
		return map(lambda x: FastlyCacheSettings(self, x), content)


	def create_cache_settings(self, 
		service_id, 
		version_number, 
		name,
		action,
		ttl=None,
		stale_ttl=None,
		cache_condition=None):
		"""Create a new cache settings object."""
		body = self._formdata({
			"name": name,
			"action": action,
			"ttl": ttl,
			"stale_ttl": stale_ttl,
			"cache_condition": cache_condition,
		}, FastlyCacheSettings.FIELDS)
		content = self._fetch("/service/%s/version/%d/cache_settings" % (service_id, version_number), method="POST", body=body)
		return FastlyCacheSettings(self, content)


	def get_cache_settings(self, service_id, version_number, name):
		"""Get a specific cache settings object."""
		content = self._fetch("/service/%s/version/%d/cache_settings/%s" % (service_id, version_number, name))
		return FastlyCacheSettings(self, content)


	def update_cache_settings(self, service_id, version_number, name_key, **kwargs):
		"""Update a specific cache settings object."""
		body = self._formdata(kwargs, FastlyCacheSettings.FIELDS)
		content = self._fetch("/service/%s/version/%d/cache_settings/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyCacheSettings(self, content)


	def delete_cache_settings(self, service_id, version_number, name):
		"""Delete a specific cache settings object."""
		content = self._fetch("/service/%s/version/%d/cache_settings/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_conditions(self, service_id, version_number):
		"""Gets all conditions for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/condition" % (service_id, version_number))
		return map(lambda x: FastlyCondition(self, x), content)


	def create_condition(self, 
		service_id, 
		version_number,
		name,
		_type,
		statement,
		priority="10", 
		comment=None):
		"""Creates a new condition."""
		body = self._formdata({
			"name": name,
			"type": _type,
			"statement": statement,
			"priority": priority,
			"comment": comment,
		}, FastlyCondition.FIELDS)
		content = self._fetch("/service/%s/version/%d/condition" % (service_id, version_number), method="POST", body=body)
		return FastlyCondition(self, content)


	def get_condition(self, service_id, version_number, name):
		"""Gets a specified condition."""
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name))
		return FastlyCondition(self, content)


	def update_condition(self, service_id, version_number, name_key, **kwargs):
		"""Updates the specified condition."""
		body = self._formdata(kwargs, FastlyCondition.FIELDS)
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyCondition(self, content)


	def delete_condition(self, service_id, version_number, name):
		"""Deletes the specified condition."""
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def content_edge_check(self, url):
		"""Retrieve headers and MD5 hash of the content for a particular url from each Fastly edge server."""
		prefixes = ["http://", "https://"]
		for prefix in prefixes:
			if url.startswith(prefix):
				url = url[len(prefix):]
				break
		content = self._fetch("/content/edge_check/%s" % url)
		return content


	def get_current_customer(self):
		"""Get the logged in customer."""
		content = self._fetch("/current_customer")
		return FastlyCustomer(self, content)


	def get_customer(self, customer_id):
		"""Get a specific customer."""
		content = self._fetch("/customer/%s" % customer_id)
		return FastlyCustomer(self, content)


	def get_customer_details(self, customer_id):
		"""Get a specific customer, owner, and billing contact."""
		content = self._fetch("/customer/details/%s" % customer_id)
		return content


	def list_customer_users(self, customer_id):
		"""List all users from a specified customer id."""
		content = self._fetch("/customer/users/%s" % customer_id)
		return map(lambda x: FastlyUser(self, x), content)


	def update_customer(self, customer_id, **kwargs):
		"""Update a customer."""
		body = self._formdata(kwargs, FastlyCustomer.FIELDS)
		content = self._fetch("/customer/%s" % customer_id, method="PUT", body=body)
		return FastlyCustomer(self, content)


	def delete_customer(self, customer_id):
		"""Delete a customer."""
		content = self._fetch("/customer/%s" % customer_id, method="DELETE")
		return self._status(content)


	def list_directors(self, service_id, version_number):
		"""List the directors for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/director" % (service_id, version_number))
		return map(lambda x: FastlyDirector(self, x), content)


	def create_director(self, service_id, version_number, 
		name, 
		quorum=75,
		_type=FastlyDirectorType.RANDOM,
		retries=5,
		shield=None):
		"""Create a director for a particular service and version."""
		body = self._formdata({
			"name": name,
			"quorum": quorum,
			"type": _type,
			"retries": retries,
			"shield": shield,

		}, FastlyDirector.FIELDS)
		content = self._fetch("/service/%s/version/%d/director" % (service_id, version_number), method="POST", body=body)
		return FastlyDirector(self, content)


	def get_director(self, service_id, version_number, name):
		"""Get the director for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name))
		return FastlyDirector(self, content)


	def update_director(self, service_id, version_number, name_key, **kwargs):
		"""Update the director for a particular service and version."""
		body = self._formdata(kwargs, FastlyDirector.FIELDS)
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyDirector(self, content)


	def delete_director(self, service_id, version_number, name):
		"""Delete the director for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def get_director_backend(self, service_id, version_number, director_name, backend_name):
		"""Returns the relationship between a Backend and a Director. If the Backend has been associated with the Director, it returns a simple record indicating this. Otherwise, returns a 404."""
		content = self._fetch("/service/%s/version/%d/director/%s/backend/%s" % (service_id, version_number, director_name, backend_name), method="GET")
		return FastlyDirectorBackend(self, content)


	def create_director_backend(self, service_id, version_number, director_name, backend_name):
		"""Establishes a relationship between a Backend and a Director. The Backend is then considered a member of the Director and can be used to balance traffic onto."""
		content = self._fetch("/service/%s/version/%d/director/%s/backend/%s" % (service_id, version_number, director_name, backend_name), method="POST")
		return FastlyDirectorBackend(self, content)

	
	def delete_director_backend(self, service_id, version_number, director_name, backend_name):
		"""Deletes the relationship between a Backend and a Director. The Backend is no longer considered a member of the Director and thus will not have traffic balanced onto it from this Director."""
		content = self._fetch("/service/%s/version/%d/director/%s/backend/%s" % (service_id, version_number, director_name, backend_name), method="DELETE")
		return self._status(content)


	def list_domains(self, service_id, version_number):
		"""List the domains for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/domain" % (service_id, version_number))
		return map(lambda x: FastlyDomain(self, x), content)


	def create_domain(self,
		service_id, 
		version_number, 
		name, 
		comment=None):
		"""Create a domain for a particular service and version."""
		body = self._formdata({
			"name": name,
			"comment": comment,

		}, FastlyDomain.FIELDS)
		content = self._fetch("/service/%s/version/%d/domain" % (service_id, version_number), method="POST", body=body)
		return FastlyDomain(self, content)


	def get_domain(self, service_id, version_number, name):
		"""Get the domain for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name))
		return FastlyDomain(self, content)


	def update_domain(self, service_id, version_number, name_key, **kwargs):
		"""Update the domain for a particular service and version."""
		body = self._formdata(kwargs, FastlyDomain.FIELDS)
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyDomain(self, content)


	def delete_domain(self, service_id, version_number, name):
		"""Delete the domain for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(self, content)


	def check_domain(self, service_id, version_number, name):
		"""Checks the status of a domain's DNS record. Returns an array of 3 items. The first is the details for the domain. The second is the current CNAME of the domain. The third is a boolean indicating whether or not it has been properly setup to use Fastly."""
		content = self._fetch("/service/%s/version/%d/domain/%s/check" % (service_id, version_number, name))
		return FastlyDomainCheck(self, content)


	def check_domains(self, service_id, version_number):
		"""Checks the status of all domain DNS records for a Service Version. Returns an array items in the same format as the single domain /check."""
		content = self._fetch("/service/%s/version/%d/domain/check_all" % (service_id, version_number))
		return map(lambda x: FastlyDomainCheck(self, x), content)


	def get_event_log(self, object_id):
		"""Get the specified event log."""
		content = self._fetch("/event_log/%s" % object_id, method="GET")
		return FastlyEventLog(self, content)


	def list_headers(self, service_id, version_number):
		"""Retrieves all Header objects for a particular Version of a Service."""
		content = self._fetch("/service/%s/version/%d/header" % (service_id, version_number))
		return map(lambda x: FastlyHeader(self, x), content)


	def create_header(self, service_id, version_number, name, destination, source, _type=FastlyHeaderType.RESPONSE, action=FastlyHeaderAction.SET, regex=None, substitution=None, ignore_if_set=None, priority=10, response_condition=None, cache_condition=None, request_condition=None):
		body = self._formdata({
			"name": name,
			"dst": destination,
			"src": source,
			"type": _type,
			"action": action,
			"regex": regex,
			"substitution": substitution,
			"ignore_if_set": ignore_if_set,
			"priority": priority,
			"response_condition": response_condition,
			"request_condition": request_condition,
			"cache_condition": cache_condition,
		}, FastlyHeader.FIELDS)
		"""Creates a new Header object."""
		content = self._fetch("/service/%s/version/%d/header" % (service_id, version_number), method="POST", body=body)
		return FastlyHeader(self, content)


	def get_header(self, service_id, version_number, name):
		"""Retrieves a Header object by name."""
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name))
		return FastlyHeader(self, content)


	def update_header(self, service_id, version_number, name_key, **kwargs):
		"""Modifies an existing Header object by name."""
		body = self._formdata(kwargs, FastlyHeader.FIELDS)
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyHeader(self, content)


	def delete_header(self, service_id, version_number, name):
		"""Deletes a Header object by name."""
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_healthchecks(self, service_id, version_number):
		"""List all of the healthchecks for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/healthcheck" % (service_id, version_number))
		return map(lambda x: FastlyHealthCheck(self, x), content)


	def create_healthcheck(self,
		service_id, 
		version_number,
		name,
		host,
		method="HEAD",
		path="/",
		http_version="1.1",
		timeout=1000,
		check_interval=5000,
		expected_response=200,
		window=5,
		threshold=3,
		initial=1):
		"""Create a healthcheck for a particular service and version."""
		body = self._formdata({
			"name": name,
			"method": method,
			"host": host,
			"path": path,
			"http_version": http_version,
			"timeout": timeout,
			"check_interval": check_interval,
			"expected_response": expected_response,
			"window": window,
			"threshold": threshold,
			"initial": initial,
		}, FastlyHealthCheck.FIELDS)
		content = self._fetch("/service/%s/version/%d/healthcheck" % (service_id, version_number), method="POST", body=body)
		return FastlyHealthCheck(self, content)


	def get_healthcheck(self, service_id, version_number, name):
		"""Get the healthcheck for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name))
		return FastlyHealthCheck(self, content)


	def update_healthcheck(self, service_id, version_number, name_key, **kwargs):
		"""Update the healthcheck for a particular service and version."""
		body = self._formdata(kwargs, FastlyHealthCheck.FIELDS)
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyHealthCheck(self, content)


	def delete_healthcheck(self, service_id, version_number, name):
		"""Delete the healthcheck for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def	purge_url(self, host, path):
		"""Purge an individual URL."""
		content = self._fetch(path, method="PURGE", headers={ "Host": host }) 
		return FastlyPurge(self, content)


	def check_purge_status(self, purge_id):
		"""Get the status and times of a recently completed purge."""
		content = self._fetch("/purge?id=%s" % purge_id)
		return map(lambda x: FastlyPurgeStatus(self, x), content)


	def list_request_settings(self, service_id, version_number):
		"""Returns a list of all Request Settings objects for the given service and version."""
		content = self._fetch("/service/%s/version/%d/request_settings" % (service_id, version_number))
		return map(lambda x: FastlyRequestSetting(self, x), content)


	def create_request_setting(self,
		service_id,
		version_number,
		name,
		default_host=None,
		force_miss=None,
		force_ssl=None,
		action=None,
		bypass_busy_wait=None,
		max_stale_age=None,
		hash_keys=None,
		xff=None,
		timer_support=None,
		geo_headers=None,
		request_condition=None):
		"""Creates a new Request Settings object."""
		body = self._formdata({
			"name": name,
			"default_host": default_host,
			"force_miss": force_miss,
			"force_ssl": force_ssl,
			"action": action,
			"bypass_busy_wait": bypass_busy_wait,
			"max_stale_age": max_stale_age,
			"hash_keys": hash_keys,
			"xff": xff,
			"timer_support": timer_support,
			"geo_headers": geo_headers,
			"request_condition": request_condition,
		}, FastlyRequestSetting.FIELDS)
		content = self._fetch("/service/%s/version/%d/request_settings" % (service_id, version_number), method="POST", body=body)
		return FastlyRequestSetting(self, content)


	def get_request_setting(self, service_id, version_number, name):
		"""Gets the specified Request Settings object."""
		content = self._fetch("/service/%s/version/%d/request_settings/%s" % (service_id, version_number, name))
		return FastlyRequestSetting(self, content)


	def update_request_setting(self, service_id, version_number, name_key, **kwargs):
		"""Updates the specified Request Settings object."""
		body = self._formdata(kwargs, FastlyHealthCheck.FIELDS)
		content = self._fetch("/service/%s/version/%d/request_settings/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyRequestSetting(self, content)


	def delete_request_setting(self, service_id, version_number, name):
		"""Removes the specfied Request Settings object."""
		content = self._fetch("/service/%s/version/%d/request_settings/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_response_objects(self, service_id, version_number):
		"""Returns all Response Objects for the specified service and version."""
		content = self._fetch("/service/%s/version/%d/response_object" % (service_id, version_number))
		return map(lambda x: FastlyResponseObject(self, x), content)


	def create_response_object(self, service_id, version_number, name, status="200", response="OK", content="", request_condition=None, cache_condition=None):
		"""Creates a new Response Object."""
		body = self._formdata({
			"name": name,
			"status": status,
			"response": response,
			"content": content,
			"request_condition": request_condition,
			"cache_condition": cache_condition,
		}, FastlyResponseObject.FIELDS)
		content = self._fetch("/service/%s/version/%d/response_object" % (service_id, version_number), method="POST", body=body)
		return FastlyResponseObject(self, content)


	def get_response_object(self, service_id, version_number, name):
		"""Gets the specified Response Object."""
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name))
		return FastlyResponseObject(self, content)


	def update_response_object(self, service_id, version_number, name_key, **kwargs):
		"""Updates the specified Response Object."""
		body = self._formdata(kwargs, FastlyResponseObject.FIELDS)
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyResponseObject(self, content)


	def delete_response_object(self, service_id, version_number, name):
		"""Deletes the specified Response Object."""
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def create_service(self, customer_id, name, publish_key=None, comment=None):
		"""Create a service."""
		body = self._formdata({
			"customer_id": customer_id,
			"name": name,
			"publish_key": publish_key,
			"comment": comment,
		}, FastlyService.FIELDS)
		content = self._fetch("/service", method="POST", body=body)
		return FastlyService(self, content)
		

	def list_services(self):
		"""List Services."""
		content = self._fetch("/service")
		return map(lambda x: FastlyService(self, x), content)


	def get_service(self, service_id):
		"""Get a specific service by id."""
		content = self._fetch("/service/%s" % service_id)
		return FastlyService(self, content)


	def get_service_details(self, service_id):
		"""List detailed information on a specified service."""
		content = self._fetch("/service/%s/details" % service_id)
		return FastlyService(self, content)


	def get_service_by_name(self, service_name):
		"""Get a specific service by name."""
		content = self._fetch("/service/search?name=%s" % service_name)
		return FastlyService(self, content)


	def update_service(self, service_id, **kwargs):
		"""Update a service."""
		body = self._formdata(kwargs, FastlyService.FIELDS)
		content = self._fetch("/service/%s" % service_id, method="PUT", body=body)
		return FastlyService(self, content)


	def delete_service(self, service_id):
		"""Delete a service."""
		content = self._fetch("/service/%s" % service_id, method="DELETE")
		return self._status(content)


	def list_domains_by_service(self, service_id):
		"""List the domains within a service."""
		content = self._fetch("/service/%s/domain" % service_id, method="GET")
		return map(lambda x: FastlyDomain(self, x), content)


	def purge_service(self, service_id):
		"""Purge everything from a service."""
		content = self._fetch("/service/%s/purge_all" % service_id, method="POST")
		return self._status(content)


	def purge_service_by_key(self, service_id, key):
		"""Purge a particular service by a key."""
		content = self._fetch("/service/%s/purge/%s" % (service_id, key), method="POST")
		return self._status(content)


	def get_settings(self, service_id, version_number):
		"""Get the settings for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/settings" % (service_id, version_number))
		return FastlySettings(self, content)


	def update_settings(self, service_id, version_number, settings={}):
		"""Update the settings for a particular service and version."""
		body = urllib.urlencode(settings)
		content = self._fetch("/service/%s/version/%d/settings" % (service_id, version_number), method="PUT", body=body)
		return FastlySettings(self, content)


	def get_stats(self, service_id, stat_type=FastlyStatsType.ALL):
		"""Get the stats from a service."""
		content = self._fetch("/service/%s/stats/%s" % (service_id, stat_type))
		return content


	def list_syslogs(self, service_id, version_number):
		"""List all of the Syslogs for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/syslog" % (service_id, version_number))
		return map(lambda x: FastlySyslog(self, x), content)


	def create_syslog(self,
		service_id,
		version_number,
		name,
		address,
		port=514,
		use_tls="0",
		tls_ca_cert=None,
		token=None,
		_format=None,
		response_condition=None):
		"""Create a Syslog for a particular service and version."""
		body = self._formdata({
			"name": name,
			"address": address,
			"port": port,
			"use_tls": use_tls,
			"tls_ca_cert": tls_ca_cert,
			"token": token,
			"format": _format,
			"response_condition": response_condition,
		}, FastlySyslog.FIELDS)
		content = self._fetch("/service/%s/version/%d/syslog" % (service_id, version_number), method="POST", body=body)
		return FastlySyslog(self, content)


	def get_syslog(self, service_id, version_number, name):
		"""Get the Syslog for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name))
		return FastlySyslog(self, content)


	def update_syslog(self, service_id, version_number, name_key, **kwargs):
		"""Update the Syslog for a particular service and version."""
		body = self._formdata(kwargs, FastlySyslog.FIELDS)
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlySyslog(self, content)


	def delete_syslog(self, service_id, version_number, name):
		"""Delete the Syslog for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def change_password(self, old_password, new_password):
		"""Update the user's password to a new one."""
		body = self._formdata({
			"old_password": old_password,
			"password": new_password,
		}, ["old_password", "password"])
		content = self._fetch("/current_user/password", method="POST", body=body)
		return FastlyUser(self, content)


	def get_current_user(self):
		"""Get the logged in user."""
		content = self._fetch("/current_user")
		return FastlyUser(self, content)


	def get_user(self, user_id):
		"""Get a specific user."""
		content = self._fetch("/user/%s" % user_id)
		return FastlyUser(self, content)


	def create_user(self, customer_id, name, login, password, role=FastlyRoles.USER, require_new_password=True):
		"""Create a user."""
		body = self._formdata({
			"customer_id": customer_id,
			"name": name,
			"login": login,
			"password": password,
			"role": role,
			"require_new_password": require_new_password,
		}, FastlyUser.FIELDS)
		content = self._fetch("/user", method="POST", body=body)
		return FastlyUser(self, content)


	def update_user(self, user_id, **kwargs):
		"""Update a user."""
		body = self._formdata(kwargs, FastlyUser.FIELDS)
		content = self._fetch("/user/%s" % user_id, method="PUT", body=body)
		return FastlyUser(self, content)


	def delete_user(self, user_id):
		"""Delete a user."""
		content = self._fetch("/user/%s" % user_id, method="DELETE")
		return self._status(content)


	def request_password_reset(self, user_id):
		"""Requests a password reset for the specified user."""
		content = self._fetch("/user/%s/password/request_reset" % (user_id), method="POST")
		return FastlyUser(self, content)


	def list_vcls(self, service_id, version_number):
		"""List the uploaded VCLs for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/vcl" % (service_id, version_number))
		return map(lambda x: FastlyVCL(self, x), content)


	def upload_vcl(self, service_id, version_number, name, content, main=None, comment=None):
		"""Upload a VCL for a particular service and version."""
		body = self._formdata({
			"name": name,
			"content": content,
			"comment": comment,
			"main": main,
		}, FastlyVCL.FIELDS)
		content = self._fetch("/service/%s/version/%d/vcl" % (service_id, version_number), method="POST", body=body)
		return FastlyVCL(self, content)


	def download_vcl(self, service_id, version_number, name):
		"""Download the specified VCL."""
		# TODO: Not sure what to do here, the documentation shows invalid response. Will have to test.
		raise Exception("Not implemented")


	def get_vcl(self, service_id, version_number, name, include_content=True):
		"""Get the uploaded VCL for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/vcl/%s?include_content=%d" % (service_id, version_number, name, int(include_content)))
		return FastlyVCL(self, content)


	def get_vcl_html(self, service_id, version_number, name):
		"""Get the uploaded VCL for a particular service and version with HTML syntax highlighting."""
		content = self._fetch("/service/%s/version/%d/vcl/%s/content" % (service_id, version_number, name))
		return content.get("content", None)


	def get_generated_vcl(self, service_id, version_number):
		"""Display the generated VCL for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/generated_vcl" % (service_id, version_number))
		return FastlyVCL(self, content)


	def get_generated_vcl_html(self, service_id, version_number):
		"""Display the content of generated VCL with HTML syntax highlighting."""
		content = self._fetch("/service/%s/version/%d/generated_vcl/content" % (service_id, version_number))
		return content.get("content", None)


	def set_main_vcl(self, service_id, version_number, name):
		"""Set the specified VCL as the main."""
		content = self._fetch("/service/%s/version/%d/vcl/%s/main" % (service_id, version_number, name), method="PUT")
		return FastlyVCL(self, content)


	def update_vcl(self, service_id, version_number, name_key, **kwargs):
		"""Update the uploaded VCL for a particular service and version."""
		body = self._formdata(kwargs, FastlyVCL.FIELDS)
		content = self._fetch("/service/%s/version/%d/vcl/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyVCL(self, content)


	def delete_vcl(self, service_id, version_number, name):
		"""Delete the uploaded VCL for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/vcl/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def create_version(self, service_id, inherit_service_id=None, comment=None):
		"""Create a version for a particular service."""
		body = self._formdata({
			"service_id": service_id,
			"inherit_service_id": inherit_service_id,
			"comment": comment,
		}, FastlyVersion.FIELDS)
		content = self._fetch("/service/%s/version" % service_id, method="POST", body=body)
		return FastlyVersion(self, content)
		

	def list_versions(self, service_id):
		content = self._fetch("/service/%s/version"% service_id)
		return map(lambda x: FastlyVersion(self, x), content)


	def get_version(self, service_id, version_number):
		"""Get the version for a particular service."""
		content = self._fetch("/service/%s/version/%d" % (service_id, version_number))
		return FastlyVersion(self, content)

	def update_version(self, service_id, version_number, **kwargs):
		"""Update a particular version for a particular service."""
		body = self._formdata(kwargs, FastlyVersion.FIELDS)
		content = self._fetch("/service/%s/version/%d/" % (service_id, version_number), method="PUT", body=body)
		return FastlyVersion(self, content)


	def clone_version(self, service_id, version_number):
		"""Clone the current configuration into a new version."""
		content = self._fetch("/service/%s/version/%d/clone" % (service_id, version_number), method="PUT")
		return FastlyVersion(self, content)


	def activate_version(self, service_id, version_number):
		"""Activate the current version."""
		content = self._fetch("/service/%s/version/%d/activate" % (service_id, version_number), method="PUT")
		return FastlyVersion(self, content)


	def deactivate_version(self, service_id, version_number):
		"""Deactivate the current version."""
		content = self._fetch("/service/%s/version/%d/deactivate" % (service_id, version_number), method="PUT")
		return FastlyVersion(self, content)


	def validate_version(self, service_id, version_number):
		"""Validate the version for a particular service and version."""
		content = self._fetch("/service/%s/version/%d/validate" % (service_id, version_number))
		return self._status(content)


	def lock_version(self, service_id, version_number):
		"""Locks the specified version."""
		content = self._fetch("/service/%s/version/%d/lock" % (service_id, version_number))
		return self._status(content)


	def list_wordpressess(self, service_id, version_number):
		"""Get all of the wordpresses for a specified service and version."""
		content = self._fetch("/service/%s/version/%d/wordpress" % (service_id, version_number))
		return map(lambda x: FastlyWordpress(self, x), content)


	def create_wordpress(self,
		service_id,
		version_number,
		name,
		path,
		comment=None):
		"""Create a wordpress for the specified service and version."""
		body = self._formdata({
			"name": name,
			"path": path,
			"comment": comment,
		}, FastlyWordpress.FIELDS)
		content = self._fetch("/service/%s/version/%d/wordpress" % (service_id, version_number), method="POST", body=body)
		return FastlyWordpress(self, content)


	def get_wordpress(self, service_id, version_number, name):
		"""Get information on a specific wordpress."""
		content = self._fetch("/service/%s/version/%d/wordpress/%s" % (service_id, version_number, name))
		return FastlyWordpress(self, content)


	def update_wordpress(self, service_id, version_number, name_key, **kwargs):
		"""Update a specified wordpress."""
		body = self._formdata(kwargs, FastlyWordpress.FIELDS)
		content = self._fetch("/service/%s/version/%d/wordpress/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyWordpress(self, content)


	def delete_wordpress(self, service_id, version_number, name):
		"""Delete a specified wordpress."""
		content = self._fetch("/service/%s/version/%d/wordpress/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	# TODO: Is this broken?
	def delete_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d" % (service_id, version_number), method="DELETE")
		return self._status(content)
	

	def _status(self, status):
		if not isinstance(status, FastlyStatus):
			status = FastlyStatus(self, status)

		if status.status != "ok":
			raise FastlyError("FastlyError: %s" % status.msg) 

		return True


	def _formdata(self, fields, valid=[]):
		data = {}
		for key in fields.keys():
			if key in valid and fields[key] is not None:
				data[key] = fields[key]
				if isinstance(data[key], bool):
					data[key] = str(int(data[key]))
		return urllib.urlencode(data)


	def _fetch(self, url, method="GET", body=None, headers={}):
		hdrs = {}
		hdrs.update(headers)
		
		print("Fetch: %s %s" % (method, url))
		if body:
			print("Body: %s" % body)
		if self._fully_authed:
			hdrs["Cookie"] = self._session
		else:
			hdrs["X-Fastly-Key"] = self._api_key

		hdrs["Content-Accept"] = "application/json"
		if not hdrs.has_key("Content-Type") and method in ["POST", "PUT"]:
			hdrs["Content-Type"] = "application/x-www-form-urlencoded"

		conn = httplib2.Http(disable_ssl_certificate_validation=True)
		endpoint = "%s://%s%s" % (FASTLY_SCHEME, FASTLY_HOST, url)
		return self._check(*conn.request(endpoint, method, body=body, headers=hdrs))


	def _check(self, resp, content):
		status = resp.status
		payload = None
		if content:
			try:
				payload = json.loads(content)
			except ValueError: # Could not decode, usually HTML
				payload = content

		if status == 200:
			# Keep track of the session. Only really set during /login
			if resp.has_key("set-cookie"):
				set_cookie = resp["set-cookie"]
				match = FASTLY_SESSION_REGEX.search(set_cookie)
				if match is not None:
					self._session = match.group(1)
			return payload

		if payload is None:
			raise Exception("HTTP Error %d occurred." % status)
		elif isinstance(payload, basestring):
			raise Exception("HTTP Error %d occurred. { %s }" % (status, payload))
		else:
			payload["status"] = "error"
			status = FastlyStatus(self, payload)
			raise FastlyError(status)


class IDateStampedObject(object):
	@property
	def created_date(self):
		if hasattr(self, "created_at"):
			return self._parse_date(self.created_at)
		else:
			return self._parse_date(self.created)

	@property
	def updated_date(self):
		if hasattr(self, "updated_at"):
			return self._parse_date(self.updated_at)
		else:
			return self._parse_date(self.updated)

	@property
	def deleted_date(self):
		if hasattr(self, "deleted_at"):
			return self._parse_date(self.deleted_at)
		else:
			return self._parse_date(self.deleted)


class IServiceObject(object):
	@property
	def service(self):
		return self._conn.get_service(self.service_id)


class IServiceVersionObject(IServiceObject):
	@property
	def service_version(self):
		return self._conn.get_service_version(self.service_id, self.version)


class FastlyObject(object):
	def __init__(self, conn, data):  
		self._conn = conn
		self._data = data or {}

	def __getattr__(self, name):
		cls = self.__class__
		if name in cls.FIELDS:
			return self._data.get(name, None)
		raise AttributeError()

	def __str__(self):
		return str(self._data)
	
	def __repr__(self):
		return repr(self._data)

	def _parse_date(self, _date):
		return datetime.strptime(_date, "%Y-%m-%dT%H:%M:%S+00:00")


class FastlyStatus(FastlyObject):
	FIELDS = [
		"msg",
		"detail",
		"status",
	]


class FastlyError(Exception):
	def __init__(self, status):
		if isinstance(status, FastlyStatus):
			Exception.__init__(self, "FastlyError: %s (%s)" % (status.msg, status.detail))
			return
		Exception.__init__(self, status)


class FastlySession(FastlyObject):
	FIELDS = []

	@property
	def customer(self):
		return FastlyCustomer(self._conn, self._data["customer"])


	@property
	def user(self):
		return FastlyUser(self._conn, self._data["user"])


class FastlyBackend(FastlyObject, IServiceVersionObject):
	"""A Backend is an address (ip or domain) from which Fastly pulls content. There can be multiple Backends for a Service."""
	FIELDS = [
		"service_id",
		"version",
		"name",
		"address",
		"port",
		"use_ssl",
		"connect_timeout",
		"first_byte_timeout",
		"between_bytes_timeout",
		"error_threshold",
		"max_conn",
		"weight",
		"auto_loadbalance",
		"shield",
		"request_condition",
		"healthcheck",
		"comment",
	]

	@property
	def healthcheck(self):
		return self._conn.get_healthcheck(self.service_id, self.version, self.healthcheck)


class FastlyCacheSettings(FastlyObject, IServiceVersionObject):
	"""Controls how caching is performed on Fastly. When used in conjunction with Conditions the Cache Settings provide you with fine grain control over how long content persists in the cache."""
	FIELDS = [
		"service_id",
		"version",
		"name",
		"action",
		"ttl",
		"stale_ttl",
		"cache_condition",
	]


class FastlyCondition(FastlyObject, IServiceVersionObject):
	"""Conditions are used to control when and how other objects are used in a service configuration. They contain a statement that evaluates to either true or false and is used to determine whether the condition is met. 

	Depending on the type of the condition, the statment field can make reference to the Varnish Variables req, resp, and/or beresp."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"type",
		"statement",
		"priority",
	]


class FastlyCustomer(FastlyObject, IDateStampedObject):
	"""A Customer is the base object which owns your Users and Services."""
	FIELDS = [
		"can_configure_wordpress",
		"can_edit_matches",
		"name",
		"created_at",
		"updated_at",
		"can_stream_syslog",
		"id",
		"pricing_plan",
		"can_upload_vcl",
		"has_config_panel",
		"raw_api_key",
		"has_billing_panel",
		"can_reset_passwords",
		"owner_id",
	]

	@property
	def owner(self):
		return self._conn.get_user(self.owner_id)


class FastlyDirector(FastlyObject, IServiceVersionObject, IDateStampedObject):
	"""A Director is responsible for balancing requests among a group of Backends. In addition to simply balancing, Directors can be configured to attempt retrying failed requests. Additionally, Directors have a quorum setting which can be used to determine when the Director as a whole is considered "up", in order to prevent "server whack-a-mole" following an outage as servers come back up."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"quorum",
		"type",
		"retries",
		"shield",
		"created",
		"updated",
		"deleted",
		"capacity",
		"comment",
	]


class FastlyDirectorBackend(FastlyObject, IServiceVersionObject, IDateStampedObject):
	"""Maps and relates backends as belonging to directors. Backends can belong to any number of directors but directors can only hold one reference to a specific backend."""
	FIELDS = [
		"service_id",
		"version",
		"director",
		"backend",
		"created",
		"updated",
		"deleted",
	]


class FastlyDomain(FastlyObject, IServiceVersionObject):
	"""A Domain represents the domain name through which visitors will retrieve content. There can be multiple Domains for a Service."""
	FIELDS = [
		"name",
		"comment",
		"service_id",
		"version",
	]


class FastlyDomainCheck(FastlyObject):
	@property
	def domain(self):
		return FastlyDomain(self._conn, self._data[0])

	@property
	def cname(self):
		return self._data[1]

	@property
	def success(self):
		return self._data[2]


class FastlyEventLog(FastlyObject):
	"""EventLogs keep track of things that occur within your services or organization. Currently we track events such as activation and deactivation of Versions and mass purges. In the future we intend to track more events and let you trigger EventLog creation as well."""
	FIELDS = [
		"object_type",
		"id",
		"message",
		"details",
		"level",
		"timestamp",
		"system",
		"subsystem",
	]


class FastlyHeader(FastlyObject, IServiceVersionObject):
	"""Header objects are used to add, modify, or delete headers from requests and responses. The header content can be simple strings or be derived from variables inside Varnish. Regular expressions can be used to customize the headers even further."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"dst",
		"src",
		"type",
		"action",
		"regex",
		"substitution",
		"ignore_if_set",
		"priority",
		"response_condition",
		"request_condition",
		"cache_condition",
	]


class FastlyHealthCheck(FastlyObject, IServiceVersionObject):
	"""Healthchecks are used to customize the way Fastly checks on your Backends. Only Backends that have successful Healthchecks will be sent traffic, thus assuring that the failure of one server does not affect visitors."""
	FIELDS = [
		"service_id",
		"version",
		"name",
		"method",
		"host",
		"path",
		"http_version",
		"timeout",
		"check_interval",
		"expected_response",
		"window",
		"threshold",
		"initial",
		"comment",
	]


class FastlyPurge(FastlyObject):
	"""Purging removes content from Fastly so it can be refreshed from your origin servers."""
	FIELDS = [
		"status",
		"id",
	]


class FastlyPurgeStatus(FastlyObject):
	"""The status of a given purge request."""
	FIELDS = [
		"timestamp",
		"server",
	]


class FastlyRequestSetting(FastlyObject, IServiceVersionObject):
	"""Settings used to customize Fastly's request handling. When used with Conditions the Request Settings object allows you to fine tune how specific types of requests are handled."""
	FIELDS = [
		"service_id",
		"version",
		"name",
		"default_host",
		"force_miss",
		"force_ssl",
		"action",
		"bypass_busy_wait",
		"max_stale_age",
		"hash_keys",
		"xff",
		"timer_support",
		"geo_headers",
		"request_condition",
	]


class FastlyResponseObject(FastlyObject, IServiceVersionObject):
	"""Allows you to create synthetic responses that exist entirely on the varnish machine. Useful for creating error or maintainence pages that exists outside the scope of your datacenter. Best when used with Condition objects."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"status",
		"response",
		"content",
		"cache_condition",
		"request_condition",
	]


class FastlyService(FastlyObject):
	"""A Service represents the configuration for a website, app, api, or anything else to be served through Fastly. A Service can have many Versions, through which Backends, Domains, and more can be configured."""
	FIELDS = [
		"id",
		"name",
		"customer_id",
		"publish_key",
		"active_version",
		"versions"
		"comment",
	]

	@property
	def active_version(self):
		for version in self.versions.values():
			if version.active:
				return version
		return None


class FastlySettings(FastlyObject, IServiceVersionObject):
	"""Handles default settings for a particular version of a service."""
	FIELDS = [
		"service_id",
		"version",
	]


class FastlySyslog(FastlyObject, IServiceVersionObject, IDateStampedObject):
	"""Fastly will stream log messages to the location, and in the format, specified in the Syslog object."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"address",
		"port",
		"use_tls",
		"tls_ca_cert",
		"token",
		"format",
		"response_condition",
		"created",
		"updated",
		"deleted",
	]


class FastlyUser(FastlyObject, IDateStampedObject):
	FIELDS = [
		"name", 
		"created_at", 
		"updated_at", 
		"role", 
		"id", 
		"email_hash", 
		"customer_id",
		"require_new_password",
		"login",
	]

	@property
	def customer(self):
		return self._conn.get_customer(self.customer_id)


class FastlyVCL(FastlyObject, IServiceVersionObject):
	"""A VCL is a Varnish configuration file used to customize the configuration for a Service."""
	FIELDS = [
		"name",
		"service_id",
		"version",
		"generation",
		"md5",
		"content",
		"main",
		"vcl",
	]


class FastlyVersion(FastlyObject, IServiceObject, IDateStampedObject):
	"""A Version represents a specific instance of the configuration for a Service. A Version can be cloned, locked, activated, or deactivated."""
	FIELDS = [
		"comment",
		"staging",
		"locked",
		"created_at",
		"testing",
		"number",
		"updated_at",
		"active",
		"service_id",
		"deleted_at",
		"deployed",
		"inherit_service_id",
	]

	@property
	def settings(self):
		dct = {}
		result = self._conn.get_service_version_settings(self.service_id)
		if result:
			dct = result.settings
		return dct

	@property
	def backends(self):
		return dict([ (b.name, b) for b in self._conn.list_backends(self.service_id, int(self.number))])

	@property
	def healthchecks(self):
		return dict([ (h.name, h) for h in self._conn.list_healthchecks(self.service_id, int(self.number))])

	@property
	def domains(self):
		return dict([ (d.name, d) for d in self._conn.list_domains(self.service_id, int(self.number))])

	@property
	def directors(self):
		return dict([ (d.name, d) for d in self._conn.list_directors(self.service_id, int(self.number))])

	@property
	def origins(self):
		return dict([ (o.name, o) for o in self._conn.list_origins(self.service_id, int(self.number))])

	@property
	def syslogs(self):
		return dict([ (s.name, s) for s in self._conn.list_syslogs(self.service_id, int(self.number))])

	@property
	def vcls(self):
		return dict([ (v.name, v) for v in self._conn.list_vcls(self.service_id, int(self.number))])


class FastlyWordpress(FastlyObject, IServiceVersionObject):
	"""The Wordpress object applies configuration optimized for Wordpress to a given path."""
	FIELDS = [
		"service_id",
		"version",
		"name",
		"path",
		"comment",
	]


def connect(api_key, username=None, password=None):
	conn = FastlyConnection(api_key)
	if username is not None and password is not None:
		conn.login(username, password)
	return conn
