"""
Isha Framework — Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

readme = Path("README.md")
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="isha",
    version="1.0.0",
    author="Isha Framework Contributors",
    author_email="isha@example.com",
    description="A modern, lightweight, high-performance Python web framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jayanthansenthilkumar/ISHA_Framework",
    project_urls={
        "Documentation": "https://github.com/jayanthansenthilkumar/ISHA_Framework",
        "Source": "https://github.com/jayanthansenthilkumar/ISHA_Framework",
        "Issues": "https://github.com/jayanthansenthilkumar/ISHA_Framework/issues",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "full": [
            "uvicorn>=0.20.0",
            "bcrypt>=4.0.0",
            "jinja2>=3.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "httpx>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "isha=isha.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Framework :: AsyncIO",
    ],
    keywords="web framework async asgi http",
    license="MIT",
)
