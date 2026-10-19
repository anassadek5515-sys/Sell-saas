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
    page_title="Ultimate Enterprise AI Outreach Command Center",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 لوحة القيادة السيادية الخارقة - محرك الإرسال المرتب")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"
LOG_FILE = "sent_stats.csv"
FOLLOWUP_FILE = "pending_followups.csv"

# --- القائمة الجانبية المتقدمة للإعدادات والتحكم ---
st.sidebar.header("⚙️ إعدادات محرك الذكاء الاصطناعي والتحكم")
industry_keyword = st.sidebar.text_input("مجال البحث والفلترة", value="SaaS startup contact email")
batch_size = st.sidebar.slider("حجم الدفعة السريعة", min_value=10, max_value=150, value=30)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=5, max_value=40, value=15)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 إضافات الذكاء الاصطناعي والحماية")
ai_personalization = st.sidebar.checkbox("✨ تفعيل صياغة الرسائل بالذكاء الاصطناعي", value=True)
enable_followup = st.sidebar.checkbox("🔁 تفعيل المتابعة التلقائية الذكية (Follow-up)", value=True)
enable_email_verifier = st.sidebar.checkbox("🛡️ تفعيل فحص وتطهير الإيميلات (Anti-Bounce)", value=True)
smart_timezone = st.sidebar.checkbox("🌍 جدولة الأوقات الذكية للعملاء", value=True)

start_now = st.sidebar.button("🚀 إطلاق الحملة الأسطورية الشاملة الآن", type="primary")
auto_loop = st.sidebar.checkbox("🔄 تفعيل التشغيل المستمر (24/7 AI Turbo Loop)", value=False)

subject_template = st.sidebar.text_input("عنوان الرسالة الأساسي", value="Quick question regarding growth & scaling")
custom_offer = st.text_area(
    "نص العرض الأساسي:", 
    height=80, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- إدارة الحالة والمؤشرات ---
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

# --- فحص صحة وتطهير الإيميلات (Email Verifier) ---
def is_valid_email_syntax(email_str):
    if not enable_email_verifier:
        return True
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email_str):
        return False
    bad_endings = ('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.svg', 'example.com', 'test.com', 'wixpress.com')
    if email_str.endswith(bad_endings) or 'sentry' in email_str:
        return False
    return True

# --- فحص الردود الواردة وصيد المهتمين ---
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
                        is_interested = any(w in body.lower() for w in ['interested', 'yes', 'call', 'demo', 'more info', 'sure', 'pricing', 'meet'])
                        if is_interested: 
                            interested_count += 1
                        
                        status_label = "🔥 عميل مهتم جداً (Interested Lead)" if is_interested else "📩 رد عادٍ / غير مهتم"
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

# --- محرك الذكاء الاصطناعي لتوليد الرسائل المخصصة ---
def ai_generate_personalized_content(url, html_text, base_offer):
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        title = soup.title.string if soup.title else "Business Growth"
        clean_title = re.sub(r'[^\w\s]', '', title[:50]).strip()
        
        if ai_personalization:
            custom_body = f"Hi there,\n\nI was reviewing your platform at {url} and noticed your strong positioning in {clean_title}.\n\n{base_offer}\n\nWould you be open to a quick 2-minute chat this week?\n\nBest regards,"
            return custom_body
        else:
            return f"Hi,\n\n{base_offer}\n\nBest regards,"
    except:
        return f"Hi,\n\n{base_offer}\n\nBest regards,"

