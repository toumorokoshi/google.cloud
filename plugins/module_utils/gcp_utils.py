# Copyright (c), Google Inc, 2017
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import ast
import os
import json

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import google.auth
    import google.auth.compute_engine
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    HAS_GOOGLE_LIBRARIES = True
except ImportError:
    HAS_GOOGLE_LIBRARIES = False

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.six import string_types
from ansible.module_utils._text import to_text, to_native


def navigate_hash(source, path, default=None):
    if not source:
        return None

    key = path[0]
    path = path[1:]
    if key not in source:
        return default
    result = source[key]
    if path:
        return navigate_hash(result, path, default)
    return result


class GcpRequestException(Exception):
    pass


def remove_nones_from_dict(obj):
    new_obj = {}
    for key in obj:
        value = obj[key]
        if value is not None and value != {} and value != []:
            new_obj[key] = value

    # Blank dictionaries should return None or GCP API may complain.
    if not new_obj:
        return None
    return new_obj


# Handles the replacement of dicts with values -> the needed value for GCP API
def replace_resource_dict(item, value):
    if isinstance(item, list):
        items = []
        for i in item:
            items.append(replace_resource_dict(i, value))
        return items
    if not item:
        return item
    return item.get(value)


# Handles all authentication and HTTP sessions for GCP API calls.
class GcpSession(object):
    def __init__(self, module, product):
        self.module = module
        self.product = product
        self._validate()

    def get(self, url, body=None, **kwargs):
        """
        This method should be avoided in favor of full_get
        """
        kwargs.update({'json': body})
        return self.full_get(url, **kwargs)

    def post(self, url, body=None, headers=None, **kwargs):
        """
        This method should be avoided in favor of full_post
        """
        kwargs.update({'json': body, 'headers': headers})
        return self.full_post(url, **kwargs)

    def post_contents(self, url, file_contents=None, headers=None, **kwargs):
        """
        This method should be avoided in favor of full_post
        """
        kwargs.update({'data': file_contents, 'headers': headers})
        return self.full_post(url, **kwargs)

    def delete(self, url, body=None):
        """
        This method should be avoided in favor of full_delete
        """
        kwargs = {'json': body}
        return self.full_delete(url, **kwargs)

    def put(self, url, body=None, params=None):
        """
        This method should be avoided in favor of full_put
        """
        kwargs = {'json': body}
        return self.full_put(url, params=params, **kwargs)

    def patch(self, url, body=None, **kwargs):
        """
        This method should be avoided in favor of full_patch
        """
        kwargs.update({'json': body})
        return self.full_patch(url, **kwargs)

    def list(self, url, callback, params=None, array_name='items',
             pageToken='nextPageToken', **kwargs):
        """
        This should be used for calling the GCP list APIs. It will return
        an array of items

        This takes a callback to a `return_if_object(module, response)`
        function that will decode the response + return a dictionary. Some
        modules handle the decode + error processing differently, so we should
        defer to the module to handle this.
        """
        resp = callback(self.module, self.full_get(url, params, **kwargs))
        items = resp.get(array_name) if resp.get(array_name) else []
        while resp.get(pageToken):
            if params:
                params['pageToken'] = resp.get(pageToken)
            else:
                params = {'pageToken': resp[pageToken]}

            resp = callback(self.module, self.full_get(url, params, **kwargs))
            if resp.get(array_name):
                items = items + resp.get(array_name)
        return items

    # The following methods fully mimic the requests API and should be used.
    def full_get(self, url, params=None, **kwargs):
        kwargs['headers'] = self._set_headers(kwargs.get('headers'))
        try:
            return self.session().get(url, params=params, **kwargs)
        except getattr(requests.exceptions, 'RequestException') as inst:
            # Only log the message to avoid logging any sensitive info.
            self.module.fail_json(msg=inst.message)

    def full_post(self, url, data=None, json=None, **kwargs):
        kwargs['headers'] = self._set_headers(kwargs.get('headers'))

        try:
            return self.session().post(url, data=data, json=json, **kwargs)
        except getattr(requests.exceptions, 'RequestException') as inst:
            self.module.fail_json(msg=inst.message)

    def full_put(self, url, data=None, **kwargs):
        kwargs['headers'] = self._set_headers(kwargs.get('headers'))

        try:
            return self.session().put(url, data=data, **kwargs)
        except getattr(requests.exceptions, 'RequestException') as inst:
            self.module.fail_json(msg=inst.message)

    def full_patch(self, url, data=None, **kwargs):
        kwargs['headers'] = self._set_headers(kwargs.get('headers'))

        try:
            return self.session().patch(url, data=data, **kwargs)
        except getattr(requests.exceptions, 'RequestException') as inst:
            self.module.fail_json(msg=inst.message)

    def full_delete(self, url, **kwargs):
        kwargs['headers'] = self._set_headers(kwargs.get('headers'))

        try:
            return self.session().delete(url, **kwargs)
        except getattr(requests.exceptions, 'RequestException') as inst:
            self.module.fail_json(msg=inst.message)

    def _set_headers(self, headers):
        if headers:
            return self._merge_dictionaries(headers, self._headers())
        return self._headers()

    def session(self):
        return AuthorizedSession(
            self._credentials())

    def _validate(self):
        if not HAS_REQUESTS:
            self.module.fail_json(msg="Please install the requests library")

        if not HAS_GOOGLE_LIBRARIES:
            self.module.fail_json(msg="Please install the google-auth library")

        if self.module.params.get('service_account_email') is not None and self.module.params['auth_kind'] != 'machineaccount':
            self.module.fail_json(
                msg="Service Account Email only works with Machine Account-based authentication"
            )

        if (self.module.params.get('service_account_file') is not None or
                self.module.params.get('service_account_contents') is not None) and self.module.params['auth_kind'] != 'serviceaccount':
            self.module.fail_json(
                msg="Service Account File only works with Service Account-based authentication"
            )

    def _credentials(self):
        cred_type = self.module.params['auth_kind']

        if cred_type == 'application':
            credentials, project_id = google.auth.default(scopes=self.module.params['scopes'])
            return credentials

        if cred_type == 'serviceaccount':
            service_account_file = self.module.params.get('service_account_file')
            service_account_contents = self.module.params.get('service_account_contents')
            if service_account_file is not None:
                path = os.path.realpath(os.path.expanduser(service_account_file))
                try:
                    svc_acct_creds = service_account.Credentials.from_service_account_file(path)
                except OSError as e:
                    self.module.fail_json(
                        msg="Unable to read service_account_file at %s: %s" % (path, e.strerror)
                    )
            elif service_account_contents is not None:
                try:
                    info = json.loads(service_account_contents)
                except json.decoder.JSONDecodeError as e:
                    self.module.fail_json(
                        msg="Unable to decode service_account_contents as JSON: %s" % e
                    )
                svc_acct_creds = service_account.Credentials.from_service_account_info(info)
            else:
                self.module.fail_json(
                    msg='Service Account authentication requires setting either service_account_file or service_account_contents'
                )
            return svc_acct_creds.with_scopes(self.module.params['scopes'])

        if cred_type == 'machineaccount':
            return google.auth.compute_engine.Credentials(
                self.module.params['service_account_email'])

        self.module.fail_json(msg="Credential type '%s' not implemented" % cred_type)

    def _headers(self):
        user_agent = "Google-Ansible-MM-{0}".format(self.product)
        if self.module.params.get('env_type'):
            user_agent = "{0}-{1}".format(user_agent, self.module.params.get('env_type'))
        return {
            'User-Agent': user_agent
        }

    def _merge_dictionaries(self, a, b):
        new = a.copy()
        new.update(b)
        return new


