# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, session
import sqlite3
import csv
import datetime

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('main.html')

