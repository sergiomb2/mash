from distutils.core import setup
import glob

setup(name='mash',
      version='0.6.11',
      description='Build system -> repository tool',
      author='Dennis gilmore',
      author_email='dennis@ausil.us',
      url='https://fedorahosted.org/releases/m/a/mash/',
      license='GPLv2',
      packages=['mash'],
      scripts = ['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*')),('/usr/share/mash',glob.glob('utils/*'))]
      )

