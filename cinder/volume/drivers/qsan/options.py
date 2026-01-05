# Copyright (c) 2024 QSAN Technology, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Configuration options for QSAN drivers."""

from oslo_config import cfg

from cinder.volume import configuration as conf


# QSAN connection options
qsan_connection_opts = [
    cfg.StrOpt('qsan_management_ip',
               help='The management IP address of the QSAN storage system.'),
    cfg.PortOpt('qsan_management_port',
                default=443,
                help='The management port of the QSAN storage system.'),
    cfg.StrOpt('qsan_management_protocol',
               default='https',
               choices=['http', 'https'],
               help='The protocol used to communicate with the QSAN '
                    'storage system.'),
]

# QSAN authentication options
qsan_auth_opts = [
    cfg.StrOpt('qsan_login',
               help='The username for QSAN storage system.'),
    cfg.StrOpt('qsan_password',
               help='The password for QSAN storage system.',
               secret=True),
]

# QSAN storage options
qsan_storage_opts = [
    cfg.StrOpt('qsan_pool_name',
               help='The storage pool name to use for volume creation.'),
    cfg.BoolOpt('qsan_ssl_verify',
                default=True,
                help='Verify SSL certificate for HTTPS connections.'),
    cfg.IntOpt('qsan_api_timeout',
               default=60,
               min=10,
               help='Timeout in seconds for QSAN API calls.'),
    cfg.IntOpt('qsan_retry_count',
               default=3,
               min=1,
               help='Number of times to retry failed API calls.'),
]

# QSAN iSCSI specific options
qsan_iscsi_opts = [
    cfg.ListOpt('qsan_iscsi_portals',
                default=[],
                help='List of iSCSI portal IPs for the QSAN storage. '
                     'If empty, uses qsan_management_ip.'),
    cfg.BoolOpt('qsan_chap_enabled',
                default=False,
                help='Enable CHAP authentication for iSCSI connections.'),
    cfg.StrOpt('qsan_chap_username',
               help='CHAP username for iSCSI authentication.'),
    cfg.StrOpt('qsan_chap_password',
               help='CHAP password for iSCSI authentication.',
               secret=True),
    cfg.BoolOpt('qsan_thin_provision',
                default=True,
                help='Enable thin provisioning for volumes.'),
]

# All QSAN options
QSAN_OPTS = (qsan_connection_opts +
             qsan_auth_opts +
             qsan_storage_opts +
             qsan_iscsi_opts)

# Register options
CONF = cfg.CONF
CONF.register_opts(QSAN_OPTS, group=conf.SHARED_CONF_GROUP)
