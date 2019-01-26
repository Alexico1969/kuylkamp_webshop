# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, session, url_for, g
import sqlite3
import csv
import datetime
import time
import json
from os import path
from MolliePy.mollie.api.client import Client

# -- Setting up App --

app = Flask(__name__)
app.secret_key = "any random string"
app.config['SECRET_KEY'] = 'something-secret2'


# -- Setting up Mollie

mollie_client = Client()
mollie_client.set_api_key('test_UAvAQ84S9PJtxRn3ARQmsy6CE8vu9F')

# -- Setting up SQLite database --

ROOT = path.dirname(path.realpath(__file__))
conn = sqlite3.connect(path.join(ROOT,"kkff.db"))
c = conn.cursor()


#---------DATABASE STUFF-----------

#c.execute("DROP TABLE OfferedTickets;")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS OfferedTickets( TicketTypeID INTEGER PRIMARY KEY AUTOINCREMENT, TicketName TEXT NOT NULL, TicketPrice FLOAT NOT NULL);")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS TicketOrders( OrderID INTEGER PRIMARY KEY AUTOINCREMENT, ?? , DateTime DATETIME DEFAULT CURRENT_TIMESTAMP, MollieID TEXT NOT NULL);")
#c.execute("CREATE TABLE IF NOT EXISTS CustomerInfo( CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, Voornaam TEXT NOT NULL , TV TEXT NOT NULL, Achternaam TEXT NOT NULL, Email TEXT NOT NULL, TelNr INT NOT NULL, WhereDidYouFindUs TEXT);")
#c.execute("INSERT INTO CustomerInfo( Voornaam,TV,Achternaam,Email,TelNr,WhereDidYouFindUs) values (?,?,?,?,?, ?)",("Piet","","Paulusma", "piet@paulusma.nl", 1234567890, ""))
#conn.commit()
#----------------------------------


bericht = "-"
order = {}
totalAmount = 0.0

@app.route('/', methods=["POST","GET"] )
def main():

    global rows
    global order
    global totalAmount
    global bericht

    bericht = "Main - start"

    if order_cookie_not_set():
        session.clear()
        session['orderstatus'] = "Empty"
    else:
        key = session.get('orderstatus')
        bericht = key



    # mapping the inputs to the function blocks
    options = { "Empty" : GetOrder,
                 "Ordering" : GetOrder,
                 "Order placed" : ConfirmOrder,
                 "Order checked" : GetCustomerInfo,
                 "NAW done" : InitiatePayment,
                 "Payment initiated" : FinishPayment,
                 "Payment done" : GenerateTickets,
                 "Tickets Generated" : SendTickets,
                 "Tickets Sent" : Finished,}

    renderPage = { "Empty" : 'main.html',
                 "Ordering" : 'main.html',
                 "Order placed" : 'confirmOrder.html',
                 "Order checked" : 'NAW-form.html',
                 "NAW done" : 'startPayment.html',
                 "Payment initiated" : 'pendingPayment.html',
                 "Payment done" : 'paymentSuccess.html',
                 "Tickets Generated" : 'ticketsGenerated.html',
                 "Tickets Sent" : 'thankYou.html',}

    options[session['orderstatus']](request.method) # this determines which Funcion is called

    #bericht = session['orderstatus']
    #bericht = rows

    return render_template( renderPage[session['orderstatus']], rows = rows, bericht = bericht, totalAmount = totalAmount )



@app.route('/addTicketType' , methods=["POST","GET"])
def addTicketType():

    bericht=" - "

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



@app.route('/showCustomers' , methods=["POST","GET"])
def showCustomers():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM CustomerInfo")
    conn.commit()

    rows=c.fetchall()
    conn.commit()

    return render_template('showCustomers.html', rows=rows , bericht = bericht)





#-------------------------------------------  LOGIN / LOGOUT / ETC.  ----------------------------------------------


def login_required():

    try:
        key = session.get('user_id', 'Harry')
    except:
        return False

    if key == "Roger":
        return True

    return False

def order_cookie_not_set():

    try:
        key = session.get('orderstatus')
    except:
        return True

    if key == None:
        return True

    return False

@app.route('/login', methods=["POST","GET"])
def login():
    global CurrentUrl
    global message

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
            message = "Cookie sent"
            return render_template('addTicketType.html', bericht=bericht)

        return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session['user_id'] = "Not"
    return redirect('/login')

'''

   Check for logged in at start of function :

        if not(login_required()):
        return redirect("/login")



    '''


#------------------------------- FUNCTIONS BASED ON ORDERSTATUS -----------------------------------------

def GetOrder(method):

    global bericht
    global rows
    global totalAmount
    global order

    bericht = "GetOrder"
    if method == 'POST':

        c.execute("SELECT * FROM OfferedTickets")
        conn.commit()
        rows = c.fetchall()

        bericht = ""
        totalAmount = 0.0

        for row in rows:

            ticketID = str(row[0])
            ticketName = row[1]
            price = str(row[2])
            amountOrdered = request.form[ticketID]
            totalPerTicket = row[2] * float(request.form[ticketID])
            if int(amountOrdered) > 0:
                bericht+= str(amountOrdered) + " x " + ticketName + " à € " + price  + "0 = € " + str(totalPerTicket) + "0 | "
                totalAmount += totalPerTicket

        session['orderstatus'] = "Order placed"
        return

    else:
        bericht = "NOT POST"
        c.execute("SELECT * FROM OfferedTickets")
        conn.commit()
        rows = c.fetchall()
        session['orderstatus'] = "Ordering"
        return


def ConfirmOrder(method):
    global bericht
    session['orderstatus'] = "Order checked"
    bericht="ConfirmOrder"
    return

def GetCustomerInfo(method):
    global bericht
    global rows

    if method == "POST":
        bericht = "POST"


        voornaam = request.form["Voornaam"]
        tv = request.form["TV"]
        achternaam = request.form["Achternaam"]
        email = request.form["Email"]
        tlnr = request.form["TelNr"]  # tussenstap
        tel = int(tlnr)
        try:
            WDYFU = request.form["WhereDidYouFindUs"]
        except:
            WDYFU = "?"

        c.execute("INSERT INTO CustomerInfo (Voornaam, TV, Achternaam, Email, TelNr, WhereDidYouFindUs) values (?, ?, ?, ?, ?, ?)",(voornaam, tv, achternaam, email, tel, WDYFU))
        conn.commit()

        #session['orderstatus'] = "NAW done"
        return

    if method == "GET":
        bericht = "GET"


    return

def InitiatePayment():
    global bericht
    bericht="InitiatePayment"

    payment = mollie_client.payments.create({
        'amount': {
            'currency': 'EUR',
            'value': '1.00'
        },
        'description': 'My first API payment',
        'redirectUrl': 'https://kkff.pythonanywhere.com/',
        'webhookUrl': 'https://kkff.pythonanywhere.com//mollie-webhook/', })

    return

def FinishPayment():
    global bericht
    bericht="FinishPayment"
    return

def GenerateTickets():
    global bericht
    bericht="GenerateTickets"
    return

def SendTickets():
    global bericht
    bericht="SendTickets"
    return

def Finished():
    global bericht
    bericht="Finished"
    return



