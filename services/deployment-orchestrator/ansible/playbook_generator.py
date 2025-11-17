"""
Ansible Playbook Generator

Dynamically generates Ansible playbooks for patch deployment.
"""

import logging
from typing import Dict, Any

from shared.models import Asset, Patch

logger = logging.getLogger(__name__)


class PlaybookGenerator:
    """
    Generates Ansible playbooks dynamically based on asset and patch.
    """

    def __init__(self):
        """Initialize playbook generator"""
        self.logger = logging.getLogger(__name__)

    def generate_patch_playbook(self, asset: Asset, patch: Patch) -> str:
        """
        Generate Ansible playbook for patch deployment.

        Args:
            asset: Target asset
            patch: Patch to deploy

        Returns:
            Ansible playbook YAML content
        """
        self.logger.info(f"Generating playbook for patch {patch.id} on asset {asset.id}")

        playbook = f"""---
- name: Deploy VulnZero Patch {patch.id}
  hosts: all
  become: yes
  vars:
    patch_id: {patch.id}
    asset_id: {asset.id}
    patch_script: "{{{{ patch_script }}}}"

  tasks:
    - name: Create backup directory
      file:
        path: /var/backups/vulnzero
        state: directory
        mode: '0755'

    - name: Backup system state
      shell: |
        dpkg -l > /var/backups/vulnzero/packages_before_{{{{ patch_id }}}}_$(date +%Y%m%d_%H%M%S).txt || true
        systemctl list-units --type=service --state=running > /var/backups/vulnzero/services_before_{{{{ patch_id }}}}_$(date +%Y%m%d_%H%M%S).txt || true
      ignore_errors: yes

    - name: Copy patch script
      copy:
        src: "{{{{ patch_script }}}}"
        dest: /tmp/vulnzero_patch_{{{{ patch_id }}}}.sh
        mode: '0755'

    - name: Execute patch script
      shell: /tmp/vulnzero_patch_{{{{ patch_id }}}}.sh
      register: patch_result
      changed_when: true

    - name: Log patch execution
      lineinfile:
        path: /var/log/vulnzero_deployments.log
        line: "[{{{{ ansible_date_time.iso8601 }}}}] Patch {{{{ patch_id }}}} deployed to asset {{{{ asset_id }}}}"
        create: yes

    - name: Cleanup patch script
      file:
        path: /tmp/vulnzero_patch_{{{{ patch_id }}}}.sh
        state: absent

    - name: Display patch result
      debug:
        var: patch_result
"""

        return playbook

    def generate_health_check_playbook(self, asset: Asset) -> str:
        """
        Generate playbook for post-deployment health checks.

        Args:
            asset: Asset to check

        Returns:
            Health check playbook YAML
        """
        playbook = f"""---
- name: VulnZero Post-Deployment Health Checks
  hosts: all
  become: yes

  tasks:
    - name: Check system uptime
      command: uptime
      register: uptime_result

    - name: Check critical services
      systemd:
        name: "{{{{ item }}}}"
        state: started
      with_items:
        - ssh
        - cron
      ignore_errors: yes

    - name: Check disk space
      shell: df -h / | tail -1 | awk '{{print $5}}' | sed 's/%//'
      register: disk_usage
      failed_when: disk_usage.stdout|int > 90

    - name: Check memory usage
      shell: free | grep Mem | awk '{{print ($3/$2) * 100.0}}'
      register: mem_usage
      failed_when: mem_usage.stdout|float > 95.0

    - name: Verify network connectivity
      command: ping -c 3 8.8.8.8
      register: ping_result
      ignore_errors: yes
"""

        return playbook
