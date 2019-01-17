#! /usr/bin/env python
# vim: set syntax=none nospell:
# ############################################## #
# title: myphyle 2019-01
# author: geoff.mcnamara@gmail.com
# purpose: flat file web based table management
# created: 2019-01-01
# requires: 
#     python2 (only because it is easier to install if used woth apache on ubuntu)
#     wraphtml.py
#     bottle
#     sqlalchemy
#     sqlite3 (or another SQL alternativei but you will need to change the app_URI)
#     bcrypt
# Notes:
#  var_d is a variable of type(dict)
#  var_l is a variable of type(list)
# status: WIP as of 2019-01-10
# todo: password encryption - bcrypt
# - delete action
# - orderby
# - filterby
# - col sort button
# - improve pg_size - use a range instead of counting rows
# - reports design
# - fix/improve sql_filter
# ############################################# #

# ####### Imports ##### #
import os
import sys
import datetime
import re
# import sqlite3
from wraphtml import WrapHtml
import bottle
from bottle import run, get, post, request, route, redirect
from beaker.middleware import SessionMiddleware
import beaker
from bcrypt import hashpw, gensalt
from sqlalchemy import Column, Integer, String, create_engine, Table, MetaData, text, schema, inspect, select, and_, desc
from sqlalchemy.orm import sessionmaker
# next lines used for debugging
sys.path.append("/home/geoffm/dev/python/gmodules/")
from dbug import dbug  # noqa: E402


# ######################## #
# ### [CONFIG OPTIONS] ### #
# ######################## #
# Where is all starts - the sqlite3 database will be named using __file__ plus ".db"
# app_name: probably no need to change this but you can - currently uses this filename
app_name = os.path.splitext(os.path.basename(__file__))[0]  
# home_d: Home dictionary entry - optional - displays top left of nav bar if provided
home_d = {"Home": "/companionway.net"}  
# organization: used in copyright displayed on bottom left
organization = "companionway"
# app_dir: this dir is important and must exist - Keep this away from the webserver DOCROOT
# - it is where the database for this app will reside
db_dir = "/var/tmp"  
# app_URI: this is the completion of where the db will be and what sql dialect will be used
app_URI = "sqlite:///" + db_dir + "/" + app_name + ".db"
# session_dir: is a work dir where session data is kept - keep this away from your webserver DOCROOT
session_dir = "/var/tmp"
# foot_center: displays in the center of the footer - can be whatever you want, including nothing ie: ""
foot_center = "Enjoy your day!"
# input_size: WIP
input_size = 40
app_title = "myPhyle"
pg_size = 20
# ########################## #
# ### EOB CONFIG OPTIONS ### #
# ########################## #


# #### establish user session opts #### #
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 30000,
    'session.data_dir': session_dir,
    'session.auto': True
}

app = beaker.middleware.SessionMiddleware(bottle.app(), session_opts)
# session = bottle.request.environ.get('beaker.session')

# #### EOB establish user session opts #### #

# ####### establish sqlalchemy app defaults ##### #
app_engine = create_engine(app_URI, echo=True)
app_meta = MetaData(app_engine, reflect=True)
app_conn = app_engine.connect()
# app_Session = sessionmaker(bind=app_engine)
# app_session = app_Session()
# ####### EOB establish sqlalchemy defaults ##### #

# #### establish globals #### #
app_var = {}
app_var['msg']=""


# ### Sandbox1 #### #
# # Declare create table Example
# # table = Table('Example',meta,
#               Column('id',Integer, primary_key=True),
#               Column('name',String))
# # Now Create all tables - specifically Example declared above
# app_meta.create_all()
# for _t in app_meta.tables:
#    print("Table: ", _t)
# Now drop the table Example
# app_meta.tables['Example'].drop()
# #### to start over ####
# MAKE SURE YOU WANT TO DO THIS!!!!
# dbug("STARTING OVER - droping 3 essential tables!!!")
# dbug("app_meta.tables: " + str(app_meta.tables) + " len(app_meta.tables): " + str(len(app_meta.tables)))
# if len(app_meta.tables) > 0:
#     for table in app_meta.tables:
#         if table=='app_users': app_meta.tables['app_users'].drop()
#         if table=='app_views': app_meta.tables['app_views'].drop()
#         if table=='app_fcontrol': app_meta.tables['app_fcontrol'].drop()
########################
# # declare essential table object
# views = Table('app_views', app_meta,
#     Column('id', Integer, primary_key=True),
#     Column('db_uri', String),
#     Column('tablename', VARCHAR(50), NOT NULL),
#     # etc
#     )
# table_name = views.name
# print("table_name: " + table_name)
# cols_l = views.columns.keys()
# print("cols_l: " + str(cols_l))
# # or another example
# cols_l = app_meta.tables['app_views'].columns.keys()
# print("cols_l: " + str(cols_l))db_uri
# now recreate fcontrol table
# ### EOF Sandbox1 #### #

# ########### Tables #####################
# Structure our three essential app tables
# these need app_meta = MetaData(app_engine)?
USERS = Table(
    'app_users', app_meta,
    Column('id', Integer, primary_key=True),
    Column('viewname', String(50), nullable=False),
    Column('username', String(50), nullable=False),
    Column('password', String(250), nullable=False),
    Column('role', String),
    Column('note', String(250)),
    Column('created', String(50)),
    Column('modified', String(50)),
    extend_existing=True,
    )

VIEWS = Table(
    'app_views', app_meta,
    Column('id', Integer, primary_key=True),
    Column('viewname', String(50), nullable=False),
    Column('uri', String(50), nullable=False),
    Column('tablename', String(250), nullable=False),
    Column('row_cols', String(250)),
    Column('detail_cols', String(250)),
    Column('orderby', String(250)),
    Column('filterby', String(250)),
    Column('note', String(250)),
    Column('created', String(50)),
    Column('modified', String(50)),
    extend_existing=True,
    )

FCONTROL = Table(
    'app_fcontrol', app_meta,
    Column('id', Integer, primary_key=True),
    Column('viewname', String(50), nullable=False),
    Column('fieldname', String(250), nullable=False),
    Column('calc', String(250)),
    Column('mask', String(250)),
    Column('note', String(250)),
    Column('created',  String, default=datetime.datetime.now),
    Column('modified', String, onupdate=datetime.datetime.now),
    extend_existing=True,
    )

# ######## EOB Tables ########### #


# ####### Functions ############# #

# ########################
def table_exists(tablename, action="", engine=app_engine, meta=app_meta):
    # ####################
    """
    docstring, untested
    action: create|drop|populate|key(test for primary_key)
    requires: from sqlalchemy import inspect, create_engine
        engine = create_engine(uri, options)
    """
    if tablename not in engine.table_names():
        # dbug("Fould the table! [" + tablename + "]")
    # else:
        # dbug("No can find tablename [" + tablename + "]")
        return False
    # assuming table exists...
    # meta = MetaData(engine, reflect=True)
    # dbug("Begin table_exists(" + str(tablename) + ", " + action + ")")
    inspection = inspect(engine)
    # dbug("All inspect(engine) tables: " + str(inspection.get_table_names()))
    for inspect_table in inspection.get_table_names():
        # dbug("Checking table [" + str(inspect_table) + "] from inspect(engine)... ")
        if inspect_table == tablename:
            # dbug("Found " + tablename + " table in engine table_names")
            if action == 'drop':
                # dbug("Dropping [" + str(tablename) + "] as requested.")
                tablename.drop(engine)
            if action == 'populate':
                # dbug("Populating [" + str(tablename) + "] as requested.")
                do_populate(tablename)
            if action == 'key':
                table_o = meta.tables[tablename]
                id_l = [key.name for key in inspect(table_o).primary_key]
                try: 
                    dbug("id_l: " + str(id_l[0]))
                except Exception, e:
                    dbug("Primary key not found with error: " + str(e))
                    return False
            return True
        # else:
            # dbug("inspect_table: " + inspect_table + " does not match supplied tablename: " + tablename)
    if action == 'create':
        dbug("Creating all tables")
        meta.create_all()
        return True
    dbug("Did not find " + str(tablename) + " table")
    return False


