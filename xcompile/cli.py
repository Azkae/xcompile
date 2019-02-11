import os
import sh
import click
import traceback
import tempfile
import shutil
from .android import AndroidBuildContext


TARGETS = {
    'android': {
        'context': AndroidBuildContext,
        'arch': ['arm', 'arm64', 'x86', 'x86_64']
    }
}


def xcompile_autotools(build_context, arch, output, path):
    host = build_context.get_host(arch)
    env = build_context.get_build_env(arch, output)
    with sh.pushd(path):
        sh.Command('./configure')(
            '--host=%s' % host,
            '--prefix', output,
            _fg=True, _env=env,
        )
        sh.make(_fg=True, _env=env)
        sh.make('install', _fg=True, _env=env)


def xcompile_openssl(build_context, arch, output, path):
    # XXX: only android
    assert isinstance(build_context, AndroidBuildContext)
    target = 'android-%s' % arch
    env = build_context.get_build_env(arch, output)
    with sh.pushd(path):
        sh.Command('./Configure')(target, '--prefix=%s' % output, _fg=True, _env=env)
        sh.make(_fg=True, _env=env)
        sh.make('install_sw', 'VERBOSE=1', _fg=True, _env=env)


def guess_build_func(source_path):
    if os.path.exists(os.path.join(source_path, 'configure')):
        return xcompile_autotools
    raise click.ClickException('Build method not found for directory "%s"' % source_path)


BUILD_FUNCS = {
    'autotools': xcompile_autotools,
    'openssl': xcompile_openssl,
}


@click.group()
def cli():
    pass


@cli.command('list-arch')
@click.argument('target')
def list_arch(target):
    if target not in TARGETS:
        raise click.ClickException('Unsupported target: %s. Supported targets: %s' % (target, list(TARGETS.keys())))
    print(','.join(TARGETS[target]['arch']))


@cli.command('build')
@click.argument('target')
@click.argument('output')
@click.argument('source_path', default='.')
@click.option('--arch', default=None)
@click.option('--build-type', default=None)
def build(target, output, source_path, arch, build_type):
    if target not in TARGETS:
        raise click.ClickException('Unsupported target: %s. Supported targets: %s' % (target, list(TARGETS.keys())))

    if arch is not None:
        archs = arch.split(',')
        unknown_archs = [arch for arch in archs if arch not in TARGETS[target]['arch']]
        if unknown_archs:
            raise click.ClickException('Unsupported arch: %s' % unknown_archs)
    else:
        archs = TARGETS[target]['arch']

    if build_type is None:
        build_func = guess_build_func(source_path)
    else:
        build_func = BUILD_FUNCS[build_type]
    build_context = TARGETS[target]['context']()

    for arch in archs:
        build_path = '%s/src' % tempfile.mkdtemp(prefix='xcompile-')
        print('-' * 80)
        print('Building %s %s in %s' % (target, arch, build_path))
        print('-' * 80)
        try:
            shutil.copytree(source_path, build_path)

            build_context.prepare(arch)
            arch_output = os.path.join(output, arch)
            os.makedirs(arch_output, exist_ok=True)

            build_func(build_context, arch, arch_output, build_path)
        except Exception:
            raise click.ClickException('Unable to compile for %s in %s:\n%s' % (arch, build_path, traceback.format_exc()))


if __name__ == '__main__':
    cli()
