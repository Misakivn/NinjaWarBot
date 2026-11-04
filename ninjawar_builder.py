# -*- coding: utf-8 -*-
"""
NINJA WAR - DISCORD SERVER BUILDER (v6 · thêm lệnh !code xem giftcode)
==============================================================================
Cách dùng nhanh:
  1. pip install -r requirements.txt        (discord.py>=2.4, python-dotenv)
  2. Tạo file .env cạnh file này, nội dung 1 dòng:   DISCORD_TOKEN=token_của_bạn
  3. Discord Developer Portal -> Bot -> bật "Server Members Intent" & "Message Content Intent"
  4. python ninjawar_builder.py
  5. Trong server, CHỦ SERVER gõ:  !xaykenh

Cơ chế ngôn ngữ:
  - Người mới vào chỉ thấy kênh 🌐-ngôn-ngữ · language, bấm 🇻🇳 Tiếng Việt hoặc 🇬🇧 English.
  - Chọn Tiếng Việt: chỉ thấy các kênh tiếng Việt. Chọn English: chỉ thấy các kênh tiếng Anh.
  - Staff thấy cả hai. Bấm lại nút khác để đổi ngôn ngữ bất cứ lúc nào.

Điểm mới bản v5:
  - Chống bấm đúp (Race Condition Lock) khi mở/đóng Ticket, tránh tạo trùng phòng hoặc gửi trùng log.
  - Bộ nhớ đệm Cooldown trên RAM & SQLite WAL mode giúp bot mượt mà khi server chat đông.
  - Tự động đồng bộ lại cả slowmode_delay của các kênh cũ khi chạy lại !xaykenh.
  - Tự động giới hạn an toàn 2000 ký tự khi đăng/sửa bài mẫu, tránh lỗi văng giữa chừng.
  - Bật Server Members Intent giúp lệnh !rank @user tra cứu chính xác mọi thành viên.
Điểm mới bản v6:
  - !code: bot gửi tin nhắn riêng danh sách giftcode còn hạn cho người gõ lệnh.
  - !themcode / !xoacode: staff thêm, xóa giftcode; bot tự đăng code mới ở kênh giftcode.
  - Tin nhắn lệnh (bắt đầu bằng "!") không còn được tính vào cấp bậc.
"""
import asyncio
import datetime as dt
import io
import logging
import os
import sqlite3
import time

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # không có python-dotenv thì đọc biến môi trường hệ thống
    pass

log = logging.getLogger("ninjawar")
TOKEN = os.getenv("DISCORD_TOKEN")
REASON = "Ninja War Discord Builder"
PO = discord.PermissionOverwrite

# =====================================================================
# 1. NỘI DUNG - CHỈNH Ở ĐÂY (không cần đụng vào phần code bên dưới)
#    MSG_* = bài tiếng Việt · EN_* = bài tiếng Anh. Mỗi bài tối đa 2000 ký tự.
# =====================================================================

# ---- Kênh chọn ngôn ngữ (ai cũng thấy, nên viết cả hai thứ tiếng) ----
MSG_LANG = (
    "# 🌐 NGÔN NGỮ · LANGUAGE\n"
    "🇻🇳 Chọn ngôn ngữ để mở các kênh của bạn. Bấm nút kia để đổi bất cứ lúc nào.\n"
    "🇬🇧 Choose your language to unlock your channels. Press the other button to switch any time."
)

# ---- TIẾNG VIỆT ----
MSG_VERIFY = (
    "# ✅ XÁC MINH NHẪN GIẢ\n"
    "Đọc kỹ `📜-nội-quy`, rồi bấm nút bên dưới để mở khóa toàn bộ kênh chat.\n"
    "> ⚠️ Staff **không bao giờ** nhắn riêng trước hay hỏi mật khẩu/OTP."
)
MSG_PING = (
    "# 🔔 NHẬN THÔNG BÁO\n"
    "Bấm để bật/tắt role nhắc nhở (bấm lần nữa để gỡ). Cần xác minh trước."
)
MSG_NOIQUY = (
    "# 📜 NỘI QUY LÀNG LÁ\n"
    "1. Tôn trọng mọi người: không chửi bới, kỳ thị, công kích cá nhân.\n"
    "2. Cấm quảng cáo server/game khác, cấm spam, cấm gửi link lạ.\n"
    "3. Cấm lợi dụng lỗi (bug) game. Gặp lỗi hãy báo tại `🐛-báo-lỗi-game`.\n"
    "4. Vấn đề nạp thẻ/tài khoản chỉ xử lý qua Ticket, không nhờ staff qua tin nhắn riêng.\n"
    "5. Quyết định của Anbu/Hokage là quyết định cuối cùng.\n"
    "> Vi phạm: nhắc nhở → timeout → ban."
)
MSG_THONGBAO = (
    "# 📢 THÔNG BÁO\n"
    "Cập nhật phiên bản, bảo trì và sự kiện sẽ được đăng tại đây."
)
MSG_LICH = (
    "# 📅 LỊCH HOẠT ĐỘNG (GIỜ VN · GMT+7)\n"
    "* **20:00** – Chốt bảng xếp hạng Tranh Bá\n"
    "* **20:30** – Phát thư thưởng\n"
    "* **Khóa đấu trường:** 20:00–21:00 và 23:00–07:00"
)
MSG_TAIGAME = (
    "# 📥 TẢI GAME\n"
    "* 🤖 Android: _(staff cập nhật link)_\n"
    "* 🍎 iOS: _(staff cập nhật link)_\n"
    "> Chỉ tải từ link đăng tại kênh này. Link ở nơi khác có thể là lừa đảo."
)
MSG_GIFTCODE = (
    "# 🎁 GIFTCODE\n"
    "Staff đăng code mới tại đây. Bật role 🔔 Ping Giftcode ở `✅-xác-minh` để được báo.\n"
    "> Gõ `!code` ở kênh chat bất kỳ, bot sẽ gửi riêng cho bạn danh sách code còn hạn."
)
MSG_NAPTHE = (
    "# 💎 QUY ĐỊNH NẠP THẺ\n"
    "1. Chỉ nạp qua Ticket tại `🎫-mở-ticket`. Staff không nhận nạp qua tin nhắn riêng.\n"
    "2. Chuẩn bị: tên nhân vật, server, gói nạp, ảnh biên lai.\n"
    "3. Chỉ chuyển khoản vào tài khoản staff gửi **trong Ticket**. Thông tin thanh toán không đăng công khai.\n"
    "> ⚠️ Giao dịch ngoài Ticket sẽ không được hỗ trợ."
)
MSG_ANTISCAM = (
    "# ⚠️ CHỐNG LỪA ĐẢO\n"
    "* Staff **không bao giờ** nhắn riêng trước hoặc hỏi mật khẩu/OTP/mã xác minh.\n"
    "* Staff thật có role 👑 Hokage / 🛡️ Anbu / 💳 Hỗ Trợ Viên.\n"
    "* Không bấm link lạ, không tải APK ngoài `📥-tải-game`.\n"
    "* Gặp kẻ mạo danh: chụp ảnh và báo qua Ticket."
)
MSG_HOCVIEN = "🏫 **[HỌC VIỆN NHẪN GIẢ]** Giáo trình tân thủ, mẹo vượt tháp, cách dùng bí kíp và tối ưu tài nguyên."
MSG_BANDO = "🗺️ **[BẢN ĐỒ LÀNG LÁ]** Lộ trình thăng cấp và mốc thời gian các hoạt động quan trọng."
MSG_THUVIEN = "📚 **[NHẪN GIẢ THƯ VIỆN]** Đánh giá kỹ năng tướng, phân tích sức mạnh và công thức đội hình công/thủ."
MSG_NHATKY = "📖 **[NHẬT KÝ CẤM THUẬT]** Cập nhật phiên bản, sửa lỗi và cân bằng chỉ số game."
MSG_LAB = "🧪 **[PHÒNG THÍ NGHIỆM]** Hé lộ tính năng, tướng mới và bản thử nghiệm trước khi cập nhật chính thức."
MSG_COUNCIL = "🏛️ **[HỘI ĐỒNG LÀNG LÁ]** Góp ý tính năng và biểu quyết cùng cộng đồng."
MSG_TICKET = (
    "# 🎫 HỖ TRỢ 1-1\n"
    "Bấm nút bên dưới để mở phòng riêng với staff: nạp thẻ, mất tài khoản, lỗi nghiêm trọng."
)
MSG_BAOLOI = (
    "# 🐛 BÁO LỖI\n"
    "Mẫu: **Thiết bị** (Android/iOS) · **Tính năng** · **Các bước tái hiện** · **Ảnh/video**."
)
MSG_HOIDAP = "# ❓ HỎI ĐÁP\nHỏi về cách chơi, đội hình, tính năng. Hãy tìm trong kênh trước khi hỏi nhé!"
MSG_GIAODICH = (
    "# 🛒 GIAO DỊCH\n"
    "> ⚠️ Không chuyển tiền trước cho người lạ. Staff không chịu trách nhiệm cho giao dịch giữa người chơi."
)

