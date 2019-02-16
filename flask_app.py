# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, session, url_for, g
import sqlite3
import csv
import datetime
import time
import json
import os
import smtplib
from helpers import makeTicket
from os import path
from MolliePy.mollie.api.client import Client
from MolliePy.mollie.api.error import Error

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from http import cookies


# -- Setting up App --

app = Flask(__name__)
app.secret_key = "any random string"
app.config['SECRET_KEY'] = 'something-secret2'


# -- Setting up Mollie

mollie_client = Client()
mollie_client.set_api_key('test_erGKTV4s4KCCmCnVx328FEWmGFQdxb')

# -- Setting up SQLite database --

ROOT = path.dirname(path.realpath(__file__))
conn = sqlite3.connect(path.join(ROOT,"kkff.db"))
c = conn.cursor()

PaymentStarted = False

#---------DATABASE STUFF-----------
#c.execute("DROP TABLE Tickets;")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS OfferedTickets( TicketTypeID INTEGER PRIMARY KEY AUTOINCREMENT, TicketName TEXT NOT NULL, TicketPrice FLOAT NOT NULL);")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS TicketOrders( OrderID INTEGER PRIMARY KEY AUTOINCREMENT, TotalAmount FLOAT NOT NULL, DateTime DATETIME DEFAULT CURRENT_TIMESTAMP, CustomerID INTEGER NOT NULL, MollieID TEXT NOT NULL , OrderStatus TEXT NOT NULL, Source TEXT NOT NULL, FOREIGN KEY(CustomerID) REFERENCES CustomerInfo(CustomerID));")
#c.execute("CREATE TABLE IF NOT EXISTS CustomerInfo( CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, Voornaam TEXT NOT NULL , TV TEXT NOT NULL, Achternaam TEXT NOT NULL, Email TEXT NOT NULL, TelNr INT NOT NULL, WhereDidYouFindUs TEXT);")
#c.execute("INSERT INTO CustomerInfo( Voornaam,TV,Achternaam,Email,TelNr,WhereDidYouFindUs) values (?,?,?,?,?, ?)",("Piet","","Paulusma", "piet@paulusma.nl", 1234567890, ""))
#c.execute("CREATE TABLE IF NOT EXISTS Tickets( TicketID INTEGER PRIMARY KEY AUTOINCREMENT, TicketNummer TEXT NOT NULL UNIQUE, OrderID INT NOT NULL, TicketTypeID INT NOT NULL, CustomerName TEXT NOT NULL, Scanned BOOLEAN NOT NULL,FOREIGN KEY(OrderID) REFERENCES TicketOrders(OrderID) ,FOREIGN KEY(TicketTypeID) REFERENCES OfferedTickets(TicketTypeID));")
#conn.commit()
#----------------------------------


bericht = "-"
order = {}
totalAmount = 0.0
source = "Regular"

# ------------ ROUTES ------------------------

@app.route('/', methods=["POST","GET"] )
def main():

    global rows
    global order
    global totalAmount
    global bericht
    global PaymentStarted

    rows = {0,0,0}

    bericht = "Main - start"

    if order_cookie_not_set():
        session.clear()
        session['orderstatus'] = "Empty"
    else:
        key = session.get('orderstatus')
        bericht = key



    # mapping the inputs to the function blocks
    options = { "Empty" : GetOrder,
                 "message" : ShowMessage,
                 "Ordering" : GetOrder,
                 "Order placed" : ConfirmOrder,
                 "Order checked" : GetCustomerInfo,
                 "NAW done" : InitiatePayment,
                 "Payment open" : InitiatePayment,
                 "Payment pending" : InitiatePayment,
                 "Payment initiated" : FinishPayment,
                 "Payment done" : GenerateTickets,
                 "Tickets Generated" : SendTickets,
                 "Tickets Sent" : Finished,}

    renderPage = { "Empty" : 'main.html',
                 "message" : 'message.html',
                 "Ordering" : 'main.html',
                 "Order placed" : 'confirmOrder.html',
                 "Order checked" : 'NAW-form.html',
                 "NAW done" : 'startPayment.html',
                 "Payment open" : 'startPayment.html',
                 "Payment pending" : 'startPayment.html',
                 "Payment initiated" : 'pendingPayment.html',
                 "Payment done" : 'paymentSuccess.html',
                 "Tickets Generated" : 'ticketsGenerated.html',
                 "Tickets Sent" : 'thankYou.html',}

    options[session['orderstatus']](request.method) # this determines which Funcion is called


    #bericht = session['orderstatus']
    #bericht = rows

    if PaymentStarted:
        FinishPayment('GET')

    if session['orderstatus'] == 'NAW done':
        InitiatePayment('GET')
        PaymentStarted = True

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

    if request.method == 'POST':

        actie = request.form.get("action")[:3]

        if actie == "Del":
            record = request.form.get("action")
            record = int(record.split()[2]) # splits "Delete 2"
            bericht = "Deleted record "+ str(record)

            c.execute("DELETE FROM CustomerInfo WHERE CustomerID = %s " % record)
            conn.commit()
            c.execute("SELECT * FROM CustomerInfo")
            conn.commit()
            rows=c.fetchall()

    return render_template('showCustomers.html', rows=rows , bericht = bericht)


