# Ninja War Discord Bot: ghi chú cho dev (v7)

## File
- `ninjawar_builder.py`: bot chính (chọn ngôn ngữ, dựng role/kênh, xác minh, ticket, cấp bậc theo tin nhắn, giftcode).
- `requirements.txt`: thư viện cần cài (`discord.py>=2.4,<3`, `python-dotenv`).
- `.gitignore`: chặn `.env` (token) và các file dữ liệu `*.db` không bị đẩy lên git.

## Chạy
```
pip install -r requirements.txt
python ninjawar_builder.py
```
- Cần `DISCORD_TOKEN` trong file `.env` cùng thư mục (một dòng, không ngoặc kép, không khoảng trắng):
  `DISCORD_TOKEN=...` Hoặc đặt thành biến môi trường hệ thống.
- Chỉ chạy **một** tiến trình cho mỗi token. Hai bản chạy cùng lúc sẽ trả lời trùng và báo lỗi nút bấm.
- Nên chạy bằng service quản lý tiến trình (systemd, pm2, docker...) để tự bật lại khi lỗi hoặc khởi động lại máy.
- Python 3.10 trở lên.
- Log in ra màn hình (stdout) kèm thời gian và chi tiết lỗi. Chạy bằng systemd thì xem bằng `journalctl -u ninjawar -f`.

