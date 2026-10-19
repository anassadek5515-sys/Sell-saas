import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

st.set_page_config(
    page_title="SaaS B2B Cold Outreach Engine",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 منصة الأوتريتش الذكية - محرك الإرسال الحقيقي")
st.markdown("---")

# 1. الشريط الجانبي لرفع الملفات والتكوين
st.sidebar.header("📁 رفع البيانات والإعدادات")
uploaded_leads = st.sidebar.file_uploader("رفع لستة الشركات المستهدفة (CSV)", type=["csv"])
uploaded_smtp = st.sidebar.file_uploader("رفع حسابات الـ SMTP (CSV)", type=["csv"])

# حقول اختيار أسماء الأعمدة في الملفات
st.sidebar.subheader("⚙️ إعدادات الحقول")
email_col = st.sidebar.text_input("اسم عمود إيميل الشركات (في ملف المستهدفين)", value="email")
subject_template = st.sidebar.text_input("عنوان الرسالة (Subject)", value="فرصة تعاون عمل مميزة")

st.sidebar.markdown("---")
sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (بالثواني)", min_value=1, max_value=10, value=2)
emails_per_account = st.sidebar.number_input("الحد الأقصى لكل أكونت", min_value=1, value=5)

# 2. نص الرسالة
st.subheader("✉️ صياغة الرسالة")
email_body = st.text_area("محتوى الرسالة:", height=150, value="مرحباً،\n\nحابين نتواصل مع شركتكم لمناقشة فرص التعاون بيننا.\n\nتحياتي،")

# 3. محرك الإرسال الفعلي (SMTP Engine)
def send_email_smtp(smtp_server, port, sender_email, password, recipient_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # الاتصال بالسيرفر
        server = smtplib.SMTP(smtp_server, int(port), timeout=10)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True, "تم الإرسال بنجاح"
    except Exception as e:
        return False, str(e)

# 4. إطلاق الحملة
if st.button("🔥 إطلاق الحملة الحقيقية الآن"):
    if uploaded_leads is None or uploaded_smtp is None:
        st.error("❌ يرجى رفع ملف المستهدفين وملف أكونتات الـ SMTP أولاً!")
    else:
        leads_df = pd.read_csv(uploaded_leads)
        smtp_df = pd.read_csv(uploaded_smtp)

        # التأكد من وجود الأعمدة
        required_smtp_cols = ['server', 'port', 'email', 'password']
        if not all(col in smtp_df.columns for col in required_smtp_cols):
            st.error(f"⚠️ ملف الـ SMTP لازم يحتوي على الأعمدة التالية بالظبط: {required_smtp_cols}")
        elif email_col not in leads_df.columns:
            st.error(f"⚠️ عمود الإيميل '{email_col}' غير موجود في ملف المستهدفين!")
        else:
            st.success("✅ تم فتح الاتصال.. جاري تدوير الحسابات والإرسال الفعلي!")
            
            total_leads = len(leads_df)
            total_accounts = len(smtp_df)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            sent_count = 0
            failed_count = 0
            account_index = 0
            account_usage = 0

            for index, row in leads_df.iterrows():
                target_email = row[email_col]
                
                # تدوير الحسابات (Account Rotation)
                current_account = smtp_df.iloc[account_index]
                
                # تنفيذ الإرسال الحقيقي
                success, log_msg = send_email_smtp(
                    smtp_server=current_account['server'],
                    port=current_account['port'],
                    sender_email=current_account['email'],
                    password=current_account['password'],
                    recipient_email=target_email,
                    subject=subject_template,
                    body=email_body
                )

                if success:
                    sent_count += 1
                else:
                    failed_count += 1

                account_usage += 1
                
                # نقل للأكونت اللي بعده لو وصلنا للحد الأقصى (مثلاً 5 رسائل)
                if account_usage >= emails_per_account:
                    account_index = (account_index + 1) % total_accounts
                    account_usage = 0

                # تحديث شريط التقدم
                progress = (index + 1) / total_leads
                progress_bar.progress(progress)
                status_text.text(f"تم إرسال {index + 1} من أصل {total_leads} | أكونت الإرسال الحالي: {current_account['email']}")
                
                time.sleep(sending_delay)

            st.balloons()
            st.success(f"🎉 اكتملت الحملة! إجمالي الناجح: {sent_count} | إجمالي الفاشل: {failed_count}")
