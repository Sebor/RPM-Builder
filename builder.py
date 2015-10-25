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

def check_func(source_dir):
	pass

def build_func(source_dir, dest_dir):
	pass

def force_rebuild_func(source_dir, dest_dir):
	pass

def check_deps_func(source_dir):
	con = lite.connect('packages.db')
	for srcrpm in os.listdir(source_dir):
		args = ['sudo', 'yum-builddep', '-y', 'source_dir + os.path.sep + srcrpm']
		ExitCode = subprocess.call(args)
		if ExitCode == 0:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET Depends = 'Ok' WHERE Name = '%s'" % srcrpm)
		else:
			with con:
				cur = con.cursor()
				cur.execute("UPDATE PACKAGES SET Depends = 'Not Ok' WHERE Name = '%s'" % srcrpm)

if ACTION == "check":
	check_func()
elif ACTION == "build":
	build_func()
elif ACTION == "force_rebuild":
	force_rebuild_func()
else:
	print "RTFM!!!"

if os.path.isfile("packages.db"):
		pass
else:
	print "DB file does not exist. Creating DB file 'packages.db'"
	con = lite.connect('packages.db')
	with con:
		State = ''
		MD5 = ''
		DATETIME = ''
		Depends = ''
		cur = con.cursor()
		cur.execute("CREATE TABLE PACKAGES(Name TEXT, State INT, MD5 TEXT, DATETIME TEXT, Depends TEXT)")
		for file in os.listdir(SRCPATH):
			MD5 = hashlib.md5(file).hexdigest()
			DATETIME = datetime.datetime.now()
			cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?);", (file, State, MD5, DATETIME))