# ##########################
def do_populate(tablename):
    # #####################
    """
    docstring
    untested
    """
    dbug("Begin do_populate(" + tablename + ")")
    new_records = []
    my_table = app_meta.tables[tablename]
    # VIEWS
    if tablename == 'app_views':
        new_records.append(VIEWS.insert().values(
                        viewname='app_views',
                        uri=app_URI,
                        tablename=VIEWS.name,
                        row_cols='id, viewname, uri, row_cols',
                        note='Do not delete this record'))
        new_records.append(VIEWS.insert().values(
                        viewname="app_users",
                        uri=app_URI,
                        tablename="app_users",
                        row_cols="id, viewname, uri, row_cols",
                        note="Do not delete this record"))
        new_records.append(VIEWS.insert().values(
                        viewname="app_fcontrol",
                        uri=app_URI,
                        tablename="app_fcontrol",
                        row_cols="id, viewname, uri, row_cols",
                        note="Do not delete this record"))
    # USERS
    if tablename == 'app_users':
        new_records.append(USERS.insert().values(
                        viewname="app_views",
                        username="admin",
                        password="plaintext",
                        role="admin",
                        note="Do not delete this record"))
        new_records.append(USERS.insert().values(
                        viewname="app_users",
                        username="admin",
                        password="plaintext",
                        role="admin",
                        note="Do not delete this record"))
        new_records.append(USERS.insert().values(
                        viewname="app_fcontrol",
                        username="admin",
                        password="plaintext",
                        role="admin",
                        note="Do not delete this record"))
    # FCONTROL
    if tablename == 'app_fcontrol':
        new_records.append(FCONTROL.insert().values(
                        viewname='app_views',
                        fieldname='modified',
                        calc='SELECT NOW()',
                        note='Example of using fcontrol calc'))
    # Execute each insert
    # now add them via db_session
    # WIP2 #
    # ins_stmt = VIEWS.insert().values(viewname='tst',tablename='tst',uri='uri')
    # result = conn.execute(ins_stmt)
    # dbug("Just tried conn.execute(" + ins_stmt + ")")
    for new_record in new_records:
        dbug("Attempting to add: " +str( new_record))
        result = app_conn.execute(new_record)
        # view_session.add(new_record)
        # view_session.commit()
        # or ??
        # view_session.flush()
  

# ###################
def tables_l(engine=app_engine):
    # ###############
    """
    input:    engine  # eg engine = create_engine('sqlite:////myfile.db')  # , echo=True)
    return:   table list from the engine db
    requires: from sqlalchemy import inspect
    purpose:  quick way to get a list of tables
    """
    inspector = inspect(engine)
    tables_l = inspector.get_table_names()
    return tables_l
    # EOB def tables_l(engine):
    


# ##################  
def cols_l(table_o, engine=app_engine):
    # ##############
    """
    unusable????
    input:  meta table obj  # eg meta = MetaData(engine); table = meta['mytable'] or mytable = Table('mytable', meta, ...; 
    return: list of col names
    """
    # tobe tested
    # inspector = inspect(engine)
    # inspector.get_columns(tablename)
    # or
    # cols_l = [col.name for col in table_o.columns]
    # or
    cols_l = table_o.columns.keys()
    return cols_l
    # EOB def cols_l(table_o):


# ################################
def col_exists(table_o, col_name):
    # ############################
    """
    docstring
    """
    cols_l = cols_l(table_o)
    if col_name in cols_l:
        return True
    return False
    # EOB def col_exists(table_o, col_name):


# ##################
def form_d(request):
    # ##############
    """
    input:  is form request obj
    return: is a dictionary pairing of form_name: form_value
    note:   lambdas to avoid errors in evaluating bottle.request.* 
    use:
        form_data = form_d(request)
        my_var = form_data['my_var']
    """
    _dicts = [
        lambda: request.json,
        lambda: request.forms,
        lambda: request.query,
        lambda: request.files,
    ]
    form_d = {}
    for dict in _dicts:
        try:
            dict = dict()
        except KeyError:
            continue
        if dict is not None and hasattr(dict, 'items'):
            for key, val in dict.items():
                form_d[key] = val
    return form_d 
    # EOB def form_d(request):


# ############################################
def check_login(viewname, username, password):
    # ########################################
    """
    docstring
    WIP
    """
    dbug("Begin check_login("+viewname+", "+username+", "+password+")")

    session = bottle.request.environ.get('beaker.session')
    dbug("session: " + str(session) + " we are starting check_login - we are nulling out session info")
    dbug("session: " + str(session) + " we are starting check_login")
    # session['username'] = ""
    # session['viewname'] = ""
    #if session.has_key('username')  and session.has_key('viewname'):
    #    username = session['username']
    #    viewname = session['viewname']
    #    dbug("session already established with " + session['username'] + " for " + session['viewname'])
    #    app_var['msg'] += "<br>You have an exisiting session with username: " + username + " and viewname: " + viewname
    #else:
    #    # username = ""
    #    # viewname = ""
    #    dbug("We will now go check the database ... ")
    #    # dbug("... because [session] username [" + session['username'] + "] or viewname [" + session['viewname'] + "] is a problem")
    #    # assuming session info failed...
    #    # app_var['msg'] += "FAILURE error: with session username: " + username + " and session viewname: " + viewname
    #    # return False
    # continue user check against app_users table
    users = app_meta.tables['app_users']
    views = app_meta.tables['app_views']
    try:
        sel = select([users]).where(and_(users.c.username==username, users.c.viewname==viewname))
        res = app_conn.execute(sel)
        res_len = len(res)  # for debugging and trial
        cnt = row_count(res)
        dbug("cnt: " + str(cnt) + " len(res): " + str(res_len))
        for record in res:
            dbug("record: " + str(record))
        if cnt == 0:
            dbug("No matching rows found in users table for user: " + username + " viewname: " + viewname)  
            app_var['msg'] += "<br>No matching rows found in users table for user: " + username + " viewname: " + viewname
    except Exception, e:
            # app_var['msg'] += "<br>FAILURE: error: " + str(e) + " No matching record found in users table for: " + username
            # app_var['msg'] += " and viewname: " + viewname
            dbug("FAILURE: error: " + str(e) + " No matching record found in users table for: " + username)
    res = app_conn.execute(sel)  # you have to reset the result each time you need it
    for row in res:
        dbug("row: " + str(row))
        if row['viewname'] == viewname and row['username'] == username:
            app_var['msg'] += "<br>There is a user entry [" + username + "] for the viewname [" + viewname + "] in the users table"
        # dbug("just for grins hashed row['password']: " + hashpw(row['password'].encode('utf-8'), gensalt()))
        if not row['password'].encode('utf-8').startswith("$2b$"):
            dbug("Does NOT look like a hashed pw")
            dbug("this must be a plain-text password")
            # so now we need to hash it and save it WIP
            hashed_password  = hashpw(row['password'].encode('utf-8'), gensalt())
            vals_d = {'password': hashed_password}
            action_stmt = USERS.update().values(vals_d).where(and_(USERS.c.viewname == viewname, USERS.c.username == username)) 
            result = app_conn.execute(action_stmt)  
            hashed_password = row['password'].encode('utf-8')
            res = app_conn.execute(sel)  # you have to reset the result each time you need it
        else:
            hashed_password = row['password'].encode('utf-8')
        # dbug("hashed_password: " + hashed_password) # fails: + " oh and res_len=" + str(res_len))
        if row['password'] == password or hashpw(password, hashed_password) == hashed_password:  # this is TEMPORARY AND NEEDS TO BE REMOVED! WIP
            app_var['msg'] += "<br>The password matches"
        # if row['viewname'] == viewname or row['username'] == username and hashpw(password,gensalt()) == row['password']:
            # now make sure there is an entry in the app_views table for this viewname
            dbug("Checking for viewname [" + viewname + "] in the views table")
            try:
                sel = select([views]).where(views.c.viewname==viewname)
                result = app_conn.execute(sel)
                cnt = row_count(result)
                dbug("cnt: " + str(cnt))
                if cnt == 0:
                    dbug("No records found ( cnt: " + str(cnt) + ") to match in viewname for: " + viewname)
                    app_var['msg'] += ("<p>No records found in views table for viewname: " + viewname + "</p>")
                else:
                    app_var['msg'] += "<p>There is a viewname [" + viewname + "] record in the views table</p>"
                    app_var['msg'] += "<p>Successful login authentication</p>"
                return True
            except Exception, e:
                dbug("oops maybe no records matched views.viewname " + str(e))
                app_var['msg'] += "<p>No record found in the views table for: " + viewname + "</p>"
                return False
        else:
            app_var['msg'] += "<br>Password failed..."
            # else here is strickly for debugging
            dbug("hmmm: row[viewname]=" + row['viewname'] + " viewname=" + viewname)
            dbug("hmmm: row[username]=" + row['username'] + " username=" + username)
            dbug("hmmm: row[password]=" + row['password'] + " password=" + password)
    app_var['msg'] += "<br>Login check failed for username: " + username + " and viewname: " + viewname
    dbug("returning false")
    return False
    # EOB def check_login(viewname, username, password):


