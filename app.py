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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(
    page_title="Autonomous B2B Outreach Engine",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 منصة الأوتريتش الذكية - إدارة 280 ألف حساب والتتبع الآلي")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt" # ملف صغير بنحفظ فيه إحنا وقفنا فين عشان ما نكررش حساب

# --- القائمة الجانبية وإعدادات الحملة ---
st.sidebar.header("⚙️ إعدادات المحرك الضخم")
industry_keyword = st.sidebar.text_input("مجال البحث عن الشركات", value="SaaS startup contact email")
batch_size = st.sidebar.slider("عدد الشركات لكل دفعة إرسال", min_value=5, max_value=50, value=10)
sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (ثواني)", min_value=1, max_value=5, value=2)
auto_loop = st.sidebar.checkbox("🔄 تفعيل التشغيل الآلي المستمر (24/7 Loop)", value=False)

subject_template = st.sidebar.text_input("عنوان الرسالة", value="Quick question regarding growth")
custom_offer = st.text_area(
    "نص العرض الإنجليزي:", 
    height=120, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- دالة تتبع الردود الواردة ---
def check_incoming_replies():
    if not os.path.exists(ACCOUNTS_FILE):
        return 0, 0, []
    
    # نقرأ أول 50 حساب بس للفحص السريع للردود عشان ما نفتحش 280 ألف اتصال IMAP في نفس اللحظة
    try:
        accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', nrows=50)
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
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP, timeout=5)
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
                        is_interested = any(w in body.lower() for w in ['interested', 'yes', 'call', 'demo', 'more info', 'sure', 'chat'])
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

# --- تحليل مواقع الشركات ---
def analyze_company_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string if soup.title else "Software & Business Services"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else title
        return re.sub(r'[^\w\s]', '', desc[:120]).strip()
    except:
        return "Digital Solutions & Services"

# --- البحث عن الشركات ---
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=8)
        urls = re.findall(r'href="(http[s]?://[^"]+)"', response.text)
        clean_urls = [u for u in urls if 'duckduckgo' not in u and 'microsoft' not in u][:limit*3]

        found = []
        for url in clean_urls:
            try:
                res = requests.get(url, headers=headers, timeout=3)
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

# --- إرسال الإيميل ---
def send_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=6)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- قراءة المؤشر الحالي للحسابات ---
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

# --- الواجهة الرئيسية والإحصائيات ---
col1, col2, col3 = st.columns(3)

with st.spinner("جاري فحص الردود الواردة من الحسابات النشطة..."):
    total_rep, interest_rep, rep_details = check_incoming_replies()

col1.metric("إجمالي الردود الواردة", f"{total_rep} رسالة")
col2.metric("عدد العملاء المهتمين 🔥", f"{interest_rep} عميل")
col3.metric("حالة النظام السحابي", "🟢 شغال 24/7" if auto_loop else "🟡 يدوي")

st.markdown("---")

if rep_details:
    st.subheader("📬 صندوق الردود والعملاء المهتمين:")
    st.dataframe(pd.DataFrame(rep_details), use_container_width=True)

# --- تشغيل الحملة الآلية ---
if st.button("🚀 بدء الإرسال والتصياد الآن", type="primary") or auto_loop:
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف الحسابات accounts.csv غير موجود!")
    else:
        st.info("🔍 جاري البحث عن الشركات المستهدفة في الخلفية...")
        leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.dataframe(leads, use_container_width=True)
            
            # قراءة الحسابات بذكاء وتدويرها
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            total_accounts = len(accounts_df)
            
            current_idx = get_current_account_index()
            
            sent_count = 0
            for idx, row in leads.iterrows():
                target = row['email']
                analysis = row['analysis']
                
                # اختيار الحساب الحالي من الـ 280 ألف حساب والتقدم خطوة
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                
                current_idx += 1
                
                body = f"Hi,\n\nI noticed your focus on {analysis}.\n\n{custom_offer}\n\nBest regards,"
                
                if send_email(sender, pwd, target, subject_template, body):
                    sent_count += 1
                
                time.sleep(sending_delay)
            
            # حفظ مكان الحساب اللي وقفنا عنده عشان الدفعة الجاية تبدأ من اللي بعده
            save_current_account_index(current_idx)
            
            st.success(f"✅ تم إرسال {sent_count} عرض بنجاح باستخدام الدوران الآلي لـ 280 ألف حساب!")
            
        if auto_loop:
            st.warning("🔄 التشغيل الأوتوماتيكي مفعّل: سيتم إعادة تدوير الحملة وإرسال دفعة جديدة خلال 60 ثانية...")
            time.sleep(60)
            st.rerun()
