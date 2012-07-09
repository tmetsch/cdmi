# Copyright (c) 2011 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from swift.common.middleware.cdmiapp.cdmibase import \
    (Consts, Controller, concat_parts)
from swift.common.middleware.cdmiapp.cdmiutils import \
    (check_resource, get_err_response)
from swift.common.middleware.cdmiapp.cdmicommoncontroller import \
    (CDMIBaseController)
from urllib import unquote
from swift.common.utils import split_path
from webob import Request, Response
import json


class NonCDMIContainerController(CDMIBaseController):
    """
    Handles non-cdmi container request for create and update.
    Both create and update use HTTP PUT method.
    """

    def PUT(self, env, start_response):
        """ Handle Container update and create request """

        # First check if the resource exists and if it is a directory
        path = '/' + concat_parts('v1', self.account_name, self.container_name,
                                  self.parent_name, self.object_name)

        exists, headers, body = check_resource(env, 'HEAD', path,
                                               self.logger, False)

        if exists:
            content_type = headers.get('content-type', '')
            content_type = content_type.lower() if content_type else ''
            if (content_type.find('application/directory') < 0 and
                self.object_name):
                return get_err_response('Conflict')
        else:
            res = self._check_parent(env, start_response)
            if res:
                return res

        req = Request(env)
        req.headers['content-type'] = 'application/directory'
        req.headers['content-length'] = '0'
        req.body = ''
        res = req.get_response(self.app)
        return res


class NonCDMIObjectController(CDMIBaseController):
    """ Handles create and update requests on objects. """

    def PUT(self, env, start_response):
        """ Handle non-CDMI Object update and create request. """

        # First check if the resource exists and if it is a directory
        path = '/' + concat_parts('v1', self.account_name, self.container_name,
                                  self.parent_name, self.object_name)

        exists, headers, body = check_resource(env, 'HEAD', path, self.logger,
                                               False, None)

        if exists:
            content_type = headers.get('content-type', '')
            content_type = content_type.lower() if content_type else ''
            if content_type.find('application/directory') >= 0:
                return get_err_response('Conflict')
        else:
            path = '/' + concat_parts('v1', self.account_name,
                                      self.container_name)

            query_string = 'delimiter=/&prefix=' + \
                concat_parts(self.parent_name, self.object_name) + '/'

            parent_exists, dummy, body = check_resource(env, 'GET', path,
                                                        self.logger, True,
                                                        query_string)

            if parent_exists:
                try:
                    children = json.loads(body)
                    if len(children) > 0:
                        #No children under, no resource exist
                        return get_err_response('Conflict')
                except ValueError:
                    return get_err_response('InconsistantState')
            else:
                return get_err_response('NoParentContainer')

        # Check if the parent is OK. it should be either a real directory
        # or a virtual directory
        res = self._check_parent(env, start_response)
        if res:
            return res

        # Create a new WebOb Request object according to the current request
        req = Request(env)

        if not req.body or len(req.body) == 0:
            req.headers['content-length'] = '0'
        res = req.get_response(self.app)
        return res