@app.route('/showTickets' , methods=["POST","GET"])
def showTickets():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM Tickets")
    conn.commit()

    rows=c.fetchall()
    conn.commit()

    if request.method == 'POST':

        actie = request.form.get("action")[:3]

        if actie == "Del":
            record = request.form.get("action")
            record = int(record.split()[2]) # splits "Delete 2"
            bericht = "Deleted record "+ str(record)

            c.execute("DELETE FROM Tickets WHERE TicketID = %s " % record)
            conn.commit()
            c.execute("SELECT * FROM Tickets")
            conn.commit()
            rows=c.fetchall()

    return render_template('showTickets.html', rows=rows , bericht = bericht)

@app.route('/showOrders' , methods=["POST","GET"])
def showOrders():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM TicketOrders")
    conn.commit()

    rows=c.fetchall()
    conn.commit()

    if request.method == 'POST':

        actie = request.form.get("action")[:3]

        if actie == "Del":
            record = request.form.get("action")
            record = int(record.split()[2]) # splits "Delete 2"
            bericht = "Deleted record "+ str(record)

            c.execute("DELETE FROM TicketOrders WHERE OrderID = %s " % record)
            conn.commit()
            c.execute("SELECT * FROM TicketOrders")
            conn.commit()
            rows=c.fetchall()

    return render_template('showOrders.html', rows=rows , bericht = bericht)






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

@app.route('/MollyReturn')
def MollyReturn():
    session['user_id'] = "Not"
    return redirect('/login')


@app.route('/admin')
def admin():

    if not(login_required()):
        return redirect("/login")

    return render_template('admin.html')



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

    bericht = "GetOrder"
    if method == 'POST':

        order = {}

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
                bericht += str(amountOrdered) + " x " + ticketName + " à € " + price  + "0 = € " + str(totalPerTicket) + "0 | "
                totalAmount += totalPerTicket
                order[int(ticketID)] = int(amountOrdered)



        if totalAmount > 0 :

            #bericht = order #om de order te checken in session['order']

            if login_required():
                source = "admin"
            else:
                source = "customer"

            session['orderstatus'] = "Order placed"
            session['totalAmount'] = totalAmount
            session['order'] = order
            c.execute("INSERT INTO Ticketorders (totalAmount, CustomerID, MollieID, OrderStatus , Source) values (?, ?, ?, ?, ?)",(totalAmount, 999999, "unknown","placed", source))
            conn.commit()
            c.execute("SELECT OrderID from Ticketorders WHERE OrderID = (SELECT MAX(OrderID) FROM TicketOrders);")
            conn.commit()
            OrderID = c.fetchall()
            bericht = order
            session['OrderID'] = int("".join(filter(str.isdigit, str(OrderID[0]))))
        else:
            bericht = "Geen tickets geselecteerd"
            session['orderstatus'] = "message"
        return

    else:
        bericht = ""
        c.execute("SELECT * FROM OfferedTickets")
        conn.commit()
        rows = c.fetchall()
        session['orderstatus'] = "Ordering"
        return


