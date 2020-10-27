from setuptools import setup


setup(
    name='djsnowpack',
    versioning='dev',
    setup_requires='setupmeta',
    author='James Pic',
    author_email='jamespic@gmail.com',
    modules=['djsnowpack'],
    url='https://yourlabs.io/oss/djsnowpack',
    include_package_data=True,
    license='MIT',
    keywords='django cli',
    python_requires='>=3',
    install_requires=['psutil'],
    extras_require={
        'test': [
            'django',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-mock'
        ],
    },
)
