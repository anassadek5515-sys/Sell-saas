import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import time

# ==========================================
# إعدادات السرعة الصارخية للإمبراطورية 🚀
# ==========================================
BATCH_SIZE = 500         # حجم الدفعة في المرة الواحدة
MAX_WORKERS = 30         # عدد خيوط الإرسال المتوازية (لأقصى سرعة)
DB_FILE = "companies.db"

def send_single_email(recipient_email):
    """دالة إرسال الإيميل الفردية"""
    try:
        # كود الـ SMTP أو API الإرسال الخاص بك
        print(f"تم الإرسال بنجاح إلى: {recipient_email}")
        return True
    except Exception as e:
        print(f"فشل الإرسال إلى {recipient_email}: {e}")
        return False

def main():
    print("--- 🚀 بدء دورة الإرسال الفائقة من قاعدة البيانات ---")
    
    if not os.path.exists(DB_FILE):
        print(f"ملف قاعدة البيانات {DB_FILE} غير موجود!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, email FROM companies WHERE status = 'Ready' LIMIT ?", (BATCH_SIZE,))
        rows = cursor.fetchall()

        if not rows:
            print("⚠️ لا توجد إيميلات جاهزة بحالة 'Ready'.")
            conn.close()
            return

        print(f"⚡ جاري إرسال دفعة صارخية تضم {len(rows)} إيميل عبر {MAX_WORKERS} خيط متوازي...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for row in rows:
                row_id, recipient_email = row
                if recipient_email:
                    futures.append((row_id, executor.submit(send_single_email, recipient_email)))

            for row_id, future in futures:
                if future.result():
                    cursor.execute("UPDATE companies SET status = 'Sent' WHERE id = ?", (row_id,))
                    conn.commit()

        print("--- 🎉 انتهت الدورة الفائقة بنجاح ---")

    except Exception as e:
        print(f"حدث خطأ أثناء معالجة قاعدة البيانات: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
