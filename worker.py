import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import time

# ==========================================
# إعدادات حملة الإرسال
# ==========================================
BATCH_SIZE = 100          # عدد الإيميلات في الدورة الواحدة
MAX_WORKERS = 10          # عدد الخيوط المتوازية للإرسال
DB_FILE = "companies.db"

def send_single_email(recipient_email):
    """دالة إرسال الإيميل الفردية"""
    try:
        # ضع هنا كود الـ SMTP أو الـ API الخاص بإرسال الإيميل الفعلي
        print(f"تم الإرسال بنجاح إلى: {recipient_email}")
        return True
    except Exception as e:
        print(f"فشل الإرسال إلى {recipient_email}: {e}")
        return False

def main():
    print("--- بدء دورة الإرسال الجديدة من قاعدة البيانات ---")
    
    if not os.path.exists(DB_FILE):
        print(f"ملف قاعدة البيانات {DB_FILE} غير موجود!")
        return

    # الاتصال بقاعدة البيانات SQLite
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # جلب الشركات التي لم يتم مراسلتها بعد (أو جاهزة للإرسال)
        # ملاحظة: تأكد أن اسم الجدول والأعمدة يتطابق مع ما ينشئه موقع البحث لديك
        cursor.execute("SELECT id, email FROM companies WHERE status = 'Ready' LIMIT ?", (BATCH_SIZE,))
        rows = cursor.fetchall()

        if not rows:
            print("لا توجد إيميلات جديدة بحالة 'Ready' في قاعدة البيانات حالياً.")
            conn.close()
            return

        print(f"جاري إرسال دفعة تضم {len(rows)} إيميل...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for row in rows:
                row_id, recipient_email = row
                if recipient_email:
                    futures.append((row_id, executor.submit(send_single_email, recipient_email)))

            # تحديث حالة الإيميلات التي تم إرسالها في قاعدة البيانات
            for row_id, future in futures:
                if future.result():
                    cursor.execute("UPDATE companies SET status = 'Sent' WHERE id = ?", (row_id,))
                    conn.commit()

        print("--- انتهت الدورة الحالية بنجاح ---")

    except Exception as e:
        print(f"حدث خطأ أثناء معالجة قاعدة البيانات: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
