import streamlit as st
import pandas as pd
import smtplib
import requests
import re
import os
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

st.set_page_config(
    page_title="AI B2B Outreach Engine",
    page_icon="🦅",
    layout="wide"
)

# تصميم عصري واحترافي للصفحة
st.markdown("""
    <style>
    .main-header {font-size: 30px; font-weight: bold; color: #FF4B4B; text-align: center;}
    .sub-text {font-size: 16px; color: #555; text-align: center; margin-bottom: 30px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🦅 منصة الأوتريتش الذكية وتحليل الشركات</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">محرك أوتوماتيكي بالكامل لاستهداف وصياغة عروض مخصصة لكل شركة بناءً على تحليل موقعهم.</div>', unsafe_allow_html=True)
st.markdown("---")

ACCOUNTS_FILE = "accounts.csv"

# التحقق من حسابات الإرسال
if os.path.exists(ACCOUNTS_FILE):
    st.sidebar.success("✅ ملف الحسابات متصل بنجاح")
else:
    st.sidebar.error("⚠️ ملف accounts.csv غير موجود!")

# إعدادات الحملة الاحترافية
st.sidebar.header("⚙️ إعدادات الحملة الذكية")
industry_keyword = st.sidebar.text_input("مجال البحث عن الشركات", value="SaaS startup contact email")
batch_size = st.sidebar.slider("عدد الشركات في الدفعة", min_value=3, max_value=20, value=5)
sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (ثواني)", min_value=2, max_value=10, value=3)

subject_template = st.sidebar.text_input("عنوان الرسالة الأساسي", value="فرصة لزيادة مبيعات منتجكم الرقمي")
custom_offer = st.text_area("العرض أو الخدمة اللي بتوفرها لشركتهم:", height=100, value="مرحباً،\n\nراجعنا موقعكم وخدماتكم المتميزة، ونعتقد أن نظامنا يمكنه مضاعفة عملائكم المستهدفين من خلال الأوتريتش الآلي.")

GMAIL_SERVER = "smtp.gmail.com"
GMAIL_PORT = 587

# دالة تحليل موقع الشركة واستخراج نبذة عن منتجاتهم
def analyze_company_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # استخراج العنوان الرئيسي أو الوصف للتعرف على نشاطهم
        title = soup.title.string if soup.title else "خدمات رقمية"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else title
        
        return clean_text(desc[:150])
    except:
        return "تطوير الأعمال والخدمات الرقمية"

def clean_text(text):
    return re.sub(r'[^\w\s]', '', text).strip()

# دالة البحث المتقدم عن الشركات والإيميلات
def search_and_analyze_leads(keyword, limit):
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
                    # تحليل موقع الشركة المستهدفة
                    business_summary = analyze_company_website(url)
                    for em in valid:
                        found.append({
                            "website": url,
                            "email": em,
                            "analysis": business_summary
                        })
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

# واجهة التشغيل والتحكم الرئيسية
if st.button("🚀 ابدأ تحليل الشركات وبدء الحملة الآلية", type="primary"):
    if not os.path.exists(ACCOUNTS_FILE):
        st.error("❌ ملف الحسابات غير موجود على الريبوزيتوري!")
    else:
        with st.spinner("🔍 جاري البحث عن الشركات وتحليل مواقعهم ومنتجاتهم... سأقوم بتجهيز البيانات الآن"):
            leads = search_and_analyze_leads(industry_keyword, batch_size)
            
        if leads.empty:
            st.warning("⚠️ لم يتم العثور على إيميلات مطابقة، جرب تغيير كلمة البحث.")
        else:
            st.success(f"🎉 تم رصد وتحليل {len(leads)} شركة مستهدفة بنجاح!")
            
            # عرض جدول الشركات وتحليلها للمستخدم
            st.subheader("📊 تقرير الشركات المستهدفة وتحليل المنتجات:")
            st.dataframe(leads, use_container_width=True)

            accounts = pd.read_csv(ACCOUNTS_FILE, encoding='utf-8', on_bad_lines='skip')
            accounts.columns = accounts.columns.str.strip().str.lower()

            sent = 0
            failed = 0
            progress = st.progress(0)
            status = st.empty()

            for idx, row in leads.iterrows():
                target = row['email']
                company_analysis = row['analysis']
                acc_idx = idx % len(accounts)
                sender = str(accounts.loc[acc_idx, 'email']).strip()
                pwd = str(accounts.loc[acc_idx, 'password']).strip()

                # صياغة رسالة مخصصة لكل شركة بناءً على تحليل موقعهم
                personalized_body = f"""مرحباً،\n\nلاحظنا من خلال تحليل موقعكم أنكم تركزون على: ({company_analysis}).\n\n{custom_offer}\n\nنتطلع لسماع رأيكم.\n\nتحياتي،"""

                if send_email(sender, pwd, target, subject_template, personalized_body):
                    sent += 1
                else:
                    failed += 1

                progress.progress((idx + 1) / len(leads))
                status.text(f"جاري إرسال العرض المخصص للشركة ({idx + 1}/{len(leads)})...")
                time.sleep(sending_delay)

            st.balloons()
            st.success(f"✅ انتهت الحملة الذكية بنجاح! الإيميلات المرسلة بنجاح: {sent} | الفاشلة: {failed}")
