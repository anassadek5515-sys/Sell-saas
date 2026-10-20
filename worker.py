import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import time
import sys

# ==========================================
# إعدادات حملة الإرسال (1.4M / Day Target)
# ==========================================
BATCH_SIZE = 14584         # عدد الإيميلات في الدورة الواحدة (كل 15 دقيقة)
MAX_WORKERS = 100          # عدد الخيوط المتوازية للسرعة العالية
INDEX_FILE = "last_account_index.txt"

# إعدادات خادم البريد (SMTP) - قم بتعديلها بما يناسب مزود الخدمة لديك
SMTP_SERVER = "smtp.yourprovider.com"
SMTP_PORT = 587
SMTP_USER = "your_email@domain.com"
SMTP_PASSWORD = "your_password"

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
    دالة إرسال الإيميل الفردية عبر SMTP
    """
    try:
        # إذا كنت تستخدم API خارجي بدلاً من SMTP، استبدل هذا الجزء بكود الـ API الخاص بك
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = recipient
        msg['Subject'] = "عروض مميزة خصيصاً لك"
        
        body = "مرحباً، هذه رسالة تجريبية من حملتنا التسويقية."
        msg.attach(MIMEText(body, 'plain'))

        # الاتصال بالسيرفر والإرسال
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())
        
        print(f"✅ تم الإرسال بنجاح إلى: {recipient}")
        return True
    except Exception as e:
        print(f"❌ فشل الإرسال إلى {recipient}: {e}")
        return False

def main():
    print("🚀 [Worker] بدأ تشغيل محرك الخلفية المستمر...", flush=True)
    
    # 1. التحقق من وجود ملف الأهداف
    if not os.path.exists("targets.csv"):
        print("❌ خطأ: ملف الأهداف targets.csv غير موجود في المستودع!", flush=True)
        return

    df_targets = pd.read_csv("targets.csv")
    current_index = load_index()

    # تحديد الدفعة الحالية
    end_index = min(current_index + BATCH_SIZE, len(df_targets))
    batch_targets = df_targets.iloc[current_index:end_index]

    if batch_targets.empty:
        print("🎉 تم الانتهاء من جميع الإيميلات في القائمة بنجاح!", flush=True)
        return

    print(f"📤 جاري إرسال دفعة من الإيميلات من الفهرس {current_index} إلى {end_index}...", flush=True)

    success_count = 0
    # 2. الإرسال المتوازي باستخدام ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for index, row in batch_targets.iterrows():
            recipient_email = row['email']  # تأكد أن عمود الإيميلات في ملف targets.csv اسمه email
            futures.append(executor.submit(send_single_email, recipient_email))
        
        for future in futures:
            if future.result():
                success_count += 1

    # 3. تحديث وحفظ مؤشر التقدم للدورة القادمة
    save_index(end_index)
    print(f"✅ [Worker] انتهت الدورة بنجاح. تم إرسال {success_count} إيميل. المؤشر الجديد: {end_index}", flush=True)

if __name__ == "__main__":
    main()
