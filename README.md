# ERDDAP Docker

This repository contains the complete toolchain for the ERDDAP server hosted on https://erddap.nodc.se. This includes:

- Setting up the server environment (with Ansible).
- A docker-compose solution for the ERDDAP server.
- A CLI for handling data

## Installation

### Prerequisites

The intended target for all instructions and scripts is a server running Ubuntu 22.04.4 LTS (Jammy Jellyfish).

### Cloning erddap-docker

Using the root user, clone this repository on the server as `/srv/erddap/`.

Links:

- https://github.com/sharksmhi/erddap-docker (the repository)

### Running the setup

The script `scripts/manage.sh setup` installs Ansible (with required community collections) and then runs the playbook
in `ansible/`. The playbook does the following:

- Creates the admin user `erddap` and makes sure that it can't be logged in using password.
- Enables the ufw firewall, disabling all incoming traffic except ssh, http, and https.
- Installs docker and docker-compose.
- Installs a systemd service that makes sure that the docker-compose file in `/docker/` is always running.

At any point, the setup can be verified with the script `scripts/manage.sh sync` (use flag `--check` for a read-only
dry run).

### Creating additional users

You can optionally create personal users that are allowed to add and manage data. This is
done with:

```console
bash scripts/manage.sh add-user <username>
```

The created user will get the correct groups to manage data and also an installation of erdap-cli (see below).

Note that the created user will not be able to log in using a password. The intended method is to add a public SSH key
to the file `/home/USERNAME/.ssh/authorized_keys`. For an introduction to SSH keys, see section
[Intro to using SSH keys](#intro-to-using-ssh-keys).

### Updating the configuration

In `docker/docker-compose.yml` you should manually change the value for variables starting with "ERDDAP_".

Especially `ERDDAP_flagKeyKey` should be changed to any string value (the documentation recommends to use a phrase).
This value is secret, but you will not have to enter it somewhere else and it can be changed anytime.

#### Using git when testing out configurations

When experimenting with configurations, there is always a risk that you don't remember what you have changed. Make use
of the fact that all files are within git repositories.

See which files and lines have been updated in a repository.

```console
$ git diff
```

Undo all local changes of a repository:

```console
$ git reset --hard HEAD
```

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

### erddapcli

This project includes `erddapcli` to simplify the above workflow. The tool handles the following:

- Generate XML for a specific dataset and put it in `/datasets.d`.
- Compile all XML files in `/datasets.d` and trigger update for each dataset.
- List all datasets described by `datasets.xml` and in files in `/datasets.d`.
- Change the attribute "active" for a specific dataset and trigger update.

## Intro to using SSH keys

SSH keys are a convenient way to authenticate to a server without having to enter a password. An SSH key is actually a
pair, one public and one private key. The private key should never be shared with anyone, while the public key can be
freely shared. Any server that has your public key associated with a user will accept authentication where you use your
matching private key.

### Generating a key pair

Open a terminal (PowerShell on Windows) and run:

```console
ssh-keygen -t ed25519
```

Press Enter to accept the default location. Optionally set a passphrase.

### Finding the public key locally

The key pair is typically created in a directory named `.ssh` inside your home directory. For example:

- `/home/<username>/.ssh/` (Linux)
- `/Users/<username>/.ssh/` (macOS)
- `C:\Users\<username>\.ssh\` (Windows)

The public key ends with `.pub`.

#### Linux and macOS

Show the public key (from your home directory):

```console
cat .ssh/id_ed25519.pub
```

#### Windows

Show the public key (from your home directory):

```console
type .ssh\id_ed25519.pub
```

### Add the public key to the server

On the server, inside the desired user's home directory, add the public key to the file `.ssh/authorized_keys`. The key
should be added on a new line. The username on the server doesn't have to match the username on your local computer.

### Connecting to the server using the SSH key

Once the public key has been added to the server, connect with:

```console
ssh <username>@erddap.nodc.se
```

As long as the private key is stored in the correct location, the key will automatically be used. If you have multiple
keys, they will be tested one after another until one is accepted.

If you store your key in a custom location or if you have keys for different users on the server, you can specify which
one to use with the `-i` flag:

```console
ssh <username>@erddap.nodc.se -i my_erddap_key
```