# ########################
def row_d(cols_l, result):
    # ####################
    """
    docstring, unusable???
    input: result = conn.execute(sel)
    """
    row_d = [dict(zip(cols_l,row)) for row in result]
    return row_d
    # EOB def row_d(cols_l, result):


# ####################
def row_count(result):
    # ################
    """
    docstring
    """
    # dbug("Begin row_count(result)")
    rowcnt = 0
    for record in result:
        rowcnt += 1
        # dbug("record: " + str(record))
    # dbug("End row_count(" + str(result) + ") with rowcnt: " + str(rowcnt))
    return rowcnt
    # EOB def row_count(result) #


# ######### EOB Functions ########### #


# #### Sandbox2 #### #
# print("app_meta.tables.keys(): " + str(app_meta.tables.keys()))
# sys.exit()
# #### sanity check - make sure essential tables exist and are populated ### #
# if table is missing - create it and populate it
for table in app_meta.tables:
    # print("DEBUG: checking for table: " + table)
    if not table_exists(table):
        # print("DEBUG: [" + table + "] table not found, creating and populating it...")
        table_exists(table, 'create')
    # ### #
    # check to see if there are no records - populate the table
    # dbug("Checking record number in table: " + table)
    sel = VIEWS.select()
    sel = app_meta.tables[table].select()
    result = app_conn.execute(sel)
    # dbug("attempted app_conn")
    cnt = row_count(result)
    if cnt == 0:
        # dbug("cnt: " + str(cnt))
        table_exists(table,'populate')
    # else:
        # dbug("We found a match for app_views and it has at least one record... continuing...")
# explore "text" module using from sqlalchemy import text
#    data = ( { "id": 1, "title": "The Hobbit", "primary_author": "Tolkien" },
#             { "id": 2, "title": "The Silmarillion", "primary_author": "Tolkien" },
#    )
#    statement = text("""INSERT INTO book(id, title, primary_author) VALUES(:id, :title, :primary_author)""")
#    for line in data:
#        con.execute(statement, **line)
# or use execute method
# with engine.connect() as con:
#    rs = con.execute('SELECT * FROM book')
#    for row in rs:
#        print row
#
# ### EOB sanity check ### #

# views = app_meta.tables['app_views']
# cols_l = cols_l(views)
# # sel = selected_row = select([views]).where('viewname'=='app_views')
# sel = select([views]).where(views.c.viewname=='app_views')
# result = app_conn.execute(sel)
# print("row_d: " + str(row_d(cols_l, result)))
# #### EOB Sandbox2 #### #

# ############################## #
# ########### routes ########### #
# ############################## #
# ##########
@route('/')
def home():
    # #####
    """
    docstring
    """
    session = bottle.request.environ.get('beaker.session')
    print("session: " + str(session))
    if not check_login('', '', ''):
        redirect('/login')
    session = bottle.request.environ.get('beaker.session')
    viewname = session['viewname']
    username = session['username']
    redirect('/db/rows/' + viewname)


# ###############
@get('/login')  # or @route('/login')
def login():
    # ##########
    """
    docstring
    # global app_vars
    # print("entering get(/login)...")
    """
    session = bottle.request.environ.get('beaker.session')
    dbug("session: " + str(session))
    if session.has_key('viewname'):
        dbug("Found session viewname: " + session['viewname'])
        viewname = session['viewname']
    else:
        dbug("Did not find a session[viewname]... ") 
        viewname = 'viewname'
    if session.has_key('username'):
        dbug("Found session viewname: " + session['viewname'])
        username = session['username']
    else:
        username = ''
    dbug("Near begining of /login with: viewname: " + viewname + " username: " + username)
    app_var['msg'] = ""  # clear/reset msg
    sel = VIEWS.select()
    result = app_conn.execute(sel)
    viewnames = []
    for row in result:
        viewnames.append(row['viewname'])

    content = "<center>"
    content += '''
        <!-- 
        <div style="border: solid #009090; width: 300px; padding: 25px; margin: 25px;"> 
        <div style="background-color: lightgrey; border: solid #0090F0; width: 300px; padding: 25px; margin: 25px;">
        -->
          <h2>Login</h2>
          <h3>[or change view]</h3>
        <!--
        </div>
        -->
      <form action="login" method="POST" name="login">
        <div style="border: solid #0090F0; width: 300px; padding: 5px 25px 5px 25px; margin: 25px;">
          Please select your viewname:
          <br>
          '''
    content += '<select name="viewname" style="width: 200px;">\n'
    for view in viewnames:
        content += '<option value="' + view + '">' + view + '</option>\n'
    content += '</select>\n'
    # content += '<input type="text" name="viewname" value=' + viewname + '>\n'
    content += '''
          <br>
          </div>
          <br>\n
        <div style="border: solid #0090F0; width: 300px; padding: 5px 25px 5px 25px; margin: 25px;">\n
          Please fill-in your credentials:
          <br>\n
          '''
    content += '<input type="text" name="username" value=' + username + '>'
    content += '''
          <!-- <br><br> -->
          <input type="password" name="password">
          <br/>
          </div>
          <br/>

          <button type="submit" > OK </button>
          <button type="button" class="close"> Cancel </button>
      </form>
      <br />
      '''
    if app_var['msg'] != '':
        content += "<br><div name=msg>Message: [" + str(app_var['msg']) + "]</div>"
    content += "</center>\n"
    title = app_title
    html = WrapHtml(content=content, title=title, org="companionway", center="Enjoy!")
    return html.render()
    # return content