class GcpModule(AnsibleModule):
    def __init__(self, *args, **kwargs):
        arg_spec = kwargs.get('argument_spec', {})

        kwargs['argument_spec'] = self._merge_dictionaries(
            arg_spec,
            dict(
                project=dict(
                    required=False,
                    type='str',
                    fallback=(env_fallback, ['GCP_PROJECT'])),
                auth_kind=dict(
                    required=True,
                    fallback=(env_fallback, ['GCP_AUTH_KIND']),
                    choices=['machineaccount', 'serviceaccount', 'application'],
                    type='str'),
                service_account_email=dict(
                    required=False,
                    fallback=(env_fallback, ['GCP_SERVICE_ACCOUNT_EMAIL']),
                    type='str'),
                service_account_file=dict(
                    required=False,
                    fallback=(env_fallback, ['GCP_SERVICE_ACCOUNT_FILE']),
                    type='path'),
                service_account_contents=dict(
                    required=False,
                    fallback=(env_fallback, ['GCP_SERVICE_ACCOUNT_CONTENTS']),
                    no_log=True,
                    type='jsonarg'),
                scopes=dict(
                    required=False,
                    fallback=(env_fallback, ['GCP_SCOPES']),
                    type='list',
                    elements='str'),
                env_type=dict(
                    required=False,
                    fallback=(env_fallback, ['GCP_ENV_TYPE']),
                    type='str')
            )
        )

        mutual = kwargs.get('mutually_exclusive', [])

        kwargs['mutually_exclusive'] = mutual.append(
            ['service_account_email', 'service_account_file', 'service_account_contents']
        )

        AnsibleModule.__init__(self, *args, **kwargs)

    def raise_for_status(self, response):
        try:
            response.raise_for_status()
        except getattr(requests.exceptions, 'RequestException') as inst:
            self.fail_json(
                msg="GCP returned error: %s" % response.json(),
                request={
                    "url": response.request.url,
                    "body": response.request.body,
                    "method": response.request.method,
                }
            )

    def _merge_dictionaries(self, a, b):
        new = a.copy()
        new.update(b)
        return new


