#!/usr/bin/env python

# Author: Asher Feldman (asher@bandpage.com)
# Copyright (c) 2014, BandPage Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
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

import sys
import fastly
from optparse import OptionParser


def main():
    """
        Upload a vcl file to a fastly service, cloning the current version if
        necessary. The uploaded vcl is set as main unless --include is given.
        All existing vcl files will be deleted first if --delete is given.
    """

    parser = OptionParser(description=
             "Upload a vcl file (set as main) to a given fastly service. All arguments are required.")
    parser.add_option("-k", "--key", dest="apikey", help="fastly api key")
    parser.add_option("-u", "--user", dest="user", help="fastly user name")
    parser.add_option("-p", "--password", dest="password",
                      help="fastly password")
    parser.add_option("-f", "--file", dest="filename",
                      help="vcl file to upload")
    parser.add_option("-s", "--service", dest="service_name",
                      help="service to update")
    parser.add_option("-d", "--delete_vcl", action="store_true",
                      dest="delete_vcl", default=False,
                      help="delete existing vcl files from service\
                            before uploading")
    parser.add_option("-i", "--include", action="store_true",
                      dest="include_vcl", default=False,
                      help="do not set uploaded vcl as main,\
                            to be included only")

    (options, args) = parser.parse_args()
    for val in options.__dict__.values():
        if val is None:
            print "Missing required options:"
            parser.print_help()
            sys.exit(1)

    vcl_name = options.filename.split('/').pop()
    service_name = options.service_name
    vcl_file = open(options.filename, 'r')
    vcl_content = vcl_file.read()

    # Need to fully authenticate to access all features.
    client = fastly.connect(options.apikey)
    client.login(options.user, options.password)

    service = client.get_service_by_name(service_name)
    versions = client.list_versions(service.id)
    latest = versions.pop()

    if latest.locked is True or latest.active is True:
        print "\n[ Cloning version %d ]\n"\
            % (latest.number)

        latest = client.clone_version(service.id, latest.number)

    if options.delete_vcl:
        vcls = client.list_vcls(service.id, latest.number)
        for vcl in vcls:
            print "\n[ Deleting vcl file %s from version %d ]\n" %\
                (service_name, latest.number)

            client.delete_vcl(service.id, latest.number, vcl.name)

    if vcl_name in latest.vcls:
        print "\n[ Updating vcl file %s on service %s version %d ]\n"\
            % (vcl_name, service_name, latest.number)

        client.update_vcl(service.id, latest.number, vcl_name,
                          content=vcl_content)
    else:
        print "\n[ Uploading new vcl file %s on service %s version %d ]\n"\
            % (vcl_name, service_name, latest.number)

        client.upload_vcl(service.id, latest.number, vcl_name, vcl_content)

    if options.include_vcl is False:
        print "\n[ Setting vcl %s as main ]\n" % (vcl_name)
        client.set_main_vcl(service.id, latest.number, vcl_name)

    client.activate_version(service.id, latest.number)
    print "\n[ Activing configuration version %d ]\n" % (latest.number)

if __name__ == "__main__":
    main()