# ################
@post('/login')  # or @route('/login', method='POST')
def do_login():
    # ###########
    """
    docstring
    """
    content = "<center>"
    title = __file__
    viewname = request.forms.get('viewname')
    username = request.forms.get('username')
    password = request.forms.get('password')
    session = bottle.request.environ.get('beaker.session')
    if check_login(viewname, username, password):
        session['username'] = username
        session['viewname'] = viewname
        dbug("session username has been set to : " + session['username'] + " and session viewname has been set to: " + session['viewname']) 
        # content += "<p>Your login [" + username + "] for viewname [" + viewname + "] was correct.</p>"
        # content += '<a href="/db/rows/' + viewname + '">View rows for viewname: ' + viewname + '</a>'
        redirect('/db/rows/' + viewname)
    else:
        content += "<p>Login failed.</p>"
        if app_var['msg'] != '':
            content += "<div name=msg>Messages: " + app_var['msg'] + "</div>"
        content += "<button><a href='/login'>Return to login page.</a></button>"
        content += "<button><a , renderhref='/logout'>Goto to logout page.</a></button>"
    content += "</center>"
    # html = WrapHtml(content=content, title=title, right="Enjoy!", nav_d=nav_d)
    html = WrapHtml(content=content, title=title, right="Enjoy!")
    return html.render()


# ##########
@route('/logout')
def logout():
    """
    WIP docstring
    """
    user_session = bottle.request.environ.get('beaker.session')
    if user_session['username']:
        username = user_session['username']
        dbug(" user_session[username]: " + user_session['username'])
    # empty the session username and viewname
    username = user_session['username'] = ''
    viewname = user_session['viewname'] = ''
    dbug(" user_session[username]: " + username)
    content = "<p>Username: " + username + " has been logged out</p>"
    content += "<p><button><a href=/login>Login Page</a></button>"
    content += "<div name=msg>Message: " + app_var['msg'] + "</div>"
    html = WrapHtml(content=content, title=title, right="Enjoy!")
    return html.render()
    # return content


