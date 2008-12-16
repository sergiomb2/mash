from distutils.core import setup
import glob

setup(name='mash',
      version='0.4.4',
      description='Build system -> repository tool',
      author='Bill Nottingham',
      author_email='notting@redhat.com',
      url='https://fedorahosted.org/releases/m/a/mash/',
      license='GPLv2',
      packages=['mash'],
      scripts = ['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*')),('/usr/share/mash',glob.glob('utils/*'))]
      )

