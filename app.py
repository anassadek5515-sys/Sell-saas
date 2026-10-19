import os
import subprocess

# تثبيت المكتبات تلقائياً عند الحاجة
try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call(["pip", "install", "beautifulsoup4", "requests", "pandas"])
    from bs4 import BeautifulSoup

import streamlit as st
import pandas as pd
import smtplib
import imaplib
import email
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(
    page_title="Enterprise B2B Command Center",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 لوحة القيادة المركزية - محرك 280 ألف حساب (السرعة القصوى)")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"
LOG_FILE = "sent_stats.csv"

# --- القائمة الجانبية لإدارة العمليات ---
st.sidebar.header("⚙️ إعدادات المحرك السيادي")
industry_keyword = st.sidebar.text_input("مجال البحث المستهدف", value="SaaS startup contact email")
batch_size = st.sidebar.slider("حجم الدفعة (عدد الشركات)", min_value=50, max_value=500, value=150)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=10, max_value=100, value=50)
auto_loop = st.sidebar.checkbox("🔄 تفعيل التشغيل اللانهائي (Infinite Turbo Loop 24/7)", value=True)

subject_template = st.sidebar.text_input("عنوان الرسالة", value="Quick question regarding growth")
custom_offer = st.text_area(
    "نص العرض الإنجليزي:", 
    height=120, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- إدارة مؤشر الحسابات وحفظ الإحصائيات ---
def get_current_account_index():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_current_account_index(idx):
    with open(STATE_FILE, "w") as f:
        f.write(str(idx))

def log_sent_metric(count):
    # تسجيل عدد الإرسال لعمل الرسم البياني
    df = pd.DataFrame([{"time": time.strftime("%H:%M:%S"), "sent": count}])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)

# --- فحص الردود الواردة ---
def check_incoming_replies():
    if not os.path.exists(ACCOUNTS_FILE):
        return 0, 0, []
    try:
        accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', nrows=20)
        accounts.columns = accounts.columns.str.strip().str.lower()
    except:
        return 0, 0, []

    total_rep, interested_count, replies_list = 0, 0, []
    for idx, row in accounts.iterrows():
        acc_email = str(row.get('email', '')).strip()
        acc_pwd = str(row.get('password', '')).strip()
        if not acc_email or not acc_pwd:
            continue
        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP, timeout=2)
            mail.login(acc_email, acc_pwd)
            mail.select("inbox")
            status, messages = mail.search(None, 'UNSEEN')
            for e_id in messages[0].split():
                _, msg_data = mail.fetch(e_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = msg.get_payload(decode=True).decode(errors='ignore') if not msg.is_multipart() else "Multipart message"
                        total_rep += 1
                        is_interested = any(w in body.lower() for w in ['interested', 'yes', 'call', 'demo', 'more info', 'sure'])
                        if is_interested: interested_count += 1
                        replies_list.append({
                            "Account": acc_email,
                            "From": msg.get("From"),
                            "Status": "🔥 مهتم" if is_interested else "📩 رد عادي",
                            "Snippet": body[:80] + "..."
                        })
            mail.logout()
        except:
            continue
    return total_rep, interested_count, replies_list

# --- تحليل موقع الشركة ---
def analyze_company_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string if soup.title else "Business Growth"
        return re.sub(r'[^\w\s]', '', title[:80]).strip()
    except:
        return "Digital Solutions"

# --- جلب الشركات فائق السرعة ---
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=5)
        urls = re.findall(r'href="(http[s]?://[^"]+)"', response.text)
        clean_urls = [u for u in urls if 'duckduckgo' not in u and 'microsoft' not in u][:limit*2]

        found = []
        for url in clean_urls:
            try:
                res = requests.get(url, headers=headers, timeout=2)
                emails = set(re.findall(r"[a-zA-Z0-9.\-_+#']+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text))
                valid = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))]
                if valid:
                    summary = analyze_company_website(url)
                    for em in valid:
                        found.append({"website": url, "email": em, "analysis": summary})
            except:
                continue
        return pd.DataFrame(found).drop_duplicates(subset=['email']).head(limit)
    except:
        return pd.DataFrame()

# --- إرسال إيميل فردي ---
def send_single_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=4)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- حساب إحصائيات الـ 280 ألف حساب ---
total_accounts_count = 280000
if os.path.exists(ACCOUNTS_FILE):
    try:
        df_acc_check = pd.read_csv(ACCOUNTS_FILE, usecols=[0], nrows=5) # قراءة سريعة جداً بدون ضغط
        # لو الملف أضخم، بنقرا الطول الحقيقي أو بنعتمد على الـ 280 ألف
        total_accounts_count = 280000 
    except:
        pass

current_idx = get_current_account_index()
used_accounts = current_idx % total_accounts_count
remaining_accounts = total_accounts_count - used_accounts

# --- عرض الـ Dashboard المتقدمة ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("إجمالي الحسابات", f"{total_accounts_count:,} حساب")
col2.metric("الحسابات المستخدمة", f"{used_accounts:,} حساب")
col3.metric("الحسابات المتبقية في الدورة", f"{remaining_accounts:,} حساب")
col4.metric("حالة المحرك السيادي", "🟢 شغال أزلي 24/7" if auto_loop else "🟡 متوقف")

st.markdown("---")

# --- عرض الرسم البياني للإرسال ---
st.subheader("📈 مؤشر معدل الإرسال اللحظي (Performance Chart)")
if os.path.exists(LOG_FILE):
    chart_df = pd.read_csv(LOG_FILE)
    if not chart_df.empty:
        st.line_chart(chart_df.set_index("time"))
    else:
        st.info("📊 بانتظار بدء أول دفعة إرسال لرسم المخطط...")
else:
    st.info("📊 سيظهر الرسم البياني فور انطلاق أول عملية إرسال ناجحة.")

st.markdown("---")

# --- تنفيذ دورة الإرسال التلقائي المستمر ---
if auto_loop:
    st.info("⚡ محرك التوربو الأزلي نشط: جاري سحب الشركات وإرسال العروض فوراً...")
    
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف accounts.csv غير موجود!")
    else:
        # جلب الشركات
        leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', skiprows=range(1, current_idx % total_accounts_count), nrows=len(leads))
            
            # لو الحسابات خلصت، نعمل لفّة من الأول
            if len(accounts_df) < len(leads):
                accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', nrows=len(leads))
                current_idx = 0
            
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            
            tasks = []
            for i, row in leads.iterrows():
                target = row['email']
                analysis = row['analysis']
                
                acc_row = accounts_df.iloc[i % len(accounts_df)]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                
                body = f"Hi,\n\nI noticed your focus on {analysis}.\n\n{custom_offer}\n\nBest regards,"
                tasks.append((sender, pwd, target, subject_template, body))
            
            # الإرسال المتوازي بأقصى سرعة
            sent_in_batch = 0
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]) for t in tasks]
                for future in as_completed(futures):
                    if future.result():
                        sent_in_batch += 1
            
            current_idx += len(leads)
            save_current_account_index(current_idx)
            log_sent_metric(sent_in_batch)
            
            st.success(f"🚀 تم بنجاح إرسال دفعة مكونة من {sent_in_batch} إيميل في ثوانٍ معدودة!")
            
            # تحديث الصفحة أوتوماتيكياً للبدء في الدفعة التالية فوراً بدون توقف
            time.sleep(3)
            st.rerun()
        else:
            st.warning("⚠️ جاري إعادة محاولة البحث عن شركات جديدة لتغذية المحرك...")
            time.sleep(5)
            st.rerun()
