# Team Dashboard (bản local + deploy)

Bản clone của trang "Team Dashboard" (Streamlit) — cùng bố cục, cùng 6 tab
(Tổng Quan, Tuyển Thủ, Tướng, Lịch Sử Trận, So Sánh, Hồ Sơ), cùng các biểu
đồ/bảng. Khác với bản gốc (lấy dữ liệu online), bản này **100% dữ liệu do
bạn/đội tự nhập tay** (không có dữ liệu mẫu/giả):

- Tab **👥 Tuyển Thủ**: thêm từng tuyển thủ (Tên, Server, Tên tài khoản,
  Rank, Sao).
- Tab **📋 Lịch Sử Trận**: thêm/sửa/xóa từng trận đấu (chọn tuyển thủ + tài
  khoản, tướng, ngày giờ, kết quả, chỉ số...). Bấm chọn 1 dòng trong bảng để
  hiện nút **✎ Sửa** / **✕ Xóa** trận đó.

Tab **🪪 Hồ Sơ** **không cần nhập gì thêm** — tự tính từ dữ liệu ở tab
Tuyển Thủ + Lịch Sử Trận, y hệt cách tab Tuyển Thủ/Tướng hoạt động.

Dữ liệu được lưu trong một **Google Sheet** (không phải file CSV trên máy)
— nhờ vậy app chạy được cả ở local lẫn deploy lên Internet, và mọi người
(bạn + đội) đều thấy/sửa chung một dữ liệu, tự động lưu lại vĩnh viễn.

## 1. Cài đặt (chạy local)

Cần Python 3.10+ đã cài trên máy.

```bash
cd team-dashboard
pip install -r requirements.txt
```

## 2. Kết nối Google Sheets (bắt buộc — làm 1 lần)

App không chạy được nếu chưa có bước này (sẽ báo lỗi thiếu `secrets`). Làm
theo đúng thứ tự:

### 2.1. Tạo Service Account trên Google Cloud

1. Vào https://console.cloud.google.com/ (đăng nhập bằng Gmail bất kỳ).
2. Tạo project mới (góc trên bên trái, chỗ tên project → **New Project** →
   đặt tên gì cũng được, ví dụ `team-dashboard` → **Create**).
3. Vào ô tìm kiếm ở trên, gõ **Google Sheets API** → bấm vào kết quả →
   bấm **Enable**. Làm tương tự với **Google Drive API**.
4. Vào ô tìm kiếm, gõ **Service Accounts** → bấm **Create Service Account**
   → đặt tên (ví dụ `team-dashboard-bot`) → **Create and Continue** → phần
   role có thể bỏ qua (**Continue**) → **Done**.
5. Trong danh sách Service Accounts vừa tạo, bấm vào nó → tab **Keys** →
   **Add Key** → **Create new key** → chọn **JSON** → **Create**. Một file
   `.json` sẽ tự tải về máy bạn — **giữ file này cẩn thận, không chia sẻ
   cho ai, không đưa lên GitHub**.
6. Mở file JSON đó bằng Notepad, bạn sẽ thấy các trường như `project_id`,
   `private_key`, `client_email`... — cần dùng ở bước 2.3.

### 2.2. Tạo Google Sheet

1. Vào https://sheets.google.com → tạo 1 spreadsheet mới, đặt tên gì cũng
   được (ví dụ `TS Team Data`).
2. Copy **Sheet ID** từ URL trên trình duyệt, ví dụ:
   `https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit`
   → ID là đoạn `1AbCdEfGhIjKlMnOpQrStUvWxYz`.
3. Bấm nút **Share** (Chia sẻ) ở góc trên phải → dán **client_email** lấy
   từ file JSON ở bước 2.1 (dạng `...@...iam.gserviceaccount.com`) vào ô
   mời → chọn quyền **Editor** → **Send/Share**. (Không cần tạo sẵn tab
   "matches"/"players" — app tự tạo khi chạy lần đầu.)

### 2.3. Điền secrets để chạy local

1. Trong folder `team-dashboard`, copy file `.streamlit/secrets.toml.example`
   thành `.streamlit/secrets.toml` (bỏ đuôi `.example`).
2. Mở `secrets.toml` bằng Notepad, điền:
   - `SHEET_ID` = ID lấy ở bước 2.2.
   - Từng dòng trong `[gcp_service_account]` = từng giá trị tương ứng lấy
     từ file JSON (mở file JSON, copy y nguyên giá trị của `project_id`,
     `private_key_id`, `private_key`, `client_email`, `client_id`,
     `client_x509_cert_url` — dán đúng vào chỗ tương ứng, giữ nguyên dấu
     `\n` trong `private_key`).
