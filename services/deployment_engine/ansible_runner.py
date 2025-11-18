"""
Ansible integration for patch deployment
"""

from typing import Dict, Any, List, Optional
import tempfile
import os
import subprocess
import yaml
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()


class AnsibleRunner:
    """
    Runs Ansible playbooks for patch deployment
    """

    def __init__(self, inventory_path: Optional[str] = None):
        """
        Initialize Ansible runner

        Args:
            inventory_path: Path to Ansible inventory file
        """
        self.inventory_path = inventory_path
        self.temp_files = []

    def create_playbook(
        self,
        patch_script: str,
        rollback_script: str,
        validation_script: Optional[str] = None,
        hosts: str = "all",
        become: bool = True,
    ) -> str:
        """
        Create Ansible playbook for patch deployment

        Args:
            patch_script: Patch script content
            rollback_script: Rollback script content
            validation_script: Optional validation script
            hosts: Target hosts pattern
            become: Use sudo

        Returns:
            Path to playbook file
        """
        logger.info("creating_ansible_playbook", hosts=hosts)

        playbook = {
            "name": "VulnZero Patch Deployment",
            "hosts": hosts,
            "become": become,
            "gather_facts": True,
            "vars": {
                "patch_script_path": "/tmp/vulnzero_patch.sh",
                "rollback_script_path": "/tmp/vulnzero_rollback.sh",
                "validation_script_path": "/tmp/vulnzero_validate.sh",
            },
            "tasks": [],
        }

        # Task 1: Copy patch script
        playbook["tasks"].append({
            "name": "Copy patch script to target",
            "copy": {
                "content": patch_script,
                "dest": "{{ patch_script_path }}",
                "mode": "0755",
            },
        })

        # Task 2: Copy rollback script
        playbook["tasks"].append({
            "name": "Copy rollback script to target",
            "copy": {
                "content": rollback_script,
                "dest": "{{ rollback_script_path }}",
                "mode": "0755",
            },
        })

        # Task 3: Copy validation script if provided
        if validation_script:
            playbook["tasks"].append({
                "name": "Copy validation script to target",
                "copy": {
                    "content": validation_script,
                    "dest": "{{ validation_script_path }}",
                    "mode": "0755",
                },
            })

        # Task 4: Execute patch script
        playbook["tasks"].append({
            "name": "Execute patch script",
            "shell": "{{ patch_script_path }}",
            "register": "patch_result",
            "ignore_errors": True,
        })

        # Task 5: Execute validation if provided
        if validation_script:
            playbook["tasks"].append({
                "name": "Execute validation script",
                "shell": "{{ validation_script_path }}",
                "register": "validation_result",
                "ignore_errors": True,
                "when": "patch_result.rc == 0",
            })

        # Task 6: Rollback on failure
        playbook["tasks"].append({
            "name": "Execute rollback on failure",
            "shell": "{{ rollback_script_path }}",
            "register": "rollback_result",
            "when": "patch_result.rc != 0",
        })

        # Task 7: Cleanup
        playbook["tasks"].append({
            "name": "Cleanup temporary scripts",
            "file": {
                "path": "{{ item }}",
                "state": "absent",
            },
            "loop": [
                "{{ patch_script_path }}",
                "{{ rollback_script_path }}",
                "{{ validation_script_path }}",
            ],
        })

        # Write playbook to temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False,
        )
        yaml.dump([playbook], temp_file, default_flow_style=False)
        temp_file.close()

        self.temp_files.append(temp_file.name)

        logger.info("ansible_playbook_created", path=temp_file.name)
        return temp_file.name

    def create_inventory(
        self,
        assets: List[Dict[str, Any]],
    ) -> str:
        """
        Create Ansible inventory from assets

        Args:
            assets: List of asset dictionaries

        Returns:
            Path to inventory file
        """
        logger.info("creating_ansible_inventory", asset_count=len(assets))

        inventory = {
            "all": {
                "hosts": {},
                "vars": {
                    "ansible_python_interpreter": "/usr/bin/python3",
                },
            },
        }

        for asset in assets:
            host_vars = {
                "ansible_host": asset.get("ip_address"),
            }

            # Add SSH connection details if provided
            if asset.get("ssh_user"):
                host_vars["ansible_user"] = asset["ssh_user"]
            if asset.get("ssh_port"):
                host_vars["ansible_port"] = asset["ssh_port"]
            if asset.get("ssh_key"):
                host_vars["ansible_ssh_private_key_file"] = asset["ssh_key"]

            inventory["all"]["hosts"][asset["name"]] = host_vars

        # Write inventory to temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False,
        )
        yaml.dump(inventory, temp_file, default_flow_style=False)
        temp_file.close()

        self.temp_files.append(temp_file.name)

        logger.info("ansible_inventory_created", path=temp_file.name)
        return temp_file.name

    def run_playbook(
        self,
        playbook_path: str,
        inventory_path: Optional[str] = None,
        extra_vars: Optional[Dict[str, Any]] = None,
        limit: Optional[str] = None,
        check_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Run Ansible playbook

        Args:
            playbook_path: Path to playbook file
            inventory_path: Path to inventory file
            extra_vars: Extra variables
            limit: Limit execution to specific hosts
            check_mode: Run in check mode (dry-run)

        Returns:
            Execution results
        """
        logger.info(
            "running_ansible_playbook",
            playbook=playbook_path,
            check_mode=check_mode,
        )

        # Build ansible-playbook command
        cmd = ["ansible-playbook", playbook_path]

        # Add inventory
        if inventory_path:
            cmd.extend(["-i", inventory_path])
        elif self.inventory_path:
            cmd.extend(["-i", self.inventory_path])

        # Add extra vars
        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])

        # Add limit
        if limit:
            cmd.extend(["--limit", limit])

        # Add check mode
        if check_mode:
            cmd.append("--check")

        # Add JSON output
        cmd.extend(["-v"])

        try:
            # Run ansible-playbook
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            logger.info(
                "ansible_playbook_completed",
                return_code=result.returncode,
            )

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output": self._parse_ansible_output(result.stdout),
            }

        except subprocess.TimeoutExpired:
            logger.error("ansible_playbook_timeout")
            return {
                "success": False,
                "error": "Playbook execution timeout",
            }
        except Exception as e:
            logger.error("ansible_playbook_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    def _parse_ansible_output(self, output: str) -> Dict[str, Any]:
        """
        Parse Ansible output

        Args:
            output: Ansible output string

        Returns:
            Parsed results
        """
        result = {
            "plays": [],
            "stats": {},
        }

        # Basic parsing - could be enhanced
        lines = output.split('\n')

        for line in lines:
            # Look for PLAY RECAP
            if "PLAY RECAP" in line:
                # Next lines contain stats
                continue

            # Parse task results
            if "ok=" in line or "changed=" in line or "failed=" in line:
                parts = line.split()
                if len(parts) > 0:
                    host = parts[0]
                    stats = {}
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=')
                            stats[key] = int(value)
                    result["stats"][host] = stats

        return result

    def deploy_to_asset(
        self,
        asset: Dict[str, Any],
        patch_script: str,
        rollback_script: str,
        validation_script: Optional[str] = None,
        check_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Deploy patch to a single asset

        Args:
            asset: Asset information
            patch_script: Patch script
            rollback_script: Rollback script
            validation_script: Optional validation script
            check_mode: Dry-run mode

        Returns:
            Deployment results
        """
        logger.info("deploying_to_asset", asset_name=asset.get("name"))

        try:
            # Create inventory for single asset
            inventory_path = self.create_inventory([asset])

            # Create playbook
            playbook_path = self.create_playbook(
                patch_script,
                rollback_script,
                validation_script,
                hosts="all",
            )

            # Run playbook
            result = self.run_playbook(
                playbook_path,
                inventory_path,
                check_mode=check_mode,
            )

            return result

        except Exception as e:
            logger.error("deployment_failed", error=str(e), asset=asset.get("name"))
            return {
                "success": False,
                "error": str(e),
            }

    def deploy_to_multiple_assets(
        self,
        assets: List[Dict[str, Any]],
        patch_script: str,
        rollback_script: str,
        validation_script: Optional[str] = None,
        strategy: str = "linear",
        serial: int = 1,
    ) -> Dict[str, Any]:
        """
        Deploy patch to multiple assets

        Args:
            assets: List of assets
            patch_script: Patch script
            rollback_script: Rollback script
            validation_script: Optional validation script
            strategy: Ansible strategy (linear, free)
            serial: Number of hosts to run at once

        Returns:
            Deployment results
        """
        logger.info(
            "deploying_to_multiple_assets",
            asset_count=len(assets),
            strategy=strategy,
        )

        try:
            # Create inventory
            inventory_path = self.create_inventory(assets)

            # Create playbook
            playbook_path = self.create_playbook(
                patch_script,
                rollback_script,
                validation_script,
            )

            # Run playbook with strategy
            extra_vars = {
                "strategy": strategy,
                "serial": serial,
            }

            result = self.run_playbook(
                playbook_path,
                inventory_path,
                extra_vars=extra_vars,
            )

            return result

        except Exception as e:
            logger.error("batch_deployment_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    def check_connectivity(self, assets: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Check connectivity to assets

        Args:
            assets: List of assets

        Returns:
            Dictionary mapping asset names to connectivity status
        """
        logger.info("checking_connectivity", asset_count=len(assets))

        # Create simple ping playbook
        playbook = [{
            "name": "VulnZero Connectivity Check",
            "hosts": "all",
            "gather_facts": False,
            "tasks": [{
                "name": "Ping host",
                "ping": {},
            }],
        }]

        # Write playbook
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        yaml.dump(playbook, temp_file, default_flow_style=False)
        temp_file.close()
        self.temp_files.append(temp_file.name)

        # Create inventory
        inventory_path = self.create_inventory(assets)

        # Run playbook
        result = self.run_playbook(temp_file.name, inventory_path)

        # Parse results
        connectivity = {}
        if result.get("success"):
            stats = result.get("output", {}).get("stats", {})
            for asset in assets:
                asset_name = asset["name"]
                asset_stats = stats.get(asset_name, {})
                # Check if ping was successful (ok >= 1)
                connectivity[asset_name] = asset_stats.get("ok", 0) >= 1
        else:
            # All failed
            for asset in assets:
                connectivity[asset["name"]] = False

        logger.info("connectivity_check_complete", reachable=sum(connectivity.values()))
        return connectivity

    def cleanup(self):
        """Cleanup temporary files"""
        logger.info("cleaning_up_ansible_files", count=len(self.temp_files))

        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning("failed_to_delete_temp_file", file=temp_file, error=str(e))

        self.temp_files = []

    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()
