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

"""Unit tests for QSAN common utilities."""

from unittest import mock

import requests

from cinder.tests.unit import test
from cinder.volume.drivers.qsan import common


# Test constants
FAKE_HOST = '192.168.1.100'
FAKE_PORT = 443
FAKE_PROTOCOL = 'https'
FAKE_USERNAME = 'admin'
FAKE_PASSWORD = 'password'
FAKE_TOKEN = 'fake-session-token-12345'
FAKE_POOL_NAME = 'Pool-1'
FAKE_VOLUME_NAME = 'volume-fake-id'
FAKE_SNAPSHOT_NAME = 'snapshot-fake-id'
FAKE_TARGET_NAME = 'target-fake-id'
FAKE_TARGET_ID = 'target-001'
FAKE_TARGET_IQN = 'iqn.2004-08.com.qsan:target-fake-id'
FAKE_LUN_ID = 0
FAKE_INITIATOR_IQN = 'iqn.1993-08.org.debian:01:604af6a341'


class QSANClientTestCase(test.TestCase):
    """Test cases for QSANClient."""

    def setUp(self):
        super(QSANClientTestCase, self).setUp()
        self.client = common.QSANClient(
            host=FAKE_HOST,
            port=FAKE_PORT,
            protocol=FAKE_PROTOCOL,
            username=FAKE_USERNAME,
            password=FAKE_PASSWORD,
            ssl_verify=False,
            timeout=60,
            retry_count=3,
        )

    def _mock_response(self, status_code=200, json_data=None):
        """Create a mock response object."""
        mock_resp = mock.Mock()
        mock_resp.status_code = status_code
        mock_resp.content = b'{"data": "test"}' if json_data else b''
        mock_resp.json.return_value = json_data or {}
        mock_resp.raise_for_status = mock.Mock()
        if status_code >= 400:
            mock_resp.raise_for_status.side_effect = (
                requests.exceptions.HTTPError())
        return mock_resp

    # ========== Authentication Tests ==========

    @mock.patch('requests.Session')
    def test_login_success(self, mock_session_class):
        """Test successful login."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.post.return_value = self._mock_response(
            200, {'token': FAKE_TOKEN})

        self.client.login()

        self.assertEqual(FAKE_TOKEN, self.client.session_token)
        mock_session.post.assert_called_once()

    @mock.patch('requests.Session')
    def test_login_failure(self, mock_session_class):
        """Test login failure."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.post.side_effect = requests.exceptions.RequestException(
            'Connection failed')

        self.assertRaises(common.QSANApiException, self.client.login)

    @mock.patch('requests.Session')
    def test_logout_success(self, mock_session_class):
        """Test successful logout."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        # Setup session first
        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.logout()

        self.assertIsNone(self.client.session_token)
        self.assertIsNone(self.client.session)

    def test_logout_no_session(self):
        """Test logout when no session exists."""
        # Should not raise any exception
        self.client.logout()

    # ========== Volume Operations Tests ==========

    @mock.patch('requests.Session')
    def test_create_volume(self, mock_session_class):
        """Test create volume."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': 'vol-001', 'name': FAKE_VOLUME_NAME})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.create_volume(FAKE_POOL_NAME, FAKE_VOLUME_NAME, 10)

        self.assertIsNotNone(result)
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('POST', call_args[0][0])
        self.assertIn('volumes', call_args[0][1])

    @mock.patch('requests.Session')
    def test_delete_volume(self, mock_session_class):
        """Test delete volume."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.delete_volume(FAKE_VOLUME_NAME)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('DELETE', call_args[0][0])
        self.assertIn(FAKE_VOLUME_NAME, call_args[0][1])

    @mock.patch('requests.Session')
    def test_extend_volume(self, mock_session_class):
        """Test extend volume."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.extend_volume(FAKE_VOLUME_NAME, 20)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('PUT', call_args[0][0])

    @mock.patch('requests.Session')
    def test_get_volume(self, mock_session_class):
        """Test get volume."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': 'vol-001', 'name': FAKE_VOLUME_NAME})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_volume(FAKE_VOLUME_NAME)

        self.assertIsNotNone(result)
        self.assertEqual(FAKE_VOLUME_NAME, result['name'])

    @mock.patch('requests.Session')
    def test_get_volume_not_found(self, mock_session_class):
        """Test get volume when not found."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.RequestException(
            'Not found')

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_volume(FAKE_VOLUME_NAME)

        self.assertIsNone(result)

    # ========== Snapshot Operations Tests ==========

    @mock.patch('requests.Session')
    def test_create_snapshot(self, mock_session_class):
        """Test create snapshot."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': 'snap-001', 'name': FAKE_SNAPSHOT_NAME})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.create_snapshot(FAKE_VOLUME_NAME, FAKE_SNAPSHOT_NAME)

        self.assertIsNotNone(result)
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('POST', call_args[0][0])
        self.assertIn('snapshots', call_args[0][1])

    @mock.patch('requests.Session')
    def test_delete_snapshot(self, mock_session_class):
        """Test delete snapshot."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.delete_snapshot(FAKE_VOLUME_NAME, FAKE_SNAPSHOT_NAME)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('DELETE', call_args[0][0])

    # ========== Clone Operations Tests ==========

    @mock.patch('requests.Session')
    def test_clone_volume(self, mock_session_class):
        """Test clone volume."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': 'vol-002', 'name': 'new-volume'})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.clone_volume(FAKE_VOLUME_NAME, 'new-volume')

        self.assertIsNotNone(result)
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('POST', call_args[0][0])
        self.assertIn('clone', call_args[0][1])

    @mock.patch('requests.Session')
    def test_create_volume_from_snapshot(self, mock_session_class):
        """Test create volume from snapshot."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': 'vol-002', 'name': 'new-volume'})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.create_volume_from_snapshot(
            FAKE_VOLUME_NAME, FAKE_SNAPSHOT_NAME, 'new-volume')

        self.assertIsNotNone(result)

    # ========== Pool Operations Tests ==========

    @mock.patch('requests.Session')
    def test_get_pool(self, mock_session_class):
        """Test get pool."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {
                'name': FAKE_POOL_NAME,
                'total_capacity': 1099511627776,  # 1 TB
                'free_capacity': 549755813888,    # 512 GB
            })

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_pool(FAKE_POOL_NAME)

        self.assertIsNotNone(result)
        self.assertEqual(FAKE_POOL_NAME, result['name'])

    @mock.patch('requests.Session')
    def test_get_pool_stats(self, mock_session_class):
        """Test get pool stats."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {
                'name': FAKE_POOL_NAME,
                'total_capacity': 1099511627776,
                'free_capacity': 549755813888,
                'used_capacity': 549755813888,
            })

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_pool_stats(FAKE_POOL_NAME)

        self.assertIn('total_capacity', result)
        self.assertIn('free_capacity', result)

    # ========== iSCSI Operations Tests ==========

    @mock.patch('requests.Session')
    def test_create_iscsi_target(self, mock_session_class):
        """Test create iSCSI target."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'id': FAKE_TARGET_ID, 'iqn': FAKE_TARGET_IQN})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.create_iscsi_target(FAKE_TARGET_NAME)

        self.assertIsNotNone(result)
        self.assertEqual(FAKE_TARGET_ID, result['id'])
        self.assertEqual(FAKE_TARGET_IQN, result['iqn'])

    @mock.patch('requests.Session')
    def test_delete_iscsi_target(self, mock_session_class):
        """Test delete iSCSI target."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.delete_iscsi_target(FAKE_TARGET_ID)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('DELETE', call_args[0][0])

    @mock.patch('requests.Session')
    def test_map_volume_to_target(self, mock_session_class):
        """Test map volume to target."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'lun_id': FAKE_LUN_ID})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.map_volume_to_target(
            FAKE_VOLUME_NAME, FAKE_TARGET_ID)

        self.assertIsNotNone(result)
        self.assertEqual(FAKE_LUN_ID, result['lun_id'])

    @mock.patch('requests.Session')
    def test_unmap_volume_from_target(self, mock_session_class):
        """Test unmap volume from target."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.unmap_volume_from_target(FAKE_TARGET_ID, FAKE_LUN_ID)

        mock_session.request.assert_called_once()

    @mock.patch('requests.Session')
    def test_add_initiator_to_target(self, mock_session_class):
        """Test add initiator to target ACL."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.add_initiator_to_target(FAKE_TARGET_ID, FAKE_INITIATOR_IQN)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('POST', call_args[0][0])
        self.assertIn('acl', call_args[0][1])

    @mock.patch('requests.Session')
    def test_remove_initiator_from_target(self, mock_session_class):
        """Test remove initiator from target ACL."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.remove_initiator_from_target(
            FAKE_TARGET_ID, FAKE_INITIATOR_IQN)

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual('DELETE', call_args[0][0])

    @mock.patch('requests.Session')
    def test_set_target_chap(self, mock_session_class):
        """Test set CHAP authentication for target."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(200)

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.client.set_target_chap(FAKE_TARGET_ID, 'chap_user', 'chap_pass')

        mock_session.request.assert_called_once()

    @mock.patch('requests.Session')
    def test_get_iscsi_portals(self, mock_session_class):
        """Test get iSCSI portals."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'portals': ['192.168.1.101', '192.168.1.102']})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_iscsi_portals()

        self.assertEqual(['192.168.1.101', '192.168.1.102'], result)

    # ========== System Operations Tests ==========

    @mock.patch('requests.Session')
    def test_get_system_info(self, mock_session_class):
        """Test get system info."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {
                'version': '5.0.0',
                'model': 'XCubeSAN',
                'iscsi_iqn_prefix': 'iqn.2004-08.com.qsan',
            })

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_system_info()

        self.assertIsNotNone(result)
        self.assertEqual('5.0.0', result['version'])

    @mock.patch('requests.Session')
    def test_get_system_version(self, mock_session_class):
        """Test get system version."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.return_value = self._mock_response(
            200, {'version': '5.0.0'})

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client.get_system_version()

        self.assertEqual('5.0.0', result)

    # ========== Error Handling Tests ==========

    @mock.patch('requests.Session')
    def test_request_retry_on_failure(self, mock_session_class):
        """Test request retry on transient failure."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session

        # First two calls fail, third succeeds
        mock_session.request.side_effect = [
            requests.exceptions.ConnectionError('Connection failed'),
            requests.exceptions.ConnectionError('Connection failed'),
            self._mock_response(200, {'result': 'success'}),
        ]

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        result = self.client._request('GET', 'http://test/api/test')

        self.assertEqual(3, mock_session.request.call_count)
        self.assertEqual('success', result['result'])

    @mock.patch('requests.Session')
    def test_request_max_retries_exceeded(self, mock_session_class):
        """Test request fails after max retries."""
        mock_session = mock.Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.ConnectionError(
            'Connection failed')

        self.client.session = mock_session
        self.client.session_token = FAKE_TOKEN

        self.assertRaises(
            common.QSANApiException,
            self.client._request,
            'GET',
            'http://test/api/test'
        )

        self.assertEqual(3, mock_session.request.call_count)
