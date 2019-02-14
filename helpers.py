import csv
import os
import urllib.request
import qrcode
import datetime

from fpdf import FPDF
from flask import redirect, render_template, request, session
from functools import wraps



def makeTicket(TicketNr, TicketTypeID, Customername):

    #def create_ticket(klantID, soort, t, klantnaam_volledig):

    global ks

    ks = TicketTypeID
    nummer = TicketNr

    '''
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=12, border=4, )
    #qr.add_data('klantID: '+str(klantID)+' soort: '+str(soort))
    qr.add_data('http://ide50-alexicoo.cs50.io:8080/scantest?ticketnr=12')
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    #filename_QR = "QR-"+ nummer +".png"
    filename_QR = "QR-temp.png"

    img.save(filename_QR)
    '''

    # Create PDF
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Times', '', 12)
    for i in range(1, 3):
        pdf.cell(0, 10, '' , 0, 1)
    pdf.cell(0, 10, 'Dit is uw ticket dat toegang geeft tot het KuylKamp Familiefestival' , 0, 1)
    pdf.cell(0, 10, 'Neem dit ticket mee en laat het scannen bij de info-stand' , 0, 1)
    pdf.cell(0, 10, 'Ticketnummer : '+nummer , 0, 1)
    pdf.cell(0, 10, 'Op naam van : ' + Customername , 0, 1)

    pdf_filename = nummer + ".pdf"

    pdf.output( "mysite/PDF/" + pdf_filename, 'F')
    #pdf.output( pdf_filename, 'F')

    return ("PDF/" + pdf_filename)

class PDF(FPDF):
    def header(self):

        global ks
        '''
        # Logo
        self.image('img/LOGO.jpg', 10, 8, 33)
        self.image('QR-temp.png', 170, 8, 33)
        '''
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(50)
        # Title
        self.cell(100, 10, 'KuylKamp Familiefestival - ticket', 1, 0, 'C')
        # Line break
        self.ln(20)
        # Move to the right
        self.cell(50)
        # print kaartsoort
        self.cell(100, 10, ks, 1, 0, 'C')

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Pagina ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')