def ConfirmOrder(method):
    global bericht
    global session

    if method == 'POST':
        if request.form['confirm'] == 'Annuleren':
            bericht = "Bedankt voor uw bezoek"
            session['orderstatus'] = "message"
            return

        session['orderstatus'] = "Order checked"
        bericht="ConfirmOrder"

        OrderID = session['OrderID']

        c.execute("UPDATE TicketOrders SET OrderStatus = 'confirmed' WHERE OrderID = %s" % OrderID )
        conn.commit()


    return

def GetCustomerInfo(method):
    global bericht
    global rows
    global session

    if method == "POST":
        bericht = "POST"


        voornaam = request.form["Voornaam"]
        tv = request.form["TV"]
        achternaam = request.form["Achternaam"]
        email = request.form["Email"]
        tlnr = request.form["TelNr"]  # tussenstap
        tel = int(tlnr)

        Cname = voornaam
        if tv != "":
            Cname += " " + tv
        Cname += " "+achternaam

        session["CustomerName"] = Cname
        session["email"] = email

        try:
            WDYFU = request.form["WhereDidYouFindUs"]
        except:
            WDYFU = "?"

        c.execute("INSERT INTO CustomerInfo (Voornaam, TV, Achternaam, Email, TelNr, WhereDidYouFindUs) values (?, ?, ?, ?, ?, ?)",(voornaam, tv, achternaam, email, tel, WDYFU))
        conn.commit()

        session['orderstatus'] = "NAW done"

        c.execute("SELECT CustomerID FROM CustomerInfo WHERE CustomerID = (SELECT MAX(CustomerID) FROM CustomerInfo);")
        conn.commit()
        ID = c.fetchall()
        bericht = str(ID[0])
        session['CustomerID'] = int("".join(filter(str.isdigit, str(ID[0]))))

        return

    if method == "GET":
        bericht = "GET"


    return

def InitiatePayment(method):
    global bericht
    global totalAmount
    global payment
    global session
    global source

    CustomerID = str(session['CustomerID'])
    totalAmount = str(session['totalAmount'])

    #bericht="InitiatePayment"

    payment = mollie_client.payments.create({
        'amount': {
            'currency': 'EUR',
            'value': str(totalAmount)+"0"  # standaard geeft het formulier 10.0 of zo. Dus.. + "0" vanwege Mollie
        },
        'description': 'CustomerID : ' + CustomerID,
        'redirectUrl': 'https://kkff.pythonanywhere.com/returnFromMollie',
        'webhookUrl': 'https://kkff.pythonanywhere.com//mollie-webhook/', })

    #bericht = str(totalAmount)
    bericht = payment.checkout_url  # Let op !  Dit wordt in de view (template) verwerkt in een href
    session['orderstatus'] = "Payment initiated"

    mollieID = ""

    OrderID = session['OrderID']
    CustomerID = session['CustomerID']

    c.execute("UPDATE TicketOrders SET CustomerID = %s WHERE OrderID = %s" % ( CustomerID , OrderID ))
    conn.commit()

    return

@app.route('/returnFromMollie' , methods=["POST","GET"])
def returnFromMollie():
    global bericht
    global session
    global totalAmount
    global payment

    bericht = "Entering FinishPayment"
    rows = {}
    FinishPayment('POST')

    try:
        if session['orderstatus'] != "Payment done" and session['orderstatus'] != "Payment initiated" :
            bericht = session['orderstatus']
            return render_template( 'plzDontTry.html', rows = rows, bericht = bericht, totalAmount = totalAmount )
    except:
            bericht = "error when trying to get session info"
            return render_template( 'plzDontTry.html', rows = rows, bericht = bericht, totalAmount = totalAmount )

    OrderID = session['OrderID']

    c.execute("UPDATE Ticketorders SET OrderStatus = 'payed'")
    conn.commit()

    GenerateTickets('GET')

    return render_template( 'paymentSuccess.html', rows = rows, bericht = bericht, totalAmount = totalAmount )