# ---- ENGLISH ----
EN_VERIFY = (
    "# ✅ VERIFY\n"
    "Read `📜-rules`, then press the button below to unlock all chat channels.\n"
    "> ⚠️ Staff will **never** DM you first or ask for your password/OTP."
)
EN_PING = (
    "# 🔔 NOTIFICATIONS\n"
    "Press to get pinged for new gift codes or events (press again to stop). Verify first."
)
EN_RULES = (
    "# 📜 SERVER RULES\n"
    "1. Be respectful: no insults, hate speech or personal attacks.\n"
    "2. No advertising other servers/games, no spam, no unknown links.\n"
    "3. Don't exploit game bugs. Report them in `🐛-bug-reports`.\n"
    "4. Top-up and account issues are handled only through tickets, never by DM.\n"
    "5. Staff decisions (Anbu/Hokage) are final.\n"
    "> Penalties: warning → timeout → ban."
)
EN_ANNOUNCE = (
    "# 📢 ANNOUNCEMENTS\n"
    "Game updates, maintenance and events are posted here."
)
EN_SCHEDULE = (
    "# 📅 SCHEDULE (VIETNAM TIME · UTC+7)\n"
    "* **20:00** – Arena ranking closes\n"
    "* **20:30** – Rewards sent by mail\n"
    "* **Arena locked:** 20:00–21:00 and 23:00–07:00\n"
    "> All times are Vietnam time (UTC+7). Please convert to your own time zone."
)
EN_DOWNLOAD = (
    "# 📥 DOWNLOAD\n"
    "* 🤖 Android: _(link coming soon)_\n"
    "* 🍎 iOS: _(link coming soon)_\n"
    "> Only download from the links in this channel. Links anywhere else may be scams."
)
EN_GIFTCODE = (
    "# 🎁 GIFT CODES\n"
    "New gift codes are posted here. Turn on 🔔 notifications in `✅-verify` to get pinged.\n"
    "> Type `!code` in any chat channel and the bot will DM you every active code."
)
EN_TOPUP = (
    "# 💎 TOP-UP RULES\n"
    "1. Top up only through a ticket in `🎫-open-ticket`. Staff never accept top-ups by DM.\n"
    "2. Have ready: character name, server, package and payment receipt.\n"
    "3. Only pay to the details staff send **inside your ticket**. Payment details are never posted publicly.\n"
    "> ⚠️ Payments made outside a ticket cannot be supported."
)
EN_ANTISCAM = (
    "# ⚠️ ANTI-SCAM\n"
    "* Staff will **never** DM you first or ask for your password, OTP or verification code.\n"
    "* Real staff have the 👑 Hokage, 🛡️ Anbu or 💳 Hỗ Trợ Viên (support) role.\n"
    "* Don't click unknown links or install APKs from anywhere except `📥-download`.\n"
    "* Found an impersonator? Take a screenshot and report it in a ticket."
)
EN_ACADEMY = "🏫 **[ACADEMY]** Beginner guides, tower tips, skill books and resource planning."
EN_ROADMAP = "🗺️ **[ROADMAP]** Levelling path and the timing of key activities."
EN_LIBRARY = "📚 **[HERO LIBRARY]** Hero skill reviews, power analysis and attack/defence team builds."
EN_PATCH = "📖 **[PATCH NOTES]** Version updates, bug fixes and balance changes."
EN_PEEK = "🧪 **[SNEAK PEEKS]** New features, new heroes and test builds before official release."
EN_COUNCIL = "🏛️ **[COUNCIL]** Suggest features and vote with the community."
EN_TICKET = (
    "# 🎫 PRIVATE SUPPORT\n"
    "Press a button below to open a private room with staff: top-up, lost account or serious bugs.\n"
    "> Staff may reply with a translator, so short, simple sentences help."
)
EN_BUGS = (
    "# 🐛 BUG REPORTS\n"
    "Template: **Device** (Android/iOS) · **Feature** · **Steps to reproduce** · **Screenshot/video**."
)
EN_HELP = "# ❓ HELP\nQuestions about gameplay, teams and features. Please search the channel before asking!"
EN_TRADE = (
    "# 🛒 TRADING\n"
    "> ⚠️ Never pay strangers first. Staff are not responsible for trades between players."
)

# ---------------------------------------------------------------------
# NÚT BẤM: (custom_id, emoji, chữ trên nút, màu). Không đổi custom_id
# (nếu đổi, các nút đã đăng trước đó sẽ ngừng hoạt động).
# ---------------------------------------------------------------------
BUTTONS = {
    "lang": [("nw:lang_vi", "🇻🇳", "Tiếng Việt", "primary"),
             ("nw:lang_en", "🇬🇧", "English", "primary")],
    # Tiếng Việt
    "verify": [("nw:verify", "✅", "Tôi đã đọc luật - Vào Làng Lá", "success")],
    "ping": [("nw:ping_gift", "🔔", "Báo Giftcode", "secondary"),
             ("nw:ping_event", "⏰", "Báo Hoạt động", "secondary")],
    "ticket": [("nw:ticket_nap", "💳", "Nạp thẻ", "success"),
               ("nw:ticket_hotro", "🆘", "Hỗ trợ", "primary")],
    "close": [("nw:ticket_close", "🔒", "Đóng ticket", "danger")],
    # English
    "en_verify": [("nw:verify_en", "✅", "I've read the rules", "success")],
    "en_ping": [("nw:en_ping_gift", "🔔", "Gift codes", "secondary"),
                ("nw:en_ping_event", "⏰", "Events", "secondary")],
    "en_ticket": [("nw:en_ticket_topup", "💳", "Top-up", "success"),
                  ("nw:en_ticket_support", "🆘", "Support", "primary")],
    "en_close": [("nw:en_ticket_close", "🔒", "Close ticket", "danger")],
}

# Loại ticket -> (ngôn ngữ, lời mở đầu)
TICKET_KINDS = {
    "nap": ("vi",
            "💳 **TICKET NẠP THẺ**\n"
            "Vui lòng gửi: **tên nhân vật**, **server**, **gói nạp** và **ảnh biên lai** (nếu đã chuyển).\n"
            "> ⚠️ Chỉ chuyển khoản theo thông tin staff gửi **trong ticket này**. "
            "Không chuyển cho bất kỳ ai nhắn riêng."),
    "hotro": ("vi",
              "🆘 **TICKET HỖ TRỢ**\n"
              "Hãy mô tả vấn đề: **tên nhân vật**, **thiết bị** (Android/iOS), chuyện gì xảy ra "
              "và **ảnh/video** nếu có.\n"
              "> ⚠️ Staff không bao giờ hỏi mật khẩu hoặc mã OTP."),
    "topup": ("en",
              "💳 **TOP-UP TICKET**\n"
              "Please send: **character name**, **server**, **package** and **receipt** (if already paid).\n"
              "> ⚠️ Only pay using the details staff send **in this ticket**. Never pay anyone who DMs you."),
    "support": ("en",
                "🆘 **SUPPORT TICKET**\n"
                "Describe the problem: **character name**, **device** (Android/iOS), what happened, "
                "and a **screenshot/video** if you have one.\n"
                "> ⚠️ Staff will never ask for your password or OTP."),
}

