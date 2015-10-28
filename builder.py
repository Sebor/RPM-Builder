__author__ = 'Sebor'
import sqlite3 as lite
import argparse, sys, hashlib, os, datetime, subprocess

parser = argparse.ArgumentParser()
parser.add_argument("source")
parser.add_argument("destination")
parser.add_argument("action")
args = parser.parse_args()
SRCPATH = args.source
DESTPATH = args.destination
ACTION = args.action

def create_db(source_dir):
	con = lite.connect('packages.db')
	with con:
		State = 'unknown'
		Depends = 'unknown'
		cur = con.cursor()
		cur.execute("CREATE TABLE PACKAGES(Name TEXT, State INT, MD5 TEXT, DATETIME TEXT, Depends TEXT)")
		for file in os.listdir(source_dir):
			md5 = hashlib.md5(file).hexdigest()
			Datetime = datetime.datetime.now()
			cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (file, State, md5, Datetime, Depends))
	return sys.exit()


def check_func(source_dir):
	if os.path.isfile("packages.db"):
		con = lite.connect('packages.db')
		with con:
			cur = con.cursor()
			cur.execute("CREATE TABLE NEW_PACKAGES(Name TEXT, MD5 TEXT)")
			for file in os.listdir(source_dir):
				md5 = hashlib.md5(file).hexdigest()
				cur.execute("INSERT INTO NEW_PACKAGES VALUES (?,?);", (file, md5))
			cur.execute("SELECT Name, MD5 FROM PACKAGES")
			old_data = dict(cur.fetchall())
			cur.execute("SELECT Name, MD5 FROM NEW_PACKAGES")
			new_data = dict(cur.fetchall())
			old_data_set = set(old_data.iteritems())
			new_data_set = set(new_data.iteritems())
			if len(new_data_set.difference(old_data_set)) != 0:
				State = 'unknown'
				Depends = 'unknown'
				for pkg in new_data_set.difference(old_data_set):
					if pkg[0] not in old_data.keys():
						Name = pkg[0]
						md5 = pkg[1]
						Datetime = datetime.datetime.now()
						cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (Name, State, md5, Datetime, Depends))
					else:
						Name = pkg[0]
						md5 = pkg[1]
						cur.execute("UPDATE PACKAGES SET MD5 = ?, State = ?, Depends = ? WHERE Name = ?", [md5, Name, State, Depends])
			con.commit()
			cur.execute("DROP TABLE NEW_PACKAGES")
			cur.execute("SELECT Name from PACKAGES WHERE State = 'Not Built' OR State = 'unknown'")
			for pkg in cur.fetchall():
				print pkg
	else:
		print "DB file doesn't exist. We don't have information about packages. Creating DB..."
		create_db(source_dir)
	return sys.exit()


def build_func(source_dir, dest_dir):
	if not os.path.isfile("packages.db"):
		force_rebuild_func(source_dir, dest_dir)
	else:
		con = lite.connect('packages.db')
		with con:
			State = ''
			Depends = ''
			cur = con.cursor()
			cur.execute("CREATE TABLE NEW_PACKAGES(Name TEXT, State INT, MD5 TEXT, DATETIME TEXT, Depends TEXT)")
			for file in os.listdir(source_dir):
				md5 = hashlib.md5(file).hexdigest()
				Datetime = datetime.datetime.now()
				cur.execute("INSERT INTO NEW_PACKAGES VALUES (?,?,?,?,?);", (file, State, md5, Datetime, Depends))
			cur.execute("SELECT DISTINCT Name FROM NEW_PACKAGES  WHERE Name Not IN (SELECT DISTINCT Name FROM PACKAGES)")
			new_pkg = cur.fetchall()
		for newpkg in new_pkg:
			args = ['rpmbuild', '--define', '_topdir ', dest_dir, '--rebuild', source_dir + os.path.sep + newpkg]
			ExitCode = subprocess.check_call(args)
			md5 = hashlib.md5(newpkg).hexdigest()
			Datetime = datetime.datetime.now()
			if ExitCode == 0:
				State = 'Built'
				with con:
					cur = con.cursor()
					cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (newpkg, State, md5, Datetime, Depends))
					cur.execute("DROP TABLE NEW_PACKAGES")
			else:
				State = 'Not Built'
				with con:
					cur = con.cursor()
					cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?,?);", (newpkg, State, md5, Datetime, Depends))
					cur.execute("DROP TABLE NEW_PACKAGES")


def force_rebuild_func(source_dir, dest_dir):
	if os.path.isfile("packages.db"):
		os.remove("packages.db")
		create_db(source_dir)
	else:
		create_db(source_dir)
	con = lite.connect('packages.db')
	for srcrpm in os.listdir(source_dir):
		args = ['rpmbuild', '--define', '_topdir ', dest_dir, '--rebuild', source_dir + os.path.sep + srcrpm]
		ExitCode = subprocess.call(args)
		if ExitCode == 0:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET State = 'Built' WHERE Name = '%s'" % srcrpm)
		else:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET State = 'Not Built' WHERE Name = '%s'" % srcrpm)


def check_deps_func(source_dir):
	con = lite.connect('packages.db')
	for srcrpm in os.listdir(source_dir):
		args = ['sudo', 'yum-builddep', '-y', source_dir + os.path.sep + srcrpm]
		ExitCode = subprocess.call(args)
		if ExitCode == 0:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET Depends = 'Resolved' WHERE Name = '%s'" % srcrpm)
		else:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET Depends = 'Unresolved' WHERE Name = '%s'" % srcrpm)


if ACTION == "check":
	check_func(SRCPATH)
elif ACTION == "build":
	build_func(SRCPATH, DESTPATH)
elif ACTION == "force_rebuild":
	force_rebuild_func(SRCPATH, DESTPATH)
else:
	print "RTFM!!!"
