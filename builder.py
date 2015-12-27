__author__ = 'Sebor'
import sqlite3 as lite
import argparse, sys, hashlib, os, datetime, subprocess, multiprocessing


parser = argparse.ArgumentParser()
parser.add_argument("source", help = "a directory contains source packages")
parser.add_argument("destination", help = "a directory where compiled packages will be stored")
parser.add_argument("action", help = "an action which applaied to packages")
args = parser.parse_args()
SRCPATH = args.source
DESTPATH = args.destination
ACTION = args.action


def set_rpmmacros():
	# Define all necessary rpmmacroses
	cpu_count = multiprocessing.cpu_count()
	rpmmacros = os.path.expanduser('~') + os.path.sep + '.rpmmacros'
	if os.path.isfile(rpmmacros):
		if '_smp_mflags' and '_unpackaged_files_terminate_build' in open(rpmmacros).read():
			print "All necessary variables already defined"
		else:
			with open(rpmmacros, "a") as f:
				f.write("%_smp_mflags -j" + str(cpu_count + 1) + "\n")
				f.write("%_unpackaged_files_terminate_build 0")
	else:
		with open(rpmmacros, "w") as f:
			f.write("%_smp_mflags -j" + str(cpu_count + 1) + "\n")
			f.write("%_unpackaged_files_terminate_build 0")
set_rpmmacros()


def create_db(source_dir):
	con = lite.connect('packages.db')
	with con:
		State = 'Unknown'
		Depends = 'Unknown'
		cur = con.cursor()
		cur.execute("CREATE TABLE PACKAGES(Name TEXT, State TEXT, MD5 TEXT, DATETIME TEXT, Depends TEXT)")
		for file in os.listdir(source_dir):
			md5 = hashlib.md5(file).hexdigest()
			Datetime = datetime.datetime.now()
			cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (file, State, md5, Datetime, Depends))


def check_func(source_dir):
	# If DB file exists
	if os.path.isfile("packages.db"):
		con = lite.connect('packages.db')
		with con:
			cur = con.cursor()
			# Create new temp table with all packages in src dir
			cur.execute("CREATE TABLE NEW_PACKAGES(Name TEXT primary key, MD5 TEXT)")
			for file in os.listdir(source_dir):
				md5 = hashlib.md5(file).hexdigest()
				cur.execute("INSERT INTO NEW_PACKAGES VALUES (?,?);", (file, md5))
			cur.execute("SELECT Name, MD5 FROM PACKAGES ORDER BY Name")
			# Create dictionary from main old table
			old_data = dict(cur.fetchall())
			cur.execute("SELECT Name, MD5 FROM NEW_PACKAGES ORDER BY Name")
			# Create dictionary from new temp table
			new_data = dict(cur.fetchall())
			# Create sets from Name and MD5 every dictionary
			old_data_set = set(old_data.iteritems())
			new_data_set = set(new_data.iteritems())
			# If length of set of difference between old_data_set and new_data_set not 0
			if len(new_data_set.difference(old_data_set)) != 0:
				State = 'Unknown'
				Depends = 'Unknown'
				# For every pair in difference
				for pkg in new_data_set.difference(old_data_set):
					Name = pkg[0]
					md5 = pkg[1]
					Datetime = datetime.datetime.now()
					# If pkg name not in main old table
					if Name not in old_data.keys():
						# Insert new pkg in old main table
						cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (Name, State, md5, Datetime, Depends))
					# Pkg name in old main table but with different MD5
					else:
						# Update info about new pkg in old main table
						cur.execute("UPDATE PACKAGES SET MD5 = ?, State = ?, Depends = ? WHERE Name = ?",
									[md5, Name, State, Depends])
			else:
				print "There are no changes in packages. Printing general status..."
			con.commit()
			# Drop new temp table
			cur.execute("DROP TABLE IF EXISTS NEW_PACKAGES")
			cur.execute("SELECT Name FROM PACKAGES WHERE State = 'Not Built' OR State = 'Unknown' ORDER BY Name")
			new_pkg = cur.fetchall()
	else:
		print "DB file doesn't exist. We don't have information about packages. Creating DB..."
		create_db(source_dir)
	return new_pkg


def force_rebuild_func(source_dir, dest_dir):
	import shutil
	#Recreate destination directory
	shutil.rmtree(dest_dir, ignore_errors=True)
	os.makedirs(dest_dir)
	try:
		os.remove("packages.db")
	except OSError:
		pass
	create_db(source_dir)
	con = lite.connect('packages.db')
	with con:
		cur = con.cursor()
		cur.execute("SELECT Name FROM PACKAGES ORDER BY Name")
		# Get list of all packages
		all_pkgs = cur.fetchall()
		for pkg in all_pkgs:
			Name = pkg[0]
			dargs = ["sudo", "yum-builddep", "-y", "--nogpgcheck", source_dir + os.path.sep + Name]
			# Exit code for yum-builddep
			ExitCodeDep = subprocess.call(dargs)
			if ExitCodeDep == 0:
				Depends = 'Resolved'
				Datetime = datetime.datetime.now()
				bargs = (["rpmbuild", "--define", "_topdir " + dest_dir,
					  "--define", "dist .el7", "--nocheck", "--rebuild", source_dir + os.path.sep + Name])
				# Exit code for rpmbuild
				ExitCodeBuild = subprocess.call(bargs)
				if ExitCodeBuild == 0:
					State = 'Built'
				else:
					State = 'Not Built'
			else:
				Depends = 'Unresolved'
				State = 'Not Built'
				Datetime = datetime.datetime.now()
			cur.execute("UPDATE PACKAGES SET State = ?, DATETIME = ?, Depends = ? WHERE Name = ?",
					[State, Datetime, Depends, Name])
			con.commit()
	return sys.exit()


