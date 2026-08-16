# Task: fix this issue in the repository

The repository (checkout of pallets/flask at commit d8c37f43724cd9fb0870f77877b7c4c7e38a19e0) is the CURRENT WORKING DIRECTORY.

Raise error when blueprint name contains a dot
This is required since every dot is now significant since blueprints can be nested. An error was already added for endpoint names in 1.0, but should have been added for this as well.
