# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, session, url_for, g
import sqlite3
import csv
import datetime
import time
from os import path

# -- Setting up App --

app = Flask(__name__)
app.secret_key = "any random string"
app.config['SECRET_KEY'] = 'something-secret2'



# -- Setting up SQLite database --

ROOT = path.dirname(path.realpath(__file__))
conn = sqlite3.connect(path.join(ROOT,"kkff.db"))
c = conn.cursor()



#---------DATABASE STUFF-----------
#c.execute("DROP TABLE OfferedTickets;")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS OfferedTickets( TicketTypeID INTEGER PRIMARY KEY AUTOINCREMENT, TicketName TEXT NOT NULL, TicketPrice FLOAT NOT NULL);")
#conn.commit()
#c.execute("DROP TABLE beoordelingen;")
#c.execute("CREATE TABLE IF NOT EXISTS beoordelingen ( beoordeling_id integer PRIMARY KEY , leerling_nr text NOT NULL, VM01 text NOT NULL, VM02 text NOT NULL, VM03 text NOT NULL, pingen text NOT NULL, WAMP text NOT NULL, delen text NOT NULL, PHP text NOT NULL, CSHARP text NOT NULL, rechten text NOT NULL, IP text NOT NULL);")
#conn.commit()
#----------------------------------



CurrentUrl = None

@app.route('/')
def main():
    global CurrentUrl
    CurrentUrl = url_for('main')

    c.execute("SELECT * FROM OfferedTickets")
    conn.commit()

    rows=c.fetchall()

    return render_template('main.html', rows = rows, message="CurrentUrl = "+CurrentUrl)

    #return render_template('main.html')

@app.route('/addTicketType' , methods=["POST","GET"])
def addTicketType():

    global CurrentUrl
    CurrentUrl = url_for('addTicketType')
    rows="EMPTY"
    bericht=" - "
    rows=[]


    if not(login_required()):
        session['url'] = url_for('addTicketType')
        return redirect("/login")

    c.execute("SELECT * FROM OfferedTickets")
    conn.commit()

    rows=c.fetchall()
    conn.commit()



    if request.method == 'POST':

        actie = request.form.get("action")[:3]

        if actie == "Add":
            bericht = ""
            T_name = request.form.get("TicketName")
            T_price = request.form.get("TicketPrice")

            if T_name == None:
                bericht = "geen ticketnaam ingevoerd"

            if T_name == "":
                bericht = "ticketnaam niet ingevoerd"

            if T_price == None:
                bericht = "geen ticketprijs ingevoerd"

            if T_price == "" or T_price == 0:
                bericht = "ticketprijs niet ingevoerd"

            if bericht == "":
                bericht = " added record "
                TicketName =  request.form.get("TicketName")
                TicketPrice = float(request.form.get("TicketPrice"))

                c.execute("INSERT INTO OfferedTickets (TicketName, TicketPrice) values (?, ?)",(TicketName, TicketPrice))
                conn.commit()


        if actie == "Del":
            record = request.form.get("action")
            record = int(record.split()[2]) # splits "Delete 2"
            bericht = "Deleted record "+ str(record)

            c.execute("DELETE FROM OfferedTickets WHERE TicketTypeID = %s " % record)
            conn.commit()
            c.execute("SELECT * FROM OfferedTickets")
            conn.commit()



    return render_template('addTicketType.html', rows=rows , bericht = bericht)




#-------------------------------------------  LOGIN / LOGOUT / ETC.  ----------------------------------------------


def login_required():

    try:
        key = session.get('user_id', 'Harry')
    except:
        return False

    if key == "Roger":
        return True

    return False

@app.route('/login', methods=["POST","GET"])   # NO LONGER USED SINCE WE GOT  SIMPLE_LOGIN
def login():
    global CurrentUrl
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error=None

        if (username != "St@r") or (password != "L@ne"):
            error = "Incorrect username."
            return render_template('login.html')

        if error is None:
            session.clear()
            session['user_id'] = "Roger"
            if 'url' in session:
                return redirect(CurrentUrl)
            return redirect('/')

        return render_template('login.html')

    return render_template('login.html')

@app.route('/logout', methods=["POST","GET"])   # NO LONGER USED SINCE WE GOT  SIMPLE_LOGIN
def logout():
    session['user_id'] = "Not"
    return redirect('/login')

'''

   Check for logged in at start of function :

        if not(login_required()):
        return redirect("/login")



    '''


