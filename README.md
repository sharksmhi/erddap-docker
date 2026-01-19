# ERDDAP Docker

This repository contains the installation process and relevant configuration for the ERDDAP server hosted on
http://erddap.nodc.se.

## Installation

### Prerequisites

#### Server

The intended target for all instructions and scripts is a server running Ubuntu 22.04.4 LTS (Jammy Jellyfish).

#### Cloning erddap-docker

Clone erddap-docker (this repository) on the server.

Links:

- https://github.com/sharksmhi/erddap-docker (the repository)

##### Running the install script

The script `install-ubuntu-server.se` does the following:

- Creates an admin user an makes sure that it can't be logged in using password.
- Enables the ufw firewall, disabling all incoming traffic except ssh, 2222, http and https.
- Installs docker.
- Installs docker-compose.

The script is partially idempotent, meaning it tries to skip steps already fulfilled and is therefore safe to run
multiple times. E.g. if you already have a user with the name you supply the script, the script will just skip that
step.

However, the script will not change configurations if something is already configured. E.g. if you already have enabled
ufw but with other rules, you will not get the expected ones by running the script.

It is advisable to manually check the result of each step afterwards.

#### Cloning errdap-docker-gold-standard

The U.S. Integrated Ocean Observing System Program (IOOS) has a guide for installing ERDDAP with Docker. This includes a
GitHub repository with basic configurations.

This repository will serve as the starting point for our installation but some configurations will be updated. To make
sure everything works, you can try out the instructions without changes.

Links:

- https://ioos.github.io/erddap-gold-standard/ (the installation guide)
- https://github.com/ioos/erddap-gold-standard (the repository)

### Updating the configuration

Copy the following files from `erddap-docker` to `erddap-gold-standard`:

| Source                        | Destination                    |
|-------------------------------|--------------------------------|
| resources/datasets.xml        | erddap/content/datasets.xml    |
| resources/setup.xml           | erddap/content/setup.xml       |
| resources/smhi.png            | erddap/content/images/smhi.png |
| resources/docker-compose.yaml | docker-compose.yaml            |

In `docker-compose.yaml` you should manually change the value for `ERDDAP_flagKeyKey`to any string value. The
documentation recommends to use a phrase. This value is secret but you will not have to enter it somewhere else and it
can be changed anytime.

#### Using git when testing out configurations

When experimenting with configurations, there is always a risk that you don't remember what you have changed. Make use
of the fact that all files are within git repositories.

See which files and lines have been updated in a repository.

```bash
$ git diff
```

Undo all local changes of a repository:

```bash
$ git reset --hard HEAD
```

#### Run the server

Start the server using docker-compose.

```bash
$ cd errdap-gold-standard
$ docker-compose up -d
```

The `-d` flag makes the server run in the background. Omit the flag when troubleshooting and you will see all output in
the terminal.

## Working with data

### Default ERDDAP workflow

Out oud the box, ERDDAP handles data in the following way:

- A single XML file called `datasets.xml` is the source for all the datasets and how different columns etc. are
  interpreted.
- An XML element describing a specific dataset can be generated with the script `GenerateDatasetsXml.sh`. This is
  intended as a starting point.
- Whenever changes have been made to `datasets.xml` the server must either be restarted or a signal must be sent to the
  server for each dataset that is to be reloaded. Signaling is made by creating an empty file named after the dataset id
  inside
  `/erddapData/hardFlag/`.

The ERDDAP version used by this project has an additional experimental feature to make it easier to work with datasets.
A directory called `/datasets.d` hosts individual XML files for each dataset. When the server is restarted or the script
`/init.d/50-datasets.d.sh` is called, all XML files are added to `datasets.xml`. Reloading of datasets must still be
performed.

### erddap-cli

This project includes `erddap-cli` to simplify the above workflow. The script handles the following:

- Generate XML for a specific dataset and put it in `/datasets.d`.
- Compile all XML files in `/datasets.d` and trigger update for each dataset.
- List all datasets described by `datasets.xml` and in files in `/datasets.d`.
- Change the attribute "active" for a specific dataset and trigger update.