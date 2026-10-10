"""Generate reviewed VPS setup/upgrade bundles without activating a remote host."""

import json
from pathlib import Path

import click
from pretty_notebook._internal.deployment import DeploySpec, bundle, write_bundle, check_deployment


def options(function):
    defaults = DeploySpec.__dataclass_fields__
    for key in reversed(('revision', 'domain', 'checkout', 'data_dir', 'env_file', 'backup_dir',
                         'tls_cert', 'tls_key', 'service', 'user', 'python', 'port', 'workers', 'prefix')):
        kwargs = {'required': True} if key in ('revision', 'domain') else {'default': defaults[key].default, 'show_default': True}
        if key in ('checkout', 'data_dir', 'env_file', 'backup_dir', 'tls_cert', 'tls_key'):
            kwargs['type'] = click.Path(path_type=Path)
        elif key in ('port', 'workers'): kwargs['type'] = int
        function = click.option('--' + key.replace('_', '-'), **kwargs)(function)
    return function


def report(action):
    try: result = action()
    except (ValueError, OSError) as error: raise click.ClickException(str(error)) from error
    click.echo(json.dumps(result, indent=2))


@click.group()
def deploy():
    """Plan Linux VPS setup, inspect local state, and prepare stopped-site upgrades."""


@deploy.command('plan')
@options
@click.option('--operation', type=click.Choice(['init', 'upgrade']), default='init')
def plan(operation, **kwargs):
    """Print an inspectable service/proxy/environment/script plan; write nothing."""
    report(lambda: json.loads(bundle(DeploySpec(**kwargs), operation)['plan.json']))


@deploy.command('init')
@options
@click.option('--output', type=click.Path(path_type=Path, file_okay=False), required=True)
def initialize(output, **kwargs):
    """Write an idempotent setup bundle; secrets and live services remain untouched."""
    report(lambda: write_bundle(DeploySpec(**kwargs), output))


@deploy.command('upgrade')
@options
@click.option('--output', type=click.Path(path_type=Path, file_okay=False), required=True)
def upgrade(output, **kwargs):
    """Write a pinned upgrade and rollback bundle with a stopped-state checkpoint."""
    report(lambda: write_bundle(DeploySpec(**kwargs), output, operation='upgrade'))


@deploy.command('check')
@options
@click.option('--health', is_flag=True, help='Also check the planned loopback health endpoint.')
@click.option('--require-bootstrap', is_flag=True, help='Require an initial owner-claim secret.')
def check(health, require_bootstrap, **kwargs):
    """Check private configuration, revision, dependencies, local assets and health."""
    report(lambda: check_deployment(DeploySpec(**kwargs), health=health, require_bootstrap=require_bootstrap))
