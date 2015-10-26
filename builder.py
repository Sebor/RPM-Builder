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
		State = ''
		md5 = ''
		Datetime = ''
		Depends = ''
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
            cur.execute("SELECT Name from PACKAGES WHERE State = 'Error'")
            print cur.fetchone()


def build_func(source_dir, dest_dir):
	pass

def force_rebuild_func(source_dir, dest_dir):
    if os.path.isfile("packages.db"):
        os.remove("packages.db")
        create_db(source_dir)
    else:
        create_db(source_dir)
    for srcrpm in os.listdir(source_dir):
        args = ['rpmbuild', '--define', '_topdir ', dest_dir, '--rebuild', source_dir + os.path.sep + srcrpm]
        subprocess.call(args)


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
