import os
import sh
import click
import traceback
import tempfile
import shutil


class AndroidBuildContext:
    TOOLCHAIN_PATH = '/tmp/android-toolchain'
    MAKE_STANDALONE_TOOLCHAIN_PATH = 'build/tools/make_standalone_toolchain.py'
    ARCH_TO_HOST = {
        'arm': 'arm-linux-androideabi',
        'arm64': 'aarch64-linux-android',
        'x86': 'i686-linux-android',
        'x86_64': 'x86_64-linux-android',
    }

    def __init__(self, ndk_path=None):
        if ndk_path is None:
            ndk_path = self.find_ndk_path()
        self.ndk_path = ndk_path

    @classmethod
    def find_ndk_path(cls):
        ndk_path = os.environ.get('NDK')
        if ndk_path is not None:
            return ndk_path

        print('$NDK not set: trying to found NDK')
        possible_ndk_paths = [
            '~/Library/Android/sdk/ndk-bundle/'
        ]
        for possible_path in possible_ndk_paths:
            path = os.path.expanduser(possible_path)
            if os.path.exists('%s/%s' % (path, cls.MAKE_STANDALONE_TOOLCHAIN_PATH)):
                print('$NDK found at %s' % path)
                return path
        raise click.ClickException('NDK not found: please set $NDK env variable ($NDK/%s must exists)' % cls.MAKE_STANDALONE_TOOLCHAIN_PATH)

    def _toolchain_path(self, arch):
        return '%s/%s' % (self.TOOLCHAIN_PATH, arch)

    def prepare(self, arch):
        print('Generating android toolchain for %s' % arch)
        sh.Command('%s/%s' % (self.ndk_path, self.MAKE_STANDALONE_TOOLCHAIN_PATH))(
            '--arch', arch,
            '--api', '26',
            '--install-dir', self._toolchain_path(arch),
            '--force',
        )

    def get_build_env(self, arch):
        host = self.get_host(arch)
        toolchain_path = self._toolchain_path(arch)

        env = os.environ.copy()
        env['PATH'] += os.pathsep + '%s/bin' % toolchain_path
        env['SYSROOT'] = '%s/sysroot' % toolchain_path
        env['AR'] = '%s-ar' % host
        env['AS'] = '%s-clang' % host
        env['CC'] = '%s-clang' % host
        env['CXX'] = '%s-clang++' % host
        env['LD'] = '%s-ld' % host
        env['STRIP'] = '%s-strip' % host
        env['CFLAGS'] = '-fPIE -fPIC'
        env['LDFLAGS'] = '-pie'
        return env

    def get_host(self, arch):
        return self.ARCH_TO_HOST[arch]


TARGETS = {
    'android': {
        'context': AndroidBuildContext,
        'arch': ['arm', 'arm64', 'x86', 'x86_64']
    }
}


def xcompile_autotools(build_context, arch, output, path):
    host = build_context.get_host(arch)
    env = build_context.get_build_env(arch)
    with sh.pushd(path):
        sh.Command('./configure')(
            '--host=%s' % host,
            '--prefix', output,
            _fg=True, _env=env,
        )
        sh.make(_fg=True, _env=env)
        sh.make('install', _fg=True, _env=env)


def guess_build_func(source_path):
    if os.path.exists(os.path.join(source_path, 'configure')):
        return xcompile_autotools
    raise click.ClickException('Build method not found for directory "%s"' % source_path)


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
def build(target, output, source_path, arch):
    if target not in TARGETS:
        raise click.ClickException('Unsupported target: %s. Supported targets: %s' % (target, list(TARGETS.keys())))

    if arch is not None:
        archs = arch.split(',')
        unknown_archs = [arch for arch in archs if arch not in TARGETS[target]['arch']]
        if unknown_archs:
            raise click.ClickException('Unsupported arch: %s' % unknown_archs)
    else:
        archs = TARGETS[target]['arch']

    build_func = guess_build_func(source_path)
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
