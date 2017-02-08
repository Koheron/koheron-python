import click

# --------------------------------------------
# Call koheron-server
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
    ''' Get the version of koheron python library '''
    from .version import __version__
    click.echo(__version__)

@cli.command()
@click.pass_obj
@click.argument('cmd', nargs=1)
@click.argument('args', nargs=-1, type=click.INT)
def common(conn_type, cmd, args):
    ''' Call the common commands '''
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
    ''' Get the list of devices '''
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    click.echo(client.devices_idx)

@cli.command()
@click.pass_obj
@click.option('--device', default=None)
def commands(conn_type, device):
    ''' Get the list of commands for a specified device '''
    from .koheron import KoheronClient
    client = KoheronClient(host=conn_type.host, unixsock=conn_type.unixsock)
    if device is None:
        click.echo(client.commands)
    else:
        device_idx = client.devices_idx[device]
        click.echo(client.commands[device_idx])

# --------------------------------------------
# Call HTTP API
# --------------------------------------------

@cli.command()
@click.pass_obj
def live(conn_type):
    ''' Get name and version of live instrument '''
    from .koheron import live_instrument
    name, version = live_instrument(conn_type.host)
    click.echo('{}-{}'.format(name, version))

@cli.command()
@click.pass_obj
@click.argument('instrument_zip')
@click.option('--run', is_flag=True)
def upload(conn_type, instrument_zip, run):
    ''' Upload instrument.zip '''
    from .koheron import upload_instrument
    upload_instrument(conn_type.host, instrument_zip, run=run)

@cli.command()
@click.pass_obj
@click.argument('instrument_zip')
@click.option('--run', is_flag=True)
def update(conn_type, instrument_zip, run):
    ''' Update instrument.zip '''
    from .koheron import update_instrument
    update_instrument(conn_type.host, instrument_zip, run=run)

@cli.command()
@click.pass_obj
@click.argument('instrument_name', required=False)
@click.argument('instrument_version', required=False)
@click.option('--restart', is_flag=True)
def run(conn_type, instrument_name, instrument_version, restart):
    ''' Run a given instrument '''
    from .koheron import run_instrument
    run_instrument(conn_type.host, instrument_name, instrument_version, restart=restart)

# --------------------------------------------
# Call koheron-sdk
# --------------------------------------------

class SDK(object):
    def __init__(self, version, path, host):
        self.version = version
        self.path = path
        self.host = host

@click.group()
@click.option('--version', default='v0.13.0', help='SDK version.', envvar='KOHERON_SDK_VERSION')
@click.option('--path', default='/tmp/koheron', help='SDK installation path.', envvar='KOHERON_SDK_PATH')
@click.option('--host', default='', help='Host ip address.', envvar='KOHERON_SDK_PATH')
@click.pass_context
def sdk(ctx, version, path, host):
    ctx.obj = SDK(version, path, host)

@sdk.command()
@click.pass_obj
def install(sdk):
    ''' Install Koheron SDK '''
    import os
    import subprocess
    import zipfile
    import shutil

    if os.path.exists(sdk.path):
        shutil.rmtree(sdk.path)

    # subprocess.call(['/usr/bin/git', 'clone', '--branch', sdk.version,
    #                  'https://github.com/Koheron/koheron-sdk.git', sdk.path])

    tmp_zip = '/tmp/koheron-sdk.zip'
    tmp_sdk = '/tmp/koheron-sdk-tmp'

    subprocess.call(['/usr/bin/curl', '-L', '-o', tmp_zip, 'http://github.com/koheron/koheron-sdk/zipball/{}/'.format(sdk.version)])

    with zipfile.ZipFile(tmp_zip, 'r') as sdk_zip:
        sdk_zip.extractall(tmp_sdk)
        shutil.copytree(os.path.join(tmp_sdk, sdk_zip.namelist()[0]), sdk.path)
        shutil.rmtree(tmp_sdk)
        os.remove(tmp_zip)

    click.echo('Koheron SDK version {} successfully installed at {}.'.format(sdk.version, sdk.path))

@sdk.command()
@click.pass_obj
def uninstall(sdk):
    ''' Uninstall Koheron SDK '''
    import os
    import shutil
    if os.path.exists(sdk.path):
        shutil.rmtree(sdk.path)

def _run_cmd(cmd_name, sdk, instrument_path):
    import subprocess
    import os
    import yaml

    if len(instrument_path) == 0:
        ipath = os.getcwd()
    else:
        ipath = instrument_path[0]

    config_yml_path = os.path.join(ipath, 'config.yml')

    if not os.path.exists(config_yml_path):
        raise click.ClickException('\'{}\' is not an instrument directory [No config.yml found]'.format(ipath))

    with open(config_yml_path) as f:
        instrument_name = yaml.load(f)['instrument']

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build.sh')
    instrument_abspath = os.path.join(os.getcwd(), ipath)
    subprocess.call(['/bin/bash', script_path, cmd_name, instrument_abspath, instrument_name, sdk.host])

@sdk.command()
@click.pass_obj
@click.argument('instrument_path', nargs=-1)
def build(sdk, instrument_path):
    ''' Build an instrument '''
    _run_cmd('--build', sdk, instrument_path)

@sdk.command()
@click.pass_obj
@click.argument('instrument_path', nargs=-1)
def clean(sdk, instrument_path):
    ''' Clean an instrument '''
    _run_cmd('--clean', sdk, instrument_path)

@sdk.command()
@click.pass_obj
@click.argument('instrument_path', nargs=-1)
def run(sdk, instrument_path):
    ''' Build and run an instrument on the given host '''
    _run_cmd('--run', sdk, instrument_path)
