#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test utilities for mapreduce framework.
"""



# Disable "Invalid method name"
# pylint: disable-msg=C6409

# os_compat must be first to ensure timezones are UTC.
# Disable "unused import" and "invalid import order"
# pylint: disable-msg=W0611
from google.appengine.tools import os_compat
# pylint: enable-msg=W0611

import base64
from testlib import mox
import os
import sys
import unittest
import urllib

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import queueinfo
from google.appengine.api.memcache import memcache_stub
from google.appengine.api.labs.taskqueue import taskqueue_stub


class MatchesUserRPC(mox.Comparator):
  """Mox comparator for UserRPC objects."""

  def __init__(self, **kwargs):
    self.kwargs = kwargs

  def equals(self, rpc):
    """Check to see if rpc matches arguments."""
    if self.kwargs.get("deadline", None) != rpc.deadline:
      return False
    return True

  def __repr__(self):
    return "MatchesUserRPC(%s)" % self.kwargs


class HandlerTestBase(unittest.TestCase):
  """Base class for all webapp.RequestHandler tests."""

  MAPREDUCE_URL = "/_ah/mapreduce/kickoffjob_callback"

  def setUp(self):
    unittest.TestCase.setUp(self)

    self.appid = "testapp"
    os.environ["APPLICATION_ID"] = self.appid

    self.memcache = memcache_stub.MemcacheServiceStub()
    self.taskqueue = taskqueue_stub.TaskQueueServiceStub()
    self.taskqueue.queue_yaml_parser = (
        lambda x: queueinfo.LoadSingleQueue(
            "queue:\n"
            "- name: default\n"
            "  rate: 10/s\n"
            "- name: crazy-queue\n"
            "  rate: 2000/d\n"
            "  bucket_size: 10\n"))
    self.datastore = datastore_file_stub.DatastoreFileStub(
        self.appid, "/dev/null", "/dev/null")

    apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
    apiproxy_stub_map.apiproxy.RegisterStub("taskqueue", self.taskqueue)
    apiproxy_stub_map.apiproxy.RegisterStub("memcache", self.memcache)
    apiproxy_stub_map.apiproxy.RegisterStub("datastore_v3", self.datastore)

  def decode_task_payload(self, task):
    """Decodes POST task payload.

    Args:
      task: a task to decode its payload.

    Returns:
      parameter_name -> parameter_value dict.
    """
    key_values = [kv.split("=") for kv in
                  base64.b64decode(task["body"]).split("&")]
    return dict((key, urllib.unquote_plus(value)) for key, value in key_values)

  def assertTaskStarted(self, queue="default"):
    tasks = self.taskqueue.GetTasks(queue)
    self.assertEquals(1, len(tasks))
    self.assertEquals(tasks[0]["url"], self.MAPREDUCE_URL)