### Mẫu systemd (`/etc/systemd/system/ninjawar.service`)
```
[Unit]
Description=Ninja War Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
User=ninjawar
WorkingDirectory=/opt/NinjaWarBot
ExecStart=/opt/NinjaWarBot/venv/bin/python ninjawar_builder.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Sửa `User` và đường dẫn cho khớp máy, rồi chạy `systemctl daemon-reload && systemctl enable --now ninjawar`.

## Điểm mới ở v7
- **Đóng ticket lưu luôn ảnh/tệp đính kèm**: bot tải ảnh biên lai và đăng lại vào `🧾-log-ticket` ngay dưới transcript (tối đa 40 tệp mỗi ticket, bỏ qua tệp vượt giới hạn tải lên của server). Trong transcript, mỗi tệp ghi dạng `[tệp: 01_tên.png]` khớp với tên tệp trong log. Bản cũ chỉ lưu link, link chết khi phòng ticket bị xóa.
- **Nút bấm trả lời Discord trước rồi mới gán role**, nên không còn báo "tương tác thất bại" khi nhiều người bấm cùng lúc.
- **`!themcode` báo lỗi khi gõ sai ngày** (ví dụ `32/12/2026`), không còn âm thầm lưu thành code không thời hạn.
- **Danh mục ticket đầy 50 phòng** (giới hạn của Discord): người chơi được báo rõ, staff nhận cảnh báo ở `🧾-log-ticket` (tối đa 10 phút một lần).
- **`!xaykenh` nhớ ID các bài bot đã đăng** (bảng `posts` trong `levels.db`), nên không sửa nhầm bài khác khi bài mẫu bị xóa tay. Lần chạy đầu sau khi nâng cấp bot vẫn ghép bài theo cách cũ rồi ghi nhớ ID. Bài mẫu bị xóa tay sẽ được đăng lại.
- Đổi ngôn ngữ: gán role mới trước, gỡ role cũ sau.
- Nâng cấp từ v6: chỉ cần thay file `.py` và khởi động lại bot. `levels.db` cũ dùng tiếp được, bảng mới tự tạo.

## Cấu hình trên Discord Developer Portal
- Mục **Bot**: bật **Message Content Intent** và **Server Members Intent** (bot dùng cả hai). Thiếu một trong hai, bot sẽ báo lỗi `PrivilegedIntentsRequired` và không khởi động. Không cần Presence Intent.
- Mời bot với quyền **Administrator** cho lần dựng đầu tiên (cần để cấp quyền Administrator cho role Hokage).
- Trong Server Settings → Roles: role của bot phải nằm **trên** các role bot cần gán: Nhẫn Giả, Shinobi, 🇻🇳 Tiếng Việt, 🇬🇧 English, Ping, Genin/Chunin/Jonin/Sannin. Nếu không, các nút sẽ không gán được role.

## Cơ chế ngôn ngữ
| Người dùng | Thấy gì |
|---|---|
| Mới vào, chưa chọn | Chỉ kênh `🌐-ngôn-ngữ-language` (2 nút 🇻🇳 Tiếng Việt / 🇬🇧 English) |
| Chọn Tiếng Việt | Kênh thông tin tiếng Việt → bấm xác minh ở `✅-xác-minh` → mở toàn bộ kênh tiếng Việt |
| Chọn English | Kênh thông tin tiếng Anh → bấm xác minh ở `✅-verify` → mở toàn bộ kênh tiếng Anh |
| Staff (Hokage, Dev, Anbu, Hỗ Trợ Viên) | Thấy cả hai bên |

- Role mới: `🇻🇳 Tiếng Việt`, `🇬🇧 English` (role ngôn ngữ) và `🥷 Shinobi (Member)` (thành viên đã xác minh bên tiếng Anh). `🥷 Nhẫn Giả (Member)` là thành viên bên tiếng Việt như cũ.
- Bấm nút ngôn ngữ kia để đổi bất cứ lúc nào. Người đã xác minh được đổi luôn role thành viên, không phải xác minh lại.
- **Thành viên cũ** (đã có Nhẫn Giả, chưa bấm chọn ngôn ngữ) vẫn thấy toàn bộ kênh tiếng Việt như trước.
- Người chưa xác minh và chưa chọn ngôn ngữ sẽ **không còn thấy** kênh thông tin tiếng Việt cho đến khi bấm chọn.
- Role (staff, VIP, cấp bậc, Ping) dùng chung cho hai bên vì Discord không cho một role có hai tên.
- Ticket: bảng tiếng Việt mở ticket `nap-*`/`hotro-*` trong `🎫 TICKET ĐANG MỞ`; bảng tiếng Anh mở `topup-*`/`support-*` trong `🎫 OPEN TICKETS`. Mỗi người chỉ mở 1 ticket cùng lúc (tính cả hai bên). Transcript chung `🧾-log-ticket`.
- Tin nhắn ở `💬 CỘNG ĐỒNG NHẪN GIẢ` và `💬 SHINOBI COMMUNITY` đều được tính cấp bậc (dùng chung bảng điểm).
- **Thông báo, giftcode, lịch sự kiện**: staff cần đăng ở cả kênh tiếng Việt và kênh tiếng Anh.

## Lệnh (chỉ chủ server dùng được)
| Lệnh | Việc |
|---|---|
| `!xaykenh` | Tạo role, danh mục, kênh và bài đăng sẵn. Chạy lại an toàn: tạo phần còn thiếu, đổi tên mục cũ, **cập nhật quyền xem** của danh mục/kênh, sửa bài bot đã đăng cho khớp file, không đăng trùng |
| `!taoticket` | Đăng hoặc cập nhật bảng ticket ở `🎫-mở-ticket` và `🎫-open-ticket` |

Lệnh cho mọi người: `!rank` (xem cấp bậc), `!top` (bảng xếp hạng), `!code` (giftcode còn hạn). Bot trả lời theo ngôn ngữ của kênh.

## Giftcode
| Lệnh | Ai dùng | Việc |
|---|---|---|
| `!code` | Mọi người | Bot xóa tin nhắn lệnh và gửi **tin nhắn riêng** danh sách code còn hạn (theo ngôn ngữ người chơi đã chọn). Gõ trong tin nhắn riêng với bot cũng được. Mỗi người 10 giây dùng 1 lần |
| `!themcode <code> <hạn> <phần thưởng>` | Chủ server, Hokage, Dev, Anbu | Thêm code và tự đăng thông báo (ping 🔔 Ping Giftcode) ở `🎁-giftcode` và `🎁-gift-codes`. Thêm lại code đã có = sửa, không ping lại |
| `!xoacode <code>` | Như trên | Xóa code khỏi danh sách |

- Hạn ghi `31/12/2026`, `31/12` hoặc `2026-12-31`; ghi `-` hoặc bỏ trống nếu không có hạn. Code hết hạn lúc 23:59 giờ Việt Nam của ngày đó.
- Phần thưởng hai thứ tiếng ngăn bằng `|`: `!themcode NINJA2026 31/12/2026 Kim cương x100 | 100 Diamonds`. Người chơi tiếng Việt thấy phần trước, tiếng Anh thấy phần sau.
- Code hết hạn tự ẩn khỏi `!code` và tự xóa sau 30 ngày.
- Nếu người chơi chặn tin nhắn riêng, bot nhắc họ bật lại trong kênh (tin nhắc tự xóa sau 20 giây).
- Tin nhắn bắt đầu bằng `!` không còn được tính vào cấp bậc.

## Lưu ý khi chạy `!xaykenh` trên server đang có
- Quyền xem của các danh mục/kênh trong `LAYOUT` sẽ được **ghi đè** theo file. Nếu staff từng tự chỉnh quyền tay ở các kênh này, phần chỉnh tay sẽ mất.
- Các bài bot đã đăng được sửa cho khớp nội dung trong file. Muốn đổi chữ thì sửa file rồi chạy lại `!xaykenh`, đừng sửa tay trong Discord.
- Kênh `🎫-mở-ticket` có thể còn 1 bài cũ trùng từ lần cài trước; bot sẽ nhắc, staff xóa tay.
- **Slowmode** của các kênh trong `LAYOUT` cũng được đặt lại theo file. Muốn đổi slowmode thì sửa giá trị `slow` trong file.
- Mất khoảng 3–5 phút vì giới hạn tốc độ của Discord.

## Dữ liệu
- Số tin nhắn của người chơi, danh sách giftcode và ID các bài mẫu bot đã đăng lưu trong `levels.db` (SQLite), tự tạo **cạnh file .py**.
- File này phải nằm ở nơi lưu trữ bền vững và cần sao lưu định kỳ. Mất file là mất toàn bộ cấp bậc.
- Bot bật chế độ WAL nên cạnh `levels.db` sẽ có thêm `levels.db-wal` và `levels.db-shm`. **Đừng chỉ copy riêng `levels.db` khi bot đang chạy** vì có thể thiếu dữ liệu mới. Cách sao lưu đúng: `sqlite3 levels.db ".backup levels-backup.db"` (cài bằng `apt install sqlite3`), hoặc dừng bot rồi copy cả 3 file.
- Không đưa `.env` và `levels.db` vào git.

## Chỉnh nội dung (đầu file, không cần đụng vào code)
- `MSG_*`: bài tiếng Việt. `EN_*`: bài tiếng Anh. `MSG_LANG`: bài chọn ngôn ngữ.
- `BUTTONS`: chữ trên nút (không đổi `custom_id`).
- `TICKET_KINDS`, `TXT`: lời mở đầu ticket và câu trả lời của bot theo từng ngôn ngữ.
- `GIFT_ADMIN_KEYS`: role được thêm/xóa giftcode. `CH_GIFT`: kênh bot đăng code mới.
- `ROLE_SPECS`, `RANKS`, `COOLDOWN`, `MIN_LEN`, `COUNT_CATEGORIES`, `LAYOUT`.

## Việc cần làm sau khi chạy
1. Điền link tải game (Android/iOS) và giftcode thật ở cả `MSG_TAIGAME` và `EN_DOWNLOAD`.
2. Kiểm tra lịch trong `MSG_LICH` và `EN_SCHEDULE`. Mốc **20:30 "phát thư thưởng" là giả định**, cần xác nhận lại theo game.
3. Gán role Hokage / Dev Shinobi / Anbu / Hỗ Trợ Viên cho đúng người.
4. Kiểm thử bằng tài khoản phụ: chọn English → chỉ thấy kênh tiếng Anh; xác minh; đổi sang Tiếng Việt → thấy kênh tiếng Việt, vẫn đã xác minh; mở ticket (tài khoản thứ ba **không** được thấy); gửi 1 ảnh trong ticket rồi đóng (transcript `.txt` và ảnh đó phải xuất hiện ở `🧾-log-ticket`); nhắn tin rồi gõ `!rank`; staff `!themcode TEST -` → thấy thông báo ở 2 kênh giftcode, tài khoản phụ gõ `!code` → nhận tin nhắn riêng, rồi `!xoacode TEST`.

## Chưa kiểm chứng
Code đã qua kiểm tra cú pháp, logic phân quyền xem theo ngôn ngữ, đổi ngôn ngữ, cập nhật bài, đếm cấp bậc, đọc ngày hết hạn và lưu tệp ticket trên dữ liệu giả lập, nhưng **chưa chạy thử trên Discord thật**. Hãy thử trên một server test trước khi dùng cho server chính.
