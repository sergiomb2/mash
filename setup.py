from distutils.core import setup
import glob

setup(name='mash',
      version='0.2.7',
      description='Build system -> repository tool',
      author='Bill Nottingham',
      author_email='notting@redhat.com',
      url='http://people.redhat.com/notting/mash/',
      license='GPLv2',
      packages=['mash'],
      scripts = ['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*')),('/usr/share/mash',glob.glob('utils/*'))]
      )