# This class does difference checking according to a set of GCP-specific rules.
# This will be primarily used for checking dictionaries.
# In an equivalence check, the left-hand dictionary will be the request and
# the right-hand side will be the response.

# Rules:
# Extra keys in response will be ignored.
# Ordering of lists does not matter.
#   - exception: lists of dictionaries are
#     assumed to be in sorted order.
class GcpRequest(object):
    def __init__(self, request):
        self.request = request

    def __eq__(self, other):
        return not self.difference(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    # Returns the difference between a request + response.
    # While this is used under the hood for __eq__ and __ne__,
    # it is useful for debugging.
    def difference(self, response):
        return self._compare_value(self.request, response.request)

    def _compare_dicts(self, req_dict, resp_dict):
        difference = {}
        for key in req_dict:
            if resp_dict.get(key):
                difference[key] = self._compare_value(req_dict.get(key), resp_dict.get(key))

        # Remove all empty values from difference.
        sanitized_difference = {}
        for key in difference:
            if difference[key]:
                sanitized_difference[key] = difference[key]

        return sanitized_difference

    # Takes in two lists and compares them.
    # All things in the list should be identical (even if a dictionary)
    def _compare_lists(self, req_list, resp_list):
        # Have to convert each thing over to unicode.
        # Python doesn't handle equality checks between unicode + non-unicode well.
        difference = []
        new_req_list = self._convert_value(req_list)
        new_resp_list = self._convert_value(resp_list)

        # We have to compare each thing in the request to every other thing
        # in the response.
        # This is because the request value will be a subset of the response value.
        # The assumption is that these lists will be small enough that it won't
        # be a performance burden.
        for req_item in new_req_list:
            found_item = False
            for resp_item in new_resp_list:
                # Looking for a None value here.
                if not self._compare_value(req_item, resp_item):
                    found_item = True
            if not found_item:
                difference.append(req_item)

        difference2 = []
        for value in difference:
            if value:
                difference2.append(value)

        return difference2

    # Compare two values of arbitrary types.
    def _compare_value(self, req_value, resp_value):
        diff = None
        # If a None is found, a difference does not exist.
        # Only differing values matter.
        if not resp_value:
            return None

        # Can assume non-None types at this point.
        try:
            if isinstance(req_value, list):
                diff = self._compare_lists(req_value, resp_value)
            elif isinstance(req_value, dict):
                diff = self._compare_dicts(req_value, resp_value)
            elif isinstance(req_value, bool):
                diff = self._compare_boolean(req_value, resp_value)
            # Always use to_text values to avoid unicode issues.
            elif to_text(req_value) != to_text(resp_value):
                diff = req_value
        # to_text may throw UnicodeErrors.
        # These errors shouldn't crash Ansible and should be hidden.
        except UnicodeError:
            pass

        return diff

    # Compare two boolean values.
    def _compare_boolean(self, req_value, resp_value):
        try:
            # Both True
            if req_value and isinstance(resp_value, bool) and resp_value:
                return None
            # Value1 True, resp_value 'true'
            if req_value and to_text(resp_value) == 'true':
                return None
            # Both False
            if not req_value and isinstance(resp_value, bool) and not resp_value:
                return None
            # Value1 False, resp_value 'false'
            if not req_value and to_text(resp_value) == 'false':
                return None
            return resp_value

        # to_text may throw UnicodeErrors.
        # These errors shouldn't crash Ansible and should be hidden.
        except UnicodeError:
            return None

    # Python (2 esp.) doesn't do comparisons between unicode + non-unicode well.
    # This leads to a lot of false positives when diffing values.
    # The Ansible to_text() function is meant to get all strings
    # into a standard format.
    def _convert_value(self, value):
        if isinstance(value, list):
            new_list = []
            for item in value:
                new_list.append(self._convert_value(item))
            return new_list
        if isinstance(value, dict):
            new_dict = {}
            for key in value:
                new_dict[key] = self._convert_value(value[key])
            return new_dict
        return to_text(value)
