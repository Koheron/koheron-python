import click

# --------------------------------------------
# Command Line Interface
# --------------------------------------------

class ConnectionType(object):
    def __init__(self, host="", unixsock=""):
        self.host = host
        self.unixsock = unixsock

@click.group()
@click.option('--host', default='', help='Host ip address', envvar='HOST')
@click.option('--unixsock', default='', help='Unix Socket path', envvar='UNIX_SOCK')
@click.pass_context
def cli(ctx, host, unixsock):
    if host != "" or unixsock != "":
        ctx.obj = ConnectionType(host=str(host), unixsock=unixsock)

@cli.command()
def version():
    """ Get the version of koheron python library."""
    from .version import __version__
    click.echo(__version__)

@cli.command()
@click.pass_obj
@click.argument('cmd', nargs=1)
@click.argument('args', nargs=-1, type=click.INT)
def common(conn_type, cmd, args):
    """ Call the common commands."""
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    from .common import Common
    driver = Common(client)
    func = getattr(driver, cmd, None)
    if func:
        click.echo(func(*args))
    else:
        click.echo('Command "{}" does not exist'.format(cmd))

@cli.command()
@click.pass_obj
def devices(conn_type):
    """ Get the list of devices."""
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    click.echo(client.devices_idx)

@cli.command()
@click.pass_obj
@click.option('--device', default=None)
def commands(conn_type, device):
    """ Get the list of commands for a specified device."""
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    if device is None:
        click.echo(client.commands)
    else:
        device_idx = client.devices_idx[device]
        click.echo(client.commands[device_idx])

# Commands that call the HTTP API:

@cli.command()
@click.pass_obj
def live(conn_type):
    """Get name and version of live instrument"""
    from .koheron import live_instrument
    name, version = live_instrument(conn_type.host)
    click.echo('{}-{}'.format(name, version))

@cli.command()
@click.pass_obj
@click.argument('instrument_zip')
@click.option('--run', is_flag=True)
def upload(conn_type, instrument_zip, run):
    """Upload instrument.zip"""
    from .koheron import upload_instrument
    upload_instrument(conn_type.host, instrument_zip, run=run)

@cli.command()
@click.pass_obj
@click.argument('instrument_name', required=False)
@click.argument('instrument_version', required=False)
@click.option('--restart', is_flag=True)
def run(conn_type, instrument_name, instrument_version, restart):
    """Run a given instrument."""
    from .koheron import run_instrument
    run_instrument(conn_type.host, instrument_name, instrument_version, restart=restart)
