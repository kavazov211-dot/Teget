import telebot
from telebot import types
import sqlite3
from datetime import datetime
import pytz  # <--- Vaqt zonasini to'g'irlash uchun kutubxona

# Bot tokeningizni shu yerga yozing
TOKEN = "8590881933:AAEaQU09nxXQ9wVAfNMeuqKL3rccRnWEmLE"
bot = telebot.TeleBot(TOKEN)

# ---- MA'LUMOTLAR BAZASI BILAN ISHLASH ----
def init_db():
    conn = sqlite3.connect("poetry_bot.db")
    cursor = conn.cursor()
    # SQLite da ON DELETE CASCADE ishlashi uchun PRAGMA ni yoqamiz
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Profil jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        author_name TEXT,
        password TEXT
    )
    """)
    # Sherlar jadvali (ON DELETE CASCADE qo'shildi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS poems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER,
        poem_title TEXT,
        poem_text TEXT,
        created_at TEXT,
        FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE
    )
    """)
    
    # 🛠 AGAR ESKI BAZA BO'LSA, MAJBURIY RAVISHDA created_at USTUNINI QO'SHISH
    try:
        cursor.execute("ALTER TABLE poems ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

init_db()

# Foydalanuvchilarning bosqichlarini saqlash
user_steps = {}

# ---- ASOSIY MENU ----
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("➕ Yangi profil ochish", callback_data="create_profile")
    btn2 = types.InlineKeyboardButton("📝 Mavjud profilga she'r qo'shish", callback_data="add_poem_start")
    btn3 = types.InlineKeyboardButton("📚 Shoirlar profillari", callback_data="view_profiles")
    btn4 = types.InlineKeyboardButton("❌ Profilni o'chirish", callback_data="delete_profile_start")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ---- /START BUYRUG'I ----
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        f"Assalomu alaykum, {message.from_user.full_name}!\n"
        "Sheriy botimizga xush kelibsiz. Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu()
    )

