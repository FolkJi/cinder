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
"""QSAN iSCSI Cinder Volume Driver.

This driver provides iSCSI-based volume management for QSAN storage systems.

Configuration example for cinder.conf:

    [qsan-iscsi]
    volume_driver = cinder.volume.drivers.qsan.qsan_iscsi.QSANISCSIDriver
    volume_backend_name = qsan-iscsi
    qsan_management_ip = 192.168.1.100
    qsan_login = admin
    qsan_password = password
    qsan_pool_name = Pool-1
    qsan_iscsi_portals = 192.168.1.101,192.168.1.102
    qsan_chap_enabled = False
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import units

from cinder import exception
from cinder.i18n import _
from cinder import interface
from cinder.volume import driver
from cinder.volume.drivers.qsan import common
from cinder.volume.drivers.qsan import options
from cinder.volume import volume_utils


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


@interface.volumedriver
class QSANISCSIDriver(driver.ISCSIDriver):
    """QSAN iSCSI driver for Cinder.

    This driver manages volumes on QSAN storage systems using iSCSI protocol.

    Version history:

    .. code-block:: none

        1.0.0 - Initial driver with basic iSCSI support
              - Create/Delete volume
              - Attach/Detach volume (iSCSI export/unexport)
              - Extend volume
              - Create/Delete snapshot
              - Create volume from snapshot
              - Clone volume
              - Copy volume to image
              - Volume migration (host assisted)

    """

    VERSION = '1.0.0'
    # Driver info for CI
    CI_WIKI_NAME = 'QSAN_CI'

    # Vendor information
    VENDOR = 'QSAN Technology, Inc.'

    def __init__(self, *args, **kwargs):
        """Initialize the QSAN iSCSI driver."""
        super(QSANISCSIDriver, self).__init__(*args, **kwargs)
        self.configuration.append_config_values(options.QSAN_OPTS)
        self._qsan_client = None
        self._stats = {}

    @classmethod
    def get_driver_options(cls):
        """Return the driver configuration options.

        :returns: List of configuration options
        """
        additional_opts = cls._get_oslo_driver_opts(
            'target_ip_address', 'target_protocol', 'target_port',
            'reserved_percentage', 'max_over_subscription_ratio')
        return options.QSAN_OPTS + additional_opts

    def do_setup(self, context):
        """Initialize the connection to QSAN storage.

        :param context: The context object
        :raises exception.VolumeDriverException: If setup fails
        """
        LOG.info("Initializing QSAN iSCSI driver...")

        # Initialize QSAN REST API client
        self._qsan_client = common.QSANClient(
            host=self.configuration.qsan_management_ip,
            port=self.configuration.qsan_management_port,
            protocol=self.configuration.qsan_management_protocol,
            username=self.configuration.qsan_login,
            password=self.configuration.qsan_password,
            ssl_verify=self.configuration.qsan_ssl_verify,
            timeout=self.configuration.qsan_api_timeout,
            retry_count=self.configuration.qsan_retry_count,
        )

        try:
            self._qsan_client.login()
            LOG.info("Successfully connected to QSAN storage at %s",
                     self.configuration.qsan_management_ip)
        except common.QSANApiException as e:
            msg = _("Failed to connect to QSAN storage: %s") % str(e)
            LOG.error(msg)
            raise exception.VolumeDriverException(message=msg)

    def check_for_setup_error(self):
        """Check for setup errors.

        Verify that the configuration is valid and the storage is accessible.

        :raises exception.VolumeDriverException: If configuration is invalid
        """
        # Verify required configuration options
        required_opts = [
            'qsan_management_ip',
            'qsan_login',
            'qsan_password',
            'qsan_pool_name',
        ]

        for opt in required_opts:
            if not getattr(self.configuration, opt, None):
                msg = _("Required configuration option '%s' is not set.") % opt
                LOG.error(msg)
                raise exception.VolumeDriverException(message=msg)

        # Verify pool exists
        pool_name = self.configuration.qsan_pool_name
        try:
            self._qsan_client.get_pool(pool_name)
            LOG.info("QSAN pool '%s' verified.", pool_name)
        except common.QSANApiException as e:
            msg = _("QSAN pool '%s' not found: %s") % (pool_name, str(e))
            LOG.error(msg)
            raise exception.VolumeDriverException(message=msg)

    def _get_volume_name(self, volume):
        """Get the QSAN volume name from Cinder volume.

        :param volume: Cinder volume object
        :returns: Volume name string
        """
        return f"volume-{volume.id}"

    def _get_snapshot_name(self, snapshot):
        """Get the QSAN snapshot name from Cinder snapshot.

        :param snapshot: Cinder snapshot object
        :returns: Snapshot name string
        """
        return f"snapshot-{snapshot.id}"

    def _get_target_name(self, volume):
        """Get the iSCSI target name for a volume.

        :param volume: Cinder volume object
        :returns: Target name string
        """
        return f"target-{volume.id}"

    def _get_iscsi_portals(self):
        """Get list of iSCSI portal addresses.

        :returns: List of portal IP:port strings
        """
        configured_portals = self.configuration.qsan_iscsi_portals
        if configured_portals:
            portals = configured_portals
        else:
            # Fall back to management IP
            portals = [self.configuration.qsan_management_ip]

        # Add default iSCSI port if not specified
        portal_list = []
        for portal in portals:
            if ':' not in portal:
                portal = f"{portal}:3260"
            portal_list.append(portal)

        return portal_list

    # ========== Volume Stats ==========

    def get_volume_stats(self, refresh=False):
        """Get volume statistics.

        :param refresh: Whether to refresh stats
        :returns: Dictionary of volume stats
        """
        if refresh or not self._stats:
            self._update_volume_stats()
        return self._stats

    def _update_volume_stats(self):
        """Update volume statistics."""
        pool_name = self.configuration.qsan_pool_name
        try:
            stats = self._qsan_client.get_pool_stats(pool_name)
            total_capacity_gb = stats['total_capacity'] / units.Gi
            free_capacity_gb = stats['free_capacity'] / units.Gi
        except common.QSANApiException:
            LOG.warning("Failed to get pool stats from QSAN storage.")
            total_capacity_gb = 0
            free_capacity_gb = 0

        backend_name = self.configuration.safe_get('volume_backend_name')

        self._stats = {
            'volume_backend_name': backend_name or 'QSAN_iSCSI',
            'vendor_name': self.VENDOR,
            'driver_version': self.VERSION,
            'storage_protocol': 'iSCSI',
            'total_capacity_gb': total_capacity_gb,
            'free_capacity_gb': free_capacity_gb,
            'reserved_percentage': self.configuration.reserved_percentage,
            'max_over_subscription_ratio': (
                self.configuration.max_over_subscription_ratio),
            'thin_provisioning_support': True,
            'thick_provisioning_support': True,
            'QoS_support': False,
            'multiattach': False,
        }

        LOG.debug("QSAN volume stats: %s", self._stats)

    # ========== Volume Operations ==========

    def create_volume(self, volume):
        """Create a volume on the QSAN storage.

        :param volume: Cinder volume object
        :returns: Dictionary with provider_location (optional)
        """
        volume_name = self._get_volume_name(volume)
        pool_name = self.configuration.qsan_pool_name
        thin = self.configuration.qsan_thin_provision

        LOG.info("Creating volume %s (size: %s GB, thin: %s)",
                 volume_name, volume.size, thin)

        try:
            self._qsan_client.create_volume(
                pool_name, volume_name, volume.size, thin=thin)
            LOG.info("Successfully created volume: %s", volume_name)
        except common.QSANApiException as e:
            msg = _("Failed to create volume %s: %s") % (volume_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

        return None

    def delete_volume(self, volume):
        """Delete a volume from the QSAN storage.

        :param volume: Cinder volume object
        """
        volume_name = self._get_volume_name(volume)

        LOG.info("Deleting volume: %s", volume_name)

        try:
            # Check if volume exists
            vol_info = self._qsan_client.get_volume(volume_name)
            if vol_info is None:
                LOG.warning("Volume %s not found, skipping delete.",
                            volume_name)
                return

            self._qsan_client.delete_volume(volume_name)
            LOG.info("Successfully deleted volume: %s", volume_name)
        except common.QSANApiException as e:
            msg = _("Failed to delete volume %s: %s") % (volume_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    def extend_volume(self, volume, new_size):
        """Extend a volume to a new size.

        :param volume: Cinder volume object
        :param new_size: New size in GB
        """
        volume_name = self._get_volume_name(volume)

        LOG.info("Extending volume %s from %s GB to %s GB",
                 volume_name, volume.size, new_size)

        try:
            self._qsan_client.extend_volume(volume_name, new_size)
            LOG.info("Successfully extended volume: %s", volume_name)
        except common.QSANApiException as e:
            msg = _("Failed to extend volume %s: %s") % (volume_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    # ========== iSCSI Export Operations ==========

    def create_export(self, context, volume, connector):
        """Create an iSCSI export for a volume.

        Creates an iSCSI target and maps the volume to it.

        :param context: Security context
        :param volume: Cinder volume object
        :param connector: Connector information
        :returns: Dictionary with provider_location and provider_auth
        """
        volume_name = self._get_volume_name(volume)
        target_name = self._get_target_name(volume)

        LOG.info("Creating iSCSI export for volume: %s", volume_name)

        try:
            # Create iSCSI target
            target_info = self._qsan_client.create_iscsi_target(target_name)
            target_id = target_info.get('id')
            target_iqn = target_info.get('iqn')

            # Map volume to target
            mapping_info = self._qsan_client.map_volume_to_target(
                volume_name, target_id)
            lun_id = mapping_info.get('lun_id', 0)

            # Set CHAP authentication if enabled
            provider_auth = None
            if self.configuration.qsan_chap_enabled:
                chap_user = self.configuration.qsan_chap_username
                chap_pass = self.configuration.qsan_chap_password
                if chap_user and chap_pass:
                    self._qsan_client.set_target_chap(
                        target_id, chap_user, chap_pass)
                    provider_auth = f"CHAP {chap_user} {chap_pass}"

            # Build provider_location
            portals = self._get_iscsi_portals()
            portal_str = ';'.join(portals)
            provider_location = f"{portal_str} {target_iqn} {lun_id}"

            LOG.info("Created iSCSI export: target=%s, lun=%s",
                     target_iqn, lun_id)

            return {
                'provider_location': provider_location,
                'provider_auth': provider_auth,
            }

        except common.QSANApiException as e:
            msg = _("Failed to create export for volume %s: %s") % (
                volume_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    def ensure_export(self, context, volume):
        """Ensure that the export exists.

        Called during service restart to recreate exports if needed.

        :param context: Security context
        :param volume: Cinder volume object
        """
        # If provider_location is set, export should still exist
        if volume.provider_location:
            LOG.debug("Export already exists for volume: %s", volume.id)
            return

        LOG.info("Recreating export for volume: %s", volume.id)
        # Recreate the export
        self.create_export(context, volume, None)

    def remove_export(self, context, volume):
        """Remove an iSCSI export for a volume.

        :param context: Security context
        :param volume: Cinder volume object
        """
        volume_name = self._get_volume_name(volume)
        target_name = self._get_target_name(volume)

        LOG.info("Removing iSCSI export for volume: %s", volume_name)

        try:
            # Find the target
            target_info = self._qsan_client.get_iscsi_target_by_name(
                target_name)
            if target_info is None:
                LOG.warning("Target %s not found, skipping removal.",
                            target_name)
                return

            target_id = target_info.get('id')

            # Delete the target (this should also unmap volumes)
            self._qsan_client.delete_iscsi_target(target_id)
            LOG.info("Successfully removed export for volume: %s", volume_name)

        except common.QSANApiException as e:
            msg = _("Failed to remove export for volume %s: %s") % (
                volume_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    def initialize_connection(self, volume, connector):
        """Initialize an iSCSI connection.

        :param volume: Cinder volume object
        :param connector: Connector information dictionary
        :returns: Connection information dictionary
        """
        LOG.debug("Initializing connection for volume %s, connector: %s",
                  volume.id, connector)

        target_name = self._get_target_name(volume)

        try:
            # Add initiator to target ACL if available
            if connector and 'initiator' in connector:
                initiator_iqn = connector['initiator']
                target_info = self._qsan_client.get_iscsi_target_by_name(
                    target_name)
                if target_info:
                    target_id = target_info.get('id')
                    try:
                        self._qsan_client.add_initiator_to_target(
                            target_id, initiator_iqn)
                        LOG.debug("Added initiator %s to target %s",
                                  initiator_iqn, target_name)
                    except common.QSANApiException:
                        # Initiator may already be in ACL
                        LOG.debug("Initiator %s may already be in ACL",
                                  initiator_iqn)

            # Get iSCSI properties
            iscsi_properties = self._get_iscsi_properties(volume)

            return {
                'driver_volume_type': 'iscsi',
                'data': iscsi_properties,
            }

        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Failed to initialize connection: %s", str(e))

    def _get_iscsi_properties(self, volume):
        """Get iSCSI connection properties for a volume.

        :param volume: Cinder volume object
        :returns: Dictionary of iSCSI properties
        """
        if not volume.provider_location:
            msg = _("Volume %s has no provider_location") % volume.id
            raise exception.VolumeBackendAPIException(data=msg)

        # Parse provider_location: "portal1;portal2 iqn lun"
        location_parts = volume.provider_location.split(' ')
        portals = location_parts[0].split(';')
        target_iqn = location_parts[1]
        target_lun = int(location_parts[2])

        properties = {
            'target_discovered': False,
            'target_iqn': target_iqn,
            'target_portal': portals[0],
            'target_lun': target_lun,
            'volume_id': volume.id,
        }

        # Add multipath info if multiple portals
        if len(portals) > 1:
            properties['target_portals'] = portals
            properties['target_iqns'] = [target_iqn] * len(portals)
            properties['target_luns'] = [target_lun] * len(portals)

        # Add CHAP authentication if configured
        if volume.provider_auth:
            auth_parts = volume.provider_auth.split(' ')
            if len(auth_parts) >= 3:
                properties['auth_method'] = auth_parts[0]
                properties['auth_username'] = auth_parts[1]
                properties['auth_password'] = auth_parts[2]

        return properties

    def terminate_connection(self, volume, connector, **kwargs):
        """Terminate an iSCSI connection.

        :param volume: Cinder volume object
        :param connector: Connector information dictionary
        """
        LOG.debug("Terminating connection for volume %s", volume.id)

        target_name = self._get_target_name(volume)

        try:
            # Remove initiator from target ACL
            if connector and 'initiator' in connector:
                initiator_iqn = connector['initiator']
                target_info = self._qsan_client.get_iscsi_target_by_name(
                    target_name)
                if target_info:
                    target_id = target_info.get('id')
                    try:
                        self._qsan_client.remove_initiator_from_target(
                            target_id, initiator_iqn)
                        LOG.debug("Removed initiator %s from target %s",
                                  initiator_iqn, target_name)
                    except common.QSANApiException:
                        LOG.debug("Failed to remove initiator, may not exist")

        except common.QSANApiException as e:
            LOG.warning("Error during terminate_connection: %s", str(e))

    # ========== Snapshot Operations ==========

    def create_snapshot(self, snapshot):
        """Create a snapshot of a volume.

        :param snapshot: Cinder snapshot object
        """
        volume_name = self._get_volume_name(snapshot.volume)
        snapshot_name = self._get_snapshot_name(snapshot)

        LOG.info("Creating snapshot %s of volume %s",
                 snapshot_name, volume_name)

        try:
            self._qsan_client.create_snapshot(volume_name, snapshot_name)
            LOG.info("Successfully created snapshot: %s", snapshot_name)
        except common.QSANApiException as e:
            msg = _("Failed to create snapshot %s: %s") % (
                snapshot_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    def delete_snapshot(self, snapshot):
        """Delete a snapshot.

        :param snapshot: Cinder snapshot object
        """
        volume_name = self._get_volume_name(snapshot.volume)
        snapshot_name = self._get_snapshot_name(snapshot)

        LOG.info("Deleting snapshot: %s", snapshot_name)

        try:
            # Check if snapshot exists
            snap_info = self._qsan_client.get_snapshot(
                volume_name, snapshot_name)
            if snap_info is None:
                LOG.warning("Snapshot %s not found, skipping delete.",
                            snapshot_name)
                return

            self._qsan_client.delete_snapshot(volume_name, snapshot_name)
            LOG.info("Successfully deleted snapshot: %s", snapshot_name)
        except common.QSANApiException as e:
            msg = _("Failed to delete snapshot %s: %s") % (
                snapshot_name, str(e))
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

    # ========== Clone Operations ==========

    def create_volume_from_snapshot(self, volume, snapshot):
        """Create a volume from a snapshot.

        :param volume: New Cinder volume object
        :param snapshot: Source Cinder snapshot object
        :returns: Dictionary with provider_location (optional)
        """
        src_volume_name = self._get_volume_name(snapshot.volume)
        snapshot_name = self._get_snapshot_name(snapshot)
        new_volume_name = self._get_volume_name(volume)

        LOG.info("Creating volume %s from snapshot %s",
                 new_volume_name, snapshot_name)

        try:
            self._qsan_client.create_volume_from_snapshot(
                src_volume_name, snapshot_name, new_volume_name,
                size_gb=volume.size)
            LOG.info("Successfully created volume %s from snapshot %s",
                     new_volume_name, snapshot_name)
        except common.QSANApiException as e:
            msg = _("Failed to create volume from snapshot: %s") % str(e)
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

        return None

    def create_cloned_volume(self, volume, src_vref):
        """Create a clone of an existing volume.

        :param volume: New Cinder volume object
        :param src_vref: Source Cinder volume reference
        :returns: Dictionary with provider_location (optional)
        """
        src_volume_name = self._get_volume_name(src_vref)
        new_volume_name = self._get_volume_name(volume)

        LOG.info("Cloning volume %s from %s", new_volume_name, src_volume_name)

        try:
            self._qsan_client.clone_volume(src_volume_name, new_volume_name)

            # Extend if new size is larger
            if volume.size > src_vref.size:
                self._qsan_client.extend_volume(new_volume_name, volume.size)

            LOG.info("Successfully cloned volume %s from %s",
                     new_volume_name, src_volume_name)
        except common.QSANApiException as e:
            msg = _("Failed to clone volume: %s") % str(e)
            LOG.error(msg)
            raise exception.VolumeBackendAPIException(data=msg)

        return None

    # ========== Migration Operations ==========

    def migrate_volume(self, context, volume, host):
        """Migrate a volume to a specified host.

        For now, this returns False to use generic host-assisted migration.

        :param context: Security context
        :param volume: Cinder volume object
        :param host: Destination host information
        :returns: Tuple of (moved, model_update)
        """
        LOG.info("Volume migration requested for %s to host %s",
                 volume.id, host)

        # Return False to let Cinder do generic migration
        # TODO: Implement storage-assisted migration if supported
        return (False, None)

    # ========== Cleanup ==========

    def terminate(self):
        """Clean up when driver is being stopped."""
        if self._qsan_client:
            try:
                self._qsan_client.logout()
            except Exception:
                LOG.warning("Error during QSAN client logout, ignoring.")
