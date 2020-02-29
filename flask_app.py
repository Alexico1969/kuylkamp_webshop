# -*- coding: utf-8 -*-
from flask import Flask, flash, render_template, request, redirect, session, url_for
import sqlite3
import datetime
import os
import glob
import smtplib
import csv
from helpers import makeTicket
from os import path
from MolliePy.mollie.api.client import Client
from MolliePy.mollie.api.error import Error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from random import randint
from fpdf import FPDF
from mailjet_rest import Client as MClient


# -- Setting up App --

app = Flask(__name__)
app.secret_key = "any random string"
app.config['SECRET_KEY'] = 'something-secret2'

# -- Setting up Mailjet --

api_key = '3eee713a034928c6b8c4642e43096140'
api_secret = '85bbed691accdfb742942aaadca82b8e'
mailjet = MClient(auth=(api_key, api_secret), version='v3.1')


# -- Setting up Mollie

mollie_client = Client()
#mollie_client.set_api_key('test_9Q9RUAA2xbT7CtTvBdS7WerNGwTV88') # TESTKEY
mollie_client.set_api_key('live_vP5pmxwcMWN3RENK3P7SfUupT9ghej') # LIVEKEY


# -- Setting up SQLite database --

ROOT = path.dirname(path.realpath(__file__))
conn = sqlite3.connect(path.join(ROOT,"kkff.db"))
c = conn.cursor()
startdate  = datetime.datetime(2019, 6, 20)

PaymentStarted = False


# -- TESTING MAILJET _ TEMP --

data = {
  'Messages': [
    {
      "From": {
        "Email": "info@alexicoo.nl",
        "Name": "Alex"
      },
      "To": [
        {
          "Email": "info@alexicoo.nl",
          "Name": "Alex"
        }
      ],
      "Subject": "Greetings from Mailjet.",
      "TextPart": "My first Mailjet email",
      "HTMLPart": "<h3>Dear passenger 1, welcome to <a href='https://www.mailjet.com/'>Mailjet</a>!</h3><br />May the delivery force be with you!",
      "CustomID": "AppGettingStartedTest"
    }
  ]
}
result = mailjet.send.create(data=data)
print("*** status_code: ",result.status_code)
print("*** result: ",result.json())



#---------DATABASE STUFF-----------
#c.execute("DROP TABLE Tickets;")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS OfferedTickets( TicketTypeID INTEGER PRIMARY KEY AUTOINCREMENT, TicketName TEXT NOT NULL, TicketPrice FLOAT NOT NULL);")
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS TicketOrders( OrderID INTEGER PRIMARY KEY AUTOINCREMENT, TotalAmount FLOAT NOT NULL, DateTime DATETIME DEFAULT CURRENT_TIMESTAMP, CustomerID INTEGER NOT NULL, MollieID TEXT NOT NULL , OrderStatus TEXT NOT NULL, Source TEXT NOT NULL, FOREIGN KEY(CustomerID) REFERENCES CustomerInfo(CustomerID));")
#c.execute("CREATE TABLE IF NOT EXISTS CustomerInfo( CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, Voornaam TEXT NOT NULL , TV TEXT NOT NULL, Achternaam TEXT NOT NULL, Email TEXT NOT NULL, TelNr INT NOT NULL, WhereDidYouFindUs TEXT);")
#c.execute("INSERT INTO CustomerInfo( Voornaam,TV,Achternaam,Email,TelNr,WhereDidYouFindUs) values (?,?,?,?,?, ?)",("Piet","","Paulusma", "piet@paulusma.nl", 1234567890, ""))
#c.execute("CREATE TABLE IF NOT EXISTS Tickets( TicketID INTEGER PRIMARY KEY AUTOINCREMENT, TicketNummer TEXT NOT NULL UNIQUE, OrderID INT NOT NULL, TicketTypeID INT NOT NULL, CustomerName TEXT NOT NULL, Scanned BOOLEAN NOT NULL, ScanDate TEXT, Ctrl INT NOT NULL,FOREIGN KEY(OrderID) REFERENCES TicketOrders(OrderID) ,FOREIGN KEY(TicketTypeID) REFERENCES OfferedTickets(TicketTypeID));")
#c.execute("INSERT INTO OfferedTickets (TicketTypeID, TicketName, TicketPrice) values (? , ?, ?)",(7 , 'Zaterdagavond', 20.0))
#conn.commit()
#c.execute("CREATE TABLE IF NOT EXISTS PeopleList(Name TEXT NOT NULL);")
#conn.commit()
#c.execute("UPDATE OfferedTickets SET TicketName = 'Kind (4-12 jaar)' WHERE TicketTypeID = 13")
#conn.commit()
#c.execute("UPDATE Tickets SET ScanDate = '0' WHERE TicketID = 19")
#conn.commit()
#c.execute("UPDATE Tickets SET Scanned = 'False' WHERE TicketID = 19")
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

    if user_cookie_not_set():
        session['user'] = "customer"

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

    if PaymentStarted:
        FinishPayment('GET')

    if session['orderstatus'] == 'NAW done':
        InitiatePayment('GET')
        PaymentStarted = True

    #session['rows'] = rows

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

    bericht = ""

    CreatePDF(rows)
    createCSV(rows)

    return render_template('addTicketType.html', rows=rows , bericht = bericht)



