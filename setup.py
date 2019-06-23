from setuptools import setup, find_packages
setup(
    name="bookworm",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'file_fetcher = bookworm.file_fetcher:main',
            'ircclient = bookworm.ircclient:main',
            'unpacker = bookworm.unpacker:main',
            'web = bookworm.web:main',
            ]
        }
)