# Câu trả lời của bot theo ngôn ngữ
TXT = {
    "vi": {
        "lang_set": "🇻🇳 Đã chọn **Tiếng Việt**. Vào `✅-xác-minh` để bắt đầu nhé!",
        "not_verified": "Hãy bấm ✅ xác minh ở kênh `✅-xác-minh` trước nhé!",
        "already": "Bạn đã là Nhẫn Giả rồi 🥷",
        "welcome": "🎉 Chào mừng Nhẫn Giả! Các kênh chat đã được mở khóa.",
        "added": "Đã bật: **{label}** ✅", "removed": "Đã tắt: **{label}**.",
        "no_role": "⚠️ Chưa có role này, hãy báo staff.",
        "no_perm": "⚠️ Bot chưa đủ quyền gán role. Hãy báo staff.",
        "has_ticket": "Bạn đang có ticket mở: {ch}", "ticket_ok": "✅ Đã mở ticket: {ch}",
        "ticket_opening": "⏳ Đang khởi tạo ticket của bạn, vui lòng đợi giây lát...",
        "ticket_fail": "⚠️ Không tạo được ticket. Hãy báo staff.",
        "no_ticket_cat": "⚠️ Chưa có danh mục ticket. Hãy báo staff.",
        "not_ticket": "⚠️ Đây không phải kênh ticket.",
        "close_denied": "⛔ Chỉ người mở ticket hoặc staff mới đóng được.",
        "closing": "🔒 Đang lưu transcript, ticket sẽ đóng sau 5 giây...",
        "already_closing": "⏳ Ticket này đang trong quá trình đóng...",
        "levelup": "🎉 {user} đã thăng cấp **{rank}**! ({n} tin nhắn)",
        "rank": "🥷 **{name}** · Cấp bậc: **{rank}** · {n} tin nhắn",
        "next": "⏭️ Còn **{left}** tin nhắn nữa để lên **{rank}**", "max": "🏆 Đã đạt cấp cao nhất!",
        "top_title": "# 🏆 BẢNG XẾP HẠNG NHẪN GIẢ", "top_empty": "Chưa có ai trên bảng xếp hạng.",
        "academy": "Học Viên", "unit": "tin nhắn",
        "code_title": "# 🎁 GIFTCODE ĐANG HOẠT ĐỘNG",
        "code_none": "Hiện chưa có giftcode nào còn hạn. Bật 🔔 Ping Giftcode ở `✅-xác-minh` để được báo khi có code mới.",
        "code_exp": "HSD: {d} (còn {n} ngày)", "code_today": "HSD: hết hôm nay", "code_noexp": "không thời hạn",
        "code_foot": "> Chạm giữ vào code để sao chép.",
        "code_sent": "📬 {user} bot đã gửi danh sách giftcode vào tin nhắn riêng của bạn.",
        "code_dm_fail": "⚠️ {user} bot không gửi tin nhắn riêng cho bạn được. Hãy bật **Tin nhắn trực tiếp** từ thành viên server (Cài đặt quyền riêng tư của server) rồi gõ lại `!code`.",
        "code_new": "🔔 {ping} **Giftcode mới:** `{code}`{reward}\n⏳ {exp}\n> Gõ `!code` ở kênh chat để xem tất cả code còn hạn.",
    },
    "en": {
        "lang_set": "🇬🇧 **English** selected. Go to `✅-verify` to get started!",
        "not_verified": "Please verify in `✅-verify` first!",
        "already": "You're already verified 🥷",
        "welcome": "🎉 Welcome, shinobi! All chat channels are now unlocked.",
        "added": "Turned on: **{label}** ✅", "removed": "Turned off: **{label}**.",
        "no_role": "⚠️ This role doesn't exist yet. Please tell staff.",
        "no_perm": "⚠️ The bot can't assign roles yet. Please tell staff.",
        "has_ticket": "You already have an open ticket: {ch}", "ticket_ok": "✅ Ticket opened: {ch}",
        "ticket_opening": "⏳ Creating your ticket, please wait a moment...",
        "ticket_fail": "⚠️ Couldn't open a ticket. Please tell staff.",
        "no_ticket_cat": "⚠️ The ticket category is missing. Please tell staff.",
        "not_ticket": "⚠️ This is not a ticket channel.",
        "close_denied": "⛔ Only the ticket owner or staff can close it.",
        "closing": "🔒 Saving the transcript, closing in 5 seconds...",
        "already_closing": "⏳ This ticket is already closing...",
        "levelup": "🎉 {user} ranked up to **{rank}**! ({n} messages)",
        "rank": "🥷 **{name}** · Rank: **{rank}** · {n} messages",
        "next": "⏭️ **{left}** more messages to reach **{rank}**", "max": "🏆 Highest rank reached!",
        "top_title": "# 🏆 LEADERBOARD", "top_empty": "The leaderboard is empty.",
        "academy": "Academy", "unit": "messages",
        "code_title": "# 🎁 ACTIVE GIFT CODES",
        "code_none": "There are no active gift codes right now. Turn on 🔔 notifications in `✅-verify` to get pinged for new ones.",
        "code_exp": "Expires: {d} ({n} days left)", "code_today": "Expires: end of today", "code_noexp": "no expiry",
        "code_foot": "> Long-press a code to copy it.",
        "code_sent": "📬 {user} the gift code list is in your DMs.",
        "code_dm_fail": "⚠️ {user} the bot can't DM you. Turn on **Direct Messages** from server members (server Privacy Settings) and type `!code` again.",
        "code_new": "🔔 {ping} **New gift code:** `{code}`{reward}\n⏳ {exp}\n> Type `!code` in a chat channel to see every active code.",
    },
}

# ---------------------------------------------------------------------
# CẤP BẬC NINJA THEO SỐ TIN NHẮN (chỉnh số mốc/tên/màu tại đây)
# (số tin nhắn tối thiểu, key, tên role, màu)
# Chỉ tính tin nhắn ở các danh mục COUNT_CATEGORIES, cách nhau >= COOLDOWN giây,
# dài >= MIN_LEN ký tự (chống spam để lên cấp).
# ---------------------------------------------------------------------
RANKS = [
    (50, "rank_genin", "🥋 Genin", 0xBDC3C7),
    (300, "rank_chunin", "⚔️ Chunin", 0x5DADE2),
    (1000, "rank_jonin", "🔥 Jonin", 0xAF7AC5),
    (3000, "rank_sannin", "🐍 Sannin", 0xF5B041),
]
RANK_ROLE_SPECS = [{"key": k, "name": n, "color": c} for _, k, n, c in RANKS][::-1]  # cao -> thấp
COUNT_CATEGORIES = ("community", "en_community")  # key danh mục được tính tin nhắn
COOLDOWN = 30   # giây giữa 2 tin nhắn được tính
MIN_LEN = 5     # độ dài tối thiểu của tin nhắn được tính

# ---------------------------------------------------------------------
# ROLE (xếp từ CAO xuống THẤP). perms = quyền cấp cho role.
# "old" = tên cũ: bot tìm theo tên cũ rồi đổi sang tên mới, không tạo trùng.
# Role dùng chung cho cả hai ngôn ngữ (Discord không cho 1 role có 2 tên).
# ---------------------------------------------------------------------
ROLE_SPECS = [
    {"key": "hokage", "name": "👑 Hokage (Admin)", "color": 0xFF2A2A, "hoist": True,
     "perms": discord.Permissions(administrator=True)},
    {"key": "dev", "name": "🔧 Dev Shinobi", "color": 0x9B59B6, "hoist": True,
     "perms": discord.Permissions(mention_everyone=True)},
    {"key": "anbu", "name": "🛡️ Anbu (Moderator)", "color": 0x3498DB, "hoist": True,
     "perms": discord.Permissions(manage_messages=True, kick_members=True,
                                  moderate_members=True, view_audit_log=True)},
    {"key": "support", "name": "💳 Hỗ Trợ Viên", "color": 0xE91E63, "hoist": True,
     "old": ["💳 Hỗ Trợ Viên (Support)"]},
    {"key": "vip", "name": "💎 Đại Gia Làng Lá (VIP)", "color": 0xF1C40F, "hoist": True},
    {"key": "ranker", "name": "🏆 Tam Nhẫn Bảng XH", "color": 0xE67E22, "hoist": True,
     "old": ["🏆 Tam Nhẫn Bảng XH (Top Rank)"]},
    {"key": "advisor", "name": "🧠 Quân Sư Nhẫn Giả", "color": 0x1ABC9C, "hoist": True,
     "old": ["🧠 Quân Sư Nhẫn Giả (Advisor)"]},
    *RANK_ROLE_SPECS,
    {"key": "member", "name": "🥷 Nhẫn Giả (Member)", "color": 0x2ECC71, "hoist": True},
    {"key": "member_en", "name": "🥷 Shinobi (Member)", "color": 0x2ECC71, "hoist": True},
    {"key": "lang_vi", "name": "🇻🇳 Tiếng Việt", "color": 0x95A5A6},
    {"key": "lang_en", "name": "🇬🇧 English", "color": 0x95A5A6, "old": ["🌏 International"]},
    {"key": "ping_gift", "name": "🔔 Ping Giftcode", "color": 0x95A5A6, "mentionable": True},
    {"key": "ping_event", "name": "⏰ Ping Event", "color": 0x95A5A6, "mentionable": True,
     "old": ["⏰ Ping Hoạt Động", "⏰ Ping Sự Kiện (Events)"]},
]
ROLE_BY_KEY = {r["key"]: r for r in ROLE_SPECS}
LANG_ROLE = {"vi": "lang_vi", "en": "lang_en"}
MEMBER_ROLE = {"vi": "member", "en": "member_en"}

