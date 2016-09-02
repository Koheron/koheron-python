import click

# --------------------------------------------
# CLI
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
    from .version import __version__
    click.echo(__version__)

@cli.command()
@click.pass_obj
@click.argument('cmd', nargs=1)
@click.argument('args', nargs=-1, type=click.INT)
def common(conn_type, cmd, args):
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
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    click.echo(client.devices_idx)

@cli.command()
@click.pass_obj
@click.option('--device', default=None)
def commands(conn_type, device):
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    if device is None:
        click.echo(client.commands)
    else:
        device_idx = client.devices_idx[device]
        click.echo(client.commands[device_idx])

@cli.command()
@click.pass_obj
@click.argument('instrument_name')
@click.option('--always_restart', is_flag=True)
def install(conn_type, instrument_name, always_restart):
    from .koheron import install_instrument
    install_instrument(conn_type.host, instrument_name, always_restart=always_restart)