# #######################################
@route('/db/rows/<viewname>', method='GET')
@route('/db/rows/<viewname>', method='POST')
def db_rows(viewname):
    # ###################################
    """
    input: viewname
    output: content = table of viewname with action links
    WIP !!
    WIP make sure we are authorized?

    """
    # dbug("Begin /db/rows/" + viewname )
    session = bottle.request.environ.get('beaker.session')
    # dbug("session: " + str(session))
    title = "Display rows for table: " + viewname
    form_data = form_d(request)
    # dbug("form_data: " + str(form_data))
    # ######### filterby ########## #
    # boil this down to filterby
    if form_data.has_key('fltr_col'):
        fltr_col = form_data['fltr_col']
    else:
        fltr_col = "none"
    #dbug("fltr_col: " + fltr_col)
    if form_data.has_key('fltr_str'):
        fltr_str = form_data['fltr_str']
        filterby = " WHERE " + fltr_col + " LIKE '%" + fltr_str + "%' "
    else:
        fltr_str = ""  # only here for dbug below
        filterby = ""
    dbug("fltr_col: " + str(fltr_col) + ' fltr_str: ' + str(fltr_str) + ' filterby: ' + filterby)
    # ######### orderby ########## #
    if form_data.has_key('orderby'):
        orderby = form_data['orderby']
        orderby = " ORDER BY " + orderby.replace("_"," ")
    else:
        orderby = ""
    # dbug("orderby: " + orderby)
    # ### start content ### #
    content = "<center>"
    # user session check
    if session.has_key('username')  and session.has_key('viewname'):
        username = session['username']
        views = app_meta.tables['app_views']
    else:
        content += "<br>No authorized session info for username and tablename"
        content += "<br><a href=/login>Return to Login (change view)</a>"
        html = WrapHtml(content, title=title)
        return html.render()
    users = app_meta.tables['app_users']
    if viewname != session['viewname']:
        # dbug("Viewname is not authorized")
        redirect('/login')
    else:
        # dbug("Supplied viewname [" + viewname + "] is authorized as it matches the user session viewname [" + session['viewname'] + "]")
        viewname = session['viewname']
        authorized_table = "none"
        # dbug("Attempting to get actual tablename from views table")
        # sel = select([views]).where(views.c.viewname==viewname)
        sel = select([VIEWS]).where(VIEWS.c.viewname==viewname)
        result = app_conn.execute(sel)
        # dbug("result: " + str(result))
        # this all needs work WIP !!!
        for row in result:
            # dbug("row: " + str(row))
            if row['viewname']==viewname:
                # dbug("YES")
                app_var['msg'] += "Found the viewname [" + viewname + "] in the views table"
            else:
                app_var['msg'] = "No records found for viewname: " + viewname + " in the views table."
                redirect('/login')
        # dbug("2nd time ...Authorized_table: " + authorized_table)
    ## WIP check this next one - it is experimental
    # dbug("## WIP check this next one - it is experimental")
    # dbug("----------- authorized_table -----------")
    # dbug("authorized_table: " + authorized_table)
    # fails: (only does first filter) sel = select([users]).where(users.c.username==username and users.c.viewname==viewname)
    sel = select([users]).where(and_(users.c.username==username, users.c.viewname==viewname))
    result = app_conn.execute(sel)
    # dbug("so row_count = " + str(row_count(result)))
    # dbug("result SHOULD BE: one record with users.c.username=" + username + " users.c.viewname=" + viewname)
    for row in result:
        # dbug("Double checkng authorization for this viewname: " + viewname + " is autorized")
        # dbug("for row in result - row: " + str(row))
        # dbug("row[viewname]: " + row['viewname'] + " and row[username]: " + row['username'])
        # dbug("viewname: " + viewname + " and username: " + username)
        # if row['viewname'] == viewname:
            # dbug("well at least viewname matches")
            # dbug("session[viewname]: " + session['viewname'])
            # So grab pg_size while we have it
            # pg_size = row['pg_size']
        # else:
            # dbug("viewname: " + viewname + " but row[viewname]: " + row['viewname'])
            # dbug("session[viewname]: " + session['viewname'])
        # if row['username'] == username:
            # dbug("well at least username matches")
            # dbug("session[username]: " + session['username'])
        if row['viewname'] == viewname and row['username'] == username:
            # dbug("viewname and username passed check out OK")
            break
        else:
            app_var['msg'] += "We have a problem as viewname: " + viewname + " and username: " + username + " fail"
            # dbug("sel: " + str(sel))
            content += "<br><div name=msg>Message: " + str(app_var['msg']) + "</div>"
            content += "<a href=/login>Return to login</a>"
            return content
            # redirect("/login")
    # EOB user session check
    # ####
    # #### set view uri and table ### #
    sel = select([views]).where(views.c.viewname==viewname)
    result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    view_URI = row['uri']
    view_TABLE = row['tablename']
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # now open the URI
    try:
        # view_engine = create_engine(view_URI, convert_unicode=True, echo=True)
        view_engine = create_engine(view_URI, convert_unicode=True, echo=False)
        view_meta = MetaData(view_engine)
        view_meta.reflect()
        view_conn = view_engine.connect()
    except Exception, e:
        # dbug("Exeception: " + str(e))
        content += "<br>Please double check the URI and declared tablename for this view [" + viewname + "]"
        content += "<br>Failed to connect using URI [" + view_URI + "] for viewname [" + viewname + "]"
        content += "<br>Received error: " + str(e) + "</p>"
        content += "<br><a href=/login>Return to Login (change view)</a>"
        html = WrapHtml(content)
        return html.render()
    # view_Session = sessionmaker(bind=app_engine)
    # view_session = view_Session()
    # ###
    table = view_meta.tables[view_TABLE]  # this should be table_o
    # lets make sure it exists and has a key
    if table.name in view_engine.table_names():
        # dbug("We found the table [" + table.name + "] in the database [" + view_URI + "]")
        id_l = [key.name for key in inspect(table).primary_key]
        try:
            primary_key = str(id_l[0])
            # dbug("id_l: " + str(id_l))
            # dbug("primary_key: " + primary_key)
        except Exception, e:
            # dbug("Primary key failed... error: " + str(e))
            app_var['msg'] += "<br>Failed to find primary key in table [" + table.name + "]"
            content += "<br>Failed to find primary key in table [" + table.name + "]"
            content += '<br><a href="/login">Return to login</a>'
            # dbug("title: " + title)
            nav_d = {"Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin" }
            html = WrapHtml(content=content, title=title, org=organization, center=foot_center, nav_d=nav_d)
            return html.render()
    else:
        app_var['msg'] += '<br>Failed to find table [' + table.name + '] in database uri [' + view_URI + ']'
        content += '<br><a href="/login">Return to login</a>'
        html = WrapHtml(content=content, title=title, org=organization, center=foot_center, nav_d=nav_d)
        return html.render()
    # #### EOB set view uri and table ### #
    cols_l = table.columns.keys()
    sel = select([table])
    result = view_conn.execute(sel)
    rows_l = [dict(zip(cols_l,row)) for row in result]
    # start content - add heading
    content = "<center>\n"
    content += '<div style="float: left;">User: ' + username + '</div>'
    content += '<div style="float: right;"> Viewname: ' + viewname + ' tablename: ' + table.name + '</div><br>\n'
    content += '<br>'
    content += '<div style="float: left;"><button><a href="/db/add/record">Add a new record</a></button><br></div>'
    # ### build the SQL query ### #
    content += '<div style="float: right;">'
    dbug("filterby: " + filterby + " orderby: " + orderby)
    sql = "SELECT * FROM " + table.name
    if filterby != "":
        sql = sql + filterby
    if orderby != "":
        sql = sql + orderby
    dbug("sql: [" + sql + "] fltr_col: " + fltr_col + " filterby: " + filterby)
    # ### start the form for filterby ### #
    content += '<form name="filterby" action="/db/rows/' + viewname + '" method="POST">'
    content += 'Quick Filter: '
    content += '<select name="fltr_col" type"text" style="width: 100px;">' + '\n'
    for item in cols_l:
        if fltr_col == item:
            # dbug("fltr_col: " + fltr_col + " item " + item)
            content += '<option value="' + item + '" selected="selected">' + str(item) + '</option>' + '\n'
        else:
            # dbug("fltr_col: " + fltr_col + " item " + item)
            content += '<option value="' + item + '">' + str(item) + '</option>' + '\n'
    content +=  '</select>'
    content += ' contains: '
    content += '<input type="text" name="fltr_str" value="' + fltr_str + '" size="30">' 
    content += '<input value="Submit" type="submit" />'
    content += '</form>'
    content += '</div>'
    # ### EOB form for filterby ### #
    content += '<br> <br>'
    # ### start table
    cols_l = table.columns.keys()
    # ### build table or rowa ### #
    content += "<table border=1>\n"
    content += "<tr>"
    # table header cells
    for col in cols_l:
        # ### orderby links ### #
        # check for and build orderby for each col
        cur_orderby = ""  # set it to "" because this col has no order
        chg_orderby = "_ASC"  # and it has no chg order either
        if form_data.has_key('orderby'):
            rcvd_orderby = form_data['orderby']
            # got a request to change orderby so lets do that and place an indicator that is is currently active with cur_orderby
            if col + '_ASC' == rcvd_orderby:
                # dbug("Found _ASC in: " + rcvd_orderby + " sel should now include order " + col + " ASC")
                cur_orderby = " (A)"
                chg_orderby = "_DESC"
            if col + '_DESC' == rcvd_orderby:
                # dbug("Found _DESC in: " + rcvd_orderby + " sel should now include order " + col + " DESC")
                cur_orderby = " (D)"
                chg_orderby = "_ASC"
        content += '<th><a href="/db/rows/' + viewname + '?orderby=' + col + chg_orderby + '">' + col + cur_orderby + '</a></th>'
        # content += "<th>" + col + "</th>"
    content += "<th colspan=3>Actions</th>"
    content += "</tr>\n"
    # content += '<tr><form action="/db/rows/' + viewname + ' method="GET">'
    # for col in cols_l:
    #     if col == 'id':
    #         content += '<td></td>'
    #     else:
    #         content += "<td>"
    #         content += '<input name="filter_' + col + '" size="10">'
    #         content += "</td>"
    # content += '<td colspan=3><submit type="submit" value="Submit"></th>'
    # content += '</form></tr>\n'
    # sel = select([table])
    # result = view_conn.execute(sel)  # bogus??
    # dbug("just set the select now going to run it in view_conn and hopefully get a reasonable result")
    try:
        stmt = text(sql)
        result = view_engine.execute(stmt, u=username)
        # row_cnt= row_count(result)
    except:
        # dbug("Got a problem - maybe with sql filterby query [" + filterby + "]")
        # so lets do a simple select without the filter(s)
        sql = "SELECT * FROM " + table.name
        stmt = text(sql)
        result = view_engine.execute(stmt, u=username)
    # dbug("hmmm got passed stmt result... lets check the row_count...")
    # TODO WIP
    pg_size = 50  # WIP change how this works
    if form_data.has_key('cur_pg'):
        cur_pg = int(form_data['cur_pg'])
        start_row = (cur_pg ) * pg_size
    else:
        start_row = 0
        cur_pg = 0
    result = view_engine.execute(stmt, u=username)  # you have to re-run it again
    # dbug("pg_size: " + str(pg_size) + " cur_pg: " + str(cur_pg) + " rows: " + str(len(rows_l)) + " start_row: " + str(start_row))
    # row_cnt = row_count(result) # if you use this line you will have to re-run result afterwards
    # dbug("OK row_cnt = " + str(row_cnt) + " so lets build out a zipped rows_l using cols_l: " + str(cols_l))
    rows_l = [dict(zip(cols_l,row)) for row in result]
    # dbug("pg_size: " + str(pg_size) + " cur_pg: " + str(cur_pg) + " rows: " + str(len(rows_l)))
    row_num = 0
    # dbug("type(rows_l): " + str(type(rows_l)))
    for row in rows_l:
        row_num += 1
        if row_num < start_row:
            # dbug(" row_num: " + str(row_num) + " start_row: " + str(start_row) + " rows: " + str(len(rows_l)))
            continue
        # dbug("row_num: " + str(row_num) + " pg_size: " + str(pg_size) + " row: " + str(row))
        # dbug("row_num: " + str(row_num) + " pg_size: " + str(pg_size) )
        if row_num > (start_row + pg_size):
            cur_pg += 1
            break
        content += "<tr>"
        for col in cols_l:
            row_val = ""
            if col == 'password':
                # dbug("row[password]: " + row['password'] + " action: " + action + " id: " + str(id))
                row_val = "********"
            else:
                row_val = str(row[col]).encode('ascii').decode('ascii','replace')
            # this next line was hard to work out - probably a better way to deal with 'foreign' chars
            # content += "<td>" + str(row[col]).encode('utf-8').decode('latin-1','replace') + "</td>"
            # content += "<td>" + str(row[col]).encode('ascii').decode('ascii','replace') + "</td>"
            content += "<td>" + row_val + "</td>"
            # s = str(row[col]).encode('utf-8')
            # content += "<td>" + s + "</td>"
        # add in actions
        # establish a list of actions
        actions = ['edit', 'detail', 'delete']
        for action in actions:
            content += "<td>"
            content += '<button><a href="/db/' + action + '/' + str(row['id']) + '">' + action.capitalize() + '</a></button>'
            content += "</td>"
        content += "</tr>\n"
    content += "</table>\n"
    content += '<br>'
    # add a line for adding a new record
    if cur_pg > 1:
        content += '<div style="float: left;"><form name="Next" type="POST" action="/db/rows/' + viewname + '"><button name="cur_pg" value="' + str(cur_pg - 2) + '">Previous</button></form></div>\n'
    if len(rows_l) > (cur_pg * pg_size):
        # dbug(" more rows viewname: " + viewname)
        content += '<div style="float: right;"><form name="Next" type="POST" action="/db/rows/' + viewname + '"><button name="cur_pg" value="' + str(cur_pg) + '">Next</button></form></div>\n'
    content += '<br><br>\n'
    content += "</center>\n"
    title=__file__
    nav_d = {"Rows: " + viewname: "/db/rows/" + viewname, "Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin" }
    html = WrapHtml(content=content, title=title, org=organization, center=foot_center, nav_d=nav_d)
    return html.render()
    # return content
    # EOB @route('/db/rows/<viewname>')