3. Lưu file lại. File này chỉ nằm trên máy bạn, **không commit lên GitHub**
   (đã được `.gitignore` loại trừ sẵn).

## 3. Chạy local

```bash
streamlit run app.py
```

(nếu máy báo `'streamlit' is not recognized`, dùng `python -m streamlit run app.py` thay thế)

Trình duyệt sẽ tự mở `http://localhost:8501`. Nếu không, mở link đó thủ công.

## 4. Cách quản lý dữ liệu

**Tuyển thủ** (tab 👥 Tuyển Thủ): bấm **➕ Thêm tuyển thủ / tài khoản mới** →
điền Tên, Server, Tên tài khoản, Rank, Sao → **💾 Lưu tuyển thủ**. Một tuyển
thủ có thể có nhiều tài khoản (nhiều server) — thêm nhiều lần, cùng Tên,
khác Tài khoản/Server. Mỗi dòng có nút **✎** để sửa lại thông tin (đổi tên,
server, tài khoản, rank, sao — bấm lại **✎** lần nữa hoặc **❌ Hủy** để đóng
form sửa) và nút **✕** để xóa từng tuyển thủ.

Bảng **Bảng Tổng Hợp Tuyển Thủ** (cột **Lượt chơi / Ranked / WR% / KDA / MVP% /
Damage TB / Gold TB**) **tự động tính toán** từ dữ liệu trận đấu — không nhập
tay các cột này.

**Trận đấu** (tab 📋 Lịch Sử Trận): bấm **➕ Thêm trận đấu mới** → chọn Tuyển
thủ + Tài khoản → điền ngày giờ, tướng, mode, kết quả (1=Thắng/0=Thua), Phút,
Kill/Death/Assist, Damage/Gold, MVP → **💾 Lưu trận đấu**. Bảng danh sách trận
đấu bên dưới hiển thị đủ các cột này (kèm ảnh Tướng) — bấm chọn 1 dòng trong
bảng để hiện nút **✎ Sửa trận đã chọn** (mở lại form với dữ liệu cũ để sửa,
giống hệt form thêm mới) và **✕ Xóa trận đã chọn**.

Tab **🪪 Hồ Sơ**: chọn 1 tuyển thủ để xem sâu — KPI (Lượt chơi/Ranked/Hero
Pool/WR%/KDA/MVP%), bảng **Hero Pool** (từng tướng đã chơi + số trận/WR%/
KDA/MVP%), 2 biểu đồ theo ngày (Ranked vs Normal, WinRate) và **Rank Hiện
Tại** của tuyển thủ đó — không cần nhập gì thêm, tự tính từ dữ liệu trận đấu
+ tuyển thủ đã có.

Vì dữ liệu nằm trên Google Sheet dùng chung, **chạy local và bản deploy trên
Internet luôn thấy cùng một dữ liệu** — không cần đồng bộ thủ công.

## 5. Deploy lên Internet (để máy khác cùng truy cập)

Sau khi đã làm xong mục 2 (Google Sheets) và test chạy local OK, làm tiếp:

### 5.1. Đưa code lên GitHub

1. Tạo tài khoản GitHub (nếu chưa có) tại https://github.com.
2. Tạo repo mới (**New repository**), đặt tên (ví dụ `team-dashboard`), để
   **Private** (khuyên dùng, vì code có cấu trúc secrets dù không chứa giá
   trị thật) hoặc Public đều được.
3. Upload toàn bộ nội dung folder `team-dashboard` lên repo đó — cách dễ
   nhất cho người không quen dòng lệnh: vào trang repo trên GitHub → **Add
   file → Upload files** → kéo thả toàn bộ file/folder vào (**trừ**
   `.streamlit/secrets.toml` nếu bạn đã tạo — không upload file này, chỉ
   upload `secrets.toml.example`) → **Commit changes**.

### 5.2. Deploy trên Streamlit Community Cloud

1. Vào https://share.streamlit.io → đăng nhập bằng tài khoản GitHub.
2. Bấm **Create app** → **Deploy a public app from GitHub** (hoặc private,
   nếu repo bạn để Private, cấp quyền cho Streamlit truy cập repo đó khi
   được hỏi).
3. Chọn repo `team-dashboard`, branch `main`, main file path `app.py` →
   trước khi bấm Deploy, mở **Advanced settings**.
4. Trong **Advanced settings → Secrets**, dán **toàn bộ nội dung** file
   `secrets.toml` thật của bạn (không phải file `.example`) vào ô đó —
   đây chính là nơi thay thế cho việc có file `secrets.toml` trên máy.
