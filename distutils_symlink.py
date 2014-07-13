from distutils.cmd import Command
from distutils.command.install import install
from distutils.command.install_scripts import install_scripts
import os
import sys

def find_top_level_packages(packages):
    if packages is None:
        return []
    toppkgs = {p for p in packages if ('.' not in p)}
    for p in packages:
        toplevel = p.split('.')[0]
        if toplevel not in toppkgs:
            raise ValueError(('{} is included, but its top level package {} is not.'
                ' This case is not handled for symlinking.').format(p, toplevel))
    return toppkgs

def replace_symlink(src, dest):
    if os.path.islink(dest):
        print('removing existing symlink at %s' % dest)
        os.unlink(dest)
    print('symlinking %s -> %s' % (src, dest))
    os.symlink(src, dest)

class install_lib_symlink(Command):
    user_options = [
        ('install-dir=', 'd', "directory to install to"),
        ]

    def initialize_options(self):
        self.install_dir = None

    def finalize_options(self):
        self.set_undefined_options('symlink',
                                   ('install_lib', 'install_dir'),
                                  )

    def run(self):
        for pkg in find_top_level_packages(self.distribution.packages):
            # TODO: Handle package_dir properly here
            src = os.path.join(os.getcwd(), pkg)
            dest = os.path.join(self.install_dir, pkg)
            replace_symlink(src, dest)
        
        py_modules = self.distribution.py_modules or []
        for mod in py_modules:
            if '.' in mod:
                raise ValueError(("Cannot handle modules specified in packages, "
                                  "such as {}").format(mod))
            # TODO: Handle package_dir properly here
            module_file = mod+'.py'
            src = os.path.join(os.getcwd(), module_file)
            dest = os.path.join(self.install_dir, module_file)
            replace_symlink(src, dest)
        
        # TODO: Raise an error if the distribution has extension modules
    
    def get_outputs(self):
        pkg_outputs = [os.path.join(self.install_dir, p) for p in 
                        find_top_level_packages(self.distribution.packages)]
        mod_outputs = [os.path.join(self.install_dir, m+'.py') for m in
                        self.distribution.py_modules]
        return pkg_outputs + mod_outputs

class unsymlink(install):
    def run(self):
        dest = os.path.join(self.install_lib, 'IPython')
        if os.path.islink(dest):
            print('removing symlink at %s' % dest)
            os.unlink(dest)
        else:
            print('No symlink exists at %s' % dest)

class install_symlinked(install):
    def run(self):
        if sys.platform == 'win32':
            raise Exception("This doesn't work on Windows.")

        # Run all sub-commands (at least those that need to be run)
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
    
    # 'sub_commands': a list of commands this command might have to run to
    # get its work done.  See cmd.py for more info.
    sub_commands = [('install_lib_symlink', lambda self:True),
                    ('install_scripts_for_symlink', lambda self:True),
                   ]

class install_scripts_for_symlink(install_scripts):
    """Scripts are installed like normal, not symlinked, but we need to
    redefine this to get options from 'symlink' instead of 'install'.
    
    I love distutils almost as much as I love setuptools.
    """
    def finalize_options(self):
        self.set_undefined_options('build', ('build_scripts', 'build_dir'))
        self.set_undefined_options('symlink',
                                   ('install_scripts', 'install_dir'),
                                   ('force', 'force'),
                                   ('skip_build', 'skip_build'),
                                  )
cmdclasses = {
    'symlink': install_symlinked,
    'install_lib_symlink': install_lib_symlink,
    'install_scripts_for_symlink': install_scripts_for_symlink,
    'unsymlink': unsymlink,
}