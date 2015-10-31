# RPM-Builder
Script for automatic building of src.rpm packages

Main functionality:
1. Building rpm-packages with information from local DB-file (sqlite)
2. The script gets 3 arguments: "source directory", "destination directory and action".
The "action" can be:
a)force_rebuild - purge dest. dir and build all src packages
b)check_deps - scanning DB for packages with unresolved dependencies and installing those dependencies
c)check - printing all packages which are not built
b)build - buiilding all packages which are not built

All information about status of packages is saved in local DB-file