# #########################
@route('/db/<action:re:(edit|add|detail|delete)>/<id>')
def db_action(action, id):  # method==GET
    # ####################
    """
    docstring
    action = edit, add (with /id = /record), detail
    """
    # dbug("Begin: route(/<" + action + ">/<" + id + ">) GET")
    title = "action: " + action + " id: " + id
    content = "<center>\n"
    # set session info
    session = bottle.request.environ.get('beaker.session')
    title = 'Action: ' + action + ' for id: ' + str(id)
    if session.has_key('username')  and session.has_key('viewname'):
        # dbug("Good we found session username and session viewname...")
        username = session['username']
        viewname = session['viewname']
    else:
        content += "Failed to find an active session"
        content += '<br><a href="/login">Return to login</a>'
        content += '</center>'
        nav_d = { "Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin"}
        html = WrapHtml(content=content, title=title, right="Enjoy!", nav_d=nav_d)
        return html.render()
    # username = session['username']
    # viewname = session['viewname']
    # ### set view table ### #
    # content += '<div style="float: left;">User: ' + username + '</div><div style="float: right;"> Viewname: ' + viewname + ' Selected: ' + str(row_cnt) + '</div><br>'
    nav_d = {"Rows: " + viewname: "/db/rows/" + viewname, "Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin"}
    views = app_meta.tables['app_views']
    # sel = select([VIEWS]).where(VIEWS.c.viewname==viewname)
    # result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    # row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    # view_URI = row['uri']
    # view_TABLE = row['tablename']
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # # now open the URI
    # # view_engine = create_engine(view_URI, echo=True)
    # view_engine = create_engine(view_URI, echo=False)
    # view_meta = MetaData(app_engine)
    # view_meta.reflect()
    # view_conn = view_engine.connect()
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # # ### EOB set view table
    # table = view_meta.tables[view_TABLE]
    # #### set view uri and table ### #
    sel = select([views]).where(views.c.viewname==viewname)
    result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    view_URI = row['uri']
    view_TABLE = row['tablename']
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # now open the URI
    # dbug("view_URI: " + view_URI)
    try:
        view_engine = create_engine(view_URI, convert_unicode=True, echo=True)
        view_meta = MetaData(view_engine)
        view_meta.reflect()
        view_conn = view_engine.connect()
    except Exception, e:
        # dbug("Exeception: " + str(e))
        content += "<p>Failed to connect... " + str(e) + "</p>"
        content += "<p><a href=/login>Return to Login (change view)</a></p>"
        return content
    # view_Session = sessionmaker(bind=app_engine)
    # view_session = view_Session()
    # ###
    table = view_meta.tables[view_TABLE]
    # dbug("GET action: " + action + " view_TABLE: " + str(view_TABLE))
    # TODO WIP
    # set col names
    col_names = [col.name for col in table.columns]
    sel = select([table]).where(table.c.id==id)
    if action == 'add':
        # change the above sel variable value (just so the zip below works properly?)
        sel = select([table])
    # result = app_conn.execute(sel)  
    result = view_conn.execute(sel)  
    row_cnt = row_count(result)
    row_d = {}
    result = view_conn.execute(sel)  # you have to re-run this
    if row_cnt == 0 or action == 'add':
        # dbug("either row_cnt [" + str(row_cnt) + "] is 0 or action [" + action + "] is equal to add")
        for col in col_names:
            row_d[col] = ""
    else:
        # dbug("zipping col_names and result rows with row_cnt: " + str(row_cnt))
        row_d = [dict(zip(col_names,row)) for row in result]
    dbug("row_d: " + str(row_d) + " row_cnt: " + str(row_cnt))
    # result = view_conn.execute(sel)  # might have to activate this
    # row_cnt = row_count(result)
    # dbug("action: " + action + " row_cnt: " + str(row_cnt) + " cols_l: " + str(col_names))
    if action == 'add':
        row_cnt = 0
    # dbug("/db/action: " + action + " after checking if action==add row_cnt: " + str(row_cnt) + " id: " + str(id))
    # build table
    # content = "<center>\n"
    content += '<div style="float: left;">User: ' + username + '</div>'
    content += '<div style="float: right;"> Viewname: ' + viewname + ' Selected: ' + str(row_cnt) + '</div><br>'
    content += title
    # ### begin form ### #
    content += '<form action="/db/' + action + '/' + id + '" method="POST" name="' + action + '">\n'
    # ### begin table ### #
    content += "<table border=1>\n"
    # for ref: input_start_str = '<textarea name="' + col + '" rows="5" cols="' + str(input_size) + '">'
    # for ref: input_end_str = '</textarea>'
    for row in row_d:
        # dbug("for row in row_d... row: " + str(row))
        for col in col_names:
            content += "<tr>"
            content += "<td>" + col + "</td>"
            # ### col_val ### #
            content += '<td>'
            if col == 'id':
                if action == 'add':
                    # content += '<input name=' + col + ' value=' + 'TBD' + ' readonly size="' + str(input_size) + '">'
                    content += '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + '" readonly >' + 'TBD' + '</textarea>\n' 
                else:
                    # content += '<input name=' + col + ' value=' + str(row[col]) + ' readonly size="' + str(input_size) + '">'
                    content += '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + '" readonly >' + str(row[col])  + '</textarea>\n' 
            # elif col == 'password':
            #     input_start_str = '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + ' type="password"">'
            #     input_end_str = '</textarea>\n' 
            #     content += '<input type="password" name=' + col + ' value="**********"' + str(input_size) + '">'
            else:
                input_start_str = '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + '">'
                input_end_str = '</textarea>\n' 
                if col == 'password':
                    dbug("row[password]: " + row['password'] + " action: " + action + " id: " + str(id))
                    row['password'] = hashpw(row['password'].encode('utf-8'), gensalt())
                    input_start_str = '<input name="' + col + '" type="password" val="**********" size="' + str(input_size) + '">'
                    input_end_str = '>'
                #else:
                    #input_start_str = '<input name="' + col + '" size="' + str(input_size) + '" value="' 
                    # content += '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + '">' + str(row[col])  + '</textarea>\n' 
                    #input_start_str = '<textarea name="' + col + '" rows="1" cols="' + str(input_size) + '">'
                    #input_end_str = '</textarea>\n' 
                    # input_end_str = '">'
                    #content += input_start_str + str(row[col]) + input_end_str
                try:
                    val_len = len(row[col])
                except:
                    val_len = input_size
                if val_len > input_size:
                    # set the input_start_str and the input_end_str
                    # dbug("val_len: " + str(val_len) + " which is over the arbitrary limit of " + str(input_size))
                    input_start_str = '<textarea name="' + col + '" rows="5" cols="' + str(input_size) + '">'
                    input_end_str = '</textarea>'
                if col == 'password':
                    dbug("row[password]: " + row['password'] + " action: " + action + " id: " + str(id))
                    # row['password'] = hashpw(row['password'].encode('utf-8'), gensalt())
                    #content += '<input name="' + col + '" type="password" size=" + str(input_size) + '" value="**********">'
                    content += '<input name="' + col + '" type="password" value="**********" size="' + str(input_size+11) + '">'
                    continue
                if action == 'edit':
                    # dbug("row[col]: " + str(row[col]))
                    content += input_start_str + str(row[col]) + input_end_str
                if action == 'add':
                    content += input_start_str + "" + input_end_str
                if action == 'detail' or action == 'delete':
                    content += input_start_str + row[col] + input_end_str
            content += '</td>'
            content += '</tr>\n'
        if action == 'add':
            break  # we did a select on all records above becuase the id is 0 (action=add) but this should only run once
    # ### end table ### #
    content += "</table>\n"
    # ### end form ### #
    if action == 'edit' or action == 'add' or action == 'delete':
        content += '<br><input value="Submit "' + action + ' type="submit" />\n'
        content += "</form>\n"
    # nav_d = {"Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin", "Rows:": "/db/rows/"+viewname}
    html = WrapHtml(content=content, title=title, right="Enjoy!", nav_d=nav_d)
    return html.render()
    # return content
    # ### EOB @route('/db/<action>/<id>')


