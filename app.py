import streamlit as st
import pandas as pd
import smtplib
import requests
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

st.set_page_config(
    page_title="SaaS B2B Cold Outreach & Lead Engine",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 منصة الأوتريتش الذكية - النسخة النهائية المطورة")
st.markdown("---")

tab1, tab2 = st.tabs(["🔍 1. البحث عن الشركات المستهدفة", "✉️ 2. محرك الإرسال والحملات"])

# ---------------------------------------------------------
# TAB 1: البحث عن الشركات واستخراج الإيميلات
# ---------------------------------------------------------
with tab1:
    st.header("🔍 البحث التلقائي عن إيميلات الشركات")
    
    search_option = st.radio("اختر طريقة البحث:", ["البحث بروابط المواقع (Domains Scraper)", "رفع ملف مواقع للبحث فيها"])
    
    def extract_emails_from_url(url):
        try:
            if not url.startswith("http"):
                url = "https://" + url
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            emails = set(re.findall(r"[a-zA-Z0-9.\-_+#']+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", response.text))
            valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
            return valid_emails
        except:
            return []

    if search_option == "البحث بروابط المواقع (Domains Scraper)":
        urls_input = st.text_area("أدخل روابط مواقع الشركات (كل رابط في سطر):", placeholder="example.com\nanother-company.com")
        
        if st.button("🔎 استخراج الإيميلات الآن"):
            urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
            if not urls:
                st.warning("يرجى إدخال رابط واحد على الأقل.")
            else:
                progress_bar = st.progress(0)
                results = []
                for idx, url in enumerate(urls):
                    emails = extract_emails_from_url(url)
                    for em in emails:
                        results.append({"domain": url, "email": em})
                    progress_bar.progress((idx + 1) / len(urls))
                
                if results:
                    df_found = pd.DataFrame(results)
                    st.session_state['found_leads'] = df_found
                    st.success(f"🎉 تم العثور على {len(df_found)} إيميل بنجاح!")
                    st.dataframe(df_found, use_container_width=True)
                else:
                    st.error("لم يتم العثور على إيميلات في المواقع المحددة.")

    elif search_option == "رفع ملف مواقع للبحث فيها":
        uploaded_domains = st.file_uploader("ارفع ملف CSV للمواقع", type=["csv"])
        if uploaded_domains and st.button("🔎 فحص الملف واستخراج الإيميلات"):
            try:
                df_dom = pd.read_csv(uploaded_domains, encoding='utf-8', on_bad_lines='skip')
                df_dom.columns = df_dom.columns.str.strip().str.lower()
                col_name = "domain" if "domain" in df_dom.columns else ("website" if "website" in df_dom.columns else df_dom.columns[0])
                
                results = []
                progress_bar = st.progress(0)
                for idx, row in df_dom.iterrows():
                    emails = extract_emails_from_url(str(row[col_name]))
                    for em in emails:
                        results.append({"domain": row[col_name], "email": em})
                    progress_bar.progress((idx + 1) / len(df_dom))
                
                df_found = pd.DataFrame(results)
                st.session_state['found_leads'] = df_found
                st.success(f"🎉 تم استخراج {len(df_found)} إيميل بنجاح!")
                st.dataframe(df_found, use_container_width=True)
            except Exception as e:
                st.error(f"خطأ في قراءة الملف: {e}")

# ---------------------------------------------------------
# TAB 2: محرك الإرسال الحقيقي وتدوير الحسابات
# ---------------------------------------------------------
with tab2:
    st.header("✉️ إطلاق الحملة وتدوير أكونتات Gmail")
    
    st.sidebar.header("📁 إعدادات الإرسال والحسابات")
    
    lead_source = st.sidebar.radio("مصدر الشركات المستهدفة:", ["استخدام القائمة المستخرجة من البحث", "رفع ملف مستهدفين (CSV)"])
    
    uploaded_leads = None
    if lead_source == "رفع ملف مستهدفين (CSV)":
        uploaded_leads = st.sidebar.file_uploader("1️⃣ ارفع لستة المستهدفين (CSV)", type=["csv"])
    
    uploaded_smtp = st.sidebar.file_uploader("2️⃣ ارفع لستة الجيميلات (CSV - حتى 280 ألف)", type=["csv"])

    email_col = st.sidebar.text_input("اسم عمود إيميل المستهدفين", value="email")
    subject_template = st.sidebar.text_input("عنوان الرسالة (Subject)", value="فرصة تعاون مميزة")

    st.sidebar.markdown("---")
    sending_delay = st.sidebar.slider("الفاصل الزمني بين الرسائل (ثواني)", min_value=1, max_value=10, value=2)
    emails_per_account = st.sidebar.number_input("الحد الأقصى لكل أكونت قبل التدوير", min_value=1, value=5)

    GMAIL_SERVER = "smtp.gmail.com"
    GMAIL_PORT = 587

    email_body = st.text_area("محتوى الرسالة:", height=150, value="مرحباً،\n\nحابين نتواصل مع شركتكم لمناقشة فرص التعاون بيننا.\n\nتحياتي،")

    def send_email_gmail(sender_email, password, recipient_email, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server = smtplib.SMTP(GMAIL_SERVER, GMAIL_PORT, timeout=10)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            return True, "تم الإرسال بنجاح"
        except Exception as e:
            return False, str(e)

    if st.button("🔥 إطلاق الحملة الآن"):
        leads_df = None
        if lead_source == "استخدام القائمة المستخرجة من البحث":
            if 'found_leads' in st.session_state and not st.session_state['found_leads'].empty:
                leads_df = st.session_state['found_leads']
            else:
                st.error("❌ لا توجد قائمة مستخرجة! يرجى البحث عن الشركات أولاً في التبويب الأول.")
        else:
            if uploaded_leads is not None:
                try:
                    leads_df = pd.read_csv(uploaded_leads, encoding='utf-8', on_bad_lines='skip')
                    leads_df.columns = leads_df.columns.str.strip().str.lower()
                except Exception as e:
                    st.error(f"خطأ في قراءة ملف المستهدفين: {e}")
            else:
                st.error("❌ يرجى رفع ملف المستهدفين أولاً.")

        if uploaded_smtp is None:
            st.error("❌ يرجى رفع ملف حسابات Gmail أولاً!")
        elif leads_df is not None:
            try:
                # قراءة ملف الـ 280 ألف حساب وتجنب مشاكل الحجم أو الترميز
                smtp_df = pd.read_csv(uploaded_smtp, encoding='utf-8', on_bad_lines='skip')
                smtp_df.columns = smtp_df.columns.str.strip().str.lower()
            except Exception as e:
                st.error(f"خطأ في قراءة ملف الجيميلات: {e}")
                smtp_df = None

            if smtp_df is not None:
                if 'email' not in smtp_df.columns or 'password' not in smtp_df.columns:
                    st.error("⚠️ ملف حسابات الجيميل لازم يحتوي على عمودين باسم: 'email' و 'password'")
                elif email_col not in leads_df.columns:
                    st.error(f"⚠️ عمود إيميلات المستهدفين '{email_col}' غير مطابق لأسماء الأعمدة في الملف!")
                else:
                    st.success("✅ تم بدء محرك الإرسال وتدوير الحسابات بنجاح!")
                    
                    total_leads = len(leads_df)
                    total_accounts = len(smtp_df)
                    
                    smtp_df['sent_count'] = 0
                    smtp_df['status'] = 'جاهز'

                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        metric_sent = st.metric("إجمالي النجاح", "0")
                    with col2:
                        metric_failed = st.metric("إجمالي الفشل", "0")
                    with col3:
                        metric_active_acc = st.metric("الأكونت الحالي", "---")

                    table_placeholder = st.empty()

                    sent_count = 0
                    failed_count = 0
                    account_index = 0
                    account_usage = 0

                    for index, row in leads_df.iterrows():
                        target_email = row[email_col]
                        
                        current_account_email = str(smtp_df.loc[account_index, 'email']).strip()
                        current_account_pass = str(smtp_df.loc[account_index, 'password']).strip()
                        
                        success, log_msg = send_email_gmail(
                            sender_email=current_account_email,
                            password=current_account_pass,
                            recipient_email=target_email,
                            subject=subject_template,
                            body=email_body
                        )

                        if success:
                            sent_count += 1
                            smtp_df.loc[account_index, 'sent_count'] += 1
                            smtp_df.loc[account_index, 'status'] = 'شغال تمام'
                        else:
                            failed_count += 1
                            smtp_df.loc[account_index, 'status'] = f'خطأ: {log_msg[:20]}'

                        account_usage += 1
                        
                        if account_usage >= emails_per_account:
                            account_index = (account_index + 1) % total_accounts
                            account_usage = 0

                        progress = (index + 1) / total_leads
                        progress_bar.progress(progress)
                        status_text.text(f"جاري الإرسال {index + 1} من {total_leads}...")
                        
                        metric_sent.metric("إجمالي النجاح", str(sent_count))
                        metric_failed.metric("إجمالي الفشل", str(failed_count))
                        metric_active_acc.metric("الأكونت الحالي", current_account_email)

                        active_view = smtp_df[smtp_df['sent_count'] > 0]
                        if not active_view.empty:
                            table_placeholder.dataframe(active_view[['email', 'sent_count', 'status']], use_container_width=True)

                        time.sleep(sending_delay)

                    st.balloons()
                    st.success(f"🎉 انتهت الحملة! الناجح: {sent_count} | الفاشل: {failed_count}")
