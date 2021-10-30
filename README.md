# How to use custom libraries with AWS Canaries

In this tutorial we will show how to install and use custom libraries on AWS
CloudWatch Synthetic Canaries.

- [How to use custom libraries with AWS Canaries](#how-to-use-custom-libraries-with-aws-canaries)
  - [Introduction](#introduction)
  - [Development Environment](#development-environment)
    - [Builder](#builder)
    - [Runner](#runner)
    - [The docker-compose.yaml](#the-docker-composeyaml)
      - [Running the Postgres container](#running-the-postgres-container)
      - [Log into builder container](#log-into-builder-container)
      - [Log into runner container](#log-into-runner-container)
  - [Using pure python modules](#using-pure-python-modules)
    - [requirements.txt](#requirementstxt)
    - [install-deps.sh](#install-depssh)
    - [build.sh](#buildsh)
    - [python/main.py](#pythonmainpy)
  - [Using binary libraries](#using-binary-libraries)
    - [Trying to run the first example](#trying-to-run-the-first-example)
    - [Trying to install psycopg2 on runner](#trying-to-install-psycopg2-on-runner)
    - [Installing psycopg2 on builder](#installing-psycopg2-on-builder)
    - [Trying to use the locally installed module](#trying-to-use-the-locally-installed-module)
    - [Trying to run on runner](#trying-to-run-on-runner)
    - [Using libpq locally](#using-libpq-locally)
    - [Using libpq locally on canaries](#using-libpq-locally-on-canaries)
    - [Finding and packing all binary dependencies](#finding-and-packing-all-binary-dependencies)
  - [Summary](#summary)

## Introduction

CloudWatch Synthetics Canaries are meant to monitor the availability of
service by checking them regularly and reporting the result. They can generate
metrics, logs and trigger alarms.

You can find the complete documentation [here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html).

For accomplish this task, canaries run a given code into a specific container.
This code can be one of the blueprints already available or you can provide
your own custom code.

The problem here is that you can't change the environment your code will run,
meaning that you can't install dependencies system-wide. To overcome this
limitation, the documented way to provide dependencies is packing them together
your custom code.

See the details [here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_WritingCanary_Python.html).

In this tutorial we will show how to set up custom dependencies and how to
properly configure the application to be able to use them.

## Development Environment

One of the most common errors when dealing with dependencies installed locally
is that usually the developer's machine already has many dependencies installed
system-wide and sometimes misleading that the local configuration was properly
set while in fact the application is using the system-wide installed libraries,
leading to the well known **"works on my machine"**.

The simpler way to avoid this is using docker containers.

I this tutorial we will use a `docker-compose.yml` to run a pair of containers
named respectively `buider` and `runner`.

Both containers mimic the production environment but the `builder` has all
development tools installed while the `runner` don't.

Doing this way we can develop in an environment very close to the real one and
then safely test in an environment that we make sure that doesn't have any
system-wide dependencies installed.

### Builder

The list of versions for the python runtime canary can be found
[here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Library_python_selenium.html).

Basically it is a container running `amazonlinux` with python 3.8.

We can create a custom image with development tools and libraries installed
using this `Dockerfile`:

```dockerfile
FROM amazonlinux

## Initial update
RUN yum update -y

## Installing dev tools
RUN yum groupinstall -y 'Development Tools'

## Installing helper tools
RUN yum install -y \
    wget curl \
    vim less tree

## Installing Python 3.8 and dev packages
RUN true \
    && amazon-linux-extras enable python3.8 \
    && yum install -y \
        python38 python38-devel

## Installing stuff to work with postgres
RUN yum install -y \
    postgresql-libs postgresql-devel

WORKDIR /app

CMD [ "bash" ]
```

There is no rocket science here. We need to manually install python 3.8 because
it is not the default version on `amazonlinux`, and since we will show an
example with Postgres later, we will also install its libraries and development
files.

### Runner

The runner is just a simplified version of the `builder`:

```dockerfile
FROM amazonlinux

## Initial update
RUN yum update -y

## Installing helper tools
RUN yum install -y wget curl vim less tree

## Installing Python 3.8 and dev packages
RUN true \
    && amazon-linux-extras enable python3.8 \
    && yum install -y python38

WORKDIR /app

CMD [ "bash" ]
```

Note that we are not going to install any libraries on the `runner`.

### The docker-compose.yaml

```yaml
version: "3.8"

services:
  my-pg:
    image: postgres:9.6.23-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=postgres

  amz-builder:
    image: amz-builder
    volumes:
      - "./:/app/src/"
    command: bash
    tty: true
    stdin_open: true

  amz-runner:
    image: amz-runner
    volumes:
      - "./:/app/src/"
    command: bash
    tty: true
    stdin_open: true

```

Firstly we will run a Postgres container for the Postgres example.

We want to access a shell terminal on each container so we set both `tty` and
`stdin_open` to `true`.

Also, we will mount the project directory simultaneously on both containers.
This will allow us to install things on `builder` and test our code on a clean
environment using the `runner`.

#### Running the Postgres container

To run the Postgres container in background we use the usual command:

```shell
docker-compose up -d my-pg
```

#### Log into builder container

We can run and get the terminal of the `builder` in a similar but slightly
different way:

```shell
docker-compose run amz-builder
```

This will give us back a terminal on the `builder` container.

To get back to your original terminal, just type `Ctrl+D` or do a regular exit
from the container shell.

#### Log into runner container

This is pretty similar. Just use the command:

```shell
docker-compose run amz-runner
```

You will see a similar terminal but in a different container.

In both cases you will be on the same directory, the project root directory,
but on different containers, meaning a different environment.

## Using pure python modules

The documented way to put custom code on canaries is having a directory called
`python/` directly on the project root directory, inside which should be a
python file containing the handler entrypoint with a specific signature. Then
the dependencies should be anywhere the application can find them.

In order to make the directories more clean we choose to put all python
dependencies in a directory called `deps/` at the same level of the `python/`
directory.

So the project structure will look like:

```
.
|-- build.sh
|-- deps/
|-- install-deps.sh
|-- python/
|   `-- main.py
`-- requirements.txt
```

In this example we need to get dog images from the [Dog API](https://dog.ceo/dog-api/)
but unfortunately the `requests` module is not available, so we need to install
it locally and pack it together with our application.

### requirements.txt

```
requests==2.22.0
```

### install-deps.sh

```shell
#!/bin/bash

pip3.8 install -U -r requirements.txt -t ./deps
```

### build.sh

```shell
#!/bin/bash

zip -r dogs-canary.zip ./deps ./python
```

### python/main.py

Firstly the full content of the file:

```python
#!/usr/bin/env python3

# Here we inform python to search for dependencies
# on this project
from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()

sys.path.append(str(deps))  # Python dependencies

# Now let's start our real work!!!

from aws_synthetics.common import synthetics_logger as logger
import requests


def main(breed):
    logger.info('Getting a dog...')

    try:
        uri = f'https://dog.ceo/api/breed/{breed}/images/random'
        res = requests.get(uri)

        if res.status_code == 200:
            logger.info(res.json()['message'])
        else:
            raise Exception(res)

    except Exception as e:
        logger.error(e)

    return 0


def handler(event, context):
    logger.info('Starting Dogs Canary')

    breed = os.environ['BREED']

    return main(breed)
```

The main thing here is telling to python where to find our locally installed
dependencies based on the location of the main script `python/main.py` before
start importing modules:

```python
...
from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()

sys.path.append(str(deps))  # Python dependencies
...
```

And that's all.

When the canary run it will generate a log very similar to:

```text
INFO: Start canary
...
INFO: temp_artifacts_path: /tmp
INFO: Start executing customer steps
INFO: Customer canary entry file name: main
INFO: Customer canary entry function name: handler
INFO: Calling customer canary: main.handler()
INFO: Starting Dogs Canary                                           <<==
INFO: Getting a dog...                                               <<==
INFO: https://images.dog.ceo/breeds/pomeranian/n02112018_13930.jpg   <<==
INFO: Customer canary response 0
INFO: Finished executing customer steps
INFO: No active browser instance. HAR generation will be skipped.
INFO: Publishing result and duration CloudWatch metrics with timestamp: ...
INFO: Uploading artifacts to S3 for canary: my-canary-name
INFO: Uploading files to S3: ["/tmp/SyntheticsReport-PASSED.json", "/tmp...
```

## Using binary libraries

For this example we will set up a Postgres connection and do a "Hello World".

This one is a lot more tricky because to connect to Postgres, the python
modules need to dynamic load a binary library called `libpq` and we need to
pack it and all its dependencies together with our application.

Full documentation [here](https://www.postgresql.org/docs/current/libpq.html).

To connect with Postgres we will use a python module called `psycopg2`. Full
documentation also [here](https://www.psycopg.org/).

So let's follow the same approach of the previous example, step by step and see
what happens.

### Trying to run the first example

On the `runner` terminal, go to the `pg-app` root directory:

```shell
cd /app/src/pg-app
```

Now put the code below on a file called `examples/first.py`:

```python
#!/usr/bin/env python3

import psycopg2

print('psycopg2 imported successfully')
```

This code is just trying to load the `psycopg2` module.

Now let's try to run it with:

```shell
python3.8 examples/first.py
```

We will see the following error:

```
Traceback (most recent call last):
  File "examples/first.py", line 12, in <module>
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
```

This is expected since the module isn't installed yet. Let's install it.

### Trying to install psycopg2 on runner

Still on the same runner terminal, type the command to install `psycopg2`
locally:

```shell
pip3.8 install psycopg2 --target deps
```

You will see an error message like this (some lines suppressed):

```
Collecting psycopg2
  Using cached https://files.pythonhosted.org/packages/aa/8a/7c80e7e44fb...
  ...
    Error: pg_config executable not found.
  ...
Command "python setup.py egg_info" failed with error code 1 in /tmp/pip-...

```

This is because the developer files are not installed at `runner` and for the
same reason we cannot install modules using `pip` at canaries.

To install dependencies even locally we need many developer tools and
development files installed beforehand.

Remember this section of `builder`'s Dockerfile:

```dockerfile
RUN yum install -y \
    postgresql-libs postgresql-devel
```

`postgresql-libs` is the package with `libpq` while `postgresql-devel` is the
package with development files needed to compile postgres binary bindings for
`psycopg`.

You can check the content of a package (on `amazonlinux`) with the command:

```shell
repoquery -l postgresql-libs
```

The result (with many lines suppressed) is showed below. Note the libraries
(files with extensions `*.so.*`):

```
...
/usr/share/doc/postgresql-libs-9.2.24
/usr/share/doc/postgresql-libs-9.2.24/COPYRIGHT
/usr/share/locale/cs/LC_MESSAGES/ecpglib6-9.2.mo
/usr/share/locale/cs/LC_MESSAGES/libpq5-9.2.mo
/usr/lib64/libecpg.so.6
/usr/lib64/libecpg.so.6.4
/usr/lib64/libecpg_compat.so.3
/usr/lib64/libecpg_compat.so.3.4
/usr/lib64/libpgtypes.so.3
/usr/lib64/libpgtypes.so.3.3
/usr/lib64/libpq.so.5
/usr/lib64/libpq.so.5.5
...
```

With a similar command you can also check the content of the development package:

```shell
repoquery -l postgresql-devel
```

To see a very large result (more than 600 lines, many of them suppressed):

```
/usr/bin/ecpg
...
/usr/include/libpq
/usr/include/libpq-events.h
/usr/include/libpq-fe.h
/usr/include/libpq/libpq-fs.h
/usr/include/pg_config.h
/usr/include/pg_config_manual.h
/usr/include/pg_config_os.h
/usr/include/pg_config_x86_64.h
...
```

It installs commands and also C header files that are used to compile things
that use postgres libraries.

### Installing psycopg2 on builder

Just remember that `builder` and `runner` share the same project directory,
so installing dependencies inside the project will make them available on
both environments.

Also note that the dependencies will be compiled using the specific libraries
during the installation process and may not work if the versions between the
developer's machine and production machine differs so much.

This is the reason we are using `amazonlinux` do develop, since the canaries
use this linux distro.

So, on `builder` terminal, let's move to the project directory:

```shell
cd /app/src/pg-app
```

And let's install `psycopg2` with the same commands:

```shell
pip3.8 install psycopg2 --target deps
```

Now the installation finish well:

```
Collecting psycopg2
  Downloading https://files.pythonhosted.org/packages/aa/8a/7c80e7e44fb1b4277e89bd9ca509aefdd4dd1b2c547c6f293afe9f7ffd04/psycopg2-2.9.1.tar.gz (379kB)
    100% |████████████████████████████████| 389kB 2.2MB/s 
Installing collected packages: psycopg2
  Running setup.py install for psycopg2 ... done
Successfully installed psycopg2-2.9.1
```

We can confirm the installation by checking the content of `deps/` dir using
the command `tree deps` to see its content (some lines suppressed):

```
deps/
|-- psycopg2
|   |-- __init__.py
|   |-- __pycache__
|   |   |-- __init__.cpython-38.pyc
|   |   |-- _ipaddress.cpython-38.pyc
...
|   |   `-- tz.cpython-38.pyc
|   |-- _ipaddress.py
|   |-- _json.py
|   |-- _psycopg.cpython-38-x86_64-linux-gnu.so
...
|   `-- tz.py
`-- psycopg2-2.9.1-py3.8.egg-info
    |-- PKG-INFO
    |-- SOURCES.txt
    |-- dependency_links.txt
    |-- installed-files.txt
    `-- top_level.txt
```

Note the `*.pyc` files suffixed with `-38`. They are bytecode compiled from
`*.py` files, specific for `python 3.8`, meaning they won't work with a
different python version.

Also note the file `_psycopg.cpython-38-x86_64-linux-gnu.so`. It is the C
binding for `psycopg2`. We will back on it later.

### Trying to use the locally installed module

Let's try to run the first example again:

```shell
python3.8 examples/first.py
```

And see the same error again:

```
Traceback (most recent call last):
  File "examples/first.py", line 3, in <module>
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
```

This is because we didn't tell python where to find our locally installed
modules.

Let's add this and save a new file at `examples/second.py` with this content:

```python
#!/usr/bin/env python3

from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()

sys.path.append(str(deps))

import psycopg2

print('psycopg2 imported successfully')
```

The lines 3 to 9 are just informing python to also seek for modules on our
`deps/` directory.

When running it:

```shell
python3.8 examples/second.py
```

We get:

```
psycopg2 imported successfully
```

### Trying to run on runner

Now, let's run the same example but from the runner terminal:

```shell
python3.8 examples/second.py 
```

To get this error:

```
Traceback (most recent call last):
  File "examples/second.py", line 12, in <module>
    import psycopg2
  File "/app/src/pg-app/deps/psycopg2/__init__.py", line 51, in <module>
    from psycopg2._psycopg import (                     # noqa
ImportError: libpq.so.5: cannot open shared object file: No such file or directory
```

The last line states that `psycopg2` is trying to import a library called
`libpq.so.5` that as you know isn't available on runner. We need to make it
available to our code.

### Using libpq locally

The way to use `libpq` locally is to copy it to a local directory and also make
the code load it from there.

Let's create a directory called `libs/` and copy `libpq` to there. You already
know where it is located by the previous sections when we showed the command
`repoquery`.

From the `builder` terminal:

```shell
cp /lib64/libpq.so.5 libs/
```

And to inform a program where to look for dynamic libraries we have to set the
environment variable `LD_LIBRARY_PATH` before calling it.

Let's do it but from the `runner` terminal:

```shell
LD_LIBRARY_PATH=libs python3.8 examples/second.py
```

You can start researching about dynamic loaded libraries [here](https://tldp.org/HOWTO/Program-Library-HOWTO/dl-libraries.html),
[here](https://man7.org/linux/man-pages/man3/dlopen.3.html) and even [here](https://en.wikipedia.org/wiki/Dynamic_loading).

### Using libpq locally on canaries

Note that here is a first gotcha here (and will be more ahead): We cannot
change the command line that the canary will use to call our code, so we can't
set `LD_LIBRARY_PATH` this way.

Also, we cannot inform it like a regular environment variable because we don't
know in advance in which directory the code will be unpacked, so we need to do
this using code like we did for locally installed python modules.

Let's add a line for `libs/` and create a new example `examples/third.py`
with the content:

```python
#!/usr/bin/env python3

from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

sys.path.append(str(deps))

os.environ['LD_LIBRARY_PATH'] = str(libs)

import psycopg2

print('psycopg2 imported successfully')
```

And try to run it on `runner` to get this:

```
Traceback (most recent call last):
  File "examples/second.py", line 12, in <module>
    import psycopg2
  File "/app/src/pg-app/deps/psycopg2/__init__.py", line 51, in <module>
    from psycopg2._psycopg import (                     # noqa
ImportError: libpq.so.5: cannot open shared object file: No such file or directory
```

Here we got our second gotcha:

Dynamic libraries are loaded by a system library called `ld-linux*.so` and it
is one of the first things that got loaded by the linux kernel when running a
program.

So when the python code starts running, the dynamic loader will have already
read the required environment variables it needed.

You can read more about this [here](https://0xax.gitbooks.io/linux-insides/content/SysCall/linux-syscall-4.html)
and at its references.

So we need to load the binaries manually in our python code before import the
python modules themselves. Fortunately this is can be done using the module
`ctypes` and calling `LoadLibrary()` manually:

```python
from ctypes import cdll

cdll.LoadLibrary(f'{libs}/libpq.so.5')
```

Let's add these lines and create a new example `examples/fourth.py` with the
following content:

```python
#!/usr/bin/env python3


# Getting absolute paths to our project
from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

# Adding 'deps' to path where python look for modules
sys.path.append(str(deps))


# Importing binary libraries manually
from ctypes import cdll

cdll.LoadLibrary(f'{libs}/libpq.so.5')


# Our actual code
import psycopg2

print('psycopg2 imported successfully')
```
 
Let's run it from the `runner` and see the result:

```
psycopg2 imported successfully
```

Nice! It works!

Not so fast... There is a third gotcha here.

Let's add the aws stuff, pack everything on a zip file, create a canary and see
what happens:

Just create a file `python/first_canary.py` with the content:

```python
#!/usr/bin/env python3


# Getting absolute paths to our project
from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

# Adding 'deps' to path where python look for modules
sys.path.append(str(deps))


# Importing binary libraries manually
from ctypes import cdll

cdll.LoadLibrary(f'{libs}/libpq.so.5')


# Our actual code
from aws_synthetics.common import synthetics_logger as logger
import psycopg2


def handler(event, context):
    print('Starting Postgres Canary')

    return 0

```

Then pack it:

```shell
zip -r first-canary.zip libs/ deps/ python/
```

After creating the canary on AWS, the first run fails with this log (some
lines suppressed and adding line breaks on the error line):

```text
INFO: Start canary
...
INFO: Customer canary entry file name: first_canary
INFO: Customer canary entry function name: handler
ERROR: Canary execution exception.Traceback (most recent call last):  \
    File "/var/task/index.py", line 71, in handle_canary    \
    customer_canary = importlib.import_module(file_name)  \
    File "/var/lang/lib/python3.8/importlib/__init__.py", line 127, \
    in import_module    \
    return _bootstrap._gcd_import(name[level:], package, level)  \
    File "<frozen importlib._bootstrap>", line 1014, in _gcd_import  \
    File "<frozen importlib._bootstrap>", line 991, in _find_and_load  \
    File "<frozen importlib._bootstrap>", line 975, in _find_and_load_unlocked  \
    File "<frozen importlib._bootstrap>", line 671, in _load_unlocked  \
    File "<frozen importlib._bootstrap_external>", line 843, in exec_module  \
    File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed  \
    File "/opt/python/first_canary.py", line 19, in <module>    \
        cdll.LoadLibrary(f'{libs}/libpq.so.5')  \
    File "/var/lang/lib/python3.8/ctypes/__init__.py", line 451, in LoadLibrary    \
        return self._dlltype(name)  \
    File "/var/lang/lib/python3.8/ctypes/__init__.py", line 373, in __init__    \
    self._handle = _dlopen(self._name, mode) \
        OSError: libldap_r-2.4.so.2: cannot open shared object file: \
        No such file or directory
...
INFO: Uploading artifacts to S3 for canary: first-canary
INFO: Uploading files to S3: ["/tmp/2021-10-30T13-49-10-638Z-log.txt", ...
```

It is a large error message but look at the final parts:

```text
OSError: libldap_r-2.4.so.2: cannot open shared object file: No such file or directory
```

So what is this library `libldap_r-2.4.so.2`?

It is a dependency of `libpq`.

Since this is the reason for dynamic libraries exist, it is very common that a
program have a library as its dependency, then that library has its own
dependencies and so on...

While our code was able to run successfully in our `runner` environment, there
are some libraries available there that are not available in the canary
environment, even though `runner` is supposed to be a minimal environment.

We must pack into the canary **all dependencies**.

### Finding and packing all binary dependencies

To see what are the dynamic libraries that a program or library is linked to we
can use the command `ldd`:

```
ldd libs/libpq.so.5 
	linux-vdso.so.1 (0x00007fffd4726000)
	libssl.so.10 => /lib64/libssl.so.10 (0x00007fecd8d0b000)
	libcrypto.so.10 => /lib64/libcrypto.so.10 (0x00007fecd88b5000)
	libkrb5.so.3 => /lib64/libkrb5.so.3 (0x00007fecd85d1000)
	libcom_err.so.2 => /lib64/libcom_err.so.2 (0x00007fecd83cd000)
	libgssapi_krb5.so.2 => /lib64/libgssapi_krb5.so.2 (0x00007fecd8181000)
	libldap_r-2.4.so.2 => /lib64/libldap_r-2.4.so.2 (0x00007fecd7f26000)
	libpthread.so.0 => /lib64/libpthread.so.0 (0x00007fecd7d08000)
	libc.so.6 => /lib64/libc.so.6 (0x00007fecd795d000)
	libk5crypto.so.3 => /lib64/libk5crypto.so.3 (0x00007fecd772c000)
	libdl.so.2 => /lib64/libdl.so.2 (0x00007fecd7528000)
	libz.so.1 => /lib64/libz.so.1 (0x00007fecd7313000)
	libkrb5support.so.0 => /lib64/libkrb5support.so.0 (0x00007fecd7104000)
	libkeyutils.so.1 => /lib64/libkeyutils.so.1 (0x00007fecd6f00000)
	libresolv.so.2 => /lib64/libresolv.so.2 (0x00007fecd6cea000)
	/lib64/ld-linux-x86-64.so.2 (0x00007fecd91a7000)
	liblber-2.4.so.2 => /lib64/liblber-2.4.so.2 (0x00007fecd6adb000)
	libsasl2.so.3 => /lib64/libsasl2.so.3 (0x00007fecd68be000)
	libssl3.so => /lib64/libssl3.so (0x00007fecd6664000)
	libsmime3.so => /lib64/libsmime3.so (0x00007fecd643e000)
	libnss3.so => /lib64/libnss3.so (0x00007fecd6116000)
	libnssutil3.so => /lib64/libnssutil3.so (0x00007fecd5ee7000)
	libplds4.so => /lib64/libplds4.so (0x00007fecd5ce3000)
	libplc4.so => /lib64/libplc4.so (0x00007fecd5ade000)
	libnspr4.so => /lib64/libnspr4.so (0x00007fecd58a2000)
	libselinux.so.1 => /lib64/libselinux.so.1 (0x00007fecd567b000)
	libcrypt.so.1 => /lib64/libcrypt.so.1 (0x00007fecd5444000)
	librt.so.1 => /lib64/librt.so.1 (0x00007fecd523c000)
	libpcre.so.1 => /lib64/libpcre.so.1 (0x00007fecd4fd8000)
```

Look how many!  

The result also shows where we can find them.

Note that some of them follow the form `name.so.* => /path/to/it (memory address)`
and some doesn't. The reason why is left as an exercise for the reader. We want
just the ones that follow that pattern.

Also, we already know that we are using `libpq`, but what if our python code
needs more binary libraries, how to find them?

Remember previous sections when we showed the content of `deps/` dir and
talked about `_psycopg.cpython-38-x86_64-linux-gnu.so`. We are back on it now.

This is the C binding that python compiles when installing `psycopg2`. It is
also the dynamic library that python loads when importing the module. Let's
use `ldd` on it:

```
ldd deps/psycopg2/_psycopg.cpython-38-x86_64-linux-gnu.so 
	linux-vdso.so.1 (0x00007ffea9140000)
	libpq.so.5 => /lib64/libpq.so.5 (0x00007fa8e4ace000)           <<=== libpq
	libpthread.so.0 => /lib64/libpthread.so.0 (0x00007fa8e48b0000)
	libc.so.6 => /lib64/libc.so.6 (0x00007fa8e4505000)
	libssl.so.10 => /lib64/libssl.so.10 (0x00007fa8e4296000)
	libcrypto.so.10 => /lib64/libcrypto.so.10 (0x00007fa8e3e40000)
	libkrb5.so.3 => /lib64/libkrb5.so.3 (0x00007fa8e3b5c000)
	libcom_err.so.2 => /lib64/libcom_err.so.2 (0x00007fa8e3958000)
	libgssapi_krb5.so.2 => /lib64/libgssapi_krb5.so.2 (0x00007fa8e370c000)
	libldap_r-2.4.so.2 => /lib64/libldap_r-2.4.so.2 (0x00007fa8e34b1000)
	/lib64/ld-linux-x86-64.so.2 (0x00007fa8e4f43000)
	libk5crypto.so.3 => /lib64/libk5crypto.so.3 (0x00007fa8e3280000)
	libdl.so.2 => /lib64/libdl.so.2 (0x00007fa8e307c000)
	libz.so.1 => /lib64/libz.so.1 (0x00007fa8e2e67000)
	libkrb5support.so.0 => /lib64/libkrb5support.so.0 (0x00007fa8e2c58000)
	libkeyutils.so.1 => /lib64/libkeyutils.so.1 (0x00007fa8e2a54000)
	libresolv.so.2 => /lib64/libresolv.so.2 (0x00007fa8e283e000)
	liblber-2.4.so.2 => /lib64/liblber-2.4.so.2 (0x00007fa8e262f000)
	libsasl2.so.3 => /lib64/libsasl2.so.3 (0x00007fa8e2412000)
	libssl3.so => /lib64/libssl3.so (0x00007fa8e21b8000)
	libsmime3.so => /lib64/libsmime3.so (0x00007fa8e1f92000)
	libnss3.so => /lib64/libnss3.so (0x00007fa8e1c6a000)
	libnssutil3.so => /lib64/libnssutil3.so (0x00007fa8e1a3b000)
	libplds4.so => /lib64/libplds4.so (0x00007fa8e1837000)
	libplc4.so => /lib64/libplc4.so (0x00007fa8e1632000)
	libnspr4.so => /lib64/libnspr4.so (0x00007fa8e13f6000)
	libselinux.so.1 => /lib64/libselinux.so.1 (0x00007fa8e11cf000)
	libcrypt.so.1 => /lib64/libcrypt.so.1 (0x00007fa8e0f98000)
	librt.so.1 => /lib64/librt.so.1 (0x00007fa8e0d90000)
	libpcre.so.1 => /lib64/libpcre.so.1 (0x00007fa8e0b2c000)
```

So, since our development environment tries mimic the platform where the code
will run, at least with a compatible kernel version, all we need is to copy
all these libraries locally and load them before our actual python code start
to import the modules we need.

And finally, the fourth gotcha...

One important thing to note is that when a library has dependencies, the loader
will try to load them recursively, looking for the dependencies on the default
paths it knows and failing since all dependencies are in our custom directory
`libs/`.

We want to avoid this behavior and load all dependencies in the correct order.
To do this we will use the command `lddtree` to help getting an ordered list
of dependencies:

```shell
lddtree deps/psycopg2/_psycopg.cpython-38-x86_64-linux-gnu.so
```

Look the result:

```
_psycopg.cpython-38-x86_64-linux-gnu.so => deps/psycopg2/_psycopg.cpython-38-x86_64-linux-gnu.so (interpreter => none)
    libpq.so.5 => /lib64/libpq.so.5
        libssl.so.10 => /lib64/libssl.so.10
            libk5crypto.so.3 => /lib64/libk5crypto.so.3
                libkrb5support.so.0 => /lib64/libkrb5support.so.0
                    libselinux.so.1 => /lib64/libselinux.so.1
                        libpcre.so.1 => /lib64/libpcre.so.1
                        ld-linux-x86-64.so.2 => /lib64/ld-linux-x86-64.so.2
                libkeyutils.so.1 => /lib64/libkeyutils.so.1
                libresolv.so.2 => /lib64/libresolv.so.2
            libdl.so.2 => /lib64/libdl.so.2
            libz.so.1 => /lib64/libz.so.1
        libcrypto.so.10 => /lib64/libcrypto.so.10
        libkrb5.so.3 => /lib64/libkrb5.so.3
        libcom_err.so.2 => /lib64/libcom_err.so.2
        libgssapi_krb5.so.2 => /lib64/libgssapi_krb5.so.2
        libldap_r-2.4.so.2 => /lib64/libldap_r-2.4.so.2
            liblber-2.4.so.2 => /lib64/liblber-2.4.so.2
            libsasl2.so.3 => /lib64/libsasl2.so.3
                libcrypt.so.1 => /lib64/libcrypt.so.1
            libssl3.so => /lib64/libssl3.so
            libsmime3.so => /lib64/libsmime3.so
            libnss3.so => /lib64/libnss3.so
            libnssutil3.so => /lib64/libnssutil3.so
            libplds4.so => /lib64/libplds4.so
            libplc4.so => /lib64/libplc4.so
            libnspr4.so => /lib64/libnspr4.so
                librt.so.1 => /lib64/librt.so.1
    libpthread.so.0 => /lib64/libpthread.so.0
    libc.so.6 => /lib64/libc.so.6
```

We can find all binary libraries using this helper script:

```shell
#!/bin/bash

## Finding all dynamic libraries on our local deps/ dir
PYTHON_DYN_LIBS=$(find deps -iname "*.so*")

## Getting filenames
FILENAMES=$(lddtree $PYTHON_DYN_LIBS | grep '  ' | sort | awk '{ print $3 }' | awk '!x[$0]++')

mkdir -p libs/

echo -e "\nCopying files to libs/...\n"

for FILE in $FILENAMES;
do
  cp -v $FILE libs/
done;

echo -e "\nGenerating ordered python list...\n"

for FILE in $FILENAMES;
do
  NAME=$(echo $FILE | cut -f3 -d '/')
  echo "'$NAME',"
done;
```

Now we can get all of them at once:

```
Copying files to libs/...

'/lib64/ld-linux-x86-64.so.2' -> 'libs/ld-linux-x86-64.so.2'
'/lib64/libpcre.so.1' -> 'libs/libpcre.so.1'
...
'/lib64/libpq.so.5' -> 'libs/libpq.so.5'
'/lib64/libpthread.so.0' -> 'libs/libpthread.so.0'

Generating ordered python list...

'ld-linux-x86-64.so.2',
'libpcre.so.1',
...
'libpq.so.5',
'libpthread.so.0',
```

The full python script will look like:

```python
#!/usr/bin/env python3


# Getting absolute paths to our project
from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

# Adding 'deps' to path where python look for modules
sys.path.append(str(deps))


# Importing binary libraries manually
from ctypes import cdll

dynamic_libs = [
    'ld-linux-x86-64.so.2',
    'libpcre.so.1',
    'libselinux.so.1',
    'libcrypt.so.1',
    'libkeyutils.so.1',
    'libkrb5support.so.0',
    'libresolv.so.2',
    'librt.so.1',
    'libdl.so.2',
    'libk5crypto.so.3',
    'liblber-2.4.so.2',
    'libnspr4.so',
    'libnss3.so',
    'libnssutil3.so',
    'libplc4.so',
    'libplds4.so',
    'libsasl2.so.3',
    'libsmime3.so',
    'libssl3.so',
    'libz.so.1',
    'libcom_err.so.2',
    'libcrypto.so.10',
    'libgssapi_krb5.so.2',
    'libkrb5.so.3',
    'libldap_r-2.4.so.2',
    'libssl.so.10',
    'libc.so.6',
    'libpq.so.5',
    'libpthread.so.0',
]

for lib in dynamic_libs:
    full_path = '{lib_dir}/{lib_name}'.format(
        lib_dir=libs,
        lib_name=lib
    )

    cdll.LoadLibrary(full_path)


# Our actual code
from aws_synthetics.common import synthetics_logger as logger
import psycopg2


def handler(event, context):
    logger.info('Starting Postgres Canary')

    return 0

```

Finally, all we need is just pack everything and create the canary.

## Summary

AWS CloudWatch Synthetics Canaries use a very restricted environment to run our
custom code.

We can pack all dependencies of our code into a zip file and create a canary
from it.

For modules that use python-only code, all we need is to install them inside
our project directory and inform python where to find them.

For modules that also have binary dependencies we must pack them together as
well and load them manually and in a specific order on our code before start
to import the modules that depends on them.

After playing around with loading modules and libraries manually we can write
our actual code.


