import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import sys

# ==========================================
# إعدادات الحملة الفائقة (1.4M / Day Target)
# ==========================================
BATCH_SIZE = 14584         # عدد الإيميلات في الدورة (كل 15 دقيقة)
MAX_WORKERS = 200          # رفع عدد المسارات لـ سرعة البرق (Lightning Fast)
INDEX_FILE = "last_account_index.txt"

# ⚠️ بيانات خادم الإرسال الحقيقي (SMTP)
SMTP_SERVER = "smtp.yourprovider.com"
SMTP_PORT = 587
SMTP_USER = "your_real_email@company.com"
SMTP_PASSWORD = "your_real_password"

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 0
    return 0

def save_index(index):
    with open(INDEX_FILE, "w") as f:
        f.write(str(index))

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
        
        print(f"⚡ [تم الإرسال بسرعة البرق] إلى: {recipient}", flush=True)
        return True
    except Exception as e:
        # لضمان عدم توقف الحملة الكبرى لو إيميل واحد فشل
        return False

def main():
    print("🚀 [النظام الذكي] بدأ التشغيل التلقائي بالكامل...", flush=True)
    
    # التحقق من وجود ملف الشركات الحقيقي
    if not os.path.exists("targets.csv"):
        print("❌ خطأ: ملف targets.csv غير موجود. يرجى التأكد من توفير قائمة إيميلات الشركات.", flush=True)
        sys.exit(1)

    df_targets = pd.read_csv("targets.csv")
    
    if 'email' not in df_targets.columns:
        print("❌ خطأ: يجب أن يحتوي الملف على عمود باسم 'email'", flush=True)
        sys.exit(1)

    current_index = load_index()
    end_index = min(current_index + BATCH_SIZE, len(df_targets))
    batch_targets = df_targets.iloc[current_index:end_index]

    if batch_targets.empty:
        print("🎉 تم إرسال الحملة بالكامل لجميع الشركات بنجاح تام!", flush=True)
        return

    print(f"⚡ جاري ضخ دفعة الشركات من {current_index} إلى {end_index} بسرعة فائقة...", flush=True)

    success_count = 0
    # تشغيل 200 مسار في نفس اللحظة (ThreadPoolExecutor) للإرسال الفوري
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_single_email, row['email']) for _, row in batch_targets.iterrows()]
        for future in futures:
            if future.result():
                success_count += 1

    # حفظ المؤشر تلقائياً للانتقال للدفعة التالية في الدورة القادمة (بعد 15 دقيقة)
    save_index(end_index)
    print(f"✅ [انتهت الدورة] تم إرسال {success_count} شركة بنجاح. المؤشر الجديد: {end_index}", flush=True)

if __name__ == "__main__":
    main()