# ########################
@post('/db/<action:re:(edit|add|detail|delete)>/<id>')
def db_action(action, id):
    # ####################
    """
    docstring
    POST
    """
    # dbug("Begin: route(/db/" + action + "/" + id + ") POST")
    content = "<center>\n"
    # post_data_d = _request(request)
    post_data_d = form_d(request)
    # dbug("post_data_d: " + str(post_data_d))
    # set session info
    session = bottle.request.environ.get('beaker.session')
    # dbug("session: " + str(session))
    title = 'Action: ' + action.capitalize() + ' for id: ' + str(id)
    nav_d = {"Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin"}
    if session.has_key('username')  and session.has_key('viewname'):
        # dbug("Good we found session username and session viewname...")
        username = session['username']
        viewname = session['viewname']
    else:
        content += "Failed to find an active session"
        content += '<br><a href="/login">Return to login</a>'
        content += '</center>'
        html = WrapHtml(content=content, title=title, right="Enjoy!", nav_d=nav_d)
        return html.render()
    if action == 'add':
        title = "Submitted data for adding"
    else:
        title = "Submitted data for updating"
    content += title
    # #### set view uri and table ### #
    sel = select([VIEWS]).where(VIEWS.c.viewname==viewname)
    result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    view_URI = row['uri']
    view_TABLE = row['tablename']
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # now open the URI
    # dbug("view_URI: " + view_URI)
    try:
        view_engine = create_engine(view_URI, convert_unicode=True, echo=True)
        view_meta = MetaData(view_engine)
        view_meta.reflect()
        view_conn = view_engine.connect()
    except Exception, e:
        # dbug("Exeception: " + str(e))
        content += "<p>Failed to connect... " + str(e) + "</p>"
        content += "<p><a href=/login>Return to Login (change view)</a></p>"
        return content
    # view_Session = sessionmaker(bind=app_engine)
    # view_session = view_Session()
    # ###
    table = view_meta.tables[view_TABLE]
    # #### EOB set view uri and table ### #
    content += '<div style="float: left;">User: ' + username + '</div>'
    content += '<div style="float: right;"> Viewname: ' + viewname + ' tablename: ' + table.name + '</div><br>\n'
    # ### set view table ### #
    # sel = select([VIEWS]).where(VIEWS.c.viewname==viewname)
    # result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    # row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    # view_URI = row['uri']
    # view_TABLE = row['tablename']
    # dbug("view_URI: "+ view_URI + " view_TABLE: " + view_TABLE)
    # # now open the URI
    # view_engine = create_engine(view_URI, echo=True)
    # view_meta = MetaData(app_engine, reflect=True)
    # view_conn = view_engine.connect()
    # # view_Session = sessionmaker(bind=app_engine)
    # # view_session = view_Session()
    # # ### EOB set view table
    #table = view_meta.tables[view_TABLE]
    # dbug("viewname: " + str(viewname) + " table: " + str(table))
    # set col names
    col_names = [col.name for col in table.columns]
    # for col in col_names:
    #     content += "<th>" + col + "</th>"
    # select record(s)
    if action == 'add':
        # change above sel variable value
        sel = select([table])
    else:
        sel = select([table]).where(table.c.id==id)
    result = view_conn.execute(sel)  # bogus??
    row_d = [dict(zip(col_names,row)) for row in result]
    # build table
    # dbug("row_d: " + str(row_d))
    # dbug("post_data_d: " + str(post_data_d))
    # insert or update the posted data
    vals_d = {}
    for row in row_d:
        for col in col_names:
            if col != 'id':
                vals_d[col]=post_data_d[col]
    if action == 'add':
        action_stmt = table.insert().values(vals_d)
        # dbug("Action: " + action + " action_stmt: " + str(action_stmt))
        result = view_conn.execute(action_stmt)  
        id = result.inserted_primary_key
        # dbug("Just inserted record: " + str(id))
    elif action == 'delete':
        action_stmt = table.delete().where(table.c.id==id)
        result = view_conn.execute(action_stmt)  
        # dbug("Just deleted record: " + str(id))
    else: 
        # action_stmt = table.update().values(vals_d).where(views.c.id==id)
        #table = Table(table.name, view_meta)  # this is bogus
        action_stmt = table.update().values(vals_d).where(table.c.id==id)
        # dbug("action: " + action + " id: " + str(id))
        result = view_conn.execute(action_stmt)  
        # dbug("Just updated record: " + str(id))
    # EOB insert or update posted data
    content += "<table border=1>\n"
    content += "<tr>"
    if action == 'add':
        id = str(id)
        filter = ""
    else:
        filter = "table.c.id==" + id
    for row in row_d:
        # dbug("action: " + action + " for row in row_d... row: " + str(row))
        for col in col_names:
            # dbug("for col in col_names... col: " + str(col))
            content += "<td>" + col + "</td>"
            content += '<td>'
            if col == 'id' and action == 'add':
                content += str(id)
            else:
                if col == 'password':
                    content += "**********"
                else:
                    content +=  post_data_d[col]
            # if col != 'id':
            #     dbug("adding: vals_d[" + col + "]=" + str(post_data_d[col]))
            #     vals_d[col]=post_data_d[col]
            #     vals_d[col]=str(id)
            content += '</td>'
            content += '<tr>\n'
        if action == 'add':
            break  # because we used a select for all records when action=add but we only need one loop here to get each col and value
    content += "</table>\n"
    # dbug("table generated vals_d: " + str(vals_d))
    # dbug("vals_d: " + str(vals_d) + " table: " + str(table) + "type(table): " + str(type(table)))
    content += "<br>Action: [" + action + "] has been completed<br>"
    content += '<br><a href="/db/rows/' + viewname + '">Return to row view: ' + viewname + '</a><br>'
    nav_d = {"Logout": "/logout", "Login (change view)": "/login", "Admin ToDo": "/admin" }
    html = WrapHtml(content=content, title=title, right="Enjoy!", nav_d=nav_d)
    return html.render()
    # return content 
    # #### EOB @post('/db/<action>/<id>') #### #