# ---------------------------------------------------------------------
# DANH MỤC & KÊNH
# "lang": "vi" / "en" = chỉ người chọn ngôn ngữ đó (và staff) thấy; None = dùng chung.
# KIỂU TRUY CẬP ("access"):
#   open         : ai cũng thấy (kể cả người mới), chỉ staff đăng
#   info         : người đã chọn ngôn ngữ thấy (chỉ đọc), staff đăng
#   members_info : người đã xác minh (cùng ngôn ngữ) thấy, chỉ đọc
#   members_chat : người đã xác minh (cùng ngôn ngữ) chat được
#   staff        : chỉ staff thấy
# Danh mục: "key" (không đổi), "name", "old" (tên cũ để đổi tên).
# Kênh: "access" ghi đè, "slow" = slowmode (giây), "kind": "voice",
# "msgs" = bài đăng sẵn; tuple (nội dung, loại nút) để kèm nút bấm.
# ---------------------------------------------------------------------
LAYOUT = [
    {"key": "lang", "lang": None, "name": "🌐 NGÔN NGỮ · LANGUAGE", "access": "open", "channels": [
        {"name": "🌐-ngôn-ngữ-language", "msgs": [(MSG_LANG, "lang")]},
    ]},
    # ======================= TIẾNG VIỆT =======================
    {"key": "info", "lang": "vi", "name": "📌 THÔNG TIN QUAN TRỌNG", "old": ["📌 THÔNG TIN QUAN TRỌNG · INFO"],
     "access": "info", "channels": [
        {"name": "✅-xác-minh", "msgs": [(MSG_VERIFY, "verify"), (MSG_PING, "ping")]},
        {"name": "📜-nội-quy", "msgs": [MSG_NOIQUY]},
        {"name": "📢-thông-báo", "msgs": [MSG_THONGBAO]},
        {"name": "📅-lịch-sự-kiện", "msgs": [MSG_LICH]},
        {"name": "📥-tải-game", "msgs": [MSG_TAIGAME]},
        {"name": "🎁-giftcode", "msgs": [MSG_GIFTCODE]},
        {"name": "💎-quy-định-nạp-thẻ", "msgs": [MSG_NAPTHE]},
        {"name": "⚠️-chống-lừa-đảo", "msgs": [MSG_ANTISCAM]},
    ]},
    {"key": "academy", "lang": "vi", "name": "⛩️ HỌC VIỆN LÀNG LÁ", "old": ["⛩️ HỌC VIỆN LÀNG LÁ · ACADEMY"],
     "access": "members_info", "channels": [
        {"name": "🏫-học-viện-nhẫn-giả", "msgs": [MSG_HOCVIEN]},
        {"name": "🗺️-bản-đồ-làng-lá", "msgs": [MSG_BANDO]},
        {"name": "📚-nhẫn-giả-thư-viện", "msgs": [MSG_THUVIEN]},
    ]},
    {"key": "dev", "lang": "vi", "name": "🏯 CƠ QUAN PHÁT TRIỂN", "old": ["🏯 CƠ QUAN PHÁT TRIỂN · DEV"],
     "access": "members_info", "channels": [
        {"name": "📖-nhật-ký-cấm-thuật", "msgs": [MSG_NHATKY]},
        {"name": "🧪-phòng-thí-nghiệm", "msgs": [MSG_LAB]},
        {"name": "🏛️-hội-đồng-làng-lá", "access": "members_chat", "slow": 10, "msgs": [MSG_COUNCIL]},
    ]},
    {"key": "support", "lang": "vi", "name": "🛠️ KHU VỰC HỖ TRỢ", "old": ["🛠️ KHU VỰC HỖ TRỢ · SUPPORT"],
     "access": "members_chat", "channels": [
        {"name": "🎫-mở-ticket", "access": "members_info", "msgs": [(MSG_TICKET, "ticket")]},
        {"name": "🐛-báo-lỗi-game", "slow": 30, "msgs": [MSG_BAOLOI]},
        {"name": "❓-hỏi-đáp", "slow": 10, "msgs": [MSG_HOIDAP]},
    ]},
    {"key": "community", "lang": "vi", "name": "💬 CỘNG ĐỒNG NHẪN GIẢ",
     "old": ["💬 CỘNG ĐỒNG NHẪN GIẢ · COMMUNITY"], "access": "members_chat", "channels": [
        {"name": "💬-sảnh-nhẫn-giả", "slow": 5},
        {"name": "⚔️-bàn-luận-đội-hình"},
        {"name": "📸-khoe-nhân-phẩm", "slow": 10},
        {"name": "🏆-tranh-bá-xếp-hạng"},
        {"name": "🏯-tìm-guild"},
        {"name": "🛒-giao-dịch", "slow": 30, "msgs": [MSG_GIAODICH]},
    ]},
    {"key": "voice", "lang": "vi", "name": "🔊 ĐÀM ĐẠO & CANH GIỜ", "old": ["🔊 ĐÀM ĐẠO & CANH GIỜ · VOICE"],
     "access": "members_chat", "channels": [
        {"name": "🔊 Đàm Đạo Chung", "kind": "voice"},
        {"name": "⚔️ Canh Giờ Chốt Hạng", "kind": "voice"},
    ]},
    # ======================= ENGLISH =======================
    {"key": "en_info", "lang": "en", "name": "📌 INFORMATION", "access": "info", "channels": [
        {"name": "✅-verify", "msgs": [(EN_VERIFY, "en_verify"), (EN_PING, "en_ping")]},
        {"name": "📜-rules", "msgs": [EN_RULES]},
        {"name": "📢-announcements", "msgs": [EN_ANNOUNCE]},
        {"name": "📅-schedule", "msgs": [EN_SCHEDULE]},
        {"name": "📥-download", "msgs": [EN_DOWNLOAD]},
        {"name": "🎁-gift-codes", "msgs": [EN_GIFTCODE]},
        {"name": "💎-top-up-rules", "msgs": [EN_TOPUP]},
        {"name": "⚠️-anti-scam", "msgs": [EN_ANTISCAM]},
    ]},
    {"key": "en_academy", "lang": "en", "name": "⛩️ LEAF VILLAGE ACADEMY", "access": "members_info", "channels": [
        {"name": "🏫-beginner-guide", "msgs": [EN_ACADEMY]},
        {"name": "🗺️-roadmap", "msgs": [EN_ROADMAP]},
        {"name": "📚-hero-library", "msgs": [EN_LIBRARY]},
    ]},
    {"key": "en_dev", "lang": "en", "name": "🏯 DEVELOPMENT", "access": "members_info", "channels": [
        {"name": "📖-patch-notes", "msgs": [EN_PATCH]},
        {"name": "🧪-sneak-peeks", "msgs": [EN_PEEK]},
        {"name": "🏛️-council", "access": "members_chat", "slow": 10, "msgs": [EN_COUNCIL]},
    ]},
    {"key": "en_support", "lang": "en", "name": "🛠️ SUPPORT", "access": "members_chat", "channels": [
        {"name": "🎫-open-ticket", "access": "members_info", "msgs": [(EN_TICKET, "en_ticket")]},
        {"name": "🐛-bug-reports", "slow": 30, "msgs": [EN_BUGS]},
        {"name": "❓-help", "slow": 10, "msgs": [EN_HELP]},
    ]},
    {"key": "en_community", "lang": "en", "name": "💬 SHINOBI COMMUNITY", "access": "members_chat", "channels": [
        {"name": "💬-global-chat", "slow": 5},
        {"name": "⚔️-team-builds"},
        {"name": "📸-show-off", "slow": 10},
        {"name": "🏆-arena-rankings"},
        {"name": "🏯-find-a-guild"},
        {"name": "🛒-trading", "slow": 30, "msgs": [EN_TRADE]},
    ]},
    {"key": "en_voice", "lang": "en", "name": "🔊 VOICE", "access": "members_chat", "channels": [
        {"name": "🔊 Global Voice", "kind": "voice"},
        {"name": "⚔️ Ranking Deadline", "kind": "voice"},
    ]},
    # ======================= DÙNG CHUNG =======================
    # Danh mục trống: bot tạo phòng ticket vào đây (chỉ staff + người mở ticket thấy)
    {"key": "tickets", "lang": None, "name": "🎫 TICKET ĐANG MỞ", "old": ["🎫 TICKET ĐANG MỞ · OPEN TICKETS"],
     "access": "staff", "channels": []},
    {"key": "en_tickets", "lang": None, "name": "🎫 OPEN TICKETS", "access": "staff", "channels": []},
    {"key": "staff", "lang": None, "name": "🔒 HOKAGE · BAN QUẢN TRỊ", "old": ["🔒 HOKAGE · BAN QUẢN TRỊ · STAFF"],
     "access": "staff", "channels": [
        {"name": "💬-staff-chat"},
        {"name": "🧾-log-ticket"},
        {"name": "🚨-log-moderation"},
    ]},
]
CAT_BY_KEY = {c["key"]: c for c in LAYOUT}
CH_PANEL = {"vi": "🎫-mở-ticket", "en": "🎫-open-ticket"}
TICKET_CAT = {"vi": "tickets", "en": "en_tickets"}  # danh mục chứa phòng ticket theo ngôn ngữ
CH_LOG = "🧾-log-ticket"
STAFF_KEYS = ("hokage", "anbu", "support")  # role được thấy và đóng mọi ticket
GIFT_ADMIN_KEYS = ("hokage", "dev", "anbu")   # role được thêm/xóa giftcode (chủ server luôn được)
CH_GIFT = {"vi": "🎁-giftcode", "en": "🎁-gift-codes"}  # nơi bot tự đăng code mới
GAME_TZ = dt.timezone(dt.timedelta(hours=7))   # giờ Việt Nam: code hết hạn lúc 23:59 ngày HSD


# =====================================================================
# 2. HÀM TIỆN ÍCH
# =====================================================================
def key(text: str) -> str:
    """Chuẩn hóa tên để so sánh: Discord tự hạ chữ thường và có thể bỏ ký tự biến thể emoji."""
    return text.replace("️", "").lower()


def names_of(spec):
    return [spec["name"], *spec.get("old", [])]


def find_by_names(items, names):
    """Ưu tiên tên mới, sau đó mới tới tên cũ."""
    for name in names:
        hit = discord.utils.find(lambda x: key(x.name) == key(name), items)
        if hit:
            return hit
    return None


def find_role(guild, role_key: str):
    return find_by_names(guild.roles, names_of(ROLE_BY_KEY[role_key]))


def find_category(guild, cat_key: str):
    return find_by_names(guild.categories, names_of(CAT_BY_KEY[cat_key]))


def find_text_channel(guild, name):
    return discord.utils.find(lambda c: key(c.name) == key(name), guild.text_channels)


def is_verified(guild, member) -> bool:
    roles = [find_role(guild, k) for k in MEMBER_ROLE.values()]
    return any(r in member.roles for r in roles if r)


def member_lang(guild, member) -> str:
    for lang in ("en", "vi"):
        for k in (LANG_ROLE[lang], MEMBER_ROLE[lang]):
            r = find_role(guild, k)
            if r and r in member.roles:
                return lang
    return "vi"


def channel_lang(channel):
    cat = getattr(channel, "category", None)
    if cat is None:
        return None
    for spec in LAYOUT:
        if spec["lang"] and key(cat.name) in {key(n) for n in names_of(spec)}:
            return spec["lang"]
    return None


async def rename_if_needed(obj, new_name, stats, warnings, what):
    if obj.name == new_name:
        return
    try:
        await obj.edit(name=new_name, reason=REASON)
        stats["renamed"] += 1
    except discord.HTTPException as e:
        warnings.append(f"Chưa đổi được tên {what} `{obj.name}` → `{new_name}` ({e}). "
                        "Kiểm tra role của bot có nằm trên role đó không.")


