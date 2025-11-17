"""VulnZero CLI tool."""
import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """
    VulnZero - Autonomous Vulnerability Remediation Platform.

    Zero-Touch Vulnerability Remediation. Zero Days of Exposure.
    """
    pass


@main.command()
def init() -> None:
    """Initialize VulnZero database and configuration."""
    console.print("[bold green]Initializing VulnZero...[/bold green]")

    try:
        from vulnzero.shared.models import init_db

        init_db()
        console.print("[green]✓[/green] Database initialized successfully")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize database: {e}")
        raise click.Abort()


@main.command()
@click.argument("cve_id")
@click.option("--os-type", default="ubuntu", help="Operating system type")
@click.option("--os-version", default="22.04", help="Operating system version")
@click.option("--output", "-o", type=click.Path(), help="Output file for generated patch")
@click.option("--save-db", is_flag=True, help="Save patch to database")
def generate_patch(cve_id: str, os_type: str, os_version: str, output: str, save_db: bool) -> None:
    """
    Generate a patch for a specific CVE.

    Example: vulnzero generate-patch CVE-2024-1234 --os-type ubuntu --os-version 22.04
    """
    from rich.panel import Panel
    from rich.syntax import Syntax

    from vulnzero.services.patch_generator import PatchGenerator
    from vulnzero.shared.models import Vulnerability

    console.print(f"[bold blue]Generating patch for {cve_id}...[/bold blue]")
    console.print(f"Target OS: {os_type} {os_version}\n")

    try:
        # Create a temporary vulnerability object for generation
        vuln = Vulnerability(
            cve_id=cve_id,
            title=f"Vulnerability {cve_id}",
            description="Fetching from NVD...",
            severity="unknown",
        )

        # Generate patch
        with console.status("[bold green]Generating patch with AI..."):
            generator = PatchGenerator()
            result = generator.generate_patch(
                vulnerability=vuln, os_type=os_type, os_version=os_version
            )

        if not result.success:
            console.print(f"[red]✗[/red] {result.error_message}")
            raise click.Abort()

        # Display CVE information
        if result.cve_data:
            console.print(Panel(
                f"[bold]CVE ID:[/bold] {result.cve_data.cve_id}\n"
                f"[bold]Severity:[/bold] {result.cve_data.severity.upper()}\n"
                f"[bold]CVSS Score:[/bold] {result.cve_data.cvss_score or 'N/A'}\n"
                f"[bold]Description:[/bold] {result.cve_data.description[:200]}...",
                title="[bold cyan]CVE Information[/bold cyan]",
            ))

        # Display validation results
        val_result = result.validation_result
        if val_result:
            status_icon = "[green]✓[/green]" if val_result.is_valid else "[red]✗[/red]"
            console.print(f"\n{status_icon} [bold]Validation Results:[/bold]")
            console.print(f"  Safety Score: {val_result.safety_score:.2%}")
            console.print(f"  Syntax Valid: {'✓' if val_result.syntax_valid else '✗'}")
            console.print(f"  Issues Found: {len(val_result.issues)}")
            console.print(f"  Confidence: {result.patch.confidence_score:.2%}")

            if val_result.issues:
                console.print("\n[yellow]Issues:[/yellow]")
                for issue in val_result.issues[:5]:  # Show first 5
                    console.print(f"  [{issue.severity.upper()}] {issue.description}")

        # Display the generated patch
        console.print("\n[bold cyan]Generated Patch:[/bold cyan]")
        syntax = Syntax(result.patch.patch_content, "bash", theme="monokai", line_numbers=True)
        console.print(syntax)

        # Save to file if requested
        if output:
            with open(output, "w") as f:
                f.write(result.patch.patch_content)
            console.print(f"\n[green]✓[/green] Patch saved to {output}")

        # Save to database if requested
        if save_db:
            try:
                from vulnzero.services.patch_generator.storage import PatchStorageService
                from vulnzero.shared.models import get_db

                db = next(get_db())
                storage = PatchStorageService(db)

                # Create/update vulnerability
                vuln_data = {
                    "cve_id": result.cve_data.cve_id,
                    "title": f"Vulnerability {result.cve_data.cve_id}",
                    "description": result.cve_data.description,
                    "severity": result.cve_data.severity,
                    "cvss_score": result.cve_data.cvss_score,
                    "cvss_vector": result.cve_data.cvss_vector,
                }
                stored_vuln = storage.create_or_update_vulnerability(vuln_data)

                # Save patch
                result.patch.vulnerability_id = stored_vuln.id
                saved_patch = storage.save_patch(result.patch, stored_vuln)

                console.print(f"\n[green]✓[/green] Saved to database:")
                console.print(f"  Vulnerability ID: {stored_vuln.id}")
                console.print(f"  Patch ID: {saved_patch.patch_id}")

            except Exception as e:
                console.print(f"\n[red]✗[/red] Failed to save to database: {e}")

        # Show recommendations
        if val_result and val_result.recommendations:
            console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in val_result.recommendations[:3]:
                console.print(f"  • {rec}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@main.command()
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low", "all"]), default="all")
@click.option("--status", type=click.Choice(["new", "remediated", "failed", "all"]), default="all")
@click.option("--limit", default=20, help="Number of vulnerabilities to display")
def list_vulns(severity: str, status: str, limit: int) -> None:
    """List vulnerabilities in the database."""
    from vulnzero.shared.models import Vulnerability, get_db

    console.print("[bold blue]Listing vulnerabilities...[/bold blue]\n")

    try:
        db = next(get_db())
        query = db.query(Vulnerability)

        # Filter by severity
        if severity != "all":
            query = query.filter(Vulnerability.severity == severity)

        # Filter by status
        if status != "all":
            query = query.filter(Vulnerability.status == status)

        vulns = query.order_by(Vulnerability.discovered_at.desc()).limit(limit).all()

        if not vulns:
            console.print("[yellow]No vulnerabilities found in database[/yellow]")
            console.print("[dim]Use 'vulnzero generate-patch CVE-ID --save-db' to add vulnerabilities[/dim]")
            return

        table = Table(title=f"Vulnerabilities (showing {len(vulns)})")
        table.add_column("CVE ID", style="cyan")
        table.add_column("Severity", style="magenta")
        table.add_column("CVSS", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Patches", style="blue")

        for vuln in vulns:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(vuln.severity, "⚪")

            table.add_row(
                vuln.cve_id,
                f"{severity_emoji} {vuln.severity.upper()}",
                f"{vuln.cvss_score:.1f}" if vuln.cvss_score else "N/A",
                vuln.status,
                str(len(vuln.patches)),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@main.command()
@click.argument("asset_hostname")
@click.option("--os-type", required=True, help="Operating system type")
@click.option("--os-version", required=True, help="Operating system version")
@click.option("--ip-address", help="IP address")
def register_asset(asset_hostname: str, os_type: str, os_version: str, ip_address: str) -> None:
    """
    Register a new asset (server/container) to monitor.

    Example: vulnzero register-asset web-server-01 --os-type ubuntu --os-version 22.04 --ip-address 10.0.1.5
    """
    console.print(f"[bold green]Registering asset: {asset_hostname}[/bold green]")

    # TODO: Save to database
    console.print("[yellow]⚠[/yellow] Asset registration not yet implemented")


@main.command()
def stats() -> None:
    """Show VulnZero statistics and dashboard."""
    from vulnzero.services.patch_generator.storage import PatchStorageService
    from vulnzero.shared.models import Vulnerability, get_db

    console.print("[bold cyan]VulnZero Statistics[/bold cyan]\n")

    try:
        db = next(get_db())
        storage = PatchStorageService(db)

        # Get vulnerability counts
        total_vulns = db.query(Vulnerability).count()
        critical = db.query(Vulnerability).filter(Vulnerability.severity == "critical").count()
        high = db.query(Vulnerability).filter(Vulnerability.severity == "high").count()
        medium = db.query(Vulnerability).filter(Vulnerability.severity == "medium").count()

        # Get patch statistics
        patch_stats = storage.get_statistics()

        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Total Vulnerabilities", str(total_vulns))
        stats_table.add_row("  Critical", f"🔴 {critical}")
        stats_table.add_row("  High", f"🟠 {high}")
        stats_table.add_row("  Medium", f"🟡 {medium}")
        stats_table.add_row("", "")
        stats_table.add_row("Total Patches Generated", str(patch_stats["total_patches"]))
        stats_table.add_row("  Approved", f"✓ {patch_stats['approved']}")
        stats_table.add_row("  Pending Review", f"⏳ {patch_stats['pending_review']}")
        stats_table.add_row("  Rejected", f"✗ {patch_stats['rejected']}")
        stats_table.add_row("", "")
        stats_table.add_row(
            "Average Confidence", f"{patch_stats['average_confidence']:.1%}"
        )
        stats_table.add_row("Approval Rate", f"{patch_stats['approval_rate']:.1%}")

        console.print(stats_table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        console.print("[dim]Make sure database is initialized: vulnzero init[/dim]")


@main.command()
@click.option("--status", type=click.Choice(["all", "pending", "approved", "rejected"]), default="all")
@click.option("--limit", default=20, help="Number of patches to display")
def list_patches(status: str, limit: int) -> None:
    """List generated patches."""
    from vulnzero.services.patch_generator.storage import PatchStorageService
    from vulnzero.shared.models import Patch, PatchStatus, get_db

    console.print("[bold blue]Listing patches...[/bold blue]\n")

    try:
        db = next(get_db())
        storage = PatchStorageService(db)

        if status == "all":
            patches = storage.get_recent_patches(limit)
        elif status == "pending":
            patches = storage.get_patches_by_status(PatchStatus.GENERATED, limit)
        elif status == "approved":
            patches = storage.get_patches_by_status(PatchStatus.APPROVED, limit)
        elif status == "rejected":
            patches = storage.get_patches_by_status(PatchStatus.REJECTED, limit)

        if not patches:
            console.print("[yellow]No patches found[/yellow]")
            return

        table = Table(title=f"Patches (showing {len(patches)})")
        table.add_column("Patch ID", style="cyan")
        table.add_column("CVE", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Confidence", style="magenta")
        table.add_column("Created", style="dim")

        for patch in patches:
            status_icon = {
                "generated": "⏳",
                "approved": "✓",
                "rejected": "✗",
                "test_passed": "🧪",
            }.get(patch.status, "")

            table.add_row(
                patch.patch_id,
                patch.vulnerability.cve_id if patch.vulnerability else "N/A",
                f"{status_icon} {patch.status}",
                f"{patch.confidence_score:.0%}",
                patch.created_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@main.command()
@click.argument("patch_id")
def view_patch(patch_id: str) -> None:
    """
    View detailed information about a patch.

    Example: vulnzero view-patch patch_abc123
    """
    from rich.panel import Panel
    from rich.syntax import Syntax

    from vulnzero.services.patch_generator.storage import PatchStorageService
    from vulnzero.shared.models import get_db

    try:
        db = next(get_db())
        storage = PatchStorageService(db)
        patch = storage.get_patch_by_id(patch_id)

        if not patch:
            console.print(f"[red]✗[/red] Patch {patch_id} not found")
            return

        # Display patch information
        console.print(
            Panel(
                f"[bold]Patch ID:[/bold] {patch.patch_id}\n"
                f"[bold]CVE:[/bold] {patch.vulnerability.cve_id if patch.vulnerability else 'N/A'}\n"
                f"[bold]Status:[/bold] {patch.status}\n"
                f"[bold]Confidence:[/bold] {patch.confidence_score:.2%}\n"
                f"[bold]LLM Model:[/bold] {patch.llm_model or 'N/A'}\n"
                f"[bold]Created:[/bold] {patch.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                title="[bold cyan]Patch Information[/bold cyan]",
            )
        )

        # Display patch content
        console.print("\n[bold cyan]Patch Script:[/bold cyan]")
        syntax = Syntax(patch.patch_content, "bash", theme="monokai", line_numbers=True)
        console.print(syntax)

        # Display rollback script if available
        if patch.rollback_script:
            console.print("\n[bold yellow]Rollback Script:[/bold yellow]")
            rollback_syntax = Syntax(
                patch.rollback_script, "bash", theme="monokai", line_numbers=True
            )
            console.print(rollback_syntax)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@main.command()
@click.argument("patch_id")
@click.option("--approver", default="cli-user", help="Name of approver")
def approve_patch(patch_id: str, approver: str) -> None:
    """
    Approve a patch for deployment.

    Example: vulnzero approve-patch patch_abc123 --approver john.doe
    """
    from vulnzero.services.patch_generator.storage import PatchStorageService
    from vulnzero.shared.models import get_db

    try:
        db = next(get_db())
        storage = PatchStorageService(db)
        patch = storage.approve_patch(patch_id, approver)

        console.print(f"[green]✓[/green] Patch {patch_id} approved by {approver}")
        console.print(f"  Status: {patch.status}")
        console.print(f"  Approved at: {patch.approved_at}")

    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@main.command()
@click.argument("patch_id")
@click.option("--reason", prompt=True, help="Reason for rejection")
@click.option("--rejector", default="cli-user", help="Name of rejector")
def reject_patch(patch_id: str, reason: str, rejector: str) -> None:
    """
    Reject a patch.

    Example: vulnzero reject-patch patch_abc123 --reason "Safety concerns"
    """
    from vulnzero.services.patch_generator.storage import PatchStorageService
    from vulnzero.shared.models import get_db

    try:
        db = next(get_db())
        storage = PatchStorageService(db)
        patch = storage.reject_patch(patch_id, rejector, reason)

        console.print(f"[yellow]✗[/yellow] Patch {patch_id} rejected by {rejector}")
        console.print(f"  Reason: {reason}")
        console.print(f"  Status: {patch.status}")

    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@main.command()
@click.argument("patch_id")
def test_patch(patch_id: str) -> None:
    """
    Test a patch in a digital twin environment.

    Example: vulnzero test-patch patch_abc123
    """
    console.print(f"[bold blue]Testing patch {patch_id}...[/bold blue]")

    # TODO: Implement digital twin testing
    console.print("[yellow]⚠[/yellow] Digital twin testing not yet implemented")
    console.print("[dim]This will spin up Docker containers to test patches safely[/dim]")


@main.command()
@click.argument("deployment_id")
def rollback(deployment_id: str) -> None:
    """
    Rollback a deployment.

    Example: vulnzero rollback deployment_xyz789
    """
    console.print(f"[bold red]Rolling back deployment {deployment_id}...[/bold red]")

    # TODO: Implement rollback
    console.print("[yellow]⚠[/yellow] Rollback not yet implemented")


@main.command()
def check_health() -> None:
    """Check health of VulnZero services."""
    console.print("[bold cyan]Checking VulnZero health...[/bold cyan]\n")

    health_table = Table(show_header=True, box=None)
    health_table.add_column("Service", style="bold")
    health_table.add_column("Status")

    # TODO: Implement actual health checks
    services = [
        ("Database", "❓ Not checked"),
        ("Redis", "❓ Not checked"),
        ("API Gateway", "❓ Not checked"),
        ("Celery Worker", "❓ Not checked"),
    ]

    for service, status in services:
        health_table.add_row(service, status)

    console.print(health_table)


if __name__ == "__main__":
    main()
