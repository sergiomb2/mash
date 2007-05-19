from distutils.core import setup
import glob

setup(name='mash',
      version='0.1.8',
      description='Build system -> repository tool',
      author='Bill Nottingham',
      author_email='notting@redhat.com',
      url='https://hosted.fedoraproject.org/projects/mash/',
      license='GPL',
      packages=['mash'],
      scripts = ['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*')),('/usr/share/mash',glob.glob('utils/*'))]
      )