async def get_or_create_role(guild, spec, stats, warnings):
    role = find_role(guild, spec["key"])
    if role:
        await rename_if_needed(role, spec["name"], stats, warnings, "role")
        return role, False
    kwargs = dict(
        name=spec["name"],
        colour=discord.Colour(spec["color"]),
        hoist=spec.get("hoist", False),
        mentionable=spec.get("mentionable", False),
        reason=REASON,
    )
    if spec.get("perms"):
        kwargs["permissions"] = spec["perms"]
    try:
        return await guild.create_role(**kwargs), True
    except discord.Forbidden:
        if "permissions" not in kwargs:
            raise
        kwargs.pop("permissions")  # bot không đủ quyền để cấp quyền này
        warnings.append(f"Tạo role `{spec['name']}` nhưng chưa cấp được quyền. Hãy tự bật quyền cho role này.")
        return await guild.create_role(**kwargs), True


def build_overwrites(guild, access, lang, R):
    posters = [R["hokage"], R["dev"], R["anbu"]]
    staff = posters + [R["support"]]
    read_only = dict(
        view_channel=True, read_message_history=True, add_reactions=True,
        send_messages=False, create_public_threads=False,
        create_private_threads=False, send_messages_in_threads=False,
    )
    chat = dict(view_channel=True, read_message_history=True, send_messages=True,
                add_reactions=True, attach_files=True, connect=True, speak=True)
    ow = {guild.me: PO(view_channel=True, send_messages=True, embed_links=True,
                       read_message_history=True, manage_messages=True)}
    who = posters
    hidden = PO(view_channel=False)

    if access == "open":
        ow[guild.default_role] = PO(**read_only)
    elif access == "info":
        ow[guild.default_role] = hidden
        ow[R[LANG_ROLE[lang]]] = PO(**read_only)    # đã chọn ngôn ngữ
        ow[R[MEMBER_ROLE[lang]]] = PO(**read_only)  # thành viên cũ chưa bấm chọn ngôn ngữ vẫn thấy
        ow[R["support"]] = PO(**read_only)
    elif access == "members_info":
        ow[guild.default_role] = hidden
        ow[R[MEMBER_ROLE[lang]]] = PO(**read_only)
        ow[R["support"]] = PO(**read_only)
    elif access == "members_chat":
        ow[guild.default_role] = hidden
        ow[R[MEMBER_ROLE[lang]]] = PO(**chat)
        who = staff
    elif access == "staff":
        ow[guild.default_role] = hidden
        who = staff
    else:
        raise ValueError(f"access không hợp lệ: {access}")

    for role in who:
        ow[role] = PO(view_channel=True, send_messages=True, embed_links=True,
                      attach_files=True, connect=True, speak=True)
    return ow


async def apply_overwrites(obj, ow, warnings):
    """Cập nhật quyền xem của danh mục/kênh đã có cho đúng cơ chế ngôn ngữ."""
    if dict(obj.overwrites) == ow:
        return False
    try:
        await obj.edit(overwrites=ow, reason=REASON)
        return True
    except discord.HTTPException as e:
        warnings.append(f"Chưa cập nhật được quyền của `{obj.name}` ({e}).")
        return False


async def get_or_create_category(guild, spec, prev_cat, ow, stats, warnings):
    cat = find_category(guild, spec["key"])
    if cat:
        await rename_if_needed(cat, spec["name"], stats, warnings, "danh mục")
        if await apply_overwrites(cat, ow, warnings):
            stats["perms"] += 1
        return cat, False
    cat = await guild.create_category(spec["name"], overwrites=ow, reason=REASON)
    try:  # đặt danh mục mới ngay sau danh mục đứng trước nó trong LAYOUT
        await cat.edit(position=(prev_cat.position + 1) if prev_cat else 0, reason=REASON)
    except discord.HTTPException as e:
        warnings.append(f"Chưa sắp được vị trí `{spec['name']}` ({e}). Hãy kéo tay.")
    return cat, True


async def get_or_create_channel(guild, category, spec, ow, stats, warnings):
    kind = spec.get("kind", "text")
    pool = category.voice_channels if kind == "voice" else category.text_channels
    existing = discord.utils.find(lambda c: key(c.name) == key(spec["name"]), pool)
    if existing:
        if await apply_overwrites(existing, ow, warnings):
            stats["perms"] += 1
        if kind == "text":
            want_slow = spec.get("slow", 0)
            new_topic = None if (existing.topic or "").startswith("🇬🇧") else existing.topic
            edit_kwargs = {}
            if existing.slowmode_delay != want_slow:
                edit_kwargs["slowmode_delay"] = want_slow
            if new_topic != existing.topic:
                edit_kwargs["topic"] = new_topic
            if edit_kwargs:
                try:
                    await existing.edit(**edit_kwargs, reason=REASON)
                    if "slowmode_delay" in edit_kwargs:
                        stats["perms"] += 1
                except discord.HTTPException:
                    pass
        return existing, False
    if kind == "voice":
        ch = await guild.create_voice_channel(spec["name"], category=category, overwrites=ow, reason=REASON)
    else:
        ch = await guild.create_text_channel(
            spec["name"], category=category, overwrites=ow,
            slowmode_delay=spec.get("slow", 0), reason=REASON)
    return ch, True


async def sort_roles(guild, ordered, warnings):
    """Discord đặt role mới ở dưới cùng nên thứ tự tạo bị đảo -> sắp lại đúng cao→thấp."""
    try:
        fresh = {r.id: r.position for r in await guild.fetch_roles()}
        slots = sorted((fresh[r.id] for r in ordered), reverse=True)
        await guild.edit_role_positions({r: pos for r, pos in zip(ordered, slots)}, reason=REASON)
    except (discord.HTTPException, AttributeError) as e:
        warnings.append(
            f"Chưa sắp được thứ tự role ({e}). Hãy kéo thủ công: Hokage > Dev > Anbu > Hỗ Trợ > ... > Nhẫn Giả, "
            "và đảm bảo role của bot nằm TRÊN các role Nhẫn Giả, Shinobi, ngôn ngữ và Ping.")


async def harden_server(guild, warnings):
    try:  # chặn thành viên thường ping @everyone/@here
        perms = guild.default_role.permissions
        perms.update(mention_everyone=False, send_tts_messages=False)
        await guild.default_role.edit(permissions=perms, reason=REASON)
    except discord.HTTPException as e:
        warnings.append(f"Chưa khóa quyền ping @everyone của mọi người ({e}).")
    try:  # xác minh mức Medium + chỉ báo khi được nhắc (đỡ spam thông báo trên mobile)
        await guild.edit(
            verification_level=discord.VerificationLevel.medium,
            default_notifications=discord.NotificationLevel.only_mentions,
            reason=REASON)
    except discord.HTTPException as e:
        warnings.append(f"Chưa chỉnh được cài đặt server (cần quyền Manage Server) ({e}).")


# =====================================================================
# 3. NÚT BẤM (chạy bền vững, vẫn hoạt động sau khi khởi động lại bot)
# =====================================================================
async def reply(interaction, text: str):
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


async def choose_language(interaction, lang: str):
    """Gán role ngôn ngữ (chỉ giữ 1). Người đã xác minh được đổi luôn role thành viên sang ngôn ngữ mới."""
    guild, member, t = interaction.guild, interaction.user, TXT[lang]
    want = find_role(guild, LANG_ROLE[lang])
    if want is None:
        return await reply(interaction, t["no_role"])
    other = "en" if lang == "vi" else "vi"
    add, remove = [want], []
    other_lang = find_role(guild, LANG_ROLE[other])
    if other_lang and other_lang in member.roles:
        remove.append(other_lang)
    if is_verified(guild, member):  # giữ trạng thái đã xác minh khi đổi ngôn ngữ
        new_member = find_role(guild, MEMBER_ROLE[lang])
        old_member = find_role(guild, MEMBER_ROLE[other])
        if new_member:
            add.append(new_member)
        if old_member and old_member in member.roles:
            remove.append(old_member)
    add = [r for r in add if r not in member.roles]
    try:
        if remove:
            await member.remove_roles(*remove, reason="Đổi ngôn ngữ")
        if add:
            await member.add_roles(*add, reason="Chọn ngôn ngữ")
    except discord.Forbidden:
        return await reply(interaction, t["no_perm"])
    await reply(interaction, t["lang_set"])


async def verify(interaction, lang: str):
    guild, member, t = interaction.guild, interaction.user, TXT[lang]
    role = find_role(guild, MEMBER_ROLE[lang])
    if role is None:
        return await reply(interaction, t["no_role"])
    if role in member.roles:
        return await reply(interaction, t["already"])
    lang_role = find_role(guild, LANG_ROLE[lang])
    try:
        await member.add_roles(*[r for r in (role, lang_role) if r and r not in member.roles],
                               reason="Xác minh bằng nút")
    except discord.Forbidden:
        return await reply(interaction, t["no_perm"])
    await reply(interaction, t["welcome"])


async def toggle_ping(interaction, role_key: str, lang: str, label: str):
    guild, member, t = interaction.guild, interaction.user, TXT[lang]
    role = find_role(guild, role_key)
    if role is None:
        return await reply(interaction, t["no_role"])
    if not is_verified(guild, member):
        return await reply(interaction, t["not_verified"])
    try:
        if role in member.roles:
            await member.remove_roles(role, reason="Tự tắt thông báo")
            await reply(interaction, t["removed"].format(label=label))
        else:
            await member.add_roles(role, reason="Tự bật thông báo")
            await reply(interaction, t["added"].format(label=label))
    except discord.Forbidden:
        await reply(interaction, t["no_perm"])