# ---- INLINE TUGMALARNI ESHITISH ----
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    
    # PROFIL YARATISH
    if call.data == "create_profile":
        bot.send_message(chat_id, "Iltimos, shoir (profil) nomini kiriting:")
        user_steps[chat_id] = {"step": "get_name"}
        bot.answer_callback_query(call.id)
        
    # YANGI SHE'R QO'SHISH BOSHLANISHI
    elif call.data == "add_poem_start":
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, author_name FROM profiles")
        profiles = cursor.fetchall()
        conn.close()
        
        if not profiles:
            bot.send_message(chat_id, "Hozircha hech qanday profil ochilmagan. Avval profil oching.", reply_markup=main_menu())
            bot.answer_callback_query(call.id)
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        for prof_id, name in profiles:
            markup.add(types.InlineKeyboardButton(f"✍️ {name}", callback_data=f"addto_{prof_id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_menu"))
        
        bot.edit_message_text("Qaysi profilga she'r qo'shmoqchisiz? Tanlang:", chat_id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # SHOIR TANLANGANDAN KEYIN PAROL SO'RASH (SHE'R QO'SHISH UCHUN)
    elif call.data.startswith("addto_"):
        profile_id = int(call.data.split("_")[1])
        user_steps[chat_id] = {"step": "check_password", "profile_id": profile_id}
        bot.send_message(chat_id, "Ushbu profil parolini kiriting:")
        bot.answer_callback_query(call.id)
        
    # PROFILLARI KO'RISH
    elif call.data == "view_profiles":
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, author_name FROM profiles")
        profiles = cursor.fetchall()
        conn.close()
        
        if not profiles:
            bot.send_message(chat_id, "Hozircha hech qanday profil ochilmagan.", reply_markup=main_menu())
            bot.answer_callback_query(call.id)
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        for prof_id, name in profiles:
            markup.add(types.InlineKeyboardButton(f"✍️ {name}", callback_data=f"prof_{prof_id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_menu"))
        
        bot.edit_message_text("Ochilgan shoirlar profillari ro'yxati:", chat_id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        
    # SHOIRNING SHE'RLARI RO'YXATI
    elif call.data.startswith("prof_"):
        profile_id = int(call.data.split("_")[1])
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT author_name FROM profiles WHERE id = ?", (profile_id,))
        author_res = cursor.fetchone()
        if not author_res:
            bot.send_message(chat_id, "Profil topilmadi.", reply_markup=main_menu())
            conn.close()
            return
        author_name = author_res[0]
        cursor.execute("SELECT id, poem_title FROM poems WHERE profile_id = ?", (profile_id,))
        poems = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for poem_id, title in poems:
            markup.add(types.InlineKeyboardButton(f"📜 {title}", callback_data=f"poem_{poem_id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Shoirlarga qaytish", callback_data="view_profiles"))
        
        bot.edit_message_text(f"✨ *{author_name}* ijodiga mansub she'rlar:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    # SHE'RNI KO'RSATISH
    elif call.data.startswith("poem_"):
        poem_id = int(call.data.split("_")[1])
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT poems.poem_title, poems.poem_text, poems.created_at, profiles.author_name, profiles.id
            FROM poems 
            JOIN profiles ON poems.profile_id = profiles.id 
            WHERE poems.id = ?
        """, (poem_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            title, text, created_at, author, prof_id = res
            time_str = created_at if created_at else "Noma'lum"
            
            response_text = (
                f"📌 *Mavzu:* {title}\n"
                f"✍️ *Muallif:* {author}\n"
                f"📅 *Yuklangan vaqti:* {time_str}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"{text}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"ℹ️ _Ushbu she'r bot foydalanuvchisi tomonidan yuklangan._"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⬅️ She'rlar ro'yxatiga qaytish", callback_data=f"prof_{prof_id}"))
            bot.edit_message_text(response_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # PROFIL O'CHIRISH BOSHLANISHI
    elif call.data == "delete_profile_start":
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, author_name FROM profiles")
        profiles = cursor.fetchall()
        conn.close()
        
        if not profiles:
            bot.send_message(chat_id, "Hozircha o'chirish uchun hech qanday profil yo'q.", reply_markup=main_menu())
            bot.answer_callback_query(call.id)
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        for prof_id, name in profiles:
            markup.add(types.InlineKeyboardButton(f"🗑 {name}", callback_data=f"delto_{prof_id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_menu"))
        
        bot.edit_message_text("Qaysi profilni o'chirmoqchisiz? Tanlang:", chat_id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # O'CHIRILADIGAN PROFIL TANLANGANDAN KEYIN PAROL SO'RASH
    elif call.data.startswith("delto_"):
        profile_id = int(call.data.split("_")[1])
        user_steps[chat_id] = {"step": "delete_check_password", "profile_id": profile_id}
        bot.send_message(chat_id, "⚠️ Diqqat! Ushbu profilni butunlay o'chirish uchun parolini kiriting:")
        bot.answer_callback_query(call.id)

    elif call.data == "back_to_menu":
        bot.edit_message_text("Asosiy menu:", chat_id, call.message.message_id, reply_markup=main_menu())
        bot.answer_callback_query(call.id)

# ---- MATNLARNI QABUL QILISH ----
@bot.message_handler(func=lambda message: message.chat.id in user_steps)
def handle_steps(message):
    chat_id = message.chat.id
    step_data = user_steps[chat_id]
    
    # --- PROFIL OCHISH BOSQICHLARI ---
    if step_data["step"] == "get_name":
        user_steps[chat_id]["author_name"] = message.text
        user_steps[chat_id]["step"] = "get_password"
        bot.send_message(chat_id, "Profil uchun parol o'ylab toping va kiriting:")
        
    elif step_data["step"] == "get_password":
        user_steps[chat_id]["password"] = message.text
        user_steps[chat_id]["step"] = "get_poem_title"
        bot.send_message(chat_id, "Ajoyib! Endi ilk she'ringizning **nomini (sarlavhasini)** kiriting:")
        
    elif step_data["step"] == "get_poem_title":
        user_steps[chat_id]["poem_title"] = message.text
        user_steps[chat_id]["step"] = "get_poem_text"
        bot.send_message(chat_id, "Endi esa she'rning **matnini (o'zini)** yuboring:")
        
    elif step_data["step"] == "get_poem_text":
        poem_text = message.text
        author_name = step_data["author_name"]
        password = step_data["password"]
        poem_title = step_data["poem_title"]
        
        # 🟢 Toshkent vaqt zonasi bo'yicha vaqtni olish
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tashkent_tz).strftime("%d.%m.%Y %H:%M")
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO profiles (user_id, author_name, password) VALUES (?, ?, ?)", (message.from_user.id, author_name, password))
        profile_id = cursor.lastrowid
        cursor.execute("INSERT INTO poems (profile_id, poem_title, poem_text, created_at) VALUES (?, ?, ?, ?)", (profile_id, poem_title, poem_text, now))
        conn.commit()
        conn.close()
        
        del user_steps[chat_id]
        bot.send_message(chat_id, f"🎉 Tabriklaymiz! *{author_name}* profili ochildi va birinchi she'r joylandi!", reply_markup=main_menu(), parse_mode="Markdown")

    # --- MAVJUD PROFILGA SHE'R QO'SHISH BOSQICHLARI ---
    elif step_data["step"] == "check_password":
        input_pass = message.text
        prof_id = step_data["profile_id"]
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password, author_name FROM profiles WHERE id = ?", (prof_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res and res[0] == input_pass:
            user_steps[chat_id]["author_name"] = res[1]
            user_steps[chat_id]["step"] = "add_poem_title"
            bot.send_message(chat_id, "🔒 Parol to'g'ri! Endi yangi she'ringizning **nomini (sarlavhasini)** kiriting:")
        else:
            del user_steps[chat_id]
            bot.send_message(chat_id, "❌ Parol noto'g'ri! Xavfsizlik yuzasidan jarayon bekor qilindi.", reply_markup=main_menu())

    elif step_data["step"] == "add_poem_title":
        user_steps[chat_id]["new_poem_title"] = message.text
        user_steps[chat_id]["step"] = "add_poem_text"
        bot.send_message(chat_id, "Endi she'rning **matnini (o'zini)** yuboring:")

    elif step_data["step"] == "add_poem_text":
        new_text = message.text
        title = step_data["new_poem_title"]
        prof_id = step_data["profile_id"]
        author = step_data["author_name"]
        
        # 🟢 Toshkent vaqt zonasi bo'yicha vaqtni olish
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tashkent_tz).strftime("%d.%m.%Y %H:%M")
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM poems 
            WHERE profile_id = ? AND poem_title = ? AND poem_text = ?
        """, (prof_id, title, new_text))
        
        existing_poem = cursor.fetchone()
        
        if existing_poem:
            conn.close()
        else:
            cursor.execute("INSERT INTO poems (profile_id, poem_title, poem_text, created_at) VALUES (?, ?, ?, ?)", (prof_id, title, new_text, now))
            conn.commit()
            conn.close()
            
        del user_steps[chat_id]
        bot.send_message(chat_id, f"✅ *{author}* profiliga yangi \"{title}\" nomli she'r muvaffaqiyatli qo'shildi!", reply_markup=main_menu(), parse_mode="Markdown")

    # --- PROFILNI PAROL BILAN O'CHIRISH BOSQICHI ---
    elif step_data["step"] == "delete_check_password":
        input_pass = message.text
        prof_id = step_data["profile_id"]
        
        conn = sqlite3.connect("poetry_bot.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("SELECT password, author_name FROM profiles WHERE id = ?", (prof_id,))
        res = cursor.fetchone()
        
        if res and res[0] == input_pass:
            author_name = res[1]
            cursor.execute("DELETE FROM profiles WHERE id = ?", (prof_id,))
            conn.commit()
            conn.close()
            
            del user_steps[chat_id]
            bot.send_message(chat_id, f"🗑 *{author_name}* profili va unga tegishli barcha she'rlar butunlay o'chirib tashlandi!", reply_markup=main_menu(), parse_mode="Markdown")
        else:
            conn.close()
            del user_steps[chat_id]
            bot.send_message(chat_id, "❌ Parol noto'g'ri! Profilni o'chirish rad etildi.", reply_markup=main_menu())

# ---- BOTNI ISHGA TUSHIRISH ----
if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()
