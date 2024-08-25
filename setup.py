from distutils.core import setup

setup(
    name="SassGraph",
    version="0.1dev",
    packages=[
        "sass_graph",
    ],
    author="Kuter Dinel",
    author_email="kuterdinel@gmail.com",
    description="A tool for visualizing NVIDIA Sass assembly files.",
    long_description=open("README.md").read(),
)
