import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import sys

# ==========================================
# إعدادات الإرسال الآلي المتكامل
# ==========================================
BATCH_SIZE = 500           # عدد الإيميلات في الدورة الواحدة للتحكم الآمن
MAX_WORKERS = 10           # عدد المسارات المتوازية (تم ضبطها بأمان للحفاظ على الحسابات)
DB_FILE = "companies.db"   # قاعدة البيانات التي يأتي بها موقع البحث أوتوماتيكياً

# ⚠️ بيانات حساب الإرسال الحالي (أو يمكن جدولتها لحسابات متعددة)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_sender_email@gmail.com"        # إيميل الإرسال
SMTP_PASSWORD = "your_app_password_here"       # كلمة مرور التطبيق

def send_single_email(recipient_email):
    """
    إرسال فوري حقيقي لإيميل الشركة المستخرجة من موقع البحث
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = recipient_email
        msg['Subject'] = "فرصة تعاون تجاري واستراتيجي"
        
        body = "مرحباً،\n\nنود عرض خدماتنا وتأسيس شراكة عمل ناجحة معكم بناءً على نشاطكم التجاري...\n\nمع تحيات فريق التطوير."
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient_email, msg.as_string())
        
        print(f"⚡ [تم الإرسال بنجاح] إلى الشركة: {recipient_email}", flush=True)
        return True
    except Exception as e:
        print(f"❌ [فشل الإرسال إلى {recipient_email}]: {e}", flush=True)
        return False

def main():
    print("🚀 [Worker] بدأ فحص قاعدة البيانات القادمة من موقع البحث...", flush=True)
    
    if not os.path.exists(DB_FILE):
        print(f"❌ خطأ: قاعدة البيانات {DB_FILE} غير موجودة (تأكد أن موقع البحث قام برفعها بنجاح).", flush=True)
        sys.exit(1)

    # الاتصال بقاعدة البيانات القادمة من موقع البحث
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # التأكد من وجود عمود الحالة أو إضافته لتتبع الإيميلات التي تم إرسالها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            email TEXT UNIQUE,
            status TEXT
        )
    """)
    conn.commit()

    # جلب الشركات التي حالتها 'Ready' فقط (التي تم توليدها حديثاً ولم تُرسل بعد)
    cursor.execute("SELECT id, email FROM emails WHERE status = 'Ready' LIMIT ?", (BATCH_SIZE,))
    rows = cursor.fetchall()

    if not rows:
        print("🎉 تم إرسال جميع الإيميلات الجديدة الواردة من موقع البحث بنجاح!", flush=True)
        conn.close()
        return

    print(f"⚡ تم العثور على {len(rows)} شركة جديدة مستخرجة من موقع البحث، جاري الإرسال...", flush=True)

    success_count = 0
    processed_ids = []

    # استخدام التوازي المعتدل لضمان وصول الرسائل بأمان
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(send_single_email, email): row_id for row_id, email in rows}
        
        for future in futures:
            row_id = futures[future]
            if future.result():
                success_count += 1
                processed_ids.append((row_id,))

    # تحديث حالة الشركات التي تم إرسالها إلى 'Sent' لكي لا يتم إعادة إرسالها مجدداً
    if processed_ids:
        cursor.executemany("UPDATE emails SET status = 'Sent' WHERE id = ?", processed_ids)
        conn.commit()

    conn.close()
    
    print(f"✅ [اكتملت الدورة] تم إرسال {success_count} إيميل حقيقي بنجاح للشركات المستخرجة!", flush=True)

if __name__ == "__main__":
    main()
