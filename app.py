import streamlit as st
import pandas as pd
import smtplib
import imaplib
import email
import requests
import re
import os
import time
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(
    page_title="Autonomous B2B Outreach & Reply Tracker",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 منصة الأوتريتش الذكية - التشغيل الذاتي وتتبع الردود")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"

# --- القائمة الجانبية والإعدادات ---
st.sidebar.header("⚙️ إعدادات المحرك الذاتي")
industry_keyword = st.sidebar.text_input("مجال البحث عن الشركات", value="SaaS startup contact email")
batch_size = st.sidebar.slider("عدد الشركات لكل دفعة", min_value=3, max_value=20, value=5)
sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (ثواني)", min_value=2, max_value=10, value=3)
auto_loop = st.sidebar.checkbox("🔄 تفعيل التشغيل الآلي المستمر (24/7 Loop)", value=False)

subject_template = st.sidebar.text_input("عنوان الرسالة", value="Quick question regarding growth")
custom_offer = st.text_area(
    "نص العرض الإنجليزي:", 
    height=120, 
    value="We help companies scale their outreach and significantly increase client acquisition through an automated engine."
)

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_IMAP = "imap.gmail.com"

# --- دالة فحص وتتبع الردود الواردة ---
def check_incoming_replies():
    if not os.path.exists(ACCOUNTS_FILE):
        return 0, 0, []
    
    accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
    total_replies = 0
    interested_count = 0
    replies_list = []

    for idx, row in accounts.iterrows():
        acc_email = str(row['email']).strip()
        acc_pwd = str(row['password']).strip()
        
        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP)
            mail.login(acc_email, acc_pwd)
            mail.select("inbox")
            
            # البحث عن جميع الرسائل غير المقروءة أو الحديثة
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
                        # تحليل بسيط لاكتشاف الاهتمام
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
        res = requests.get(url, headers=headers, timeout=5)
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
        response = requests.get(search_url, headers=headers, timeout=10)
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

# --- إرسال الإيميلات ---
def send_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=8)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- الواجهة الرئيسية والإحصائيات ---
col1, col2, col3 = st.columns(3)

# زر تحديث الردود
with st.spinner("جاري فحص الردود الجديدة من الحسابات..."):
    total_rep, interest_rep, rep_details = check_incoming_replies()

col1.metric("إجمالي الردود الواردة", f"{total_rep} رسالة")
col2.metric("عدد العملاء المهتمين 🔥", f"{interest_rep} عميل")
col3.metric("حالة النظام السحابي", "🟢 شغال 24/7" if auto_loop else "🟡 يدوي")

st.markdown("---")

# عرض جدول الردود الواردة لو وجد
if rep_details:
    st.subheader("📬 صندوق الردود والعملاء المهتمين:")
    st.dataframe(pd.DataFrame(rep_details), use_container_width=True)

# --- تشغيل الحملة ---
if st.button("🚀 بدء الإرسال والتصياد الآن", type="primary") or auto_loop:
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف الحسابات غير موجود!")
    else:
        accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
        accounts.columns = accounts.columns.str.strip().str.lower()
        
        st.info("🔍 جاري البحث والاستهداف في الخلفية...")
        leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.dataframe(leads, use_container_width=True)
            for idx, row in leads.iterrows():
                target = row['email']
                analysis = row['analysis']
                acc_idx = idx % len(accounts)
                sender = str(accounts.loc[acc_idx, 'email']).strip()
                pwd = str(accounts.loc[acc_idx, 'password']).strip()

                body = f"Hi,\n\nI noticed your focus on {analysis}.\n\n{custom_offer}\n\nBest regards,"
                send_email(sender, pwd, target, subject_template, body)
                time.sleep(sending_delay)
            st.success("✅ تم إرسال الدفعة بنجاح!")
            
        if auto_loop:
            st.warning("🔄 التشغيل الأوتوماتيكي مفعّل: سيعاد البحث والإرسال تلقائياً خلال 60 ثانية...")
            time.sleep(60)
            st.rerun()
