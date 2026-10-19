import os
import subprocess

# تثبيت المكتبة تلقائياً في حال عدم وجودها
try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call(["pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

import streamlit as st
import pandas as pd
import smtplib
import imaplib
import email
import requests
import re
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
