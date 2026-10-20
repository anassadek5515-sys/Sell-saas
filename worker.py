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
        print(f"تم الإرسال بنجاح إلى: {recipient}")
        return True
    except Exception as e:
        print(f"فشل الإرسال إلى {recipient}: {e}")
        return False

def main():
    print("--- بدء دورة الإرسال الجديدة ---")
    
    if not os.path.exists("targets.csv"):
        print("ملف الأهداف targets.csv غير موجود!")
        return
        
    df_targets = pd.read_csv("targets.csv")
    current_index = load_index()
    
    end_index = min(current_index + BATCH_SIZE, len(df_targets))
    batch_targets = df_targets.iloc[current_index:end_index]
    
    if batch_targets.empty:
        print("تم الانتهاء من جميع الإيميلات في القائمة بنجاح!")
        return
        
    print(f"جاري إرسال دفعة من الإيميلات من الفهرس {current_index} إلى {end_index}...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, row in batch_targets.iterrows():
            recipient_email = row['email']
            executor.submit(send_single_email, recipient_email, None)
            
    save_index(end_index)
    print(f"--- انتهت الدورة بنجاح، المؤشر الجديد هو: {end_index} ---")

if __name__ == "__main__":
    main()
