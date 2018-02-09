# SimpleSync

## Installation

* Clone this repo
* Create a virtualenv (better use virtualenvwrapper: `mkvirtualenv <venv-name>`)
* Install python requirements: `pip install -r requirements.txt`

That's it. If you want, you can create a `conf.ini` file using the `conf.ini.sample` already given, to set options for the sync program.

## Usage

Just running `python simplesync.py` will output the help message on how
to use the program, along with the various options.

    Usage: simplesync.py [OPTIONS]

    Options:
      -d, --syncdir DIRECTORY     Directory to watch.
      -r, --recursive             Watch directories recursively.
      -p, --server_port INTEGER   Server port.
      -ri, --remote_ip TEXT       Remote machine IP.
      -rp, --remote_port INTEGER  Remote machine port.
      --help                      Show this message and exit.

Eg.: To run local machine's webserver on port 8000, and to connect to a remote machine serving on port 3000, with recursive check true, and sync dir specified to be `www` in relative to current directory:

    python simplesync.py -d www -r -p 8000 -rp 3000

OR create a `conf.ini` file using the sample one provided, and set various options accordingly.

## Enhancements  
TODO:
* setup as a pip package.
    - Do `pip install <github-repo:branch>`
* Activate usage of `TheAccountant`
* Add basic auth check