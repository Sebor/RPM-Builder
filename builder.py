__author__ = 'Sebor'
import sqlite3 as lite
import argparse, sys, hashlib, os, datetime

parser = argparse.ArgumentParser()
parser.add_argument("source")
parser.add_argument("dest")
parser.add_argument("action")
args = parser.parse_args()
SRCPATH = args.source
DESTPATH = args.dest
ACTION = args.action

def check_func():
	pass

def build_func():
	pass

def force_rebuild_func():
	pass

def check_deps_func():
	pass

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
		cur = con.cursor()
		cur.execute("CREATE TABLE PACKAGES(Name TEXT, State INT, MD5 TEXT, DATETIME TEXT)")
		for file in os.listdir(SRCPATH):
			MD5 = hashlib.md5(file).hexdigest()
			DATETIME = datetime.datetime.now()
			cur.execute("INSERT INTO PACKAGES VALUES (?,?,?,?);", (file, State, MD5, DATETIME))