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
    page_title="Enterprise 3-Section Command Center",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 لوحة القيادة المركزية السيادية - محرك المليون ونصف إيميل")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"
LOG_FILE = "sent_stats.csv"

# --- القائمة الجانبية لإدارة العمليات ---
st.sidebar.header("⚙️ إعدادات المحرك الصاروخي")
industry_keyword = st.sidebar.text_input("مجال البحث والفلترة", value="SaaS startup contact email")
batch_size = st.sidebar.slider("حجم الدفعة السريعة", min_value=30, max_value=300, value=100)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=10, max_value=100, value=50)

start_campaign = st.sidebar.button("🚀 إطلاق الحملة الصاروخية الآن", type="primary")
auto_loop = st.sidebar.checkbox("🔄 تفعيل التشغيل المستمر (24/7 Turbo Loop)", value=False)

subject_template = st.sidebar.text_input("عنوان الرسالة (Subject)", value="Quick question regarding growth")
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

# --- فحص الردود وصيد العملاء المهتمين ---
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
                        if is_interested: 
                            interested_count += 1
                        
                        status_label = "🔥 عميل مهتم جداً (Interested)" if is_interested else "📩 رد عادٍ / غير مهتم"
                        replies_list.append({
                            "Account": acc_email,
                            "From": msg.get("From"),
                            "Status": status_label,
                            "Snippet": body[:80] + "..."
                        })
            mail.logout()
        except:
            continue
    return total_rep, interested_count, replies_list

# --- تحليل موقع الشركة بلمح البصر ---
def analyze_company_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string if soup.title else "Business Growth"
        return re.sub(r'[^\w\s]', '', title[:80]).strip()
    except:
        return "Digital Solutions"

# --- محرك البحث الصاروخي السريع ---
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

# --- إرسال إيميل فردي متوازي ---
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
        return True
    except:
        return False

# حسابات النظام
total_accounts_count = 280000
current_idx = get_current_account_index()
used_accounts = current_idx % total_accounts_count
remaining_accounts = total_accounts_count - used_accounts

total_rep, interest_rep, rep_details = check_incoming_replies()

# ==================== التقسيم الاحترافي لـ 3 أقسام ====================
tab1, tab2, tab3 = st.tabs([
    "🎯 القسم الأول: الشركات (المهتمة وغير المهتمة)", 
    "📊 القسم الثاني: نشاط الـ 280 ألف حساب", 
    "📈 القسم الثالث: الرسومات البيانية ومعاينة الرسائل"
])

# --- القسم الأول ---
with tab1:
    st.subheader("🎯 إدارة العملاء والشركات المستهدفة (المهتمة / غير المهتمة)")
    if rep_details:
        df_rep = pd.DataFrame(rep_details)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🔥 الشركات المهتمة (Hot Leads)")
            interested_df = df_rep[df_rep['Status'].str.contains("مهتم", na=False)]
            if not interested_df.empty:
                st.dataframe(interested_df, use_container_width=True)
            else:
                st.info("لم يتم رصد عملاء مهتمين بعد، جارٍ صيد العروض...")
                
        with col_b:
            st.markdown("### 📩 الردود العادية / غير المهتمة")
            uninterested_df = df_rep[~df_rep['Status'].str.contains("مهتم", na=False)]
            if not uninterested_df.empty:
                st.dataframe(uninterested_df, use_container_width=True)
            else:
                st.info("لا توجد ردود عادية حالياً.")
    else:
        st.info("📬 صندوق الوارد قيد الفحص الذكي... ستظهر النتائج هنا فور وصول ردود من الشركات.")

# --- القسم الثاني ---
with tab2:
    st.subheader("⚙️ تفاصيل ونشاط الـ 280 ألف حساب (Account Operations)")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الحسابات الكلي", f"{total_accounts_count:,}")
    col2.metric("الحسابات المستهلكة في الدورة", f"{used_accounts:,}")
    col3.metric("الحسابات المتبقية الجاهزة", f"{remaining_accounts:,}")
    col4.metric("حالة الـ Rotation", "🟢 تدوير أمن 100%")
    
    st.markdown("---")
    st.markdown("### 📄 معاينة عينة حية من ملف الحسابات المرفق (`accounts.csv`):")
    if os.path.exists(ACCOUNTS_FILE):
        try:
            acc_preview = pd.read_csv(ACCOUNTS_FILE, nrows=10)
            st.dataframe(acc_preview, use_container_width=True)
        except:
            st.error("❌ خطأ في قراءة ملف accounts.csv تأكد من صحة الأعمدة.")
    else:
        st.warning("⚠️ ملف accounts.csv غير مرفوع حالياً على السيرفر.")

# --- القسم الثالث ---
with tab3:
    st.subheader("📈 الرسومات البيانية ومعاينة الرسائل المُرسلة")
    
    col_chart, col_preview = st.columns([2, 1])
    
    with col_chart:
        st.markdown("#### 📊 مؤشر معدل الإرسال اللحظي الحقيقي")
        if os.path.exists(LOG_FILE):
            chart_df = pd.read_csv(LOG_FILE)
            if not chart_df.empty:
                st.line_chart(chart_df.set_index("time"))
            else:
                st.info("📊 بانتظار بدء أول دفعة إرسال لرسم المخطط البياني...")
        else:
            st.info("📊 سيظهر الرسم البياني بمجرد ضغط زر الإطلاق وبدء الضخ.")
            
    with col_preview:
        st.markdown("#### ✉️ معاينة قالب الرسالة الحالية")
        st.info(f"**العنوان:** {subject_template}")
        st.text_area("نص الرسالة المرسلة للشركات:", value=f"Hi,\n\nI noticed your focus on [Dynamic Company Analysis].\n\n{custom_offer}\n\nBest regards,", height=150, disabled=True)

# ==================== تشغيل الحملة (البحث الصاروخي والضخ) ====================
if start_campaign or auto_loop:
    st.info("⚡ محرك البحث الصاروخي يعمل بكامل طاقته لجلب الشركات وإرسال العروض...")
    
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف accounts.csv غير موجود!")
    else:
        leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.success(f"✨ تم رصد {len(leads)} شركة بنجاح، جاري ضخ الإيميلات بالتوازي عبر الـ 280 ألف حساب...")
            
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
            
            sent_in_batch = 0
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]) for t in tasks]
                for future in as_completed(futures):
                    if future.result():
                        sent_in_batch += 1
            
            save_current_account_index(current_idx)
            log_sent_metric(sent_in_batch)
            
            st.success(f"🚀 تم بنجاح إرسال دفعة مكونة من {sent_in_batch} إيميل بسرعة فائقة!")
            
            if auto_loop:
                time.sleep(3)
                st.rerun()
        else:
            st.warning("⚠️ جارٍ البحث عن شركات إضافية لتغذية محرك الإرسال...")
            if auto_loop:
                time.sleep(5)
                st.rerun()
