import streamlit as st
import pandas as pd
import smtplib
import requests
import re
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

st.set_page_config(
    page_title="Autonomous Outreach Engine",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 منصة الأوتريتش الذكية - التشغيل الذاتي")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"

# التحقق من وجود ملف الحسابات
if os.path.exists(ACCOUNTS_FILE):
    st.sidebar.success("✅ ملف الحسابات متصل بنجاح من GitHub")
else:
    st.sidebar.error("⚠️ ملف accounts.csv غير موجود على GitHub!")

# إعدادات الحملة
st.sidebar.header("⚙️ إعدادات الحملة")
industry_keyword = st.sidebar.text_input("مجال البحث عن الشركات", value="software development companies contact email")
batch_size = st.sidebar.slider("عدد الإيميلات في الدفعة الواحدة", min_value=5, max_value=50, value=10)
sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (ثواني)", min_value=1, max_value=5, value=2)

subject_template = st.sidebar.text_input("عنوان الرسالة (Subject)", value="فرصة تعاون مشتركة")
email_body = st.text_area("محتوى الرسالة:", height=150, value="مرحباً،\n\nلاحظنا نشاط شركتكم المتميز ونود مناقشة فرص الشراكة.\n\nتحياتي،")

GMAIL_SERVER = "smtp.gmail.com"
GMAIL_PORT = 587

# دالة البحث عن الإيميلات
def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=10)
        
        urls = re.findall(r'href="(http[s]?://[^"]+)"', response.text)
        clean_urls = [u for u in urls if 'duckduckgo' not in u and 'microsoft' not in u][:limit*2]

        found = []
        for url in clean_urls:
            try:
                res = requests.get(url, headers=headers, timeout=3)
                emails = set(re.findall(r"[a-zA-Z0-9.\-_+#']+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text))
                valid = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
                for em in valid:
                    found.append({"domain": url, "email": em})
            except:
                continue
        return pd.DataFrame(found).drop_duplicates(subset=['email']).head(limit)
    except Exception as e:
        st.error(f"خطأ في البحث: {e}")
        return pd.DataFrame()

# دالة إرسال الإيميل
def send_email(sender, password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(GMAIL_SERVER, GMAIL_PORT, timeout=8)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except:
        return False

if st.button("🚀 بدء تشغيل الحملة"):
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف الحسابات غير موجود!")
    else:
        leads = search_leads(industry_keyword, batch_size)
        if leads.empty:
            st.warning("⚠️ لم يتم العثور على إيميلات، جرب كلمة بحث أخرى.")
        else:
            st.success(f"🎉 تم العثور على {len(leads)} شركة مستهدفة. جاري الإرسال...")
            st.dataframe(leads, use_container_width=True)

            accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts.columns = accounts.columns.str.strip().str.lower()

            sent = 0
            failed = 0
            progress = st.progress(0)
            status = st.empty()

            for idx, row in leads.iterrows():
                target = row['email']
                acc_idx = idx % len(accounts)
                sender = str(accounts.loc[acc_idx, 'email']).strip()
                pwd = str(accounts.loc[acc_idx, 'password']).strip()

                if send_email(sender, pwd, target, subject_template, email_body):
                    sent += 1
                else:
                    failed += 1

                progress.progress((idx + 1) / len(leads))
                status.text(f"جاري إرسال دفعة الإيميلات... ({idx + 1}/{len(leads)})")
                time.sleep(sending_delay)

            st.success(f"✅ انتهت الدفعة! الناجح: {sent} | الفاشل: {failed}")