# @route('/tst/<item:re:(edit|detail)>')
@route('/tst')
# def tst(item):
def tst():
    """
    for testing only
    """
    form_data = form_d(request)
    item = "debug testing only"
    session = bottle.request.environ.get('beaker.session')
    print("session: " + str(session))
    content = "testing only item: " + item + "<br>"
    viewname = 'a'
    # username = "%adm%"
    content += "<br>======== where username = admin ======================"
    username = "adm%"
    sel = select([VIEWS]).where(VIEWS.c.viewname==viewname)
    result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    row = result.fetchone()
    # dbug("row: " + str(row) + " and row_cnt: " + str(row_count(result)))
    content += "<br>sel: " + str(sel)
    content += "<br>row: " + str(row) + " and row_cnt: " + str(row_count(result))

    result = app_conn.execute(sel)  # hmmm, you have to re-run this after each manipulation of the result
    rows = result.fetchall()
    for r in rows:
        content += "<br> row: " + str(r)

    sql = "SELECT * FROM " + USERS.name + " WHERE username==" + username
    sql = "SELECT * FROM " + USERS.name + " WHERE username LIKE :u"
    content += "<br>sql: " + sql
    stmt = text(sql)
    content += "<BR>u=" + username
    result = app_engine.execute(stmt, u=username)
    rows = result.fetchall()
    for row in rows:
        # dbug("row: " + str(row))
        content += "<br>row: " + str(row)
    
    content += "<br>======== where username = admin ======================"
    quick_search = "WHERE username=='admin'"
    stmt = text("SELECT * FROM " + USERS.name + " " + quick_search)
    result = app_engine.execute(stmt, u=username)
    rows = result.fetchall()
    for row in rows:
        # dbug("row: " + str(row))
        content += "<br>row: " + str(row)

    content += "<br>======== recipes table and id exist ======================"
    view_URI = "sqlite:////data/share/db_dir/myphile.db"
    view_tablename = "recipes"
    view_engine = create_engine(view_URI, echo=True)
    view_meta = MetaData(view_engine)
    view_meta.reflect()
    view_conn = view_engine.connect()
    view_Session = sessionmaker(bind=view_engine)
    view_session = view_Session()
    # dbug("tables: " + str(view_engine.table_names()))
    # if view_tablename in view_engine.table_names():
    #     dbug("Fould the table! [" + view_tablename + "]")
    # else:
    #     dbug("Could not find view_tablename [" + view_tablename + "]")
    # how to get the last id
    table_o = view_meta.tables[view_tablename]
    # fails: sel = select([table_o]).order_by(table.c.id)(table.c.id.desc())
    #sel = select([table_o]).order_by('id')
    sel = select([table_o]).order_by(table_o.c.id.desc())
    res = view_conn.execute(sel)
    #dbug("res: " + str(res))
    #res = res.desc()
    obj = res.first()
    dbug("obj: " + str(obj))
    # obj = view_conn.execute(table_o.order_by('id')(table_o.id.desc()).first())
    res = view_conn.execute(sel)
    # dbug("res: " + str(res.first()))
    # obj1 = view_session.query(table_o).order_by(table_o.id desc()).first()
    # dbug("obj1: " + str(obj1))
    # dbug("primary key: " + str(inspect(VIEWS).primary_key))
    # dbug("type(USERS): " + str(type(USERS)))  # class
    # dbug("pkey: " + str(type(inspect(VIEWS).primary_key)))  # class
    # getting the name of the primary key
    id_l = [key.name for key in inspect(USERS).primary_key]
    # dbug("id_l: " + str(id_l[0]))
    # dbug("primary key: " + str(inspect(table_o).primary_key))
    id_l = [key.name for key in inspect(table_o).primary_key]
    # dbug("id_l: " + str(id_l[0]))
    inspector = inspect(view_engine)
    db_name = inspector.default_schema_name
    # dbug("db_name: " + str(db_name))
    if table_exists(table_o.name,engine=view_engine, meta=view_meta):
        # dbug("Great, the table exists")
        content += "<br>table: " + table_o.name + " exists"
        if table_exists(table_o.name,'key',view_engine, view_meta):
            # dbug("Great, the primary key exists")
            content += "<br>primary key: " + str(id_l[0]) + " exists"
        # else:
            # dbug("Woops, no primary key")
    # else:
        # dbug("Woops table does not exist in this database")
    # ######## viewnames #####
    content += "<BR>============= viewnames ==================" + '\n'
    sel = select([VIEWS])
    result = app_conn.execute(sel)  # 
    # or
    cur = app_engine.execute("SELECT * FROM app_views")
    viewnames = []
    uris = []
    tablenames = []

    content += "<br>sel: " + str(sel) + '\n'
    content += "<br>type(cur): " + str(type(cur)) + '\n'
    content += "<br>cur: " + str(cur) + '\n'
    content += "<br>type(result): " + str(type(result)) + '\n'
    content += "<br>result: " + str(result) + '\n'
    for row in result:
        content += "<br>row: " + str(row) + '\n'
        viewnames.append(row['viewname'])
        uris.append(row['uri'])
        tablenames.append(row['tablename'])
    content += "<br> viewnames: " + str(viewnames) + '\n'
    content += "<br> uris: " + str(uris) + '\n'
    content += "<br> tablenames: " + str(tablenames) + '\n'
    content += '<form action="/" method="GET">' + '\n'
    content += '<select name="viewname" type"text" style="width: 200px;">' + '\n'
    for item in viewnames:
        content += '<option value="' + item + '">' + str(item) + '</option>' + '\n'
    content += '</select>' + '\n'
    content += '</form>' + '\n'


    content += "<br>============ experiments =============" + '\n'
    # from sqlalchemy import MetaData, Table, Column, Integer
    meta = MetaData()
    users_table = Table('users', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(50))
        )
    engine = create_engine('sqlite:///file.db')
    content += "<br>Try create on a single table: " + users_table.name
    try:
        users_table.create(engine)  # creates a single table
    except Exception, e:
        content += "<br>Table probably exists... error: " + str(e)
    content += "<br>users_table: " + str(users_table)  # calling the table object displays its table name by default
    content += "<br>table_names: " + str(engine.table_names())
    result = engine.execute(users_table.select())
    content += "<br>columns: " + str(users_table.columns)
    content += "<br>column_names: " + str(users_table.columns.keys())
    # works: content += "<br>users_table.__doc__: " + str("<BR>".join(users_table.__doc__.split('\n')))
    # help(users_table)  # actually this spits out LOTS of info
    # works: content += "<br>dir(users_table): " + str(dir(users_table))
    for row in result:
        # ....
        content += "<BR>row: " + row
    result.close()

    # fails: if users_table.exists():
    #    content += "<BR>apparently the table exists..."
    # meta.bind = engine
    # content += "<BR>users_table.schema: " + str(users_table.metadata)

    content += "<br>========== form_data ================="
    cols = ["fieldname1", "field2"]
    cols_data = ["data_bit_1", "data_bit_2"]
    content += '<center><table border=1>'
    content += '<tr>'
    for col in cols:
        cur_orderby = ""  # set it to "" because this col has no order
        chg_orderby = "_ASC"  # and it has no chg order either
        if form_data.has_key('orderby'):
            rcvd_orderby = form_data['orderby']
            # got a request to change orderby so lets do that and place an indicator that is is currently active with cur_orderby
            if col + '_ASC' == rcvd_orderby:
                # dbug("Found _ASC in: " + rcvd_orderby + " sel should now include order " + col + " ASC")
                cur_orderby = " (A)"
                chg_orderby = "_DESC"
            if col + '_DESC' == rcvd_orderby:
                # dbug("Found _DESC in: " + rcvd_orderby + " sel should now include order " + col + " DESC")
                cur_orderby = " (D)"
                chg_orderby = "_ASC"
        content += '<td><a href="/tst?orderby=' + col + chg_orderby + '">' + col + cur_orderby + '</a></td>'
    content += "</tr><tr>\n"
    for data in cols_data:
        content += "<td>" + data + "</td>"
    content += "</tr>\n"
    content += '</table></center>'
    content += "<br>it certainly is not pretty, but it works"
    content += "<br>========== EOB form_data ================="

    
    return content



# ##### EOB routes ####### #


# ##### Main Code ####### #
if __name__ == '__main__':
    run(app, debug=True)
