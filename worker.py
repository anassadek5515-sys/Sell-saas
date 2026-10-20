import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time

# --- الإعدادات الأساسية ---
DB_FILE = "companies.db"

# بيانات سيرفر الإرسال (SMTP) - يتم سحبها من البيئة في جيت هب
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password")

def run_worker():
    """
    سحب الـ Leads الجاهزة وإرسالها بشكل متسلسل وآمن لمنع الحظر
    """
    if not os.path.exists(DB_FILE):
        print("⚠️ قاعدة البيانات غير موجودة محلياً!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. التأكد من إنشاء الجدول لو مش موجود أصلاً
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            status TEXT DEFAULT 'Ready',
            reply_text TEXT
        )
    """)
    conn.commit()

    # 2. فحص ذكي لعمود name
    cursor.execute("PRAGMA table_info(companies);")
    columns = [col[1] for col in cursor.fetchall()]
    if 'name' not in columns:
        try:
            cursor.execute("ALTER TABLE companies ADD COLUMN name TEXT;")
            conn.commit()
            print("🔧 تم إضافة عمود 'name' المفقود أوتوماتيكياً بنجاح!")
        except Exception as ex:
            print(f"⚠️ خطأ أثناء إضافة العمود: {ex}")

    # سحب عدد محدود (مثلاً 10 إيميلات في كل تشغيل لاختبار الأمان)
    cursor.execute("SELECT id, name, email FROM companies WHERE status = 'Ready' LIMIT 10")
    leads = cursor.fetchall()
    conn.close()

    if not leads:
        print("ℹ️ لا توجد إيميلات جديدة بحالة Ready جاهزة للإرسال حالياً.")
        return

    print(f"🚀 بدء إرسال {len(leads)} إيميل بشكل آمن...")

    for lead in leads:
        lead_id, company_name, recipient_email = lead[0], lead[1], lead[2]
        
        # ضبط اسم الشركة افتراضياً لو فاضي
        if not company_name:
            company_name = "your company"

        subject = f"Quick question regarding your product analytics, {company_name}"
        body = f"""Hi there,

I was checking out your store ({company_name}) and noticed you are constantly updating your product catalog.

We built an AI-powered product analytics tool that tracks real-time market trends, competitors, and exact best-sellers—helping e-commerce brands instantly spot winning products before spending thousands on testing.

Our subscription is $200/mo, and we offer a 3-minute video demo to show you how it works for your store.

Would you be open to checking out a quick demo?

Best regards,
Anas
Founder & CEO
"""

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            # الاتصال وإرسال الرسالة
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()

            # تحديث الحالة إلى Sent في قاعدة البيانات فوراً
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("UPDATE companies SET status = 'Sent' WHERE id = ?", (lead_id,))
            conn.commit()
            conn.close()

            print(f"✅ تم الإرسال بنجاح إلى: {recipient_email}")
            
            # التوقف 5 ثواني بين كل إيميل والثاني لمنع حظر جوجل (Rate Limiting)
            time.sleep(5)

        except Exception as e:
            print(f"❌ فشل الإرسال إلى {recipient_email}: {e}")

    print("✨ اكتملت دورة الإرسال بنجاح!")

if __name__ == "__main__":
    run_worker()
