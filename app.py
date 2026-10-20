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

st.title("🦅 لوحة القيادة السيادية - محرك الإرسال المستقر")
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"
STATE_FILE = "last_index.txt"
LOG_FILE = "sent_stats.csv"

# --- القائمة الجانبية للتحكم ---
st.sidebar.header("⚙️ إعدادات الإرسال الفوري")
industry_keyword = st.sidebar.text_input("مجال البحث والفلترة", value="SaaS startup contact email")
batch_size = st.sidebar.slider("حجم الدفعة", min_value=5, max_value=30, value=10)
max_threads = st.sidebar.slider("خطوط الإرسال المتوازية (Threads)", min_value=1, max_value=5, value=2)

ai_personalization = st.sidebar.checkbox("✨ تفعيل صياغة الرسائل بالذكاء الاصطناعي", value=True)
enable_email_verifier = st.sidebar.checkbox("🛡️ تفعيل فحص وتطهير الإيميلات", value=True)

# زرار التشغيل اليدوي
start_now = st.sidebar.button("🚀 بدء الإرسال الآن", type="primary")

subject_template = st.sidebar.text_input("عنوان الرسالة", value="Quick question regarding growth & scaling")
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

def ai_generate_personalized_content(url, html_text, base_offer):
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        title = soup.title.string if soup.title else "Business Growth"
        clean_title = re.sub(r'[^\w\s]', '', title[:50]).strip()
        
        if ai_personalization:
            return f"Hi there,\n\nI was reviewing your platform at {url} and noticed your strong positioning in {clean_title}.\n\n{base_offer}\n\nWould you be open to a quick 2-minute chat?\n\nBest regards,"
        else:
            return f"Hi,\n\n{base_offer}\n\nBest regards,"
    except:
        return f"Hi,\n\n{base_offer}\n\nBest regards,"

def search_leads(keyword, limit):
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={keyword}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=5)
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
        return True, f"✅ تم إرسال إيميل إلى العميل **{recipient}** باستخدام الحساب: `{sender}`"
    except Exception as e:
        return False, f"❌ فشل إرسال الإيميل إلى **{recipient}** من الحساب `{sender}`"

# --- واجهة العمليات الأساسية ---
st.subheader("📋 تقرير حالة الحملة والإرسال")

if start_now:
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف accounts.csv غير موجود على السيرفر!")
    else:
        with st.spinner("🔍 جارٍ البحث عن الشركات وجلب الإيميلات المستهدفة..."):
            leads = search_leads(industry_keyword, batch_size)
        
        if not leads.empty:
            st.success(f"✨ تم العثور على {len(leads)} شركة، جارٍ بدء الضخ المستقر...")
            
            accounts_df = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts_df.columns = accounts_df.columns.str.strip().str.lower()
            total_accounts = len(accounts_df)
            
            current_idx = get_current_account_index()
            tasks = []
            
            for i, row in leads.iterrows():
                target = row['email']
                body = row['content']
                
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row.get('email', '')).strip()
                pwd = str(acc_row.get('password', '')).strip()
                current_idx += 1
                
                tasks.append((sender, pwd, target, subject_template, body))
            
            sent_in_batch = 0
            live_logs = []
            
            # تنفيذ الإرسال بشكل آمن ومستقر بدون أخطاء واجهة المستخدم
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(send_single_email, t[0], t[1], t[2], t[3], t[4]): t for t in tasks}
                completed_count = 0
                
                for future in as_completed(futures):
                    success, message = future.result()
                    if success:
                        sent_in_batch += 1
                    live_logs.append(message)
                    completed_count += 1
                    
                    # تحديث شريط التقدم بأمان
                    progress_bar.progress(completed_count / len(tasks))
                    status_text.text(f"⏳ تم معالجة {completed_count} من {len(tasks)} إيميل...")
            
            save_current_account_index(current_idx)
            log_sent_metric(sent_in_batch)
            
            st.success(f"🎉 تم الانتهاء بنجاح من إرسال دفعة مكونة من {sent_in_batch} إيميل!")
            
            # عرض السجل النهائي مرتباً وواضحاً
            st.markdown("### 📝 سجل الإرسال النهائي لهذه الدفعة:")
            for log in live_logs:
                st.write(log)
        else:
            st.warning("⚠️ لم يتم العثور على إيميلات جديدة في هذه الدفعة، جرب تغيير كلمة البحث في القائمة الجانبية.")
else:
    st.info("ℹ️ اضغط على زر **'بدء الإرسال الآن'** في القائمة الجانبية لتنفيذ الحملة بشكل مستقر وسريع.")