# =====================================================================
# 3b. HỆ THỐNG TICKET TỰ LÀM (Chống bấm đúp / Race Condition)
# =====================================================================
_opening_tickets: set[tuple[int, int]] = set()  # khóa (guild_id, user_id) đang tạo ticket
_closing_tickets: set[int] = set()              # khóa channel_id đang đóng ticket


def is_staff(guild, member):
    roles = [find_role(guild, k) for k in STAFF_KEYS]
    return any(r in member.roles for r in roles if r)


async def open_ticket(interaction, kind: str):
    guild, member = interaction.guild, interaction.user
    lang, intro = TICKET_KINDS[kind]
    t = TXT[lang]
    if not is_verified(guild, member):
        return await reply(interaction, t["not_verified"])

    lock_key = (guild.id, member.id)
    if lock_key in _opening_tickets:
        return await reply(interaction, t["ticket_opening"])

    _opening_tickets.add(lock_key)
    try:
        cat = find_category(guild, TICKET_CAT[lang])
        if cat is None:
            return await reply(interaction, t["no_ticket_cat"])
        for tc in filter(None, (find_category(guild, k) for k in TICKET_CAT.values())):
            for ch in tc.text_channels:  # mỗi người chỉ mở 1 ticket cùng lúc (tính cả hai bên)
                if ch.topic and ch.topic.startswith(f"ticket:{member.id}:"):
                    return await reply(interaction, t["has_ticket"].format(ch=ch.mention))

        await interaction.response.defer(ephemeral=True)
        staff_roles = [r for r in (find_role(guild, k) for k in STAFF_KEYS) if r]
        overwrites = {
            guild.default_role: PO(view_channel=False),
            guild.me: PO(view_channel=True, send_messages=True, read_message_history=True,
                         manage_channels=True, embed_links=True),
            member: PO(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
        }
        for role in staff_roles:
            overwrites[role] = PO(view_channel=True, send_messages=True,
                                  read_message_history=True, attach_files=True)
        try:
            ch = await guild.create_text_channel(
                f"{kind}-{member.name}"[:90], category=cat, overwrites=overwrites,
                topic=f"ticket:{member.id}:{kind}", reason=f"Ticket của {member}")
        except discord.HTTPException:
            log.exception("Không tạo được ticket")
            return await interaction.followup.send(t["ticket_fail"], ephemeral=True)

        support = find_role(guild, "support")
        ping = support.mention if support else ""
        await ch.send(
            f"{member.mention} {ping}\n{intro}",
            view=make_view("en_close" if lang == "en" else "close"),
            allowed_mentions=discord.AllowedMentions(users=True, roles=True))
        await interaction.followup.send(t["ticket_ok"].format(ch=ch.mention), ephemeral=True)
    finally:
        _opening_tickets.discard(lock_key)


async def close_ticket(interaction, lang: str):
    guild, ch, user, t = interaction.guild, interaction.channel, interaction.user, TXT[lang]
    topic = getattr(ch, "topic", None) or ""
    try:
        opener_id = int(topic.split(":")[1]) if topic.startswith("ticket:") else None
    except (IndexError, ValueError):
        opener_id = None
    if opener_id is None:
        return await reply(interaction, t["not_ticket"])
    if user.id != opener_id and not is_staff(guild, user):
        return await reply(interaction, t["close_denied"])
    if ch.id in _closing_tickets:
        return await reply(interaction, t["already_closing"])

    log_ch = find_text_channel(guild, CH_LOG)
    if log_ch is None:
        return await reply(interaction, f"⚠️ Không thấy kênh `{CH_LOG}` để lưu transcript nên chưa đóng ticket.")

    _closing_tickets.add(ch.id)
    try:
        await interaction.response.send_message(t["closing"])
        lines = []
        async for m in ch.history(limit=2000, oldest_first=True):
            text = m.clean_content
            if m.attachments:
                text += " " + " ".join(a.url for a in m.attachments)
            stamp = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{stamp} UTC] {m.author}: {text}")
        data = io.BytesIO("\n".join(lines).encode("utf-8"))
        try:
            await log_ch.send(
                f"🧾 Ticket **{ch.name}** (người mở: <@{opener_id}>) do {user.mention} đóng.",
                file=discord.File(data, filename=f"{ch.name}.txt"),
                allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException as e:
            return await interaction.followup.send(f"⚠️ Lưu transcript thất bại ({e}), chưa đóng ticket.")
        await asyncio.sleep(5)
        try:
            await ch.delete(reason=f"Ticket đóng bởi {user}")
        except discord.NotFound:
            pass
    finally:
        _closing_tickets.discard(ch.id)


def _label(cid):
    return next(b[2] for v in BUTTONS.values() for b in v if b[0] == cid)


HANDLERS = {
    "nw:lang_vi": lambda i: choose_language(i, "vi"),
    "nw:lang_en": lambda i: choose_language(i, "en"),
    "nw:verify": lambda i: verify(i, "vi"),
    "nw:verify_en": lambda i: verify(i, "en"),
    "nw:ping_gift": lambda i: toggle_ping(i, "ping_gift", "vi", _label("nw:ping_gift")),
    "nw:ping_event": lambda i: toggle_ping(i, "ping_event", "vi", _label("nw:ping_event")),
    "nw:en_ping_gift": lambda i: toggle_ping(i, "ping_gift", "en", _label("nw:en_ping_gift")),
    "nw:en_ping_event": lambda i: toggle_ping(i, "ping_event", "en", _label("nw:en_ping_event")),
    "nw:ticket_nap": lambda i: open_ticket(i, "nap"),
    "nw:ticket_hotro": lambda i: open_ticket(i, "hotro"),
    "nw:en_ticket_topup": lambda i: open_ticket(i, "topup"),
    "nw:en_ticket_support": lambda i: open_ticket(i, "support"),
    "nw:ticket_close": lambda i: close_ticket(i, "vi"),
    "nw:en_ticket_close": lambda i: close_ticket(i, "en"),
}


class ActionView(discord.ui.View):
    """Một nhóm nút trong BUTTONS. custom_id cố định nên nút vẫn chạy sau khi bot khởi động lại."""

    def __init__(self, kind: str):
        super().__init__(timeout=None)
        for cid, emoji, label, style in BUTTONS[kind]:
            btn = discord.ui.Button(custom_id=cid, emoji=emoji, label=label,
                                    style=getattr(discord.ButtonStyle, style))
            btn.callback = self._callback(cid)
            self.add_item(btn)

    @staticmethod
    def _callback(cid):
        async def run(interaction):
            await HANDLERS[cid](interaction)
        return run


def make_view(kind):
    return ActionView(kind)


# =====================================================================
# 4. BOT & LỆNH
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True  # bắt buộc cho lệnh tiền tố "!"
intents.members = True          # giúp lệnh !rank @user tra cứu chính xác mọi thành viên


class NinjaBot(commands.Bot):
    async def setup_hook(self):
        for kind in BUTTONS:  # đăng ký lại mọi nút sau mỗi lần khởi động
            self.add_view(make_view(kind))


bot = NinjaBot(command_prefix="!", intents=intents)


def owner_only():
    async def predicate(ctx):
        return ctx.guild is not None and ctx.author.id == ctx.guild.owner_id
    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã sẵn sàng. Vào server và gõ: !xaykenh")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Đợi {error.retry_after:.0f} giây rồi thử lại.", delete_after=5)
    if isinstance(error, NotGiftAdmin):
        return await ctx.send("⛔ Chỉ chủ server, Hokage, Dev hoặc Anbu mới quản lý giftcode được.")
    if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)) and ctx.command \
            and ctx.command.name in ("themcode", "xoacode"):
        return await ctx.send(f"⚠️ Sai cú pháp. Dùng: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`\n"
                              "Ví dụ: `!themcode NINJA2026 31/12/2026 Kim cương x100 | 100 Diamonds`")
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("⛔ Lệnh này chỉ **chủ server** dùng được, và chỉ trong server.")
    if isinstance(error, commands.MemberNotFound):
        return await ctx.send("⚠️ Không tìm thấy thành viên này trong server.")
    log.error("Lỗi lệnh %s: %s", ctx.command, error)


def button_ids(msg):
    ids = set()
    for row in getattr(msg, "components", []) or []:
        for child in getattr(row, "children", []) or []:
            if getattr(child, "custom_id", None):
                ids.add(child.custom_id)
    return ids


def button_labels(msg):
    return [getattr(child, "label", None)
            for row in getattr(msg, "components", []) or []
            for child in getattr(row, "children", []) or []]


def resolve_msgs(spec):
    return [item if isinstance(item, tuple) else (item, None) for item in spec.get("msgs", [])]


async def sync_posts(guild, channel, spec, stats, warnings):
    """Đăng bài còn thiếu và SỬA bài bot đã đăng cho khớp nội dung mới (không đăng trùng).
    Bài có nút được ghép theo nút; bài thường ghép theo thứ tự cũ → mới."""
    items = resolve_msgs(spec)
    if not items:
        return
    own = [m async for m in channel.history(limit=50, oldest_first=True) if m.author.id == guild.me.id]
    for raw_text, kind in items:
        text = raw_text[:2000]  # đảm bảo không vượt giới hạn 2000 ký tự của Discord
        if len(raw_text) > 2000:
            warnings.append(f"Bài mẫu tại `{channel.name}` dài quá 2000 ký tự nên đã được cắt bớt.")
        if kind:
            want = {b[0] for b in BUTTONS[kind]}
            match = next((m for m in own if button_ids(m) & want), None)
        else:
            match = next((m for m in own if not button_ids(m)), None)
        if match is None:
            await channel.send(text, view=make_view(kind) if kind else None)
            stats["posted"] += 1
            continue
        own.remove(match)
        labels = [b[2] for b in BUTTONS[kind]] if kind else []
        if match.content != text or (kind and button_labels(match) != labels):
            if kind:
                await match.edit(content=text, view=make_view(kind))
            else:
                await match.edit(content=text)
            stats["edited"] += 1
    leftovers = [m for m in own if m.content.startswith("#") or button_ids(m)]
    if leftovers:
        warnings.append(f"Kênh `{channel.name}` còn {len(leftovers)} bài cũ của bot bị trùng. Có thể xóa tay cho gọn.")


