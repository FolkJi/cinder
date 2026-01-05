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
"""Common utilities for QSAN drivers."""

import time

from oslo_log import log as logging
from oslo_utils import units
import requests

from cinder import exception
from cinder.i18n import _


LOG = logging.getLogger(__name__)


class QSANApiException(exception.VolumeDriverException):
    """Exception for QSAN API errors."""
    message = _("QSAN API error: %(message)s")


class QSANClient:
    """REST API client for QSAN storage systems.

    This class handles all communication with the QSAN storage system
    through its REST API.
    """

    def __init__(self, host, port, protocol, username, password,
                 ssl_verify=True, timeout=60, retry_count=3):
        """Initialize the QSAN REST API client.

        :param host: Management IP address of the QSAN storage
        :param port: Management port of the QSAN storage
        :param protocol: Protocol to use (http or https)
        :param username: API username
        :param password: API password
        :param ssl_verify: Whether to verify SSL certificates
        :param timeout: API call timeout in seconds
        :param retry_count: Number of times to retry failed calls
        """
        self.host = host
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.retry_count = retry_count

        self.base_url = f"{protocol}://{host}:{port}/api"
        self.session = None
        self.session_token = None

    def _create_session(self):
        """Create a new HTTP session."""
        self.session = requests.Session()
        self.session.verify = self.ssl_verify

    def login(self):
        """Authenticate with the QSAN storage system.

        :raises QSANApiException: If authentication fails
        """
        if self.session is None:
            self._create_session()

        url = f"{self.base_url}/login"
        data = {
            'username': self.username,
            'password': self.password,
        }

        try:
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            self.session_token = result.get('token')
            LOG.debug("Successfully logged in to QSAN storage at %s",
                      self.host)
        except requests.exceptions.RequestException as e:
            msg = _("Failed to login to QSAN storage: %s") % str(e)
            LOG.error(msg)
            raise QSANApiException(message=msg)

    def logout(self):
        """Logout from the QSAN storage system."""
        if self.session is None or self.session_token is None:
            return

        url = f"{self.base_url}/logout"
        try:
            self._request('POST', url)
            LOG.debug("Successfully logged out from QSAN storage at %s",
                      self.host)
        except Exception:
            LOG.warning("Failed to logout from QSAN storage, ignoring.")
        finally:
            self.session_token = None
            self.session = None

    def _request(self, method, url, data=None, params=None):
        """Make an HTTP request to the QSAN API.

        :param method: HTTP method (GET, POST, PUT, DELETE)
        :param url: URL to request
        :param data: Request body data
        :param params: Query parameters
        :returns: Response JSON data
        :raises QSANApiException: If the request fails
        """
        headers = {
            'Content-Type': 'application/json',
        }
        if self.session_token:
            headers['Authorization'] = f"Bearer {self.session_token}"

        for attempt in range(self.retry_count):
            try:
                response = self.session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                if response.content:
                    return response.json()
                return None
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_count - 1:
                    LOG.warning("API request failed, retrying: %s", str(e))
                    time.sleep(1)
                    continue
                msg = _("QSAN API request failed: %s") % str(e)
                LOG.error(msg)
                raise QSANApiException(message=msg)

    # ========== Volume Operations ==========

    def create_volume(self, pool_name, volume_name, size_gb, thin=True):
        """Create a volume on the QSAN storage.

        :param pool_name: Name of the storage pool
        :param volume_name: Name of the volume to create
        :param size_gb: Size of the volume in GB
        :param thin: Whether to create a thin-provisioned volume
        :returns: Volume information dictionary
        """
        url = f"{self.base_url}/volumes"
        data = {
            'pool': pool_name,
            'name': volume_name,
            'size': size_gb * units.Gi,
            'thin_provision': thin,
        }
        return self._request('POST', url, data=data)

    def delete_volume(self, volume_name):
        """Delete a volume from the QSAN storage.

        :param volume_name: Name of the volume to delete
        """
        url = f"{self.base_url}/volumes/{volume_name}"
        return self._request('DELETE', url)

    def extend_volume(self, volume_name, new_size_gb):
        """Extend a volume on the QSAN storage.

        :param volume_name: Name of the volume to extend
        :param new_size_gb: New size of the volume in GB
        """
        url = f"{self.base_url}/volumes/{volume_name}"
        data = {
            'size': new_size_gb * units.Gi,
        }
        return self._request('PUT', url, data=data)

    def get_volume(self, volume_name):
        """Get information about a volume.

        :param volume_name: Name of the volume
        :returns: Volume information dictionary or None if not found
        """
        url = f"{self.base_url}/volumes/{volume_name}"
        try:
            return self._request('GET', url)
        except QSANApiException:
            return None

    # ========== Snapshot Operations ==========

    def create_snapshot(self, volume_name, snapshot_name):
        """Create a snapshot of a volume.

        :param volume_name: Name of the source volume
        :param snapshot_name: Name for the new snapshot
        :returns: Snapshot information dictionary
        """
        url = f"{self.base_url}/volumes/{volume_name}/snapshots"
        data = {
            'name': snapshot_name,
        }
        return self._request('POST', url, data=data)

    def delete_snapshot(self, volume_name, snapshot_name):
        """Delete a snapshot.

        :param volume_name: Name of the source volume
        :param snapshot_name: Name of the snapshot to delete
        """
        url = f"{self.base_url}/volumes/{volume_name}/snapshots/{snapshot_name}"
        return self._request('DELETE', url)

    def get_snapshot(self, volume_name, snapshot_name):
        """Get information about a snapshot.

        :param volume_name: Name of the source volume
        :param snapshot_name: Name of the snapshot
        :returns: Snapshot information dictionary or None if not found
        """
        url = f"{self.base_url}/volumes/{volume_name}/snapshots/{snapshot_name}"
        try:
            return self._request('GET', url)
        except QSANApiException:
            return None

    # ========== Clone Operations ==========

    def clone_volume(self, src_volume_name, dst_volume_name, snapshot_name=None):
        """Clone a volume.

        :param src_volume_name: Name of the source volume
        :param dst_volume_name: Name for the new volume
        :param snapshot_name: Optional snapshot to clone from
        :returns: New volume information dictionary
        """
        url = f"{self.base_url}/volumes/{src_volume_name}/clone"
        data = {
            'name': dst_volume_name,
        }
        if snapshot_name:
            data['snapshot'] = snapshot_name
        return self._request('POST', url, data=data)

    def create_volume_from_snapshot(self, snapshot_volume_name, snapshot_name,
                                    new_volume_name, size_gb=None):
        """Create a new volume from a snapshot.

        :param snapshot_volume_name: Name of the volume the snapshot belongs to
        :param snapshot_name: Name of the snapshot
        :param new_volume_name: Name for the new volume
        :param size_gb: Optional new size in GB (must be >= snapshot size)
        :returns: New volume information dictionary
        """
        url = f"{self.base_url}/volumes/{snapshot_volume_name}/snapshots/{snapshot_name}/clone"
        data = {
            'name': new_volume_name,
        }
        if size_gb:
            data['size'] = size_gb * units.Gi
        return self._request('POST', url, data=data)

    # ========== Pool Operations ==========

    def get_pool(self, pool_name):
        """Get information about a storage pool.

        :param pool_name: Name of the pool
        :returns: Pool information dictionary
        """
        url = f"{self.base_url}/pools/{pool_name}"
        return self._request('GET', url)

    def get_pool_stats(self, pool_name):
        """Get capacity statistics for a storage pool.

        :param pool_name: Name of the pool
        :returns: Dictionary with total_capacity and free_capacity in bytes
        """
        pool_info = self.get_pool(pool_name)
        return {
            'total_capacity': pool_info.get('total_capacity', 0),
            'free_capacity': pool_info.get('free_capacity', 0),
            'used_capacity': pool_info.get('used_capacity', 0),
        }

    # ========== iSCSI Operations ==========

    def create_iscsi_target(self, target_name, target_iqn=None):
        """Create an iSCSI target.

        :param target_name: Name for the target
        :param target_iqn: Optional custom IQN, auto-generated if not provided
        :returns: Target information including IQN
        """
        url = f"{self.base_url}/iscsi/targets"
        data = {
            'name': target_name,
        }
        if target_iqn:
            data['iqn'] = target_iqn
        return self._request('POST', url, data=data)

    def delete_iscsi_target(self, target_id):
        """Delete an iSCSI target.

        :param target_id: ID of the target to delete
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}"
        return self._request('DELETE', url)

    def get_iscsi_target(self, target_id):
        """Get information about an iSCSI target.

        :param target_id: ID of the target
        :returns: Target information dictionary
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}"
        return self._request('GET', url)

    def get_iscsi_target_by_name(self, target_name):
        """Get iSCSI target by name.

        :param target_name: Name of the target
        :returns: Target information dictionary or None if not found
        """
        url = f"{self.base_url}/iscsi/targets"
        params = {'name': target_name}
        try:
            result = self._request('GET', url, params=params)
            if result and len(result) > 0:
                return result[0]
            return None
        except QSANApiException:
            return None

    def map_volume_to_target(self, volume_name, target_id, lun_id=None):
        """Map a volume to an iSCSI target.

        :param volume_name: Name of the volume to map
        :param target_id: ID of the target
        :param lun_id: Optional specific LUN ID, auto-assigned if not provided
        :returns: Mapping information including LUN ID
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/luns"
        data = {
            'volume': volume_name,
        }
        if lun_id is not None:
            data['lun_id'] = lun_id
        return self._request('POST', url, data=data)

    def unmap_volume_from_target(self, target_id, lun_id):
        """Unmap a volume from an iSCSI target.

        :param target_id: ID of the target
        :param lun_id: LUN ID to unmap
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/luns/{lun_id}"
        return self._request('DELETE', url)

    def get_target_luns(self, target_id):
        """Get all LUN mappings for a target.

        :param target_id: ID of the target
        :returns: List of LUN mapping dictionaries
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/luns"
        return self._request('GET', url)

    def get_volume_lun_mapping(self, volume_name):
        """Get LUN mapping information for a volume.

        :param volume_name: Name of the volume
        :returns: Mapping information or None if not mapped
        """
        url = f"{self.base_url}/volumes/{volume_name}/mapping"
        try:
            return self._request('GET', url)
        except QSANApiException:
            return None

    def add_initiator_to_target(self, target_id, initiator_iqn):
        """Add an initiator to an iSCSI target's ACL.

        :param target_id: ID of the target
        :param initiator_iqn: IQN of the initiator to add
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/acl"
        data = {
            'initiator': initiator_iqn,
        }
        return self._request('POST', url, data=data)

    def remove_initiator_from_target(self, target_id, initiator_iqn):
        """Remove an initiator from an iSCSI target's ACL.

        :param target_id: ID of the target
        :param initiator_iqn: IQN of the initiator to remove
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/acl/{initiator_iqn}"
        return self._request('DELETE', url)

    def set_target_chap(self, target_id, username, password):
        """Set CHAP authentication for a target.

        :param target_id: ID of the target
        :param username: CHAP username
        :param password: CHAP password
        """
        url = f"{self.base_url}/iscsi/targets/{target_id}/chap"
        data = {
            'username': username,
            'password': password,
        }
        return self._request('PUT', url, data=data)

    def get_iscsi_portals(self):
        """Get list of iSCSI portal IPs.

        :returns: List of portal IP addresses
        """
        url = f"{self.base_url}/iscsi/portals"
        result = self._request('GET', url)
        return result.get('portals', [])

    # ========== System Operations ==========

    def get_system_info(self):
        """Get system information from the QSAN storage.

        :returns: System information dictionary
        """
        url = f"{self.base_url}/system"
        return self._request('GET', url)

    def get_system_version(self):
        """Get the firmware version of the QSAN storage.

        :returns: Version string
        """
        info = self.get_system_info()
        return info.get('version', 'unknown')

    def get_iscsi_iqn_prefix(self):
        """Get the iSCSI IQN prefix for this storage system.

        :returns: IQN prefix string
        """
        info = self.get_system_info()
        return info.get('iscsi_iqn_prefix', 'iqn.2004-08.com.qsan')
