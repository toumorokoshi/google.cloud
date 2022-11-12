#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Google
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# ----------------------------------------------------------------------------
#
#     ***     AUTO GENERATED CODE    ***    Type: MMv1     ***
#
# ----------------------------------------------------------------------------
#
#     This file is automatically generated by Magic Modules and manual
#     changes will be clobbered when the file is regenerated.
#
#     Please read more about how to change this file at
#     https://www.github.com/GoogleCloudPlatform/magic-modules
#
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

__metaclass__ = type

################################################################################
# Documentation
################################################################################

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: gcp_resourcemanager_project
description:
- Represents a GCP Project. A project is a container for ACLs, APIs, App Engine Apps,
  VMs, and other Google Cloud Platform resources.
short_description: Creates a GCP Project
author: Google Inc. (@googlecloudplatform)
requirements:
- python >= 2.6
- requests >= 2.18.4
- google-auth >= 1.3.0
options:
  state:
    description:
    - Whether the given object should exist in GCP
    choices:
    - present
    - absent
    default: present
    type: str
  name:
    description:
    - 'The user-assigned display name of the Project. It must be 4 to 30 characters.
      Allowed characters are: lowercase and uppercase letters, numbers, hyphen, single-quote,
      double-quote, space, and exclamation point.'
    required: false
    type: str
  labels:
    description:
    - The labels associated with this Project.
    - 'Label keys must be between 1 and 63 characters long and must conform to the
      following regular expression: `[a-z]([-a-z0-9]*[a-z0-9])?`.'
    - Label values must be between 0 and 63 characters long and must conform to the
      regular expression `([a-z]([-a-z0-9]*[a-z0-9])?)?`.
    - No more than 256 labels can be associated with a given resource.
    - Clients should store labels in a representation such as JSON that does not depend
      on specific characters being disallowed .
    required: false
    type: dict
  parent:
    description:
    - A parent organization.
    required: false
    type: dict
    suboptions:
      type:
        description:
        - Must be organization.
        required: false
        type: str
      id:
        description:
        - Id of the organization.
        required: false
        type: str
  id:
    description:
    - The unique, user-assigned ID of the Project. It must be 6 to 30 lowercase letters,
      digits, or hyphens. It must start with a letter.
    - Trailing hyphens are prohibited.
    required: true
    type: str
  project:
    description:
    - The Google Cloud Platform project to use.
    type: str
  auth_kind:
    description:
    - The type of credential used.
    type: str
    required: true
    choices:
    - application
    - machineaccount
    - serviceaccount
  service_account_contents:
    description:
    - The contents of a Service Account JSON file, either in a dictionary or as a
      JSON string that represents it.
    type: jsonarg
  service_account_file:
    description:
    - The path of a Service Account JSON file if serviceaccount is selected as type.
    type: path
  service_account_email:
    description:
    - An optional service account email address if machineaccount is selected and
      the user does not wish to use the default email.
    type: str
  scopes:
    description:
    - Array of scopes to be used
    type: list
    elements: str
  env_type:
    description:
    - Specifies which Ansible environment you're running this module within.
    - This should not be set unless you know what you're doing.
    - This only alters the User Agent string for any API requests.
    type: str
"""

EXAMPLES = """
- name: create a project
  google.cloud.gcp_resourcemanager_project:
    name: My Sample Project
    id: ansible-test-{{ 10000000000 | random }}
    auth_kind: serviceaccount
    service_account_file: "/tmp/auth.pem"
    parent:
      type: organization
      id: 636173955921
    state: present
"""

RETURN = """
number:
  description:
  - Number uniquely identifying the project.
  returned: success
  type: int
lifecycleState:
  description:
  - The Project lifecycle state.
  returned: success
  type: str
name:
  description:
  - 'The user-assigned display name of the Project. It must be 4 to 30 characters.
    Allowed characters are: lowercase and uppercase letters, numbers, hyphen, single-quote,
    double-quote, space, and exclamation point.'
  returned: success
  type: str
createTime:
  description:
  - Time of creation.
  returned: success
  type: str
labels:
  description:
  - The labels associated with this Project.
  - 'Label keys must be between 1 and 63 characters long and must conform to the following
    regular expression: `[a-z]([-a-z0-9]*[a-z0-9])?`.'
  - Label values must be between 0 and 63 characters long and must conform to the
    regular expression `([a-z]([-a-z0-9]*[a-z0-9])?)?`.
  - No more than 256 labels can be associated with a given resource.
  - Clients should store labels in a representation such as JSON that does not depend
    on specific characters being disallowed .
  returned: success
  type: dict
parent:
  description:
  - A parent organization.
  returned: success
  type: complex
  contains:
    type:
      description:
      - Must be organization.
      returned: success
      type: str
    id:
      description:
      - Id of the organization.
      returned: success
      type: str
id:
  description:
  - The unique, user-assigned ID of the Project. It must be 6 to 30 lowercase letters,
    digits, or hyphens. It must start with a letter.
  - Trailing hyphens are prohibited.
  returned: success
  type: str