def build_func(source_dir, dest_dir):
	# If DB file does not exist
	if not os.path.isfile("packages.db"):
		# Build all packages
		force_rebuild_func(source_dir, dest_dir)
	else:
		# Set list of new packages
		new_pkg = check_func(source_dir)
		con = lite.connect('packages.db')
		for newpkg in new_pkg:
			Name = newpkg[0]
			md5 = hashlib.md5(Name).hexdigest()
			dargs = (["sudo", "yum-builddep", "-y", "--nogpgcheck", source_dir + os.path.sep + Name])
			ExitCodeDep = subprocess.call(dargs)
			if ExitCodeDep == 0:
				bargs = (["rpmbuild", "--define", "_topdir " + dest_dir,
						"--define", "dist .el7", "--nocheck", "--rebuild", source_dir + os.path.sep + Name])
				ExitCodeBuild = subprocess.call(bargs)
				Datetime = datetime.datetime.now()
				if ExitCodeBuild == 0:
					State = 'Built'
				else:
					State = 'Not Built'
				Depends = 'Resolved'
			else:
				Datetime = datetime.datetime.now()
				Depends = 'Unresolved'
				State = 'Unknown'
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET State = ?, md5 = ?, Datetime = ?, Depends = ? WHERE Name = ?",
							[State, md5, Datetime, Depends, Name])
				con.commit()
	return sys.exit()


def check_deps_func(source_dir):
	# source_dir - directory with source packages
	if os.path.isfile("packages.db"):
		# Check source directory for new packages
		check_func(source_dir)
		con = lite.connect('packages.db')
		with con:
			cur = con.cursor()
			cur.execute("SELECT Name FROM PACKAGES WHERE Depends = 'Unresolved' OR Depends = 'Unknown' ORDER BY Name")
			new_deps = cur.fetchall()
			for dep in new_deps:
				Name = dep[0]
				args = ["sudo", "yum-builddep", "-y", "--nogpgcheck", source_dir + os.path.sep + Name]
				ExitCode = subprocess.call(args)
				if ExitCode == 0:
					Depends = 'Resolved'
				else:
					Depends = 'Unresolved'
				cur.execute("UPDATE PACKAGES SET Depends = ? WHERE Name = ?", [Depends, Name])
				con.commit()
	else:
		print "DB doesn't exist. You need to run 'check' first"
	return sys.exit()


def build_rake_func(source_dir, dest_dir):
	# source_dir - directory with uncompressed source files
	# dest_dir - directory for future repository
	import shutil, glob
	# Check if source path and destination path exist
	if os.path.isdir(source_dir) and os.path.isdir(dest_dir):
		os.chdir(source_dir)
		args = ["rake", "artifact:rpm"]
		ExitCode = subprocess.call(args)
		if ExitCode == 0:
			rpm_path = source_dir + os.path.sep + "*.rpm"
			# glob.glob(path) return a possibly-empty list of path names that match path
			for rpm_file in glob.glob(rpm_path):
				# Copy all '/source_dir/*.rpm' files to dest_dir
				shutil.copy2(rpm_file, dest_dir)
		else:
			print "RPM-package hasn't been built!"
	else:
		print "Check PATHs to source and destination directories!"
	return sys.exit()


def check_list_func(source_dir, dest_dir):
	# source_dir - directory with all compilled pkgs
	# dest_dir - directory for future repository
	import shutil
	try:
		# Open file contained all necessary packages. This file must contain only package names
		with open("list.txt", "r") as f:
			pkg_list = f.read().splitlines()
	except:
		print "File 'list.txt' doesn't exist!"
		sys.exit()
	# Create a list of files which has been copied
	with open("copied_pkg.txt", "w") as copied:
		cur_list = []
		for filename in sorted(os.listdir(source_dir)):
			args = (["rpm", "-q", "--queryformat", "'%{NAME}'", "--package",
					source_dir + os.path.sep + filename])
			pkg_name = subprocess.check_output(args)[1:-1]
			if pkg_name in sorted(pkg_list):
				# Copy every necessary package to dest_dir
				pkg_path = source_dir + os.path.sep + filename
				shutil.copy2(pkg_path, dest_dir)
				# Add copied pkg name to 'copied_pkg.txt'
				copied.write(pkg_name + "\n")
				cur_list.append(pkg_name)
	# Create and write list of missing packages
	miss_pkg = set(pkg_list) - set(cur_list)
	with open("missing_pkg.txt", "w") as m:
		for pkg in sorted(miss_pkg):
			m.write(pkg + "\n")
	return sys.exit()


if ACTION == "check":
	Packages = check_func(SRCPATH)
	for package in Packages:
		print package[0]
elif ACTION == "build":
	build_func(SRCPATH, DESTPATH)
elif ACTION == "force_rebuild":
	force_rebuild_func(SRCPATH, DESTPATH)
elif ACTION == "check_deps":
	check_deps_func(SRCPATH)
elif ACTION == "build_rake":
	build_rake_func(SRCPATH, DESTPATH)
elif ACTION == "check_list":
	check_list_func(SRCPATH, DESTPATH)
else:
	print "The action can be 'check', 'build', 'force_rebuild', 'check_deps', 'build_rake' or 'check_list'"
