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

"""Unit tests for QSAN iSCSI volume driver."""

from unittest import mock

from cinder import context
from cinder import exception
from cinder.tests.unit import fake_constants as fake
from cinder.tests.unit import fake_volume
from cinder.tests.unit import test
from cinder.volume import configuration as conf
from cinder.volume.drivers.qsan import common
from cinder.volume.drivers.qsan import qsan_iscsi


# Test constants
FAKE_MANAGEMENT_IP = '192.168.1.100'
FAKE_ISCSI_PORTAL_1 = '192.168.1.101'
FAKE_ISCSI_PORTAL_2 = '192.168.1.102'
FAKE_USERNAME = 'admin'
FAKE_PASSWORD = 'password'
FAKE_POOL_NAME = 'Pool-1'
FAKE_TARGET_IQN = 'iqn.2004-08.com.qsan:target-' + fake.VOLUME_ID
FAKE_TARGET_ID = 'target-001'
FAKE_LUN_ID = 0
FAKE_INITIATOR_IQN = 'iqn.1993-08.org.debian:01:604af6a341'

FAKE_VOLUME = {
    'name': fake.VOLUME_NAME,
    'id': fake.VOLUME_ID,
    'display_name': 'fake_volume',
    'size': 10,
    'provider_location': None,
}

FAKE_VOLUME_WITH_LOCATION = {
    'name': fake.VOLUME_NAME,
    'id': fake.VOLUME_ID,
    'display_name': 'fake_volume',
    'size': 10,
    'provider_location': (
        f'{FAKE_ISCSI_PORTAL_1}:3260;{FAKE_ISCSI_PORTAL_2}:3260 '
        f'{FAKE_TARGET_IQN} {FAKE_LUN_ID}'
    ),
    'provider_auth': None,
}

FAKE_NEW_VOLUME = {
    'name': fake.VOLUME2_NAME,
    'id': fake.VOLUME2_ID,
    'display_name': 'new_fake_volume',
    'size': 10,
}

FAKE_SNAPSHOT = {
    'name': fake.SNAPSHOT_NAME,
    'id': fake.SNAPSHOT_ID,
    'volume_id': fake.VOLUME_ID,
    'volume_name': fake.VOLUME_NAME,
    'volume_size': 10,
    'display_name': 'fake_snapshot',
}

FAKE_CONNECTOR = {
    'initiator': FAKE_INITIATOR_IQN,
    'host': 'fakehost',
}


