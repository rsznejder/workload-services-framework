# Copyright 2018 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module containing AWS credential file installation and cleanup helpers.

AWS credentials consist of a secret access key and its ID, stored in a single
file. Following PKB's AWS setup instructions (see
https://github.com/GoogleCloudPlatform/PerfKitBenchmarker#install-aws-cli-and-setup-authentication),
the default location of the file will be at ~/.aws/credentials

This package copies the credentials file to the remote VM to make them available
for calls from the VM to other AWS services, such as SQS or Kinesis.
"""

import configparser
import logging
import os
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from subprocess import check_output


FLAGS = flags.FLAGS

flags.DEFINE_string(
    'aws_credentials_local_path', os.path.join('~', '.aws'),
    'Path where the AWS credential files can be found on the local machine.')

flags.DEFINE_string(
    'aws_credentials_remote_path', '.aws',
    'Path where the AWS credential files will be written on remote machines.')

flags.DEFINE_boolean(
    'aws_credentials_overwrite', False,
    'When set, if an AWS credential file already exists at the destination '
    'specified by --aws_credentials_remote_path, it will be overwritten during '
    'AWS credential file installation.')
flags.DEFINE_string('aws_s3_region', None, 'Region for the S3 bucket')


def _GetLocalPath():
  """Gets the expanded local path of the credential files.

  Returns:
    string. Path to the credential files on the local machine.
  """
  return os.path.expanduser(FLAGS.aws_credentials_local_path)


def GetCredentials(credentials_file_name='credentials'):
  """Gets the credentials from the local credential file.

  AWS credentials file is expected to be called 'credentials'.
  AWS credentials file looks like this, and ends with a newline:
  [default]
  aws_access_key_id = {access_key}
  aws_secret_access_key = {secret_access_key}

  Args:
    credentials_file_name: String name of the file containing the credentials.

  Returns:
    A string, string tuple of access_key and secret_access_key
  """
  config = configparser.ConfigParser()
  config.read(os.path.join(_GetLocalPath(), credentials_file_name))
  key_id = config['default']['aws_access_key_id']
  key = config['default']['aws_secret_access_key']
  return key_id, key


def CheckPrerequisites():
  """Verifies that the required resources are present.

  Raises:
    perfkitbenchmarker.data.ResourceNotFound: On missing resource.
  """
  local_path = _GetLocalPath()
  if not os.path.exists(local_path):
    raise data.ResourceNotFound(
        'AWS credential files were not found at {0}'.format(local_path))


def _IsCopyNeeded(vm, local_path, remote_path):
  # return False: if the username, file_path, IP (or localhost) are the same for local and remote
  local_ips = check_output(['hostname', '--all-ip-addresses'])
  local_ip_list_str = local_ips.decode('utf-8')
  remote_ip = vm.GetConnectionIp()
  if remote_path == '.aws':
    full_remote_path = '/home/{}/{}'.format(vm.user_name, remote_path)
  else:
    full_remote_path = remote_path
  local_user = os.environ.get('USER') or os.environ.get('USERNAME') or ''
  # remote_ip is the same as one of the local IP or localhost
  if remote_ip in local_ip_list_str or remote_ip == 'localhost':
    # same user and same path, do NOT copy
    if local_user == vm.user_name and local_path == full_remote_path:
      return False
  return True


def Install(vm):
  """Copies credential files to the specified VM.

  Args:
    vm: BaseVirtualMachine. VM that receives the credential files.

  Raises:
    errors.Error: If the file destination on the VM already exists, and the
        overwrite behavior is not specified via --aws_credentials_overwrite.
  """
  local_path = _GetLocalPath()
  remote_path = FLAGS.aws_credentials_remote_path
  overwrite = FLAGS.aws_credentials_overwrite
  try:
    vm.RemoteCommand('[[ ! -e {0} ]]'.format(remote_path))
  except errors.VirtualMachine.RemoteCommandError:
    err_msg = 'File {0} already exists on VM {1}.'.format(remote_path, vm)
    if overwrite:
      logging.info('%s Overwriting.', err_msg)
    else:
      raise errors.Error(err_msg)
  remote_dir = os.path.dirname(remote_path)
  if remote_dir:
    vm.RemoteCommand('mkdir -p {0}'.format(remote_dir))
  if _IsCopyNeeded(vm, local_path, remote_path):
    if FLAGS.enable_rsync:
      vm.PushFile(f"{local_path}/", remote_path)
    else:
      vm.PushFile(local_path, remote_path)


def Uninstall(vm):
  """Deletes the credential files from the specified VM.

  Args:
    vm: BaseVirtualMachine. VM that has the credential files.
  """
  vm.RemoveFile(FLAGS.aws_credentials_remote_path)


def IsInstalled(vm):
  """Checks whether aws credentials is installed on the VM."""
  _, _, retVal = vm.RemoteCommandWithReturnCode('test -d {0}'.format(FLAGS.aws_credentials_remote_path),
                                                ignore_failure=True,
                                                suppress_warning=True)
  # It is not installed
  if retVal != 0:
    return False

  return True
