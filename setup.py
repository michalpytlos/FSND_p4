from setuptools import setup

setup(
    name='boardgameclub',
    version='1.0',
    packages=['boardgameclub'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'bgc_init_db = boardgameclub.scripts.init_db:main',
            'bgc_add_admin = boardgameclub.scripts.add_admin:main'
        ]
    },
    install_requires=[
        'Flask>=1.0.2',
        'oauth2client>=4.1.2',
        'requests>=2.19.1',
        'SQLAlchemy>=1.2.9'
    ]
)
