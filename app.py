import os
import subprocess

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
    page_title="Live B2B Command Center",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 لوحة القيادة الحية - تتبع الإرسال لحظة بلحظة")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"
LOG_FILE = "sent_stats.csv"

# --- القائمة الجانبية للتحكم والتشغيل الفوري ---
st.sidebar.header("⚙️ إعدادات الإرسال الفوري")
industry_keyword = st.sidebar.text_input("مجال البحث", value="SaaS startup contact email")
batch_size = st.sidebar.slider("عدد الشركات في الدفعة", min_value=10, max_value=150, value=30)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=5, max_value=30, value=10)

# زرار التشغيل الأساسي اللي هيعمل كل حاجة بضغطة واحدة
start_now = st.sidebar.button("🚀 اضغط هنا للبدء والإنجاز الفوري", type="primary")

subject_template = st.sidebar.text_input("عنوان الرسالة", value="Quick question regarding growth")
custom_offer = st.text_area(
    "نص العرض الإنجليزي:", 
    height=100, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- إدارة مؤشر الحسابات ---
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
    df = pd.DataFrame([{"time": time.strftime("%H:%M:%S"), "sent": count}])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)

# --- فحص الردود والعملاء المهتمين ---
def check_incoming_replies():
    if not os.path.exists(ACCOUNTS_FILE):
        return 0, 0, []
    try:
        accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip', nrows=15)
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
                        body = msg.get_payload(decode=True).decode(errors='ignore') if not msg.is_multipart() else "Multipart"
                        total_rep += 1
                        is_interested = any(w in body.lower() for w in ['interested', 'yes', 'call', 'demo', 'more info', 'sure'])
                        if is_interested: 
                            interested_count += 1
                        replies_list.append({
                            "Account": acc_email,
                            "From": msg.get("From"),
                            "Status": "🔥 عميل مهتم جداً" if is_interested else "📩 رد عادٍ",
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

# --- محرك البحث الصاروخي ---
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=4)
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

# --- إرسال إيميل فردي مع إرجاع تقرير حي ---
def send_single_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=3)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True, f"✅ تم إرسال إيميل إلى [{recipient}] بنجاح عبر الحساب [{sender}]"
    except Exception as e:
        return False, f"❌ فشل إرسال الإيميل إلى [{recipient}] من الحساب [{sender}]"

# --- الحسابات والإحصائيات الأساسية ---
total_accounts_count = 280000
current_idx = get_current_account_index()
used_accounts = current_idx % total_accounts_count
remaining_accounts = total_accounts_count - used_accounts

total_rep, interest_rep, rep_details = check_incoming_replies()

# --- واجهة الـ 3 أقسام المطلوبة ---
tab1, tab2, tab3 = st.tabs([
    "🎯 القسم الأول: الردود والعملاء المهتمين", 
    "📊 القسم الثاني: نشاط الـ 280 ألف حساب", 
    "📈 القسم الثالث: لوحة البث الحي للإرسال (Live Logs)"
])

with tab1:
    st.subheader("🎯 إدارة الشركات والعملاء المهتمين")
    if rep_details:
        df_rep = pd.DataFrame(rep_details)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🔥 الشركات المهتمة")
            st.dataframe(df_rep[df_rep['Status'].str.contains("مهتم", na=False)], use_container_width=True)
        with col_b:
            st.markdown("### 📩 الردود العادية")
            st.dataframe(df_rep[~df_rep['Status'].str.contains("مهتم", na=False)], use_container_width=True)
    else:
        st.info("📬 صندوق الوارد قيد المراقبة... ستظهر الردود والعملاء المهتمين هنا فور وصولهم.")

with tab2:
    st.subheader("📊 تفاصيل حسابات الـ 280 ألف وتدويرها")
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الحسابات", f"{total_accounts_count:,}")
    col2.metric("الحسابات المستخدمة", f"{used_accounts:,}")
    col3.metric("الحسابات المتبقية", f"{remaining_accounts:,}")
    
    if os.path.exists(ACCOUNTS_FILE):
        st.dataframe(pd.read_csv(ACCOUNTS_FILE, nrows=10), use_container_width=True)
    else:
        st.warning("⚠️ ملف accounts.csv غير مرفوع.")

with tab3:
    st.subheader("📈 مؤشر الإرسال والبث الحي المباشر (Live Feed)")
    if os.path.exists(LOG_FILE):
        chart_df = pd.read_csv(LOG_FILE)
        if not chart_df.empty:
            st.line_chart(chart_df.set_index("time"))
    else:
        st.info("📊 سيظهر الرسم البياني وسجلات البث فور الضغط على زر الإطلاق بالجانب.")

# ==================== عند الضغط على زر التشغيل الفوري ====================
if start_now:
    st.info("⚡ تم إطلاق المحرك الصاروخي! جاري البحث عن الشركات وبدء الضخ المباشر...")
    
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف accounts.csv غير موجود!")
    else:
        with st.spinner("🔍 جاري جلب الشركات المستهدفة وتحليل مواقعها..."):
            leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.success(f"✨ تم رصد {len(leads)} شركة بنجاح، شاهد تقرير البث الحي للإرسال أدناه:")
            
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            total_accounts = len(accounts_df)
            
            tasks = []
            for i, row in leads.iterrows():
                target = row['email']
                analysis = row['analysis']
                
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                current_idx += 1
                
                body = f"Hi,\n\nI noticed your focus on {analysis}.\n\n{custom_offer}\n\nBest regards,"
                tasks.append((sender, pwd, target, subject_template, body))
            
            # صندوق عرض العمليات الحية أمام عيون المستخدم
            log_container = st.empty()
            live_logs_text = "🚀 بدء ضخ الرسائل...\n"
            
            sent_in_batch = 0
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]) for t in tasks]
                for future in as_completed(futures):
                    success, message = future.result()
                    if success:
                        sent_in_batch += 1
                    live_logs_text += message + "\n"
                    log_container.text_area("📋 سجل الإرسال الحي (Live Console):", value=live_logs_text, height=200)
            
            save_current_account_index(current_idx)
            log_sent_metric(sent_in_batch)
            
            st.balloons()
            st.success(f"🎉 تم بنجاح إرسال دفعة مكونة من {sent_in_batch} إيميل ورؤيتها مباشرة قدام عينك!")
        else:
            st.warning("⚠️ لم يتم العثور على شركات كافية في هذه الدفعة، حاول مرة أخرى أو غير كلمة البحث.")
