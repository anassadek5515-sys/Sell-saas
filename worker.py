import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import concurrent.futures

# --- الإعدادات الأساسية ---
DB_FILE = "companies.db"

# بيانات سيرفر الإرسال (SMTP) - يتم سحبها من البيئة في جيت هب
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password")

# عدد الخيوط لتسريع الإرسال بالتوازي
MAX_THREADS = 10

def send_email(lead):
    """
    وظيفة إرسال الإيميل لشركة واحدة وتحديث حالتها في قاعدة البيانات
    """
    lead_id, company_name, recipient_email = lead[0], lead[1], lead[2]
    
    # نص الإيميل التسويقي الاحترافي لمنتج تحليل المنتجات (200$ شهرياً)
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
        # الاتصال بالسيرفر وإرسال الرسالة
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        # تحديث حالة الإيميل في قاعدة البيانات إلى Sent
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE companies SET status = 'Sent' WHERE id = ?", (lead_id,))
        conn.commit()
        conn.close()

        print(f"✅ تم الإرسال بنجاح إلى: {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ فشل الإرسال إلى {recipient_email}: {e}")
        return False

def run_worker():
    """
    سحب الـ Leads الجاهزة من قاعدة البيانات وإرسالها بالتوازي
    """
    if not os.path.exists(DB_FILE):
        print("⚠️ قاعدة البيانات غير موجودة محلياً!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # التأكد من إنشاء الجدول بالأعمدة الصحيحة تماماً لمنع أي خطأ
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

    # سحب الشركات التي حالتها Ready فقط
    cursor.execute("SELECT id, name, email FROM companies WHERE status = 'Ready' LIMIT 50")
    leads = cursor.fetchall()
    conn.close()

    if not leads:
        print("ℹ️ لا توجد إيميلات جديدة بحالة Ready جاهزة للإرسال حالياً.")
        return

    print(f"🚀 بدء معالجة إرسال {len(leads)} إيميل...")

    # تشغيل الإرسال المتوازي باستخدام Multi-threading
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(send_email, leads)

    print("✨ اكتملت دورة الإرسال بنجاح!")

if __name__ == "__main__":
    run_worker()
