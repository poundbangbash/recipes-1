#!/usr/bin/python
#
# Copyright 2013 Timothy Sutton
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
"""See docstring for BarebonesURLProvider class"""
# suppress 'missing class member env'
#pylint: disable=e1101

from __future__ import absolute_import

import plistlib
import ssl
from distutils.version import LooseVersion
from functools import wraps
from operator import itemgetter

from autopkglib import Processor, ProcessorError

try:
    from urllib.parse import urlopen  # For Python 3
except ImportError:
    from urllib2 import urlopen  # For Python 2

__all__ = ["BarebonesURLProvider"]

URLS = {"bbedit": "https://versioncheck.barebones.com/BBEdit.xml"}

def sslwrap(func):
    """http://stackoverflow.com/a/24175862"""
    @wraps(func)
    def wraps_sslwrap(*args, **kw):
        """Monkey-patch for sslwrap to force TLSv1"""
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return wraps_sslwrap

ssl.wrap_socket = sslwrap(ssl.wrap_socket)

class BarebonesURLProvider(Processor):
    """Provides a version and dmg download for the Barebones product given."""
    description = __doc__
    input_variables = {
        "product_name": {
            "required": True,
            "description":
                "Product to fetch URL for. One of 'textwrangler', 'bbedit'.",
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the product.",
        },
        "url": {
            "description": "Download URL.",
        },
        "minimum_os_version": {
            "description":
                "Minimum OS version supported according to product metadata."
        }
    }

    def main(self):
        '''Find the download URL'''
        def compare_version(this, that):
            '''compare LooseVersions'''
            return cmp(LooseVersion(this), LooseVersion(that))

        prod = self.env.get("product_name")
        if prod not in URLS:
            raise ProcessorError(
                "product_name %s is invalid; it must be one of: %s"
                % (prod, ', '.join(URLS)))
        url = URLS[prod]
        try:
            manifest_str = urlopen(url).read()
        except Exception as err:
            raise ProcessorError(
                "Unexpected error retrieving product manifest: '%s'" % err)

        try:
            plist = plistlib.readPlistFromString(manifest_str)
        except Exception as err:
            raise ProcessorError(
                "Unexpected error parsing manifest as a plist: '%s'" % err)

        entries = plist.get("SUFeedEntries")
        if not entries:
            raise ProcessorError(
                "Expected 'SUFeedEntries' manifest key wasn't found.")

        sorted_entries = sorted(
            entries,
            key=itemgetter("SUFeedEntryShortVersionString"),
            cmp=compare_version)
        metadata = sorted_entries[-1]
        url = metadata["SUFeedEntryDownloadURL"]
        min_os_version = metadata["SUFeedEntryMinimumSystemVersion"]
        version = metadata["SUFeedEntryShortVersionString"]

        self.env["version"] = version
        self.env["minimum_os_version"] = min_os_version
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])

if __name__ == "__main__":
    PROCESSOR = BarebonesURLProvider()
    PROCESSOR.execute_shell()
