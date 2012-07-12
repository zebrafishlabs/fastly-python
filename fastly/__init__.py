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


class FastlyHeaderType(object):
	RESPONSE="response"
	FETCH="fetch"
	CACHE="cache"
	REQUEST="request"


class FastlyHeaderAction(object):
	SET="set"
	APPEND="append"
	DELETE="delete"
	REGEX="regex"
	REGEX_ALL="regex_repeat"


class FastlyConditionType(object):
	RESPONSE="RESPONSE"
	CACHE="CACHE"
	REQUEST="REQUEST"
	FETCH="FETCH"


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


	def get_current_user(self):
		content = self._fetch("/current_user")
		return FastlyUser(self, content)


	def list_users(self):
		content = self._fetch("/user")
		return map(lambda x: FastlyUser(self, x), content)


	def get_user(self, user_id):
		content = self._fetch("/user/%s" % user_id)
		return FastlyUser(self, content)


	def create_user(self, customer_id, name, login, password, role=FastlyRoles.USER, require_new_password=True):
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
		body = self._formdata(kwargs, FastlyUser.FIELDS)
		content = self._fetch("/user/%s" % user_id, method="PUT", body=body)
		return FastlyUser(self, content)


	def delete_user(self, user_id):
		content = self._fetch("/user/%s" % user_id, method="DELETE")
		return self._status(content)


	def get_current_customer(self):
		content = self._fetch("/current_customer")
		return FastlyCustomer(self, content)


	def list_customers(self):
		content = self._fetch("/customer")
		return map(lambda x: FastlyCustomer(self, x), content)


	def get_customer(self, customer_id):
		content = self._fetch("/customer/%s" % customer_id)
		return FastlyCustomer(self, content)


	def update_customer(self, customer_id, **kwargs):
		body = self._formdata(kwargs, FastlyCustomer.FIELDS)
		content = self._fetch("/customer/%s" % customer_id, method="PUT", body=body)
		return FastlyCustomer(self, content)


	def delete_customer(self, customer_id):
		content = self._fetch("/customer/%s" % customer_id, method="DELETE")
		return self._status(content)


	def create_service(self, customer_id, name, stat_type="all", comment=None):
		body = self._formdata({
			"customer_id": customer_id,
			"name": name,
			"type": stat_type,
			"comment": comment,
		}, FastlyService.FIELDS)
		content = self._fetch("/service", method="POST", body=body)
		return FastlyService(self, content)
		

	def list_services(self):
		content = self._fetch("/service")
		return map(lambda x: FastlyService(self, x), content)


	def get_service(self, service_id):
		content = self._fetch("/service/%s" % service_id)
		return FastlyService(self, content)


	def get_service_by_name(self, service_name):
		content = self._fetch("/service/search?name=%s" % service_name)
		return FastlyService(self, content)


	def update_service(self, service_id, **kwargs):
		body = self._formdata(kwargs, FastlyService.FIELDS)
		content = self._fetch("/service/%s" % service_id, method="PUT", body=body)
		return FastlyService(self, content)


	def delete_service(self, service_id):
		content = self._fetch("/service/%s" % service_id, method="DELETE")
		return self._status(content)


	def get_service_stats(self, service_id, stat_type="all"):
		content = self._fetch("/service/%s/stats/%s" % (service_id, stat_type))
		# TODO: This doesn't seem to be working.


	def create_service_version(self, service_id, comment=None):
		body = self._formdata({
			"service_id": service_id,
			"comment": comment,
		}, FastlyServiceVersion.FIELDS)
		content = self._fetch("/service/%s/version" % service_id, method="POST", body=body)
		return FastlyServiceVersion(self, content)
		

	def list_service_versions(self, service_id):
		content = self._fetch("/service/%s/version"% service_id)
		return map(lambda x: FastlyServiceVersion(self, x), content)


	def get_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d" % (service_id, version_number))
		return FastlyServiceVersion(self, content)


	def clone_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/clone" % (service_id, version_number), method="PUT")
		return FastlyServiceVersion(self, content)


	def activate_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/activate" % (service_id, version_number), method="PUT")
		return FastlyServiceVersion(self, content)


	def deactivate_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/deactivate" % (service_id, version_number), method="PUT")
		return FastlyServiceVersion(self, content)


	def validate_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/validate" % (service_id, version_number))
		return self._status(content)


	def get_service_version_settings(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/settings" % (service_id, version_number))
		return FastlyServiceVersionSettings(self, content)


	def update_service_version_settings(self, service_id, version_number, settings={}):
		body = urllib.urlencode(settings)
		content = self._fetch("/service/%s/version/%d/settings" % (service_id, version_number), method="PUT", body=body)
		return FastlyServiceVersionSettings(self, content)


	# TODO: Is this broken?
	def delete_service_version(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d" % (service_id, version_number), method="DELETE")
		return self._status(content)


	def purge_url(self, url):
		content = self._fetch("/purge/%s" % url, method="POST") 
		return self._status(content)


	def purge_key(self, service_id, key):
		content = self._fetch("/service/%s/purge/%s" % (service_id, key), method="POST")
		return self._status(content)


	# TODO: Is this broken?
	def purge_all(self, service_id):
		content = self._fetch("/service/%s/purge_all" % service_id, method="POST")
		return self._status(content)


	def list_backends(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/backend" % (service_id, version_number))
		return map(lambda x: FastlyBackend(self, x), content)


	def create_backend(self, service_id, version_number, 
		name, 
		address,
		healthcheck,
		port=80,
		between_bytes_timeout=10000,
		connect_timeout=1000,
		error_threshold=0,
		first_byte_timeout=15000,
		max_conn=20,
		use_ssl=False,
		weight=100,
		comment=None):
		body = self._formdata({
			"name": name,
			"address": address,
			"port": port,
			"healthcheck": healthcheck,
			"between_bytes_timeout": between_bytes_timeout,
			"connect_timeout": connect_timeout,
			"error_threshold": error_threshold,
			"first_byte_timeout": first_byte_timeout,
			"max_conn": max_conn,
			"use_ssl": use_ssl,
			"weight": weight,
			"comment": comment,

		}, FastlyBackend.FIELDS)
		content = self._fetch("/service/%s/version/%d/backend" % (service_id, version_number), method="POST", body=body)
		return FastlyBackend(self, content)


	def get_backend(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name))
		return FastlyBackend(self, content)


	def update_backend(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyBackend.FIELDS)
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyBackend(self, content)


	def delete_backend(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/backend/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	# TODO: Not working?
	def check_backends(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/backend/check_all" % (service_id, version_number))
		print content


	def list_domains(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/domain" % (service_id, version_number))
		return map(lambda x: FastlyDomain(self, x), content)


	def create_domain(self, service_id, version_number, 
		name, 
		comment=None):
		body = self._formdata({
			"name": name,
			"comment": comment,

		}, FastlyDomain.FIELDS)
		content = self._fetch("/service/%s/version/%d/domain" % (service_id, version_number), method="POST", body=body)
		return FastlyDomain(self, content)


	def get_domain(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name))
		return FastlyDomain(self, content)


	def update_domain(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyDomain.FIELDS)
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyDomain(self, content)


	def delete_domain(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/domain/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def check_domain(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/domain/%s/check" % (service_id, version_number, name))
		return FastlyDomainCheck(self, content)


	def list_directors(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/director" % (service_id, version_number))
		return map(lambda x: FastlyDirector(self, x), content)


	def create_director(self, service_id, version_number, 
		name, 
		quorum=75,
		_type=1,
		retries=5,
		comment=None):
		body = self._formdata({
			"name": name,
			"comment": comment,
			"quorum": quorum,
			"type": _type,
			"retries": retries,

		}, FastlyDirector.FIELDS)
		content = self._fetch("/service/%s/version/%d/director" % (service_id, version_number), method="POST", body=body)
		return FastlyDirector(self, content)


	def get_director(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name))
		return FastlyDirector(self, content)


	def update_director(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyDirector.FIELDS)
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyDirector(self, content)


	def delete_director(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/director/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_origins(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/origin" % (service_id, version_number))
		return map(lambda x: FastlyOrigin(self, x), content)


	def create_origin(self, service_id, version_number, 
		name, 
		quorum=75,
		_type=1,
		retries=5,
		comment=None):
		body = self._formdata({
			"name": name,
			"comment": comment,
			"quorum": quorum,
			"type": _type,
			"retries": retries,

		}, FastlyOrigin.FIELDS)
		content = self._fetch("/service/%s/version/%d/origin" % (service_id, version_number), method="POST", body=body)
		return FastlyOrigin(self, content)


	def get_origin(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/origin/%s" % (service_id, version_number, name))
		return FastlyOrigin(self, content)


	def update_origin(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyOrigin.FIELDS)
		content = self._fetch("/service/%s/version/%d/origin/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyOrigin(self, content)


	def delete_origin(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/origin/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_vcls(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/vcl" % (service_id, version_number))
		return map(lambda x: FastlyVCL(self, x), content)


	def create_vcl(self, service_id, version_number, name, content, comment=None):
		body = self._formdata({
			"name": name,
			"content": content,
			"comment": comment,

		}, FastlyOrigin.FIELDS)
		content = self._fetch("/service/%s/version/%d/vcl" % (service_id, version_number), method="POST", body=body)
		return FastlyVCL(self, content)


	def get_vcl(self, service_id, version_number, name, include_content=True):
		content = self._fetch("/service/%s/version/%d/vcl/%s?include_content=%d" % (service_id, version_number, name, int(include_content)))
		return FastlyVCL(self, content)


	def get_vcl_html(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/vcl/%s/content" % (service_id, version_number, name))
		return content.get("content", None)


	def get_generated_vcl(self, service_id, version_number, include_content=True):
		content = self._fetch("/service/%s/version/%d/generated_vcl?include_content=%d" % (service_id, version_number, int(include_content)))
		return FastlyVCL(self, content)


	def get_generated_vcl_html(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/generated_vcl/content" % (service_id, version_number))
		return content.get("content", None)


	def update_vcl(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyVCL.FIELDS)
		content = self._fetch("/service/%s/version/%d/vcl/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyVCL(self, content)


	def delete_vcl(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/vcl/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_healthchecks(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/healthcheck" % (service_id, version_number))
		return map(lambda x: FastlyHealthCheck(self, x), content)


	def create_healthcheck(self, service_id, version_number, name, host, method="HEAD", path="/", http_version="1.1", timeout=1000, window=5, threshold=3):
		body = self._formdata({
			"name": name,
			"host": host,
			"method": method,
			"path": path,
			"http_version": http_version,
			"timeout": timeout,
			"window": window,
			"threshold": threshold,
		}, FastlyHealthCheck.FIELDS)
		content = self._fetch("/service/%s/version/%d/healthcheck" % (service_id, version_number), method="POST", body=body)
		return FastlyHealthCheck(self, content)


	def get_healthcheck(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name))
		return FastlyHealthCheck(self, content)


	def update_healthcheck(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyHealthCheck.FIELDS)
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyHealthCheck(self, content)


	def delete_healthcheck(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/healthcheck/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_conditions(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/condition" % (service_id, version_number))
		return map(lambda x: FastlyCondition(self, x), content)


	def create_condition(self, service_id, version_number, name, _type, statement, priority="10", comment=None):
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
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name))
		return FastlyCondition(self, content)


	def update_condition(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyCondition.FIELDS)
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyCondition(self, content)


	def delete_condition(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/condition/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_headers(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/header" % (service_id, version_number))
		return map(lambda x: FastlyHeader(self, x), content)


	def create_header(self, service_id, version_number, name, destination, source, _type=FastlyHeaderType.RESPONSE, action=FastlyHeaderAction.SET, regex=None, substitution=None, ignore_if_set=None, priority="10", response_condition=None, cache_condition=None, request_condition=None):
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
		content = self._fetch("/service/%s/version/%d/header" % (service_id, version_number), method="POST", body=body)
		return FastlyHeader(self, content)


	def get_header(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name))
		return FastlyHeader(self, content)


	def update_header(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyHeader.FIELDS)
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyHeader(self, content)


	def delete_header(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/header/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_response_objects(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/response_object" % (service_id, version_number))
		return map(lambda x: FastlyResponseObject(self, x), content)


	def create_response_object(self, service_id, version_number, name, status="200", response="OK", content="", request_condition=None, cache_condition=None):
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
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name))
		return FastlyResponseObject(self, content)


	def update_response_object(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlyResponseObject.FIELDS)
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlyResponseObject(self, content)


	def delete_response_object(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/response_object/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def list_syslogs(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/syslog" % (service_id, version_number))
		return map(lambda x: FastlySyslog(self, x), content)


	def list_syslogs(self, service_id, version_number):
		content = self._fetch("/service/%s/version/%d/syslog" % (service_id, version_number))
		return map(lambda x: FastlySyslog(self, x), content)


	def create_syslog(self, service_id, version_number, name, address=None, ipv4=None, hostname=None, port=514, _format=None):
		body = self._formdata({
			"name": name,
			"address": address,
			"ipv4": ipv4,
			"hostname": hostname,
			"port": port,
			"format": _format,
		}, FastlySyslog.FIELDS)
		content = self._fetch("/service/%s/version/%d/syslog" % (service_id, version_number), method="POST", body=body)
		return FastlySyslog(self, content)


	def get_syslog(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name))
		return FastlySyslog(self, content)


	def update_syslog(self, service_id, version_number, name_key, **kwargs):
		body = self._formdata(kwargs, FastlySyslog.FIELDS)
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name_key), method="PUT", body=body)
		return FastlySyslog(self, content)


	def delete_syslog(self, service_id, version_number, name):
		content = self._fetch("/service/%s/version/%d/syslog/%s" % (service_id, version_number, name), method="DELETE")
		return self._status(content)


	def content_edge_check(self, url):
		prefixes = ["http://", "https://"]
		for prefix in prefixes:
			if url.startswith(prefix):
				url = url[len(prefix):]
				break
		content = self._fetch("/content/edge_check/%s" % url)
		print content
	

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
		
		print "Fetch: %s %s" % (method, url)
		if body:
			print "Body: %s" % body
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
				payload = None

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
		else:
			payload["status"] = "error"
			status = FastlyStatus(self, payload)
			raise FastlyError(status)


class FastlyError(Exception):
	def __init__(self, status):
		if isinstance(status, FastlyStatus):
			Exception.__init__(self, "FastlyError: %s (%s)" % (status.msg, status.detail))
			return
		Exception.__init__(self, status)


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
	


class FastlyStatus(FastlyObject):
	FIELDS = [
		"msg",
		"detail",
		"status",
	]


class FastlySession(FastlyObject):
	FIELDS = []

	@property
	def customer(self):
		return FastlyCustomer(self._conn, self._data["customer"])


	@property
	def user(self):
		return FastlyUser(self._conn, self._data["user"])


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


class FastlyCustomer(FastlyObject, IDateStampedObject):
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


class FastlyService(FastlyObject):
	FIELDS = [
		"comment",
		"name",
		"version",
		"customer_id",
		"id",
	]

	@property
	def versions(self):
		return dict([ (v.number, v) for v in self.list_service_versions(self.id) ])

	@property
	def active_version(self):
		for version in self.versions.values():
			if version.active:
				return version
		return None


class IServiceObject(object):
	@property
	def service(self):
		return self._conn.get_service(self.service_id)


class FastlyServiceVersion(FastlyObject, IServiceObject, IDateStampedObject):
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


class IServiceVersionObject(IServiceObject):
	@property
	def service_version(self):
		return self._conn.get_service_version(self.service_id, self.version)


class FastlyServiceVersionSettings(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"service_id",
		"version",
		"settings",
	]


class FastlyBackend(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"name",
		"comment",
		"service_id",
		"version",
		"address",
		"ipv4",
		"ipv6",
		"hostname",
		"healthcheck",
		"port",
		"between_bytes_timeout",
		"connect_timeout",
		"error_threshold",
		"first_byte_timeout",
		"max_conn",
		"use_ssl",
		"weight",
		"client_cert",
	]

	@property
	def healthcheck(self):
		return self._conn.get_healthcheck(self.service_id, self.version, self.healthcheck)


class FastlyHealthCheck(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"name",
		"comment",
		"service_id",
		"version",
		"method",
		"initial",
		"host",
		"path",
		"http_version",
		"timeout",
		"window",
		"threshold",
	]


class FastlyDomain(FastlyObject, IServiceVersionObject):
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


class FastlyDirector(FastlyObject, IServiceVersionObject, IDateStampedObject):
	FIELDS = [
		"name",
		"service_id",
		"version"
		"quorum",
		"type",
		"retries",
		"created",
		"updated",
		"deleted",
		"capacity",
		"comment",
	]


class FastlyOrigin(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"name",
		"comment",
		"service_id",
		"version",
	]


class FastlyVCL(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"name",
		"service_id",
		"version",
		"generation",
		"md5",
		"content",
		"main",
	]


class FastlySyslog(FastlyObject, IServiceVersionObject, IDateStampedObject):
	FIELDS = [
		"name",
		"service_id",
		"version",
		"address",
		"ipv4",
		"hostname",
		"port",
		"format",
		"created",
		"updated",
		"deleted",
	]


class FastlyResponseObject(FastlyObject, IServiceVersionObject):
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


class FastlyHeader(FastlyObject, IServiceVersionObject):
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


class FastlyCondition(FastlyObject, IServiceVersionObject):
	FIELDS = [
		"name",
		"service_id",
		"version",
		"type",
		"statement",
		"priority",
	]


def connect(api_key, username=None, password=None):
	conn = FastlyConnection(api_key)
	if username is not None and password is not None:
		conn.login(username, password)
	return conn
