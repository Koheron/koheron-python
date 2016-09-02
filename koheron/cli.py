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
@click.argument('led_value', type=click.INT)
def set_led(conn_type, led_value):
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    from .common import Common
    driver = Common(client)
    driver.set_led(led_value)
    click.echo('Led set to %d' % led_value)

@cli.command()
@click.pass_obj
def get_led(conn_type):
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    from .common import Common
    driver = Common(client)
    click.echo(driver.get_led())

@cli.command()
@click.pass_obj
def init(conn_type):
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    from .common import Common
    driver = Common(client)
    driver.init()