"""

################################################################################
# Imports
################################################################################

from ansible_collections.google.cloud.plugins.module_utils.gcp_utils import (
    navigate_hash,
    GcpSession,
    GcpModule,
    GcpRequest,
    remove_nones_from_dict,
    replace_resource_dict,
)
import json
import time

################################################################################
# Main
################################################################################


def main():
    """Main function"""

    module = GcpModule(
        argument_spec=dict(
            state=dict(default="present", choices=["present", "absent"], type="str"),
            name=dict(type="str"),
            labels=dict(type="dict"),
            parent=dict(
                type="dict", options=dict(type=dict(type="str"), id=dict(type="str"))
            ),
            id=dict(required=True, type="str"),
        )
    )

    if not module.params["scopes"]:
        module.params["scopes"] = ["https://www.googleapis.com/auth/cloud-platform"]

    state = module.params["state"]

    fetch = fetch_resource(module, self_link(module))
    changed = False

    if fetch:
        if state == "present":
            if is_different(module, fetch):
                update(module, self_link(module))
                fetch = fetch_resource(module, self_link(module))
                changed = True
        else:
            delete(module, self_link(module))
            fetch = {}
            changed = True
    else:
        if state == "present":
            fetch = create(module, collection(module))
            changed = True
        else:
            fetch = {}

    fetch.update({"changed": changed})

    module.exit_json(**fetch)


def create(module, link):
    auth = GcpSession(module, "resourcemanager")
    return wait_for_operation(module, auth.post(link, resource_to_request(module)))


def update(module, link):
    auth = GcpSession(module, "resourcemanager")
    return wait_for_operation(module, auth.put(link, resource_to_request(module)))


def delete(module, link):
    auth = GcpSession(module, "resourcemanager")
    return wait_for_operation(module, auth.delete(link))


def resource_to_request(module):
    request = {
        "projectId": module.params.get("id"),
        "name": module.params.get("name"),
        "labels": module.params.get("labels"),
        "parent": ProjectParent(module.params.get("parent", {}), module).to_request(),
    }
    return_vals = {}
    for k, v in request.items():
        if v or v is False:
            return_vals[k] = v

    return return_vals


def fetch_resource(module, link, allow_not_found=True):
    auth = GcpSession(module, "resourcemanager")
    return return_if_object(module, auth.get(link), allow_not_found)


def self_link(module):
    return "https://cloudresourcemanager.googleapis.com/v1/projects/{id}".format(
        **module.params
    )


def collection(module):
    return "https://cloudresourcemanager.googleapis.com/v1/projects".format(
        **module.params
    )


def return_if_object(module, response, allow_not_found=False):
    # If not found, return nothing.
    if allow_not_found and response.status_code == 404:
        return None

    # If no content, return nothing.
    if response.status_code == 204:
        return None

    # SQL only: return on 403 if not exist
    if allow_not_found and response.status_code == 403:
        return None

    try:
        result = response.json()
    except getattr(json.decoder, "JSONDecodeError", ValueError) as inst:
        module.fail_json(msg="Invalid JSON response with error: %s" % inst)

    if navigate_hash(result, ["error", "message"]):
        module.fail_json(msg=navigate_hash(result, ["error", "message"]))

    return result


def is_different(module, response):
    request = resource_to_request(module)
    response = response_to_hash(module, response)

    # Remove all output-only from response.
    response_vals = {}
    for k, v in response.items():
        if k in request:
            response_vals[k] = v

    request_vals = {}
    for k, v in request.items():
        if k in response:
            request_vals[k] = v

    return GcpRequest(request_vals) != GcpRequest(response_vals)


# Remove unnecessary properties from the response.
# This is for doing comparisons with Ansible's current parameters.
def response_to_hash(module, response):
    return {
        "projectNumber": response.get("projectNumber"),
        "lifecycleState": response.get("lifecycleState"),
        "name": response.get("name"),
        "createTime": response.get("createTime"),
        "labels": response.get("labels"),
        "parent": ProjectParent(response.get("parent", {}), module).from_response(),
    }


def async_op_url(module, extra_data=None):
    if extra_data is None:
        extra_data = {}
    url = "https://cloudresourcemanager.googleapis.com/v1/{op_id}"
    combined = extra_data.copy()
    combined.update(module.params)
    return url.format(**combined)


def wait_for_operation(module, response):
    op_result = return_if_object(module, response)
    if op_result is None:
        return {}
    status = navigate_hash(op_result, ["done"])
    wait_done = wait_for_completion(status, op_result, module)
    raise_if_errors(wait_done, ["error"], module)
    return navigate_hash(wait_done, ["response"])


def wait_for_completion(status, op_result, module):
    op_id = navigate_hash(op_result, ["name"])
    op_uri = async_op_url(module, {"op_id": op_id})
    while not status:
        raise_if_errors(op_result, ["error"], module)
        time.sleep(1.0)
        op_result = fetch_resource(module, op_uri, False)
        status = navigate_hash(op_result, ["done"])
    return op_result


def raise_if_errors(response, err_path, module):
    errors = navigate_hash(response, err_path)
    if errors is not None:
        module.fail_json(msg=errors)


class ProjectParent(object):
    def __init__(self, request, module):
        self.module = module
        if request:
            self.request = request
        else:
            self.request = {}

    def to_request(self):
        return remove_nones_from_dict(
            {"type": self.request.get("type"), "id": self.request.get("id")}
        )

    def from_response(self):
        return remove_nones_from_dict(
            {"type": self.request.get("type"), "id": self.request.get("id")}
        )


if __name__ == "__main__":
    main()
