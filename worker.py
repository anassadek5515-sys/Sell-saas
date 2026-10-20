import os
import time
import random
import smtplib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ACCOUNTS_FILE = "final_ready_accounts.csv"
STATE_FILE = "last_account_index.txt"
LOG_FILE = "sent_stats.csv"

GMAIL_SMTP = "smtp.gmail.com"

def get_index(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_index(filename, idx):
    with open(filename, "w") as f:
        f.write(str(idx))

def send_email_silent(sender, password, recipient, subject, body):
    try:
        time.sleep(random.uniform(0.2, 0.6)) # تأخير أمان عشوائي
        server = smtplib.SMTP(GMAIL_SMTP, 587, timeout=5)
        server.starttls()
        server.login(sender, password)
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

def run_background_outreach():
    print("🚀 [Worker] بدأ تشغيل محرك الخلفية المستمر...")
    
    while True:
        if not os.path.exists(ACCOUNTS_FILE):
            print("⏳ في انتظار ملف الحسابات final_ready_accounts.csv...")
            time.sleep(10)
            continue
            
        try:
            accounts_df = pd.read_csv(ACCOUNTS_FILE, header=None, names=["email", "password"], encoding='utf-8', on_bad_lines='skip')
            total_accounts = len(accounts_df)
            
            if total_accounts == 0:
                time.sleep(10)
                continue
                
            current_idx = get_index(STATE_FILE)
            
            # توليد دفعة جديدة للإرسال
            batch_leads = [
                {"company": f"Global Tech {i}", "email": f"contact{i}@startupstore{i}.io"} 
                for i in range(current_idx, current_idx + 200)
            ]
            
            tasks = []
            for lead in batch_leads:
                acc_row = accounts_df.iloc[current_idx % total_accounts]
                sender = str(acc_row['email']).strip()
                pwd = str(acc_row['password']).strip()
                current_idx += 1
                
                body = f"Hi {lead['company']} team,\n\nWe built an automated analytics engine for $200/month.\n\nBest,\nAnas"
                tasks.append((sender, pwd, lead['email'], "Quick question about analytics", body))
                
            save_index(STATE_FILE, current_idx)
            
            # تنفيذ الإرسال المتوازي السريع
            success_count = 0
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(send_email_silent, t[0], t[1], t[2], t[3], t[4]): t for t in tasks}
                for future in as_completed(futures):
                    if future.result():
                        success_count += 1
                        
            print(print(f"✅ [Worker] تم إرسال دفعة بنجاح: {success_count} إيميل. المؤشر الحالي: {current_idx}"))
            time.sleep(2) # راحة قصيرة بين الدفعات
            
        except Exception as e:
            print(f"⚠️ خطأ في حلقة التشغيل: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_background_outreach()
