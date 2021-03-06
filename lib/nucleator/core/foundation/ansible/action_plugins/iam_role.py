# Copyright 2015 47Lining LLC.
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

from ansible.runner.return_data import ReturnData
from ansible.utils import parse_kv, template
from ansible import utils
from boto.sts import STSConnection

import json
import boto
import urllib
import os
import time

class ActionModule(object):
    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        
        try:
            
            args = {}
            if complex_args:
                args.update(complex_args)
            args.update(parse_kv(module_args))

            access_policies = {}

            role_name = args["role_name"]
            print "Role Name: ", role_name

            assume_role_trust_policy = json.dumps(args["trust_policy"])

            access_policies = args["access_policies"]

            envdict={}
            if self.runner.environment:
                env=template.template(self.runner.basedir, self.runner.environment, inject, convert_bare=True)
                env = utils.safe_eval(env)
                
                sts_connection = STSConnection(
                    aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN")
                )

            c = boto.connect_iam(aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"), security_token=env.get("AWS_SECURITY_TOKEN"))
            
            #Look for the role
            try:
                role = c.get_role(role_name)

                #Make sure the trust policy exists
                try:
                    temp_trust_policy = urllib.unquote(role["get_role_response"]["get_role_result"]["role"]["assume_role_policy_document"])
                
                    #Reorganize the json dict so it is in the same order of the yaml policy
                    temp_trust_policy = json.dumps(json.loads(temp_trust_policy))
                    
                    #Trust policy does not match, update it
                    if not assume_role_trust_policy == temp_trust_policy:
                        if not assume_role_trust_policy == "\"\"":
                            c.update_assume_role_policy(role_name, assume_role_trust_policy)

                    #Make sure each new policy exists
                    for policies in access_policies:
                        try:

                            temp_policy = urllib.unquote(c.get_role_policy(role_name, policies["policy_name"])["get_role_policy_response"]["get_role_policy_result"]["policy_document"])
                            
                            #Policy has same name but does not match, update it
                            if not temp_policy == json.dumps(policies["policy_document"]):
                                if not policies["policy_document"] == "\"\"":
                                    c.delete_role_policy(role_name, policies["policy_name"])
                                    c.put_role_policy(role_name, policies["policy_name"], json.dumps(policies["policy_document"]))
                            
                        #Can't find policy, add it
                        except Exception, e:
                            try:
                                c.put_role_policy(role_name, policies["policy_name"], json.dumps(policies["policy_document"]))
                            except Exception, e:
                                # deal with failure gracefully
                                result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
                                return ReturnData(conn=conn, comm_ok=False, result=result)

                    #Returns true if the policy name exists
                    def checkIfPolicyExists(access_policies, temp_name):
                        for policy_name in access_policies:
                            if policy_name["policy_name"] == temp_name:
                                return True
                        return False

                    #Delete any policies that are not in the yaml
                    temp_policy_names = c.list_role_policies(role_name)
                    for temp_name in temp_policy_names["list_role_policies_response"]["list_role_policies_result"]["policy_names"]:
                        exists = checkIfPolicyExists(access_policies, temp_name)
                        if not exists:
                            c.delete_role_policy(role_name, temp_name)
                    
                #Can't find trust policy, add it
                except Exception, e:
                    try:
                        c.update_assume_role_policy(role_name, assume_role_trust_policy)
                    except Exception, e:
                        # deal with failure gracefully
                        result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
                        return ReturnData(conn=conn, comm_ok=False, result=result)
            
            #Can't find role, add the role and its policies
            except Exception, e:
                try:
                    if assume_role_trust_policy == "\"\"":
                        c.create_role(role_name)
                    else:
                        c.create_role(role_name, assume_role_trust_policy)
                    for policies in access_policies:
                        c.put_role_policy(role_name, policies["policy_name"], json.dumps(policies["policy_document"]))
                except Exception, e:
                    # deal with failure gracefully
                    result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
                    return ReturnData(conn=conn, comm_ok=False, result=result)

            # add a short delay to allow for eventual consistency
            if role_name == "NucleatorAgent" or role_name == "NucleatorBucketandqDistributorServiceRunner":
                print "30 second delay to let roles catch up"
                time.sleep(30)
                '''
                role = None
                attemptNumber = 1

                while role == None:
                    print "attemptNumber: ", attemptNumber
                    try:
                        role = c.get_role(role_name)
                    except Exception, e:
                        role = None
                        print "Failed, Trying Again"
                        time.sleep(5)
                        attemptNumber = attemptNumber + 1

                        if attemptNumber == 60:
                            # deal with failure gracefully
                            result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
                            return ReturnData(conn=conn, comm_ok=False, result=result)
                '''
                

            return ReturnData(conn=conn,
                comm_ok=True,
                result=dict(failed=False, changed=False, msg="Roles are updated!"))

        except Exception, e:
            # deal with failure gracefully
            result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
            return ReturnData(conn=conn, comm_ok=False, result=result)


                                