@app.route('/showCustomers' , methods=["POST","GET"])
def showCustomers():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM CustomerInfo ORDER BY CustomerID DESC")
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
            c.execute("SELECT * FROM CustomerInfo ORDER BY CustomerID DESC")
            conn.commit()
            rows=c.fetchall()

    CreatePDF(rows)
    createCSV(rows)

    return render_template('showCustomers.html', rows=rows , bericht = bericht)


@app.route('/showTickets' , methods=["POST","GET"])
def showTickets():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM Tickets ORDER BY TicketID DESC")
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
            c.execute("SELECT * FROM Tickets ORDER BY TicketID DESC")
            conn.commit()
            rows=c.fetchall()

        if actie == "Res":
            record = request.form.get("action")
            record = int(record.split()[2]) # splits "Delete 2"
            bericht = "Record "+ str(record) + " is reset"
            DateTime = 0
            c.execute("UPDATE Tickets SET Scanned = 'False' WHERE TicketID = %s" % record )
            conn.commit()
            c.execute("UPDATE Tickets SET ScanDate ==:pv0 WHERE TicketID ==:pv1", {"pv0":DateTime, "pv1":record})
            conn.commit()
            rows=c.fetchall()

    #session['rows'] = rows

    CreatePDF(rows)
    createCSV(rows)

    return render_template('showTickets.html', rows=rows , bericht = bericht)

@app.route('/showOrders' , methods=["POST","GET"])
def showOrders():

    bericht=" - "

    if not(login_required()):
        return redirect("/login")

    c.execute("SELECT * FROM TicketOrders ORDER BY OrderID DESC")
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
            c.execute("SELECT * FROM TicketOrders ORDER BY OrderID DESC")
            conn.commit()
            rows=c.fetchall()
            rows.sort(reverse=True)

    #session['rows'] = rows

    CreatePDF(rows)
    createCSV(rows)

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

def login_required2():

    try:
        key = session.get('user_id', 'Harry')
    except:
        return False

    if key == "Scan":
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

def user_cookie_not_set():

    try:
        key = session.get('user')
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

        return render_template('admin.html')

    return render_template('login.html')

@app.route('/login2', methods=["POST","GET"])
def login2():
    global CurrentUrl
    global message

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error=None

        if (username != "Kuyl") or (password != "K@mp"):
            error = "Incorrect username."
            return render_template('login.html')

        if error is None:
            session.clear()
            session['user_id'] = "Scan"
            bericht = "ingelogd !"
            return render_template('bericht.html', bericht = bericht)

        bericht = "Hallo !"

        return render_template('bericht.html' , bericht = bericht)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session['user_id'] = "Not"
    return redirect('/login')

@app.route('/MollyReturn')
def MollyReturn():
    session['user_id'] = "Not"
    return redirect('/login')

@app.route('/purge')
def purge():
    c.execute("DELETE FROM TicketOrders;")
    c.execute("DELETE FROM sqlite_sequence WHERE name='TicketOrders';")
    c.execute("DELETE FROM Tickets;")
    c.execute("DELETE FROM sqlite_sequence WHERE name='Tickets';")
    c.execute("DELETE FROM CustomerInfo;")
    c.execute("DELETE FROM sqlite_sequence WHERE name='Customers';")
    conn.commit()

    for fl in glob.glob("mysite/PDF/*.*"):
        os.remove(fl)

    return redirect('/admin')




@app.route('/admin')
def admin():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"
    return render_template('admin.html')