def FinishPayment(method):
    global bericht
    global session
    bericht="FinishPayment"

    try:
        #
        # Retrieve the payment's current state.
        #
        if 'id' not in request.form:
            bericht = ""
            return

        payment_id = request.form['id']
        payment = mollie_client.payments.get(payment_id)
        my_webshop_id = payment.metadata['my_webshop_id']

        #
        # Update the order in the database.
        #

        if payment.is_paid():
            #
            # At this point you'd probably want to start the process of delivering the product to the customer.
            #
            session['orderstatus'] = "Payment done"
            bericht - "Payment Successful !"
            OrderID = session['OrderID']
            MollieID = my_webshop_id
            MollieID = "TEST"
            c.execute("UPDATE TicketOrders SET MollieID = %s WHERE OrderID = %s" % ( MollieID , OrderID ))
            conn.commit()

        elif payment.is_pending():
            #
            # The payment has started but is not complete yet.
            #
            session['orderstatus'] = "Payment pending"
            bericht - "Payment Pending !"

        elif payment.is_open():
            #
            # The payment has not started yet. Wait for it.
            #
            session['orderstatus'] = "Payment open"
            bericht - "Payment Open !"

        elif payment.is_cancelled():
            #
            # The payment has not started yet. Wait for it.
            #
            session['orderstatus'] = "message"
            bericht - "Payment cancelled"

        else:
            #
            # The payment isn't paid, pending nor open. We can assume it was aborted.
            #
            session['orderstatus'] = "message"
            bericht - "Payment crashed"



    except Error as err:
        bericht = "API call failed"
        return


    rows = {}

    #return render_template( 'paymentSuccess.html', rows = rows, bericht = "WHAT ?!", totalAmount = totalAmount )
    return

def GenerateTickets(method):
    global bericht

    bericht="GenerateTickets"

    order = session['order']
    customerID = session['CustomerID']
    orderID = session['OrderID']
    ticketbatch = []

    CustomerName = session["CustomerName"]
    counter = 1

    for key in order:
        for t in range(order[key]):

            ticketNr = "KKFF2019-" + str(customerID) + "-" + str(orderID) + "-" + str(counter)
            TicketTypeID = key
            c.execute("INSERT INTO Tickets (TicketNummer, OrderID, TicketTypeID, CustomerName, Scanned) values (?, ?, ?, ?, ?)",(ticketNr, orderID, TicketTypeID, CustomerName, 'False'))
            conn.commit()

            c.execute("SELECT TicketID FROM Tickets WHERE TicketID = (SELECT MAX(TicketID) FROM Tickets);")
            conn.commit()
            ID = c.fetchall()
            bericht = str(ID[0])
            ticketID = int("".join(filter(str.isdigit, str(ID[0]))))
            email = session["email"]

            k = int(key)

            c.execute("SELECT * FROM OfferedTickets WHERE TicketTypeID = %s " % k)
            conn.commit

            f = c.fetchall()

            TicketType = f[0][1]
            Ticket = makeTicket(ticketID, ticketNr, TicketTypeID, TicketType, CustomerName)

            ticketbatch.append(Ticket)

            counter += 1

            # ---------------- mail the tickets to the customer -------------------

            # initiate a secure connection

            email_user = 'KuylKampTicketService@gmail.com'
            email_password = 'KuylKuyl_01'
            email_send = email #argument meegegeven bij het aanroepen van de functie

            subject = 'Tickets KuylKamp Familiefestival'

            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = email_send
            msg['Subject'] = subject

            body = 'Beste ' + CustomerName + ","
            body+=  """
            Bij dezen ontvangt u de door u bestelde tickets voor het KuylKamp Familiefestival.
            Gelieve deze tickets uit te printen en mee te brengen naar het Festival.
            Veel plezier op het festival !
            De festival-organisatie.
            """

            msg.attach(MIMEText(body,'plain'))

            for att in ticketbatch:
                filename= "/home/kkff/mysite/" + att
                attachment  =open(filename,'rb')

                part = MIMEBase('application','octet-stream')
                part.set_payload((attachment).read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',"attachment; filename= "+filename)
                msg.attach(part)

    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(email_user,email_password)


    server.sendmail(email_user,email_send,text)
    server.quit()



    return

def SendTickets():
    global bericht
    bericht="SendTickets"
    return

def Finished():
    global bericht
    bericht="Finished"
    return

def ShowMessage(method):
    global session
    global bericht

    session['orderstatus'] = 'Empty'
    return



