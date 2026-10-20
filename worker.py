import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import sys

# ==========================================
# إعدادات الحملة الفائقة (1.4M / Day Target)
# ==========================================
BATCH_SIZE = 14584         # عدد الإيميلات في الدورة (كل 15 دقيقة)
MAX_WORKERS = 200          # عدد المسارات المتوازية للسرعة الفائقة
DB_FILE = "companies.db"   # قاعدة البيانات الخفيفة للملايين
INDEX_FILE = "last_db_id.txt" # حفظ آخر رقم ID تم الإرسال إليه

# ⚠️ بيانات خادم الإرسال الحقيقي (SMTP)
SMTP_SERVER = "smtp.yourprovider.com"
SMTP_PORT = 587
SMTP_USER = "your_real_email@company.com"
SMTP_PASSWORD = "your_real_password"

def get_last_id():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 0
    return 0

def save_last_id(last_id):
    with open(INDEX_FILE, "w") as f:
        f.write(str(last_id))

def send_single_email(recipient):
    """
    إرسال فوري فائق السرعة لإيميل الشركة
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = recipient
        msg['Subject'] = "فرصة تعاون استراتيجي وتجاري"
        
        body = "مرحباً،\n\nنود عرض خدماتنا وتأسيس شراكة عمل ناجحة معكم...\n\nمع تحيات إدارة التطوير."
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())
        
        print(f"⚡ [تم الإرسال] إلى: {recipient}", flush=True)
        return True
    except Exception as e:
        return False

def main():
    print("🚀 [النظام الخفيف] بدأ تشغيل محرك ملايين الشركات...", flush=True)
    
    if not os.path.exists(DB_FILE):
        print(f"❌ خطأ: قاعدة البيانات {DB_FILE} غير موجودة في المستودع!", flush=True)
        sys.exit(1)

    # الاتصال بقاعدة البيانات الخفيفة
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    last_id = get_last_id()

    # جلب الدفعة التالية فقط (14,584 إيميل) بسرعة خيالية ودون تحميل الملف كله بالذاكرة
    cursor.execute("SELECT id, email FROM emails WHERE id > ? ORDER BY id ASC LIMIT ?", (last_id, BATCH_SIZE))
    rows = cursor.fetchall()

    if not rows:
        print("🎉 تم إرسال الحملة بالكامل لجميع الشركات في قاعدة البيانات!", flush=True)
        conn.close()
        return

    print(f"⚡ جاري ضخ دفعة من {len(rows)} شركة بسرعة فائقة...", flush=True)

    success_count = 0
    max_id_reached = last_id

    # تشغيل 200 مسار في نفس اللحظة للإرسال الفوري
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for row_id, email in rows:
            futures[executor.submit(send_single_email, email)] = row_id
        
        for future in futures:
            row_id = futures[future]
            if future.result():
                success_count += 1
            if row_id > max_id_reached:
                max_id_reached = row_id

    # حفظ آخر ID تم الوصول إليه
    save_last_id(max_id_reached)
    conn.close()
    
    print(f"✅ [انتهت الدورة] تم إرسال {success_count} شركة بنجاح. آخر ID تم الوصول إليه: {max_id_reached}", flush=True)

if __name__ == "__main__":
    main()