@app.route('/tools')
def tools():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"
    return render_template('tools.html')

@app.route('/riet', methods=["POST","GET"])
def riet():

    global bericht
    bericht="----"

    if request.method  == 'POST':
        code = request.form['code']
        if str(code) == '1591':
            session['molliekey'] = 'test_9Q9RUAA2xbT7CtTvBdS7WerNGwTV88'
            session['user']="Riet"
            return redirect("/")
        else:
            bericht = "Foutieve pin"




    return render_template('riet.html', bericht=bericht)

@app.route('/reset')
def reset():
    session['orderstatus'] = 'Empty'
    session['totalAmount'] = 0
    session['order'] = {}
    session['user'] = "customer"
    return redirect("/")


'''

   Check for logged in at start of function :

        if not(login_required()):
        return redirect("/login")



    '''

@app.route('/bezoekers', methods=["POST","GET"])
def bezoekers():

    data = [0,0,0,0,0,0,0,0]

    '''
    0 = vrijdagavond - verwacht
    1 = vrijdagavond - gescand
    2 = zaterdagmiddag - verwacht
    3 = zaterdagmiddag - gescand
    4 = zaterdagavond - verwacht
    5 = zaterdagavond - gescand
    6 = zondag - verwacht
    7 = zondag - gescand
    '''

    c.execute("SELECT * FROM Tickets")
    rows = c.fetchall()
    conn.commit()

    bericht = ""

    check = {
        2 : 'vrav zami zaav zon',
        5 : 'vrav',  # betekent : een kaartje met ID 5 is voor de vrijdagavond
        6 : 'zami',
        10 : 'zami zaav',
        11 : 'zon',
        13 : 'zami zaav',
        14 : 'vrav zami zaav zon',
        15 : 'zami zaav',
        16 : 'vrav zami zaav zon',
        }

    for row in rows:

        TicketTypeId = row[3]
        gescand = row[5]

        for key in check:
            if TicketTypeId == key:
                if 'vrav' in check[key]:
                    data[0] += 1
                    if gescand == 'True':
                        data[1] +=1
                if 'zami' in check[key]:
                    data[2] += 1
                    if gescand == 'True':
                        data[3] +=1
                if 'zaav' in check[key]:
                    data[4] += 1
                    if gescand == 'True':
                        data[5] +=1
                if 'zon' in check[key]:
                    data[6] += 1
                    if gescand == 'True':
                        data[7] +=1




    return render_template("bezoekers.html", data = data , bericht = bericht)



@app.route('/scanTicket', methods=["POST","GET"])
def scanTicket():

    d1 = datetime.datetime.now()
    d2 = startdate


    if d1<d2:
        bericht = "Het festival is nog niet begonnen !"
        site = "message.html"
        return render_template(site , bericht = bericht)



    try:
        TicketID = int(request.args.get('ticketID'))
        CtrlScan = int(request.args.get('ctrl'))
    except:
        site = "message.html"
        bericht = "Scan - error"
        return render_template(site , bericht = bericht)

    c.execute("SELECT * FROM Tickets WHERE TicketID =%s" % TicketID)
    conn.commit()

    rows = c.fetchall()


    try:
        state = rows[0][5]
        ctrl = rows[0][7]
    except:
        site = "NOTOK.html"
        return render_template(site , CustomerName = "No such Ticket")

    if state == "False":
        if CtrlScan == ctrl:
            site = "OK.html"
            name = rows[0][4]  #CustomerName
            now = datetime.datetime.now()
            DateTime = str(now.strftime("%Y-%m-%d %H:%M"))
            c.execute("UPDATE Tickets SET Scanned = 'True' WHERE TicketID = %s" % TicketID )
            conn.commit()
            c.execute("UPDATE Tickets SET ScanDate ==:pv0 WHERE TicketID ==:pv1", {"pv0":DateTime, "pv1":TicketID})
            conn.commit()
            if rows[0][3] == 17:
                site="ThanksForDonation.html"
                name="Bedankt voor uw donatie - Dit is echter geen ticket !"
        else:
            site = "NOTOK.html"
            name = "bad ctrl"
    else:
        site = "NOTOK.html"
        name = rows[0][6]  #DateScanned



    return render_template(site , CustomerName = name)