async def build_layout(guild, R, stats, warnings):
    prev = None
    for cat_spec in LAYOUT:
        lang, cat_access = cat_spec["lang"], cat_spec["access"]
        cat, new = await get_or_create_category(
            guild, cat_spec, prev, build_overwrites(guild, cat_access, lang, R), stats, warnings)
        stats["ch_new" if new else "ch_old"] += 1
        prev = cat
        for spec in cat_spec["channels"]:
            ow = build_overwrites(guild, spec.get("access", cat_access), lang, R)
            channel, created = await get_or_create_channel(guild, cat, spec, ow, stats, warnings)
            stats["ch_new" if created else "ch_old"] += 1
            if spec.get("kind", "text") == "text":
                await sync_posts(guild, channel, spec, stats, warnings)


@bot.command(name="xaykenh")
@commands.guild_only()
@owner_only()
async def xaykenh(ctx: commands.Context):
    guild = ctx.guild
    perms = guild.me.guild_permissions
    if not (perms.manage_roles and perms.manage_channels):
        return await ctx.send(
            "⛔ Bot thiếu quyền **Manage Roles** và **Manage Channels**. Hãy mời lại bot với các quyền này.")

    status = await ctx.send("⏳ Đang dựng/cập nhật Làng Lá... (có thể mất 3–5 phút do giới hạn tốc độ của Discord)")
    stats = {"role_new": 0, "role_old": 0, "ch_new": 0, "ch_old": 0,
             "renamed": 0, "perms": 0, "posted": 0, "edited": 0}
    warnings: list[str] = []

    try:
        R = {}
        for spec in ROLE_SPECS:
            role, created = await get_or_create_role(guild, spec, stats, warnings)
            R[spec["key"]] = role
            stats["role_new" if created else "role_old"] += 1

        await sort_roles(guild, [R[s["key"]] for s in ROLE_SPECS], warnings)
        await harden_server(guild, warnings)
        await build_layout(guild, R, stats, warnings)
    except discord.HTTPException as e:
        log.exception("Lỗi khi dựng server")
        return await status.edit(content=(
            f"❌ Dừng giữa chừng: `{e}`\nPhần đã làm được giữ nguyên. "
            "Sửa quyền của bot rồi gõ lại `!xaykenh` để làm tiếp, sẽ không bị trùng."))

    text = (f"🎉 **HOÀN TẤT!** Mới tạo: {stats['role_new']} role, {stats['ch_new']} kênh/danh mục · "
            f"đổi tên: {stats['renamed']} · cập nhật quyền/slowmode: {stats['perms']} · "
            f"bài mới: {stats['posted']} · bài được sửa: {stats['edited']}.")
    if warnings:
        text += "\n\n⚠️ **Cần xem lại:**\n" + "\n".join(f"• {w}" for w in warnings)
    await status.edit(content=text[:2000])


# =====================================================================
# 5. CẤP BẬC THEO SỐ TIN NHẮN (SQLite WAL mode + Bộ nhớ đệm RAM)
# =====================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "levels.db")
db = sqlite3.connect(DB_PATH)
db.execute("PRAGMA journal_mode=WAL;")
db.execute("PRAGMA synchronous=NORMAL;")
db.execute(
    "CREATE TABLE IF NOT EXISTS msgs ("
    "guild_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, last_ts REAL DEFAULT 0, "
    "PRIMARY KEY (guild_id, user_id))")
db.commit()

# Bộ nhớ đệm thời gian nhắn tin gần nhất trên RAM để tránh quét Role & gọi SQLite liên tục khi chat nhanh
_last_msg_ts: dict[tuple[int, int], float] = {}


def rank_for(count: int):
    """Cấp bậc cao nhất mà số tin nhắn đạt được (None nếu chưa đủ mốc đầu)."""
    current = None
    for r in RANKS:
        if count >= r[0]:
            current = r
    return current


def count_message(guild_id: int, user_id: int, now: float):
    """Cộng 1 tin nhắn nếu qua thời gian chờ. Trả về tổng mới, hoặc None nếu không tính."""
    row = db.execute("SELECT count, last_ts FROM msgs WHERE guild_id=? AND user_id=?",
                     (guild_id, user_id)).fetchone()
    if row is None:
        db.execute("INSERT INTO msgs (guild_id, user_id, count, last_ts) VALUES (?,?,1,?)",
                   (guild_id, user_id, now))
        db.commit()
        _last_msg_ts[(guild_id, user_id)] = now
        return 1
    count, last = row
    if now - last < COOLDOWN:
        _last_msg_ts[(guild_id, user_id)] = last
        return None
    count += 1
    db.execute("UPDATE msgs SET count=?, last_ts=? WHERE guild_id=? AND user_id=?",
               (count, now, guild_id, user_id))
    db.commit()
    _last_msg_ts[(guild_id, user_id)] = now
    return count


async def sync_rank(member, count: int):
    """Gán role cấp bậc phù hợp, gỡ role cấp thấp. Trả về rank mới nếu vừa thăng cấp."""
    target = rank_for(count)
    if target is None:
        return None
    guild = member.guild
    want = find_role(guild, target[1])
    if want is None:
        return None  # chưa có role -> chạy !xaykenh để tạo
    others = [r for r in (find_role(guild, x[1]) for x in RANKS) if r and r != want]
    remove = [r for r in others if r in member.roles]
    if want in member.roles and not remove:
        return None
    if remove:
        await member.remove_roles(*remove, reason="Đổi cấp bậc")
    if want not in member.roles:
        await member.add_roles(want, reason=f"Đạt {count} tin nhắn")
        return target
    return None


def in_counted_category(channel) -> bool:
    cat = getattr(channel, "category", None)
    if cat is None:
        return False
    return any(key(cat.name) in {key(n) for n in names_of(CAT_BY_KEY[k])} for k in COUNT_CATEGORIES)


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot or message.guild is None:
        return
    if message.content.startswith(bot.command_prefix):  # lệnh như !code, !rank không tính cấp bậc
        return
    if len(message.content.strip()) < MIN_LEN:
        return
    if not in_counted_category(message.channel):
        return

    # Kiểm tra nhanh Cooldown trên RAM trước khi quét Role & gọi SQLite
    now = time.time()
    cache_key = (message.guild.id, message.author.id)
    if now - _last_msg_ts.get(cache_key, 0.0) < COOLDOWN:
        return

    member = message.author
    if not is_verified(message.guild, member):
        return  # chưa xác minh thì không tính

    count = count_message(message.guild.id, member.id, now)
    if count is None:
        return
    try:
        new_rank = await sync_rank(member, count)
    except discord.Forbidden:
        log.warning("Bot không đủ quyền gán role cấp bậc. Kéo role bot lên trên các role Genin/Chunin/...")
        return
    if new_rank:
        t = TXT[channel_lang(message.channel) or "vi"]
        await message.channel.send(
            t["levelup"].format(user=member.mention, rank=new_rank[2], n=count),
            allowed_mentions=discord.AllowedMentions(users=[member]))


def cmd_lang(ctx) -> str:
    return channel_lang(ctx.channel) or member_lang(ctx.guild, ctx.author)


@bot.command(name="rank")
@commands.guild_only()
async def rank_cmd(ctx: commands.Context, member: discord.Member = None):
    """Xem cấp bậc và số tin nhắn của bạn (hoặc của người được tag)."""
    t = TXT[cmd_lang(ctx)]
    member = member or ctx.author
    row = db.execute("SELECT count FROM msgs WHERE guild_id=? AND user_id=?",
                     (ctx.guild.id, member.id)).fetchone()
    count = row[0] if row else 0
    cur = rank_for(count)
    nxt = next((r for r in RANKS if r[0] > count), None)
    text = t["rank"].format(name=member.display_name, rank=cur[2] if cur else t["academy"], n=count)
    text += "\n" + (t["next"].format(left=nxt[0] - count, rank=nxt[2]) if nxt else t["max"])
    await ctx.send(text, allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="top")
@commands.guild_only()
async def top_cmd(ctx: commands.Context):
    """Bảng xếp hạng 10 người nhiều tin nhắn nhất."""
    t = TXT[cmd_lang(ctx)]
    rows = db.execute("SELECT user_id, count FROM msgs WHERE guild_id=? ORDER BY count DESC LIMIT 10",
                      (ctx.guild.id,)).fetchall()
    if not rows:
        return await ctx.send(t["top_empty"])
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
    lines = [f"{medals[i]} <@{uid}> · {(rank_for(cnt) or (0, 0, t['academy']))[2]} · {cnt} {t['unit']}"
             for i, (uid, cnt) in enumerate(rows)]
    await ctx.send(t["top_title"] + "\n" + "\n".join(lines), allowed_mentions=discord.AllowedMentions.none())


