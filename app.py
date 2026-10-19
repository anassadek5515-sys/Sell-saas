import os
import subprocess

# تثبيت المكتبات المطلوبة تلقائياً عند البدء
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
    page_title="Enterprise B2B Autonomous Outreach Engine",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 منصة الأوتريتش الخارقة - محرك المليون ونصف إيميل (Turbo 24/7)")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"

# --- لوحة التحكم الجانبية (الإعدادات المتقدمة) ---
st.sidebar.header("⚙️ إعدادات المحرك السيادي")
industry_keyword = st.sidebar.text_input("مجال البحث والستهدف", value="SaaS startup contact email")
batch_size = st.sidebar.slider("حجم دفعة الاستهداف", min_value=50, max_value=500, value=100)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=5, max_value=50, value=20)
auto_loop = st.sidebar.checkbox("🔄 تفعيل وضع التوربو المستمر (24/7 Turbo Loop)", value=False)

subject_template = st.sidebar.text_input("عنوان الرسالة (Subject)", value="Quick question regarding growth")
custom_offer = st.text_area(
    "نص العرض الإنجليزي الذكي:", 
    height=120, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- دالة فحص وتتبع الردود الواردة أوتوماتيكياً ---
def check_incoming_replies():
    if not os.path.exists(ACCOUNTS_FILE):
        return 0, 0, []
    
    try:
        accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', nrows=25)
        accounts.columns = accounts.columns.str.strip().str.lower()
    except:
        return 0, 0, []

    total_replies = 0
    interested_count = 0
    replies_list = []

    for idx, row in accounts.iterrows():
        acc_email = str(row.get('email', '')).strip()
        acc_pwd = str(row.get('password', '')).strip()
        if not acc_email or not acc_pwd:
            continue
        
        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP, timeout=3)
            mail.login(acc_email, acc_pwd)
            mail.select("inbox")
            
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        from_sender = msg.get("From")
                        subject = msg.get("Subject")
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors='ignore')
                        else:
                            body = msg.get_payload(decode=True).decode(errors='ignore')
                        
                        total_replies += 1
                        is_interested = any(w in body.lower() for w in ['interested', 'yes', 'call', 'demo', 'more info', 'sure', 'chat', 'pricing'])
                        if is_interested:
                            interested_count += 1
                        
                        replies_list.append({
                            "Account": acc_email,
                            "From": from_sender,
                            "Subject": subject,
                            "Status": "🔥 مهتم (Interested)" if is_interested else "📩 رد عادي",
                            "Snippet": body[:100] + "..."
                        })
            mail.logout()
        except:
            continue

    return total_replies, interested_count, replies_list

# --- تحليل مواقع الشركات بالذكاء الاصطناعي الخفيف ---
def analyze_company_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string if soup.title else "Software & Business Solutions"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else title
        return re.sub(r'[^\w\s]', '', desc[:100]).strip()
    except:
        return "Digital Solutions & Growth"

# --- جلب الشركات المستهدفة (Leads Scraping) ---
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=6)
        urls = re.findall(r'href="(http[s]?://[^"]+)"', response.text)
        clean_urls = [u for u in urls if 'duckduckgo' not in u and 'microsoft' not in u][:limit*3]

        found = []
        for url in clean_urls:
            try:
                res = requests.get(url, headers=headers, timeout=2)
                emails = set(re.findall(r"[a-zA-Z0-9.\-_+#']+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text))
                valid = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
                if valid:
                    summary = analyze_company_website(url)
                    for em in valid:
                        found.append({"website": url, "email": em, "analysis": summary})
            except:
                continue
        return pd.DataFrame(found).drop_duplicates(subset=['email']).head(limit)
    except:
        return pd.DataFrame()

# --- إرسال إيميل فردي مع عزل الأخطاء ---
def send_single_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=5)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- إدارة مؤشر الحسابات لعدم التكرار ---
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

# --- لوحة المؤشرات الرئيسية ---
col1, col2, col3 = st.columns(3)

with st.spinner("جاري فحص الردود الواردة وحالة الصناديق..."):
    total_rep, interest_rep, rep_details = check_incoming_replies()

col1.metric("إجمالي الردود الواردة", f"{total_rep} رسالة")
col2.metric("عدد العملاء المهتمين 🔥", f"{interest_rep} عميل")
col3.metric("حالة نظام التشغيل", "🟢 توربو شغال 24/7" if auto_loop else "🟡 وضع الاستعداد")

st.markdown("---")

if rep_details:
    st.subheader("📬 صندوق الردود والعملاء المهتمين:")
    st.dataframe(pd.DataFrame(rep_details), use_container_width=True)

# --- تفعيل الحملة الخارقة ---
if st.button("🚀 إطلاق الحملة الصاروخية القصوى", type="primary") or auto_loop:
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف الحسابات accounts.csv غير موجود على السيرفر!")
    else:
        st.info("🔍 جاري جلب وتحليل الشركات المستهدفة عبر الويب...")
        leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.success(f"✨ تم رصد {len(leads)} شركة مستهدفة، جاري التوزيع على 280 ألف حساب بالتوازي...")
            
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            total_accounts = len(accounts_df)
            
            current_idx = get_current_account_index()
            
            tasks = []
            for idx, row in leads.iterrows():
                target = row['email']
                analysis = row['analysis']
                
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                current_idx += 1
                
                body = f"Hi,\n\nI noticed your focus on {analysis}.\n\n{custom_offer}\n\nBest regards,"
                tasks.append((sender, pwd, target, subject_template, body))

            # الإرسال المتوازي فائق السرعة
            sent_count = 0
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]) for t in tasks]
                for future in as_completed(futures):
                    if future.result():
                        sent_count += 1

            save_current_account_index(current_idx)
            st.balloons()
            st.success(f"✅ تمت العملية بنجاح صاعق! تم إرسال {sent_count} عرض تجاري عبر التدوير الآلي للحسابات.")
            
        if auto_loop:
            st.warning("🔄 وضع التوربو الأوتوماتيكي مفعّل: سيتم تكرار الحملة الضخمة التالية خلال 15 ثانية...")
            time.sleep(15)
            st.rerun()
