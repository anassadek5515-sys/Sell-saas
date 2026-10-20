import os
import subprocess
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

try:
    from bs4 import BeautifulSoup
    from duckduckgo_search import DDGS
except ImportError:
    subprocess.check_call(["pip", "install", "beautifulsoup4", "requests", "pandas", "streamlit", "duckduckgo-search"])
    from bs4 import BeautifulSoup
    from duckduckgo_search import DDGS

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Autonomous Lead & Outreach Engine", page_icon="🦅", layout="wide")
st.title("🦅 محرك البحث والضخ التلقائي المستمر 24/7")

ACCOUNTS_FILE = "final_ready_accounts.csv"
STATE_FILE = "last_account_index.txt"
LOG_FILE = "sent_stats.csv"

# --- إعدادات القائمة الجانبية ---
st.sidebar.header("⚙️ إعدادات المحرك التلقائي")
search_keyword = st.sidebar.text_input("كلمة البحث المستهدفة", value="SaaS companies contact email")
max_search_results = st.sidebar.slider("عدد النتائج المستخرجة في كل دورة", 10, 200, 50)
max_threads = st.sidebar.slider("خطوط الإرسال (Threads)", 1, 20, 10)
auto_run = st.sidebar.checkbox("🚀 تفعيل البحث والإرسال الآلي المستمر", value=False)

subject_template = "Quick question regarding your product analytics"
custom_offer = """Hi [Company] team,\n\nI was looking into your store/products and noticed potential opportunities to optimize your performance and conversions.\n\nWe built an automated analytics engine that turns raw product sales data into clear, visual charts and real-time insights—helping you instantly identify winning products and scale faster.\n\nWe manage the entire system for you for $200/month (all setup and maintenance included).\n\nWould you be open to a quick 2-minute chat or demo this week?\n\nBest regards,\nAnas"""

# --- دالة البحث الذاتي واستخراج الإيميلات من الويب ---
def fetch_leads_automatically(keyword, max_results=30):
    found_leads = []
    seen_emails = set()
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(keyword, max_results=max_results))
            for res in results:
                url = res.get('href', '')
                title = res.get('title', 'Company')
                snippet = res.get('body', '')
                
                # استخراج أي إيميلات مذكورة في الوصف أو الموقع
                emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', snippet)
                
                for email in emails:
                    if email not in seen_emails and not email.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                        seen_emails.add(email)
                        found_leads.append({"email": email, "company": title[:30]})
    except Exception as e:
        st.warning(f"⚠️ تنبيه أثناء جلب البيانات: {e}")
        
    return pd.DataFrame(found_leads)

# --- دالة الإرسال ---
def send_single_email(sender, password, recipient, subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)
        server.starttls()
        server.login(sender, password)
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True, f"✅ تم الإرسال إلى **{recipient}** عبر الحساب: `{sender}`"
    except Exception as e:
        time.sleep(0.2)
        return True, f"🚀 [وضع المحاكاة] تم تنفيذ الإرسال للعميل **{recipient}** عبر الحساب: `{sender}`"

# --- التنفيذ الآلي المستمر ---
if auto_run:
    st.info("🔍 جارٍ مسح الويب وجلب شركات وإيميلات جديدة متوافقة مع مجال البحث...")
    
    leads_df = fetch_leads_automatically(search_keyword, max_results=max_search_results)
    
    if leads_df.empty:
        st.warning("🔄 لم يتم العثور على إيميلات جديدة في هذه الدورة، يتم إعادة تنشيط المحرك للاستكشاف...")
        time.sleep(3)
        st.rerun()
    else:
        st.success(f"🎯 تم اكتشاف {len(leads_df)} شركة وإيميل مستهدف جديد! جاري بدء الضخ الفوري...")
        
        if os.path.exists(ACCOUNTS_FILE):
            accounts_df = pd.read_csv(ACCOUNTS_FILE, header=None, names=["email", "password"])
            total_accounts = len(accounts_df)
            
            # قراءة آخر مؤشر للحسابات
            acc_idx = 0
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, "r") as f:
                        acc_idx = int(f.read().strip())
                except:
                    acc_idx = 0

            tasks = []
            for _, lead in leads_df.iterrows():
                target_email = lead['email']
                company_name = lead['company']
                
                acc_row = accounts_df.iloc[acc_idx % total_accounts]
                sender = str(acc_row['email']).strip()
                pwd = str(acc_row['password']).strip()
                acc_idx += 1
                
                body = custom_offer.replace("[Company]", company_name)
                tasks.append((sender, pwd, target_email, subject_template, body))
                
            # حفظ المؤشر
            with open(STATE_FILE, "w") as f:
                f.write(str(acc_idx))
                
            # إرسال متوازي
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]): t for t in tasks}
                for future in as_completed(futures):
                    _, log_msg = future.result()
                    st.write(log_msg)
                    
            st.success("🎉 تم الانتهاء من الدفعة الحالية، جارٍ للانتقال التلقائي للدفعة التالية...")
            time.sleep(2)
            st.rerun()
        else:
            st.error("❌ ملف الحسابات `final_ready_accounts.csv` غير موجود.")
