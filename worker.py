import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import time

# ==========================================
# إعدادات حملة الإرسال (1.4M / Day Target)
# ==========================================
BATCH_SIZE = 14584         # عدد الإيميلات في الدورة الواحدة (كل 15 دقيقة)
MAX_WORKERS = 100          # عدد الخيوط المتوازية (Threads) للسرعة العالية
INDEX_FILE = "last_account_index.txt"

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

def send_single_email(recipient, account_data):
    # دالة إرسال الإيميل الفردية عبر الحساب المحدد
    try:
        # ضع هنا كود الـ API أو الـ SMTP الخاص بإرسال الإيميل
        # مثال وهمي لطلب HTTP:
        # response = requests.post("https://api.emailservice.com/send", json={...})
        print(f"تم الإرسال بنجاح إلى: {recipient}")
        return True
    except Exception as e:
        print(f"فشل الإرسال إلى {recipient}: {e}")
        return False

def main():
    print("--- بدء دورة الإرسال الجديدة ---")
    
    # 1. تحميل قائمة الإيميلات المستهدفة وقائمة الحسابات
    # تأكد من مسارات الملفات لديك (مثل targets.csv و accounts.csv)
    if not os.path.exists("targets.csv"):
        print("ملف الأهداف targets.csv غير موجود!")
        return

    df_targets = pd.read_csv("targets.csv")
    current_index = load_index()

    # تحديد الدفعة الحالية بناءً على مؤشر التقدم
    end_index = min(current_index + BATCH_SIZE, len(df_targets))
    batch_targets = df_targets.iloc[current_index:end_index]

    if batch_targets.empty:
        print("تم الانتهاء من جميع الإيميلات في القائمة بنجاح!")
        return

    print(f"جاري إرسال دفعة من الإيميلات من الفهرس {current_index} إلى {end_index}...")

    # 2. الإرسال المتوازي باستخدام ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, row in batch_targets.iterrows():
            recipient_email = row['email'] # اسم عمود الإيميل في ملفك
            executor.submit(send_single_email, recipient_email, None)

    # 3. تحديث وحفظ مؤشر التقدم للدورة القادمة
    save_index(end_index)
    print(f"--- انتهت الدورة بنجاح، المؤشر الجديد هو: {end_index} ---")

if __name__ == "__main__":
    main()