@app.route('/acceptByOrderNr', methods=["POST","GET"])
def acceptByOrderNr():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    if request.method == 'POST':

        TicketID_input = int(request.form['OrderNr'])
        session['OrderID'] = TicketID_input
        c.execute("SELECT * FROM Tickets WHERE OrderID = %s " % TicketID_input )
        conn.commit()
        rows=c.fetchall()

        return render_template('acceptedByOrderNrShowTickets.html' , rows=rows, bericht = "acceptByOrderNr")

    else:
        return render_template('acceptByOrderNr.html')

@app.route('/acceptBO', methods=["POST","GET"])   # accept bij Order Nr.
def acceptBO():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    if request.method == 'POST':

        try:
            temp = request.form['OBON']
        except:
            bericht = "Deze pagina is niet rechtstreeks benaderbaar !";
            return render_template( 'message.html',bericht = bericht )


        orderID = session['OrderID']

        c.execute("UPDATE Tickets SET Scanned = 'True' WHERE OrderID = %s" % orderID)
        conn.commit()

        now = datetime.datetime.now()
        DateTime = str(now.strftime("%Y-%m-%d %H:%M"))
        c.execute("UPDATE Tickets SET ScanDate ==:pv0 WHERE OrderID ==:pv1", {"pv0":DateTime, "pv1":orderID})
        conn.commit()

        c.execute("SELECT * FROM Tickets WHERE OrderID = %s " % orderID )
        conn.commit()
        rows=c.fetchall()



        return render_template('acceptedByOrderNrShowTickets.html' , rows=rows, bericht = "acceptByOrderNr")

@app.route('/listWT', methods=["POST","GET"])  #list weekend-tickets
def listWT():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    c.execute("SELECT * FROM Tickets WHERE TicketTypeID ='2' ")

    conn.commit()
    rows=c.fetchall()

    CreatePDF(rows)
    createCSV(rows)

    return render_template('listWeekendTickets.html' , rows=rows, bericht = bericht)


@app.route('/peoplelist',methods=["POST","GET"])  #display list of ski jumpers
def peoplelist():
    rows=""
    bericht=""

    c.execute("SELECT CustomerName FROM Tickets WHERE Scanned = 'True' ORDER BY ScanDate DESC LIMIT 10;")
    conn.commit()
    temprows = c.fetchall()

    rows = []

    for row in temprows:
            rows += row

    rows = list(dict.fromkeys(rows))

    CreatePDF(rows)
    createCSV(rows)

    return render_template('peoplelist.html' , rows=rows, bericht = rows)


@app.route('/MakePDF', methods=["GET"])
def MakePDFList():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    return render_template('showPDF.html')


