"""
Ansible Inventory Manager

Dynamically generates Ansible inventory from database assets.
"""

import logging
from typing import List, Dict, Any
from io import StringIO

from shared.models import Asset

logger = logging.getLogger(__name__)


class InventoryManager:
    """
    Generates Ansible inventory from database assets.
    """

    def __init__(self):
        """Initialize inventory manager"""
        self.logger = logging.getLogger(__name__)

    def generate_inventory(self, assets: List[Asset]) -> str:
        """
        Generate Ansible inventory INI format from assets.

        Args:
            assets: List of assets to include

        Returns:
            Inventory content in INI format
        """
        self.logger.info(f"Generating inventory for {len(assets)} assets")

        inventory = StringIO()

        # Group assets by type
        groups: Dict[str, List[Asset]] = {}
        for asset in assets:
            asset_type = asset.type or "ungrouped"
            if asset_type not in groups:
                groups[asset_type] = []
            groups[asset_type].append(asset)

        # Write inventory
        for group_name, group_assets in groups.items():
            inventory.write(f"[{group_name}]\n")
            for asset in group_assets:
                # Format: hostname ansible_host=ip ansible_user=user
                line = f"{asset.hostname}"

                if asset.ip_address:
                    line += f" ansible_host={asset.ip_address}"

                # Default to root for MVP
                line += " ansible_user=root"

                # Add asset metadata as variables
                if asset.asset_metadata:
                    if "ssh_port" in asset.asset_metadata:
                        line += f" ansible_port={asset.asset_metadata['ssh_port']}"
                    if "python_interpreter" in asset.asset_metadata:
                        line += f" ansible_python_interpreter={asset.asset_metadata['python_interpreter']}"

                inventory.write(f"{line}\n")

            inventory.write("\n")

        # Add all hosts group
        inventory.write("[all:vars]\n")
        inventory.write("ansible_connection=ssh\n")
        inventory.write("ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")

        content = inventory.getvalue()
        inventory.close()

        return content

    def generate_inventory_json(self, assets: List[Asset]) -> Dict[str, Any]:
        """
        Generate Ansible inventory in JSON format.

        Args:
            assets: List of assets

        Returns:
            Inventory as JSON dict
        """
        inventory = {
            "_meta": {
                "hostvars": {}
            }
        }

        # Group assets
        groups: Dict[str, List[str]] = {}
        for asset in assets:
            asset_type = asset.type or "ungrouped"
            if asset_type not in groups:
                groups[asset_type] = []

            groups[asset_type].append(asset.hostname)

            # Add host vars
            inventory["_meta"]["hostvars"][asset.hostname] = {
                "ansible_host": asset.ip_address or asset.hostname,
                "ansible_user": "root",
                "asset_id": asset.id,
                "asset_type": asset.type,
            }

            if asset.asset_metadata:
                if "ssh_port" in asset.asset_metadata:
                    inventory["_meta"]["hostvars"][asset.hostname]["ansible_port"] = asset.asset_metadata["ssh_port"]

        # Add groups
        for group_name, hosts in groups.items():
            inventory[group_name] = {
                "hosts": hosts
            }

        return inventory
