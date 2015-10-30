__author__ = 'Sebor'
import sqlite3 as lite
import argparse, sys, hashlib, os, datetime, subprocess, multiprocessing


parser = argparse.ArgumentParser()
parser.add_argument("source")
parser.add_argument("destination")
parser.add_argument("action")
args = parser.parse_args()
SRCPATH = args.source
DESTPATH = args.destination
ACTION = args.action


# Define rpmmacros file for multicore compiling
cpu_count = multiprocessing.cpu_count()
rpmmacros = os.path.expanduser('~') + os.path.sep + '.rpmmacros'
if os.path.isfile(rpmmacros):
	if '_make' in open(rpmmacros).read():
		print "Multicore compile variable already defined"
	else:
		with open(rpmmacros, "a") as f:
			f.write("%_make    /usr/bin/make -j " + str(cpu_count))
			print "Set multicore compile variable"
else:
	print "Rpmmacros file not found!"


def create_db(source_dir):
	con = lite.connect('packages.db')
	with con:
		State = 'Unknown'
		Depends = 'Unknown'
		cur = con.cursor()
		cur.execute("CREATE TABLE PACKAGES(Name TEXT, State INT, MD5 TEXT, DATETIME TEXT, Depends TEXT)")
		for file in os.listdir(source_dir):
			md5 = hashlib.md5(file).hexdigest()
			Datetime = datetime.datetime.now()
			cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (file, State, md5, Datetime, Depends))
	return sys.exit()


def check_func(source_dir):
	# If DB file exists
	if os.path.isfile("packages.db"):
		con = lite.connect('packages.db')
		with con:
			cur = con.cursor()
			# Create new temp table with all packages in src dir
			cur.execute("CREATE TABLE NEW_PACKAGES(Name TEXT, MD5 TEXT)")
			for file in os.listdir(source_dir):
				md5 = hashlib.md5(file).hexdigest()
				cur.execute("INSERT INTO NEW_PACKAGES VALUES (?,?);", (file, md5))
			cur.execute("SELECT Name, MD5 FROM PACKAGES")
			# Create dictionary from main old table
			old_data = dict(cur.fetchall())
			cur.execute("SELECT Name, MD5 FROM NEW_PACKAGES")
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
						# Undate info about new pkg in in old main
						cur.execute("UPDATE PACKAGES SET MD5 = ?, State = ?, Depends = ? WHERE Name = ?", [md5, Name, State, Depends])
			else:
				print "There are no changes in packages. Printing general status..."
			con.commit()
			# Drop new temp table
			cur.execute("DROP TABLE IF EXISTS NEW_PACKAGES")
			cur.execute("SELECT Name FROM PACKAGES WHERE State = 'Not Built' OR State = 'Unknown'")
			new_pkg = cur.fetchall()
	else:
		print "DB file doesn't exist. We don't have information about packages. Creating DB..."
		create_db(source_dir)
	return new_pkg


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
			args = ["rpmbuild", "--define", "_topdir " + dest_dir, "--rebuild", source_dir + os.path.sep + newpkg[0]]
			ExitCode = subprocess.call(args)
			md5 = hashlib.md5(newpkg[0]).hexdigest()
			Datetime = datetime.datetime.now()
			Name = newpkg[0]
			if ExitCode == 0:
				State = 'Built'
				Depends = 'Resolved'
			else:
				State = 'Not Built'
				Depends = 'Unknown'
			with con:
				cur = con.cursor()
				cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (Name, State, md5, Datetime, Depends))
				cur.execute("DROP TABLE IF EXISTS NEW_PACKAGES")
	return sys.exit()


def force_rebuild_func(source_dir, dest_dir):
	if os.path.isfile("packages.db"):
		# Delete and create DB
		os.remove("packages.db")
		create_db(source_dir)
	else:
		create_db(source_dir)
	con = lite.connect('packages.db')
	for srcrpm in os.listdir(source_dir):
		args = ["rpmbuild", "--define", "_topdir " + dest_dir, "--rebuild", source_dir + os.path.sep + srcrpm]
		ExitCode = subprocess.call(args)
		if ExitCode == 0:
			State = 'Built'
			Depends = 'Resolved'
		else:
			State = 'Not Built'
			Depends = 'Unknown'
		with con:
			cur = con.cursor()
			cur.execute("UPDATE PACKAGES SET State = ?, Depends = ? WHERE Name = ?", [State, Depends, srcrpm])
	return sys.exit()


def check_deps_func(source_dir):
	if os.path.isfile("packages.db"):
		# Check source directory for new packages
		check_func(source_dir)
		con = lite.connect('packages.db')
		with con:
			cur = con.cursor()
			cur.execute("SELECT Name FROM PACKAGES WHERE Depends = 'Unresolved' OR Depends = 'Unknown'")
			new_deps = cur.fetchall()
			for dep in new_deps:
				Name = dep[0]
				args = ['sudo', 'yum-builddep', '-y', source_dir + os.path.sep + Name]
				ExitCode = subprocess.call(args)
				if ExitCode == 0:
					Depends = 'Resolved'
				else:
					Depends = 'Unresolved'
				cur.execute("UPDATE PACKAGES SET Depends = ? WHERE Name = ?", [Depends, Name])
	else:
		print "DB doesn't exist. You need to run 'check' first"
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
else:
	print "The action can be 'check', 'build', 'force_rebuild' or 'check_deps'"