def CreatePDF(rows):

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    dt = str(datetime.datetime.now())

    # Create PDF
    pdf = FPDF()
    pdf.add_page(orientation = 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.write(5, 'Rows : ')
    pdf.ln(h = '')

    for row in rows:
        pdf.write(5, str(row))
        pdf.write(5,',')
        pdf.ln(h = '')

    pdf.output('tuto1.pdf', 'F')


    #pdf_filename =  dt + ".pdf"
    pdf_filename =  "output.pdf"

    pdf.output( "mysite/PDF/" + pdf_filename, 'F')

    return


def createCSV(rows):

    ofile  = open('mysite/PDF/rows.csv', "wt")
    writer = csv.writer(ofile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

    for row in rows:
        writer.writerow(row)

    ofile.close()

    return

@app.route('/ShowStats', methods=["GET"])
def ShowStats():

    if not(login_required()):
        return redirect("/login")

    session['user'] = "Admin"

    c.execute("SELECT * FROM Tickets;")
    conn.commit()
    temprows = c.fetchall()

    rows = {}
    counter = 0
    weekendCounter = 0
    vrijdagCounter = 0
    zaterdagCounter = 0
    zondagCounter = 0
    zamiCounter = 0
    kindCounter = 0
    kindWeekendCounter = 0
    tienerCounter = 0
    tienerWeekendCounter = 0
    donatieCounter = 0


    for row in temprows:
        counter += 1
        ticket = row[3]
        if ticket == 2:
            weekendCounter += 1
        if ticket == 5:
            vrijdagCounter += 1
        if ticket == 6:
            zamiCounter += 1
        if ticket == 10:
            zaterdagCounter += 1
        if ticket == 11:
            zondagCounter += 1
        if ticket == 13:
            kindCounter += 1
        if ticket == 14:
            kindWeekendCounter += 1
        if ticket == 15:
            tienerCounter += 1
        if ticket == 16:
            tienerWeekendCounter += 1
        if ticket == 17:
            donatieCounter += 1



    rows["TotaalTickets"] = counter
    rows["WeekendCounter"] = weekendCounter
    rows["VrijdagCounter"] = vrijdagCounter
    rows["ZaterdagCounter"] = zaterdagCounter
    rows["ZamiCounter"] = zamiCounter
    rows["ZondagCounter"] = zondagCounter
    rows["KindCounter"] = kindCounter
    rows["KindWeekendCounter"] = kindWeekendCounter
    rows["TienerCounter"] = tienerCounter
    rows["TienerWeekendCounter"] = tienerWeekendCounter
    rows["DonatieCounter"] = donatieCounter




    return render_template('ShowStats.html', rows = rows)


#------------------------------- FUNCTIONS BASED ON ORDERSTATUS -----------------------------------------

def GetOrder(method):

    global bericht
    global rows
    global totalAmount

    bericht = "GetOrder"
    if method == 'POST':

        try:

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

                try:
                    if session['user'] == "Riet":
                        source = "Riet"
                except:
                    print('*** session key eror ***')

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

        except:
            bericht = "Fout in bestelling"
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
        bericht="-"

        OrderID = session['OrderID']

        c.execute("UPDATE TicketOrders SET OrderStatus = 'confirmed' WHERE OrderID = %s" % OrderID )
        conn.commit()


    return

def GetCustomerInfo(method):
    global bericht
    global rows
    global session

    bericht="";

    if method == "POST":

        voornaam = request.form["Voornaam"]
        tv = request.form["TV"]
        achternaam = request.form["Achternaam"]
        email = request.form["Email"]
        email2 = request.form["Email2"]

        if email != email2:
            bericht="emailadressen komen niet overeen";
            print( '*** EMAILS NIET HETZELFDE ***')
            render_template( 'message.html',bericht = bericht )

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

        if bericht =="":

            c.execute("INSERT INTO CustomerInfo (Voornaam, TV, Achternaam, Email, TelNr, WhereDidYouFindUs) values (?, ?, ?, ?, ?, ?)",(voornaam, tv, achternaam, email, '0', WDYFU))
            conn.commit()

            session['orderstatus'] = "NAW done"

            c.execute("SELECT CustomerID FROM CustomerInfo WHERE CustomerID = (SELECT MAX(CustomerID) FROM CustomerInfo);")
            conn.commit()
            ID = c.fetchall()
            bericht = str(ID[0])

            session['CustomerID'] = int("".join(filter(str.isdigit, str(ID[0]))))

            CustomerID = session['CustomerID']
            OrderID = session['OrderID']

            c.execute("UPDATE TicketOrders SET CustomerID ==:pv0 WHERE OrderID ==:pv1", {"pv0":CustomerID, "pv1":OrderID})

            conn.commit()

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

    if not(session['user']):
        bericht = "SESSION - ERROR"
        session['orderstatus'] = message
        return
    elif (session['user'] == "Admin" or session['user'] == "Riet"):
        flash('User : ' + session['user'])
        if session.get("molliekey"):
            mollie_client.set_api_key(session['molliekey'])
        else:
            mollie_client.set_api_key('live_vP5pmxwcMWN3RENK3P7SfUupT9ghej')
    elif session['user'] != "customer":
        bericht = "SESSION - ERROR - User: " + str(session['user'])
        session['orderstatus'] = "message"
        return


    #mollie_client.set_api_key('test_NtexBbugzAF7ebKvmvEUfdhDjuBckN')  # <<< Om te testen, un-comment deze regel code


    payment = mollie_client.payments.create({
        'amount': {
            'currency': 'EUR',
            'value': str(totalAmount)+"0"  # standaard geeft het formulier 10.0 of zo. Dus.. + "0" vanwege Mollie
        },
        'description': 'CustomerID : ' + CustomerID,
        'redirectUrl': 'https://kkff.pythonanywhere.com/returnFromMollie',
        #'webhookUrl': 'https://kkff.pythonanywhere.com//mollie-webhook/',
        'webhookUrl': 'https://kkff.pythonanywhere.com/webhook',

        })


    bericht = payment.checkout_url  # Let op !  Dit wordt in de view (template) verwerkt in een href

    session['MollieID'] = payment.id
    MollieID = session['MollieID']
    OrderID = session['OrderID']

    c.execute("UPDATE TicketOrders SET MollieID ==:pv0 WHERE OrderID ==:pv1", {"pv0":MollieID, "pv1":OrderID})
    conn.commit

    return

    session['orderstatus'] = "Payment initiated"

    OrderID = session['OrderID']
    CustomerID = session['CustomerID']

    c.execute("UPDATE TicketOrders SET CustomerID = %s WHERE OrderID = %s" % ( CustomerID , OrderID ))

    conn.commit()

    return

@app.route('/webhook' , methods=["POST","GET"])
def webhook():
    global bericht
    global session
    global totalAmount
    global payment

    order_id = request.form['id']




    return render_template( 'message.html',bericht = bericht )

    bericht = "Entering FinishPayment"
    rows = {}
    FinishPayment('POST')



    return render_template( 'message.html',bericht = bericht )


@app.route('/returnFromMollie' , methods=["POST","GET"])
def returnFromMollie():
    global bericht
    global session
    global totalAmount
    global payment

    try:
        pay_ID = session['MollieID']
    except:
        bericht = "No MollieID"
        return render_template( 'message.html', bericht = bericht )

    try:
        payment = mollie_client.payments.get(pay_ID)
    except:
        bericht = "Mollie Key Error"
        return render_template( 'message.html', bericht = bericht )

    mollie_client.set_api_key('live_vP5pmxwcMWN3RENK3P7SfUupT9ghej')

    if payment.is_paid():

        OrderID = session['OrderID']

        c.execute("UPDATE Ticketorders SET OrderStatus = 'payed' WHERE OrderID is %s" % OrderID)
        conn.commit()

        GenerateTickets('GET')

        return render_template( 'paymentSuccess.html', rows = rows, bericht = bericht, totalAmount = totalAmount )

    else:

        bericht = "Order not payed"
        return render_template( 'message.html', bericht = bericht )


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
    global order
    global PaymentStarted

    bericht="GenerateTickets"

    order = session['order']
    customerID = session['CustomerID']
    orderID = session['OrderID']
    ticketbatch = []

    CustomerName = session["CustomerName"]
    counter = 1


    for key in order:
        for t in range(order[key]):



            ctrl = randint(1111, 9999)
            rnd = randint(0000, 9999)

            ticketNr = "KKFF2020-" + str(customerID) + "-" + str(orderID) + "-" + str(counter) + "-" + str(rnd);
            TicketTypeID = key
            DateTime = 0
            c.execute("INSERT INTO Tickets (TicketNummer, OrderID, TicketTypeID, CustomerName, Scanned, ScanDate, Ctrl) values (?, ?, ?, ?, ?, ? ,?)",(ticketNr, orderID, TicketTypeID, CustomerName, 'False' , DateTime , ctrl))
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
            Ticket = makeTicket(ticketID, ticketNr, TicketTypeID, TicketType, CustomerName, ctrl)

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
            body +=  """

Hierbij ontvang je de door jou bestelde tickets voor het KuylKamp Familiefestival.
Graag deze tickets uitprinten en meebrengen naar het Festival.
Veel plezier op het festival !

De festival-organisatie.

            """

            body += "OrderID: " + str(orderID)

            msg.attach(MIMEText(body,'plain'))

            for att in ticketbatch:
                filename= "/home/kkff/mysite/" + att
                attachment  =open(filename,'rb')

                part = MIMEBase('application','octet-stream')
                part.set_payload((attachment).read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',"attachment; filename= "+filename)
                msg.attach(part)

    data = {
  'Messages': [
        {
        "From": {
        "Email": "KuylKampTicketService@gmail.com",
        "Name": "KuylKampTicketService"
        },
        "To": [
        {
          "Email": "info@alexicoo.nl",
          "Name": email_send
        }
        ],
        "Subject": 'Tickets KuylKamp Familiefestival',
        "TextPart": body,
        "HTMLPart": "<h3>test!</h3>",
        "CustomID": "AppTest"
        }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())



    '''

    text = msg.as_string()
    #server = smtplib.SMTP('smtp.gmail.com',587)
    server = smtplib.SMTP('smtp.gmail.com', 465)
    server.starttls()
    server.login(email_user,email_password)


    server.sendmail(email_user,email_send,text)
    server.quit() '''

    session['orderstatus'] = 'Empty'
    PaymentStarted = False
    bericht = "-"
    order = {}
    totalAmount = 0.0


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














