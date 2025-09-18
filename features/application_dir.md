## Feature: standard application directory

Modern applications that store persistent data use a platform specific
directory to hold things like:

- config files in YAML or TOML
- caches of downloade data
- user preferences
- application specific databases in SQLite or embedded key/value
  stores
  
Let’s add a module to retrocast that uses the
[platformdirs](https://platformdirs.readthedocs.io/en/latest/) module
to locate the appropriate application directory for the platform we
are running on.

The location of that directory should be passed to subcommands as a Python
pathlib.Path object using a click context object. 

Then we should change the retrocast `auth` subcommand to save its
captured token information in the application directory. Use the same
format that’s currently used, JSON, to store the token
information. All functions that depend on the auth token should
reference this file in the application directory.
