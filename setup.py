from setuptools import setup, find_packages

setup(
    name='telegram_sender',
    version='1.1.3',
    description='SenderMessages is an asynchronous Python tool for sending messages and photos to multiple Telegram users efficiently. It supports batching, error handling, MongoDB logging, and is optimized for fast, non-blocking delivery while adhering to Telegram API rate limits.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Alexander Smirnov',
    author_email='Alex@TheSmirnov.com',
    url='https://github.com/smalyu/tg-bot-sender',
    packages=find_packages(),
    install_requires=[
        'aiohttp>=3,<4',
        'motor>=3,<4',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    project_urls={
        'Source': 'https://github.com/smalyu/tg-bot-sender',
    },
)