# =====================================================================
# 6. GIFTCODE: !code (ai cũng dùng), !themcode / !xoacode (staff)
# =====================================================================
db.execute(
    "CREATE TABLE IF NOT EXISTS giftcodes ("
    "guild_id INTEGER, code TEXT COLLATE NOCASE, reward TEXT DEFAULT '', expires TEXT, "
    "added_by INTEGER, added_at REAL, PRIMARY KEY (guild_id, code))")
db.commit()

NO_EXPIRY_WORDS = {"-", "0", "khong", "không", "none", "vinhvien", "vĩnhviễn"}


class NotGiftAdmin(commands.CheckFailure):
    pass


def gift_admin():
    async def predicate(ctx):
        if ctx.guild is None:
            raise NotGiftAdmin()
        if ctx.author.id == ctx.guild.owner_id:
            return True
        roles = [find_role(ctx.guild, k) for k in GIFT_ADMIN_KEYS]
        if any(r in ctx.author.roles for r in roles if r):
            return True
        raise NotGiftAdmin()
    return commands.check(predicate)


def game_today() -> dt.date:
    return dt.datetime.now(GAME_TZ).date()


def parse_expiry(text: str):
    """'31/12/2026', '31-12-2026', '2026-12-31', '31/12' (năm nay/năm sau) hoặc '-' (không hạn).
    Trả về (ngày hoặc None, True nếu hiểu được)."""
    t = text.strip().lower()
    if t in NO_EXPIRY_WORDS:
        return None, True
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(t, fmt).date(), True
        except ValueError:
            pass
    try:
        d = dt.datetime.strptime(t, "%d/%m").date().replace(year=game_today().year)
        if d < game_today():
            d = d.replace(year=d.year + 1)
        return d, True
    except ValueError:
        return None, False


def split_reward(reward: str, lang: str) -> str:
    """Phần thưởng dạng 'Tiếng Việt | English' -> lấy phần đúng ngôn ngữ."""
    if "|" not in reward:
        return reward.strip()
    vi, en = (x.strip() for x in reward.split("|", 1))
    return (en or vi) if lang == "en" else (vi or en)


def expiry_text(expires, t) -> str:
    if not expires:
        return t["code_noexp"]
    d = dt.date.fromisoformat(expires)
    left = (d - game_today()).days
    return t["code_today"] if left <= 0 else t["code_exp"].format(d=d.strftime("%d/%m/%Y"), n=left)


def active_codes(guild_id: int):
    today = game_today().isoformat()
    # dọn code đã hết hạn quá 30 ngày cho gọn
    db.execute("DELETE FROM giftcodes WHERE expires IS NOT NULL AND expires < ?",
               ((game_today() - dt.timedelta(days=30)).isoformat(),))
    db.commit()
    return db.execute(
        "SELECT code, reward, expires FROM giftcodes WHERE guild_id=? AND (expires IS NULL OR expires >= ?) "
        "ORDER BY expires IS NULL, expires, added_at DESC", (guild_id, today)).fetchall()


def code_messages(rows, lang: str) -> list[str]:
    """Danh sách code thành các tin nhắn <= 2000 ký tự."""
    t = TXT[lang]
    if not rows:
        return [t["code_none"]]
    lines = []
    for code, reward, expires in rows:
        r = split_reward(reward or "", lang)
        lines.append(f"🎁 `{code}`" + (f" · {r}" if r else "") + f"\n   ⏳ {expiry_text(expires, t)}")
    msgs, cur = [], t["code_title"]
    for line in lines + [t["code_foot"]]:
        if len(cur) + len(line) + 1 > 1900:
            msgs.append(cur)
            cur = line
        else:
            cur += "\n" + line
    msgs.append(cur)
    return msgs


def gift_context(ctx):
    """(guild, lang) cho lệnh !code, kể cả khi gõ trong tin nhắn riêng với bot."""
    if ctx.guild is not None:
        return ctx.guild, cmd_lang(ctx)
    for g in bot.guilds:
        m = g.get_member(ctx.author.id)
        if m is not None:
            return g, member_lang(g, m)
    return None, "vi"


@bot.command(name="code", aliases=["codes", "giftcode"])
@commands.cooldown(1, 10, commands.BucketType.user)
async def code_cmd(ctx: commands.Context):
    """Gửi tin nhắn riêng danh sách giftcode còn hạn."""
    guild, lang = gift_context(ctx)
    t = TXT[lang]
    msgs = code_messages(active_codes(guild.id) if guild else [], lang)
    if ctx.guild is None:  # đang ở tin nhắn riêng: trả lời luôn
        for m in msgs:
            await ctx.send(m)
        return
    try:
        await ctx.message.delete()  # xóa lệnh cho kênh chat gọn
    except discord.HTTPException:
        pass
    try:
        for m in msgs:
            await ctx.author.send(m)
    except discord.Forbidden:
        return await ctx.send(t["code_dm_fail"].format(user=ctx.author.mention), delete_after=20,
                              allowed_mentions=discord.AllowedMentions(users=[ctx.author]))
    await ctx.send(t["code_sent"].format(user=ctx.author.mention), delete_after=8,
                   allowed_mentions=discord.AllowedMentions(users=[ctx.author]))


@bot.command(name="themcode", aliases=["addcode"])
@commands.guild_only()
@gift_admin()
async def themcode(ctx: commands.Context, code: str, han: str = "-", *, phan_thuong: str = ""):
    """Thêm giftcode. Ví dụ: !themcode NINJA2026 31/12/2026 Kim cương x100 | 100 Diamonds"""
    code = code.strip()
    if not code or len(code) > 64 or "`" in code:
        return await ctx.send("⚠️ Code không hợp lệ (tối đa 64 ký tự, không chứa dấu `).")
    expires, ok = parse_expiry(han)
    if not ok:  # không ghi hạn: chữ thứ hai là phần thưởng
        phan_thuong = f"{han} {phan_thuong}".strip()
    if expires and expires < game_today():
        return await ctx.send(f"⚠️ Ngày hết hạn {expires.strftime('%d/%m/%Y')} đã qua.")
    existed = db.execute("SELECT 1 FROM giftcodes WHERE guild_id=? AND code=?", (ctx.guild.id, code)).fetchone()
    db.execute("INSERT OR REPLACE INTO giftcodes (guild_id, code, reward, expires, added_by, added_at) "
               "VALUES (?,?,?,?,?,?)",
               (ctx.guild.id, code, phan_thuong, expires.isoformat() if expires else None,
                ctx.author.id, time.time()))
    db.commit()

    exp_vi = expiry_text(expires.isoformat() if expires else None, TXT["vi"])
    done = []
    if not existed:  # chỉ thông báo code mới, sửa code cũ thì không ping lại
        ping_role = find_role(ctx.guild, "ping_gift")
        for lang, ch_name in CH_GIFT.items():
            ch = find_text_channel(ctx.guild, ch_name)
            if ch is None:
                continue
            t = TXT[lang]
            r = split_reward(phan_thuong, lang)
            try:
                await ch.send(
                    t["code_new"].format(ping=ping_role.mention if ping_role else "", code=code,
                                         reward=f"\n🎁 {r}" if r else "",
                                         exp=expiry_text(expires.isoformat() if expires else None, t)),
                    allowed_mentions=discord.AllowedMentions(roles=[ping_role] if ping_role else []))
                done.append(ch.mention)
            except discord.HTTPException as e:
                log.warning("Không đăng được giftcode ở %s: %s", ch_name, e)
    msg = f"✅ {'Đã cập nhật' if existed else 'Đã thêm'} code `{code}` · {exp_vi}"
    if phan_thuong:
        msg += f" · {phan_thuong}"
    if done:
        msg += f"\n📢 Đã thông báo ở {', '.join(done)}."
    await ctx.send(msg, allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="xoacode", aliases=["delcode"])
@commands.guild_only()
@gift_admin()
async def xoacode(ctx: commands.Context, code: str):
    """Xóa giftcode khỏi danh sách !code."""
    cur = db.execute("DELETE FROM giftcodes WHERE guild_id=? AND code=?", (ctx.guild.id, code.strip()))
    db.commit()
    if cur.rowcount:
        await ctx.send(f"🗑️ Đã xóa code `{code}`.", allowed_mentions=discord.AllowedMentions.none())
    else:
        await ctx.send(f"⚠️ Không có code `{code}` trong danh sách.", allowed_mentions=discord.AllowedMentions.none())


@bot.command(name="taoticket")
@commands.guild_only()
@owner_only()
async def taoticket(ctx: commands.Context):
    """Đăng (hoặc cập nhật) bảng ticket ở cả kênh tiếng Việt và tiếng Anh."""
    done, warnings = [], []
    for lang, kind, text in (("vi", "ticket", MSG_TICKET), ("en", "en_ticket", EN_TICKET)):
        ch = find_text_channel(ctx.guild, CH_PANEL[lang])
        if ch is None:
            warnings.append(f"Không tìm thấy kênh `{CH_PANEL[lang]}`. Hãy chạy `!xaykenh` trước.")
            continue
        await sync_posts(ctx.guild, ch, {"msgs": [(text, kind)]}, {"posted": 0, "edited": 0}, warnings)
        done.append(ch.mention)
    msg = f"✅ Bảng ticket đã sẵn sàng tại {', '.join(done)}." if done else ""
    await ctx.send("\n".join([msg, *warnings]).strip() or "⛔ Không làm được gì.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ Chưa có DISCORD_TOKEN. Tạo file .env với dòng: DISCORD_TOKEN=token_của_bạn")
    bot.run(TOKEN)