5. Bấm **Deploy**. Đợi khoảng 1-2 phút để app build xong.
6. Bạn sẽ có 1 link dạng `https://<tên-app>.streamlit.app` — gửi link này
   cho bất kỳ ai, họ mở bằng trình duyệt là vào được, không cần cài gì.

### 5.3. Sau khi deploy

- Mỗi khi bạn sửa code và muốn cập nhật bản online: chỉ cần đẩy thay đổi
  lên GitHub (upload lại file đã sửa), Streamlit Cloud tự phát hiện và
  build lại app.
- Dữ liệu (tuyển thủ/trận đấu) **không mất** khi app khởi động lại, vì nó
  nằm trên Google Sheet chứ không phải trên ổ đĩa của app.
- App có thể "ngủ" nếu không ai truy cập một thời gian — người dùng chỉ
  cần mở link, chờ vài giây để nó "thức dậy" là dùng bình thường.
- Muốn xem/sửa dữ liệu thô: mở thẳng Google Sheet bạn đã tạo, có 2 tab
  `matches` và `players`.

## 6. Cấu trúc project

```
team-dashboard/
├── app.py                     # App chính — sidebar + 6 tab (Tổng Quan, Tuyển Thủ,
│                               # Tướng, Lịch Sử Trận, So Sánh, Hồ Sơ)
├── store.py                    # Lớp lưu trữ: đọc/ghi Google Sheet (tab matches/
│                               # players) qua gspread; add/delete/clear cho cả
│                               # trận đấu và tuyển thủ
├── data.py                     # Hằng số roster/game (server, tướng, mode, rank...)
│                               # + vài hàm tổng hợp KPI dùng chung
├── theme.py                     # CSS + các "kpi-card" cho giao diện tối
├── charts.py                     # Các biểu đồ Plotly (bar kép trục, radar...)
├── generate_avatars.py             # Script tạo ảnh đại diện tướng/tuyển thủ (đã chạy sẵn,
│                               # kết quả nằm trong assets/)
├── assets/                     # Ảnh đại diện tướng (avatars/) và tuyển thủ (players/)
├── .streamlit/
│   ├── config.toml               # Theme tối mặc định cho Streamlit
│   └── secrets.toml.example       # Mẫu file secrets — copy thành secrets.toml và
│                               # điền giá trị thật (không commit file thật)
├── .gitignore                   # Loại trừ secrets.toml thật khi đẩy lên GitHub
└── requirements.txt
```

## 7. Đổi tên team / tướng / server

Mở `data.py`, sửa các biến ở đầu file:

- `TEAM_NAME` — tên team hiển thị ở góc trên sidebar (hiện là "TS").
- `HEROES` — danh sách đầy đủ 128 tướng hiện tại (dùng trong form thêm trận
  đấu), lấy theo trang chính thức
  https://lienquan.garena.vn/hoc-vien/tuong-skin/.
- `SERVERS` — danh sách server lọc ở sidebar (đang là VN/TH/TW).

Tuyển thủ giờ nhập tay hoàn toàn trong app (tab Tuyển Thủ), không cần sửa
code. Nếu thêm tướng mới vào `HEROES` mà chưa có ảnh thật, chạy lại
`python generate_avatars.py` — script sẽ tự tạo ảnh placeholder (hình tròn
màu + chữ cái đầu) cho riêng tướng mới đó, không đụng tới các ảnh thật đã có
sẵn trong `assets/avatars/`.

## 8. Ghi chú

- Ảnh đại diện **tướng** (`assets/avatars/`) là ảnh thật, tải từ trang chính
  thức Garena Liên Quân Mobile (https://lienquan.garena.vn/hoc-vien/tuong-skin/),
  cắt tròn 96x96. Ảnh đại diện **tuyển thủ** (`assets/players/`) vẫn là hình
  tròn màu + chữ cái đầu tự tạo (vì tuyển thủ không có ảnh chính thức).
- File `secrets.toml` (thật) chứa khóa bí mật để ghi vào Google Sheet của
  bạn — không chia sẻ, không đưa lên GitHub, không dán vào bất kỳ đâu công
  khai. Nếu lỡ lộ, vào lại Google Cloud Console → Service Account → Keys →
  xóa key cũ, tạo key mới, cập nhật lại secrets.
- Muốn xóa hết dữ liệu để làm lại: xóa từng dòng bằng nút **✕** (tuyển thủ)
  hoặc chọn dòng rồi bấm nút xóa (trận đấu) ngay trong app, hoặc xóa trực
  tiếp nội dung tab tương ứng trên Google Sheet.