class QSANISCSIDriverTestCase(test.TestCase):
    """Test cases for QSANISCSIDriver."""

    def setUp(self):
        super(QSANISCSIDriverTestCase, self).setUp()

        self.configuration = self._create_configuration()
        self.driver = qsan_iscsi.QSANISCSIDriver(
            configuration=self.configuration)

        # Mock the QSAN client
        self.mock_client = mock.Mock(spec=common.QSANClient)
        self.driver._qsan_client = self.mock_client

        self.context = context.get_admin_context()

    def _create_configuration(self):
        """Create a mock configuration."""
        config = mock.Mock(spec=conf.Configuration)
        config.qsan_management_ip = FAKE_MANAGEMENT_IP
        config.qsan_management_port = 443
        config.qsan_management_protocol = 'https'
        config.qsan_login = FAKE_USERNAME
        config.qsan_password = FAKE_PASSWORD
        config.qsan_pool_name = FAKE_POOL_NAME
        config.qsan_ssl_verify = False
        config.qsan_api_timeout = 60
        config.qsan_retry_count = 3
        config.qsan_iscsi_portals = [FAKE_ISCSI_PORTAL_1, FAKE_ISCSI_PORTAL_2]
        config.qsan_chap_enabled = False
        config.qsan_chap_username = None
        config.qsan_chap_password = None
        config.qsan_thin_provision = True
        config.reserved_percentage = 0
        config.max_over_subscription_ratio = 1.0
        config.safe_get = mock.Mock(return_value='QSAN_iSCSI')
        return config

    def _create_volume(self, volume_id=fake.VOLUME_ID, size=10,
                       provider_location=None, provider_auth=None):
        """Create a fake volume object."""
        volume = fake_volume.fake_volume_obj(self.context)
        volume.id = volume_id
        volume.size = size
        volume.provider_location = provider_location
        volume.provider_auth = provider_auth
        return volume

    def _create_snapshot(self, snapshot_id=fake.SNAPSHOT_ID, volume=None):
        """Create a fake snapshot object."""
        if volume is None:
            volume = self._create_volume()

        snapshot = mock.Mock()
        snapshot.id = snapshot_id
        snapshot.volume = volume
        snapshot.volume_id = volume.id
        return snapshot

    # ========== Setup Tests ==========

    def test_do_setup(self):
        """Test driver do_setup."""
        with mock.patch.object(common, 'QSANClient') as mock_client_class:
            mock_client_instance = mock.Mock()
            mock_client_class.return_value = mock_client_instance

            self.driver.do_setup(self.context)

            mock_client_class.assert_called_once()
            mock_client_instance.login.assert_called_once()

    def test_do_setup_login_failure(self):
        """Test driver do_setup when login fails."""
        with mock.patch.object(common, 'QSANClient') as mock_client_class:
            mock_client_instance = mock.Mock()
            mock_client_class.return_value = mock_client_instance
            mock_client_instance.login.side_effect = (
                common.QSANApiException(message='Login failed'))

            self.assertRaises(exception.VolumeDriverException,
                              self.driver.do_setup, self.context)

    def test_check_for_setup_error(self):
        """Test check_for_setup_error with valid config."""
        self.mock_client.get_pool.return_value = {'name': FAKE_POOL_NAME}

        # Should not raise any exception
        self.driver.check_for_setup_error()

        self.mock_client.get_pool.assert_called_once_with(FAKE_POOL_NAME)

    def test_check_for_setup_error_pool_not_found(self):
        """Test check_for_setup_error when pool not found."""
        self.mock_client.get_pool.side_effect = (
            common.QSANApiException(message='Pool not found'))

        self.assertRaises(exception.VolumeDriverException,
                          self.driver.check_for_setup_error)

    def test_check_for_setup_error_missing_config(self):
        """Test check_for_setup_error with missing config."""
        self.configuration.qsan_management_ip = None

        self.assertRaises(exception.VolumeDriverException,
                          self.driver.check_for_setup_error)

    # ========== Volume Stats Tests ==========

    def test_get_volume_stats(self):
        """Test get_volume_stats."""
        self.mock_client.get_pool_stats.return_value = {
            'total_capacity': 1099511627776,  # 1 TB
            'free_capacity': 549755813888,    # 512 GB
        }

        result = self.driver.get_volume_stats(refresh=True)

        self.assertEqual('QSAN_iSCSI', result['volume_backend_name'])
        self.assertEqual('QSAN Technology, Inc.', result['vendor_name'])
        self.assertEqual('iSCSI', result['storage_protocol'])
        self.assertEqual(1024.0, result['total_capacity_gb'])
        self.assertEqual(512.0, result['free_capacity_gb'])

    def test_get_volume_stats_cached(self):
        """Test get_volume_stats returns cached stats."""
        self.driver._stats = {'cached': True}

        result = self.driver.get_volume_stats(refresh=False)

        self.assertTrue(result['cached'])
        self.mock_client.get_pool_stats.assert_not_called()

    # ========== Volume Operations Tests ==========

    def test_create_volume(self):
        """Test create_volume."""
        volume = self._create_volume()
        self.mock_client.create_volume.return_value = {'id': 'vol-001'}

        result = self.driver.create_volume(volume)

        self.assertIsNone(result)
        self.mock_client.create_volume.assert_called_once_with(
            FAKE_POOL_NAME,
            f'volume-{volume.id}',
            volume.size,
            thin=True
        )

    def test_create_volume_failure(self):
        """Test create_volume when API fails."""
        volume = self._create_volume()
        self.mock_client.create_volume.side_effect = (
            common.QSANApiException(message='Create failed'))

        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_volume, volume)

    def test_delete_volume(self):
        """Test delete_volume."""
        volume = self._create_volume()
        self.mock_client.get_volume.return_value = {'id': 'vol-001'}

        self.driver.delete_volume(volume)

        self.mock_client.delete_volume.assert_called_once_with(
            f'volume-{volume.id}')

    def test_delete_volume_not_found(self):
        """Test delete_volume when volume not found."""
        volume = self._create_volume()
        self.mock_client.get_volume.return_value = None

        # Should not raise exception
        self.driver.delete_volume(volume)

        self.mock_client.delete_volume.assert_not_called()

    def test_extend_volume(self):
        """Test extend_volume."""
        volume = self._create_volume()
        new_size = 20

        self.driver.extend_volume(volume, new_size)

        self.mock_client.extend_volume.assert_called_once_with(
            f'volume-{volume.id}', new_size)

    def test_extend_volume_failure(self):
        """Test extend_volume when API fails."""
        volume = self._create_volume()
        self.mock_client.extend_volume.side_effect = (
            common.QSANApiException(message='Extend failed'))

        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.extend_volume, volume, 20)

    # ========== iSCSI Export Tests ==========

    def test_create_export(self):
        """Test create_export."""
        volume = self._create_volume()

        self.mock_client.create_iscsi_target.return_value = {
            'id': FAKE_TARGET_ID,
            'iqn': FAKE_TARGET_IQN,
        }
        self.mock_client.map_volume_to_target.return_value = {
            'lun_id': FAKE_LUN_ID,
        }

        result = self.driver.create_export(self.context, volume, FAKE_CONNECTOR)

        self.assertIn('provider_location', result)
        self.assertIn(FAKE_TARGET_IQN, result['provider_location'])
        self.mock_client.create_iscsi_target.assert_called_once()
        self.mock_client.map_volume_to_target.assert_called_once()

    def test_create_export_with_chap(self):
        """Test create_export with CHAP authentication."""
        volume = self._create_volume()

        self.configuration.qsan_chap_enabled = True
        self.configuration.qsan_chap_username = 'chap_user'
        self.configuration.qsan_chap_password = 'chap_pass'

        self.mock_client.create_iscsi_target.return_value = {
            'id': FAKE_TARGET_ID,
            'iqn': FAKE_TARGET_IQN,
        }
        self.mock_client.map_volume_to_target.return_value = {
            'lun_id': FAKE_LUN_ID,
        }

        result = self.driver.create_export(self.context, volume, FAKE_CONNECTOR)

        self.assertIn('provider_auth', result)
        self.assertEqual('CHAP chap_user chap_pass', result['provider_auth'])
        self.mock_client.set_target_chap.assert_called_once()

    def test_remove_export(self):
        """Test remove_export."""
        volume = self._create_volume()

        self.mock_client.get_iscsi_target_by_name.return_value = {
            'id': FAKE_TARGET_ID,
        }

        self.driver.remove_export(self.context, volume)

        self.mock_client.delete_iscsi_target.assert_called_once_with(
            FAKE_TARGET_ID)

    def test_remove_export_target_not_found(self):
        """Test remove_export when target not found."""
        volume = self._create_volume()

        self.mock_client.get_iscsi_target_by_name.return_value = None

        # Should not raise exception
        self.driver.remove_export(self.context, volume)

        self.mock_client.delete_iscsi_target.assert_not_called()

    def test_initialize_connection(self):
        """Test initialize_connection."""
        volume = self._create_volume(
            provider_location=(
                f'{FAKE_ISCSI_PORTAL_1}:3260;{FAKE_ISCSI_PORTAL_2}:3260 '
                f'{FAKE_TARGET_IQN} {FAKE_LUN_ID}'
            )
        )

        self.mock_client.get_iscsi_target_by_name.return_value = {
            'id': FAKE_TARGET_ID,
        }

        result = self.driver.initialize_connection(volume, FAKE_CONNECTOR)

        self.assertEqual('iscsi', result['driver_volume_type'])
        self.assertEqual(FAKE_TARGET_IQN, result['data']['target_iqn'])
        self.assertEqual(FAKE_LUN_ID, result['data']['target_lun'])
        self.mock_client.add_initiator_to_target.assert_called_once()

    def test_initialize_connection_multipath(self):
        """Test initialize_connection with multipath."""
        volume = self._create_volume(
            provider_location=(
                f'{FAKE_ISCSI_PORTAL_1}:3260;{FAKE_ISCSI_PORTAL_2}:3260 '
                f'{FAKE_TARGET_IQN} {FAKE_LUN_ID}'
            )
        )

        self.mock_client.get_iscsi_target_by_name.return_value = {
            'id': FAKE_TARGET_ID,
        }

        result = self.driver.initialize_connection(volume, FAKE_CONNECTOR)

        # Check multipath properties
        self.assertIn('target_portals', result['data'])
        self.assertEqual(2, len(result['data']['target_portals']))

    def test_terminate_connection(self):
        """Test terminate_connection."""
        volume = self._create_volume()

        self.mock_client.get_iscsi_target_by_name.return_value = {
            'id': FAKE_TARGET_ID,
        }

        self.driver.terminate_connection(volume, FAKE_CONNECTOR)

        self.mock_client.remove_initiator_from_target.assert_called_once()

    # ========== Snapshot Tests ==========

    def test_create_snapshot(self):
        """Test create_snapshot."""
        volume = self._create_volume()
        snapshot = self._create_snapshot(volume=volume)

        self.mock_client.create_snapshot.return_value = {'id': 'snap-001'}

        self.driver.create_snapshot(snapshot)

        self.mock_client.create_snapshot.assert_called_once_with(
            f'volume-{volume.id}',
            f'snapshot-{snapshot.id}'
        )

    def test_create_snapshot_failure(self):
        """Test create_snapshot when API fails."""
        volume = self._create_volume()
        snapshot = self._create_snapshot(volume=volume)

        self.mock_client.create_snapshot.side_effect = (
            common.QSANApiException(message='Snapshot failed'))

        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_snapshot, snapshot)

    def test_delete_snapshot(self):
        """Test delete_snapshot."""
        volume = self._create_volume()
        snapshot = self._create_snapshot(volume=volume)

        self.mock_client.get_snapshot.return_value = {'id': 'snap-001'}

        self.driver.delete_snapshot(snapshot)

        self.mock_client.delete_snapshot.assert_called_once()

    def test_delete_snapshot_not_found(self):
        """Test delete_snapshot when snapshot not found."""
        volume = self._create_volume()
        snapshot = self._create_snapshot(volume=volume)

        self.mock_client.get_snapshot.return_value = None

        # Should not raise exception
        self.driver.delete_snapshot(snapshot)

        self.mock_client.delete_snapshot.assert_not_called()

    # ========== Clone Tests ==========

    def test_create_volume_from_snapshot(self):
        """Test create_volume_from_snapshot."""
        src_volume = self._create_volume()
        snapshot = self._create_snapshot(volume=src_volume)
        new_volume = self._create_volume(volume_id=fake.VOLUME2_ID)

        self.mock_client.create_volume_from_snapshot.return_value = {
            'id': 'vol-002'
        }

        result = self.driver.create_volume_from_snapshot(new_volume, snapshot)

        self.assertIsNone(result)
        self.mock_client.create_volume_from_snapshot.assert_called_once()

    def test_create_cloned_volume(self):
        """Test create_cloned_volume."""
        src_volume = self._create_volume()
        new_volume = self._create_volume(volume_id=fake.VOLUME2_ID)

        self.mock_client.clone_volume.return_value = {'id': 'vol-002'}

        result = self.driver.create_cloned_volume(new_volume, src_volume)

        self.assertIsNone(result)
        self.mock_client.clone_volume.assert_called_once()

    def test_create_cloned_volume_with_extend(self):
        """Test create_cloned_volume when new volume is larger."""
        src_volume = self._create_volume(size=10)
        new_volume = self._create_volume(volume_id=fake.VOLUME2_ID, size=20)

        self.mock_client.clone_volume.return_value = {'id': 'vol-002'}

        self.driver.create_cloned_volume(new_volume, src_volume)

        self.mock_client.clone_volume.assert_called_once()
        self.mock_client.extend_volume.assert_called_once_with(
            f'volume-{new_volume.id}', 20)

    # ========== Migration Tests ==========

    def test_migrate_volume(self):
        """Test migrate_volume returns False for host-assisted migration."""
        volume = self._create_volume()
        host = {'host': 'new_host'}

        moved, model_update = self.driver.migrate_volume(
            self.context, volume, host)

        self.assertFalse(moved)
        self.assertIsNone(model_update)

    # ========== Helper Method Tests ==========

    def test_get_volume_name(self):
        """Test _get_volume_name."""
        volume = self._create_volume()

        result = self.driver._get_volume_name(volume)

        self.assertEqual(f'volume-{volume.id}', result)

    def test_get_snapshot_name(self):
        """Test _get_snapshot_name."""
        volume = self._create_volume()
        snapshot = self._create_snapshot(volume=volume)

        result = self.driver._get_snapshot_name(snapshot)

        self.assertEqual(f'snapshot-{snapshot.id}', result)

    def test_get_target_name(self):
        """Test _get_target_name."""
        volume = self._create_volume()

        result = self.driver._get_target_name(volume)

        self.assertEqual(f'target-{volume.id}', result)

    def test_get_iscsi_portals(self):
        """Test _get_iscsi_portals."""
        result = self.driver._get_iscsi_portals()

        self.assertEqual(2, len(result))
        self.assertIn('3260', result[0])

    def test_get_iscsi_portals_fallback_to_management_ip(self):
        """Test _get_iscsi_portals falls back to management IP."""
        self.configuration.qsan_iscsi_portals = []

        result = self.driver._get_iscsi_portals()

        self.assertEqual(1, len(result))
        self.assertIn(FAKE_MANAGEMENT_IP, result[0])

    # ========== Cleanup Tests ==========

    def test_terminate(self):
        """Test terminate."""
        self.driver.terminate()

        self.mock_client.logout.assert_called_once()

    def test_terminate_logout_error(self):
        """Test terminate handles logout error gracefully."""
        self.mock_client.logout.side_effect = Exception('Logout failed')

        # Should not raise exception
        self.driver.terminate()

    # ========== Driver Options Tests ==========

    def test_get_driver_options(self):
        """Test get_driver_options returns options list."""
        options = qsan_iscsi.QSANISCSIDriver.get_driver_options()

        self.assertIsInstance(options, list)
        self.assertGreater(len(options), 0)