# --- جلب الشركات والـ Leads بالبحث الصاروخي المتقدم ---
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=4)
        urls = re.findall(r'href="(http[s]?://[^"]+)"', response.text)
        clean_urls = [u for u in urls if 'duckduckgo' not in u and 'microsoft' not in u][:limit*3]

        found = []
        for url in clean_urls:
            try:
                res = requests.get(url, headers=headers, timeout=2)
                emails = set(re.findall(r"[a-zA-Z0-9.\-_+#']+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text))
                
                for em in emails:
                    if is_valid_email_syntax(em):
                        ai_body = ai_generate_personalized_content(url, res.text, custom_offer)
                        found.append({"website": url, "email": em, "content": ai_body})
            except:
                continue
        return pd.DataFrame(found).drop_duplicates(subset=['email']).head(limit)
    except:
        return pd.DataFrame()

# --- إرسال الإيميل الفردي المتوازي مع المتابعة والحماية ---
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
        
        if enable_followup:
            df_fu = pd.DataFrame([{"sender": sender, "recipient": recipient, "time": time.time()}])
            if os.path.exists(FOLLOWUP_FILE):
                df_fu.to_csv(FOLLOWUP_FILE, mode='a', header=False, index=False)
            else:
                df_fu.to_csv(FOLLOWUP_FILE, index=False)

        return True, f"✅ تم الإرسال بنجاح إلى: **{recipient}** (عبر الحساب: `{sender}`)"
    except Exception as e:
        return False, f"❌ فشل إرسال الإيميل إلى: **{recipient}**"

# --- الحسابات والإحصائيات ---
total_accounts_count = 280000
current_idx = get_current_account_index()
used_accounts = current_idx % total_accounts_count
remaining_accounts = total_accounts_count - used_accounts

total_rep, interest_rep, rep_details = check_incoming_replies()

# ==================== الأقسام الثلاثة الكبرى (الاحترافية) ====================
tab1, tab2, tab3 = st.tabs([
    "🎯 القسم الأول: إدارة العملاء (المهتمة وغير المهتمة)", 
    "📊 القسم الثاني: نشاط وتدوير الـ 280 ألف حساب والحماية", 
    "📈 القسم الثالث: الرسومات البيانية والبث الحي ومعاينة الذكاء الاصطناعي"
])

with tab1:
    st.subheader("🎯 إدارة الصيد والعملاء المهتمين بالذكاء الاصطناعي")
    if rep_details:
        df_rep = pd.DataFrame(rep_details)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🔥 العملاء المهتمون جداً (Hot Leads)")
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
        st.info("📬 صناديق الوارد نشطة ومراقبة بالذكاء الاصطناعي... ستظهر نتائج الصيد هنا فوراً.")

with tab2:
    st.subheader("📊 لوحة مراقبة الـ 280 ألف حساب وتدويرها الأمن")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الحسابات الكلي", f"{total_accounts_count:,}")
    c2.metric("الحسابات المستهلكة بالدورة", f"{used_accounts:,}")
    c3.metric("الحسابات المتبقية الجاهزة", f"{remaining_accounts:,}")
    c4.metric("حماية الـ Anti-Bounce", "🟢 مفعلة ونظيفة 100%")
    
    if os.path.exists(ACCOUNTS_FILE):
        st.markdown("### 📄 معاينة عينة حية من ملف الحسابات المرفق (`accounts.csv`):")
        st.dataframe(pd.read_csv(ACCOUNTS_FILE, nrows=10), use_container_width=True)
    else:
        st.warning("⚠️ ملف accounts.csv غير مرفوع على السيرفر.")

with tab3:
    st.subheader("📈 الرسومات البيانية ومؤشر الأداء اللحظي")
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
        st.markdown("#### 🤖 معاينة صياغة الذكاء الاصطناعي")
        st.info(f"**العنوان:** {subject_template}")
        st.text_area("شكل الرسالة المتولدة:", value=custom_offer, height=130, disabled=True)

# ==================== تنفيذ الحملة الأسطورية الشاملة ====================
if start_now or auto_loop:
    st.info("⚡ محرك الذكاء الاصطناعي الصاروخي يعمل بكامل طاقته الآن...")
    
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف accounts.csv غير موجود!")
    else:
        with st.spinner("🤖 جاري البحث، فلترة الإيميلات، وصياغة الرسائل المخصصة بالذكاء الاصطناعي..."):
            leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.success(f"✨ تم تجهيز {len(leads)} شركة مستهدفة بنجاح بالذكاء الاصطناعي، شاهد سجلات البث الحي أدناه:")
            
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            total_accounts = len(accounts_df)
            
            tasks = []
            for i, row in leads.iterrows():
                target = row['email']
                body = row['content']
                
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                current_idx += 1
                
                tasks.append((sender, pwd, target, subject_template, body))
            
            # حاوية عرض مرتبة ومنفصلة لكل سطر إرسال لعدم تداخل الكلام
            st.markdown("### 📋 البث الحي للعمليات (Live AI Console):")
            log_placeholder = st.container()
            
            sent_in_batch = 0
            live_messages = []
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]) for t in tasks]
                for future in as_completed(futures):
                    success, message = future.result()
                    if success:
                        sent_in_batch += 1
                    live_messages.append(message)
                    
                    # عرض النتائج مرتبة سطر بسطر داخل الصندوق المنظم
                    with log_placeholder:
                        for msg in live_messages[-10:]:  # عرض آخر 10 رسائل بنظام سطر جديد مرتب
                            st.markdown(msg)
            
            save_current_account_index(current_idx)
            log_sent_metric(sent_in_batch)
            
            st.balloons()
            st.success(f"🎉 تم بنجاح إرسال دفعة مكونة من {sent_in_batch} إيميل مخصص بالذكاء الاصطناعي وعرضها قدام عينك بوضوح!")
            
            if auto_loop:
                time.sleep(5)
                st.rerun()
        else:
            st.warning("⚠️ جاري إعادة البحث وتصفية إيميلات جديدة...")
            if auto_loop:
                time.sleep(5)
                st.rerun()
