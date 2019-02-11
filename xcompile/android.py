import os
import click
import platform

MAKE_STANDALONE_TOOLCHAIN_PATH = 'build/tools/make_standalone_toolchain.py'
ARCH_TO_HOST = {
    'arm': 'armv7a-linux-androideabi',
    'arm64': 'aarch64-linux-android',
    'x86': 'i686-linux-android',
    'x86_64': 'x86_64-linux-android',
}

# removing v7a sub on arm
TOOL_PREFIX = {
    'arm': 'arm-linux-androideabi',
    'arm64': 'aarch64-linux-android',
    'x86': 'i686-linux-android',
    'x86_64': 'x86_64-linux-android',
}
ANDROID_API = 28


# TODO: find another way to verify toolchain path that using make_standalone_toolchain.py
def _find_ndk_path():
    ndk_path = os.environ.get('NDK')
    if ndk_path is not None:
        return ndk_path

    print('$NDK not set: trying to found NDK')
    possible_ndk_paths = [
        '~/Library/Android/sdk/ndk-bundle/'
    ]
    for possible_path in possible_ndk_paths:
        path = os.path.expanduser(possible_path)
        if os.path.exists('%s/%s' % (path, MAKE_STANDALONE_TOOLCHAIN_PATH)):
            print('$NDK found at %s' % path)
            return path
    raise click.ClickException('NDK not found: please set $NDK env variable ($NDK/%s must exists)' % MAKE_STANDALONE_TOOLCHAIN_PATH)


class AndroidBuildContext:
    def __init__(self, ndk_path=None):
        if ndk_path is None:
            ndk_path = _find_ndk_path()
        self.ndk_path = ndk_path

    def prepare(self, arch):
        pass

    def _clang_name(self, name, arch):
        host = ARCH_TO_HOST[arch]
        return '{}{}-{}'.format(host, ANDROID_API, name)

    def _tool_name(self, name, arch):
        prefix = TOOL_PREFIX[arch]
        return '{}-{}'.format(prefix, name)

    def get_build_env(self, arch, output):
        system_name = platform.system().lower()
        toolchain_path = '{}/toolchains/llvm/prebuilt/{}-x86_64'.format(self.ndk_path, system_name)

        env = os.environ.copy()
        env['ANDROID_NDK'] = self.ndk_path
        env['PATH'] = '%s/bin' % toolchain_path + os.pathsep + env['PATH']
        env['SYSROOT'] = '%s/sysroot' % toolchain_path
        env['AR'] = self._tool_name('ar', arch)
        env['AS'] = self._clang_name('clang', arch)
        env['CC'] = self._clang_name('clang', arch)
        env['CXX'] = self._clang_name('clang++', arch)
        env['LD'] = self._tool_name('ld', arch)
        env['STRIP'] = self._tool_name('strip', arch)
        env['RANLIB'] = self._tool_name('ranlib', arch)
        env['CFLAGS'] = '-fPIE -fPIC'
        env['LDFLAGS'] = '-pie'
        env['PKG_CONFIG_PATH'] = os.path.join(output, 'lib', 'pkgconfig')
        return env

    def get_host(self, arch):
        return ARCH_TO_HOST[arch]
