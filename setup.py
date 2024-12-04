from setuptools import setup, find_packages

setup(
    name="DBSQLite",                     # 包的名称
    version="1.0.0",                     # 版本号
    description="A lightweight SQLite helper library.",  # 简短描述
    long_description=open("README.md").read(),  # 从 README.md 读取长描述
    long_description_content_type="text/markdown",  # 描述的格式
    author="alec",                  # 作者
    author_email="aalisx@gmail.com",  # 作者邮箱
    url="https://github.com/alisx/DBSQLite",  # 项目主页
    license="MIT",                       # 开源许可证类型
    packages=find_packages(),            # 自动发现包
    include_package_data=True,           # 包含包内的其他文件
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",             # 支持的最低 Python 版本
)
