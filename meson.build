project('frfun7', 'cpp',
  default_options : ['buildtype=release', 'b_ndebug=if-release', 'cpp_std=c++17'],
  meson_version : '>=0.64.0',
  version : '1.1'
)

sources = ['src/frfun7.cpp']

cxx = meson.get_compiler('cpp')

# Prefer system VapourSynth headers, fall back to the vendored API 4 headers.
system_vs_dep = dependency('vapoursynth', version : '>=55', required : false)
if system_vs_dep.found()
  vapoursynth_dep = system_vs_dep.partial_dependency(compile_args : true, includes : true)
else
  vapoursynth_dep = declare_dependency(include_directories : include_directories('include/vapoursynth', is_system : true))
endif

cflags = cxx.get_supported_arguments(['-Wall', '-Wextra', '-Wshadow'])
ldflags = []

host_cpu_family = host_machine.cpu_family()
host_system = host_machine.system()

if host_cpu_family.startswith('x86')
  # Enables the SSE2 code paths. MSVC has SSE2 on by default for x86-64.
  cflags += '-DFRFUN7_X86=1'
  cflags += cxx.get_supported_arguments(['-mfpmath=sse', '-msse2'])

  if (host_system == 'windows' or host_system == 'cygwin') and host_cpu_family == 'x86' and cxx.get_argument_syntax() == 'gcc'
    cflags += '-mstackrealign'
    ldflags += '-Wl,--kill-at'
  endif
endif

# VapourSynth only autoloads *.dylib on macOS, while Meson defaults to *.so for modules.
module_kwargs = {}
if host_system == 'darwin'
  module_kwargs += {'name_suffix' : 'dylib'}
endif

if get_option('python_package')
  # Same layout as the VapourSynth PyPI package autoloads from: site-packages/vapoursynth/plugins
  py = import('python').find_installation(pure : false)
  install_dir = join_paths(py.get_install_dir(), 'vapoursynth', 'plugins')
else
  libdir = join_paths(get_option('prefix'), get_option('libdir'))
  if system_vs_dep.found()
    libdir = system_vs_dep.get_variable(pkgconfig : 'libdir', default_value : libdir)
  endif
  install_dir = join_paths(libdir, 'vapoursynth')
endif

shared_module('frfun7', sources,
  dependencies : vapoursynth_dep,
  cpp_args : cflags,
  link_args : ldflags,
  install : true,
  install_dir : install_dir,
  gnu_symbol_visibility : 'hidden',
  kwargs : module_kwargs
)
