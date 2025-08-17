# YouTube Highlight Maker

Ứng dụng desktop này giúp bạn tự động tạo các đoạn video highlight từ bất kỳ video YouTube nào. Công cụ sử dụng thuật toán phân tích âm thanh để tìm ra những khoảnh khắc nổi bật nhất và cắt chúng ra thành các clip ngắn.

## Yêu cầu

Để chạy ứng dụng này, bạn cần có:

1.  **Python 3.7+**: Tải và cài đặt Python từ trang chính thức. Hãy đảm bảo bạn chọn tùy chọn **"Add Python to PATH"** trong quá trình cài đặt.
2.  **FFmpeg**: Đây là công cụ cần thiết để xử lý và cắt video. 
      * Đã có sẵn cùng thư mục với ai.py
      * Mở ứng dụng, vào phần **Cài đặt**, và chỉ định đường dẫn đến file `ffmpeg.exe` hoặc thư mục chứa nó (ví dụ: `C:\ffmpeg\bin`).

## Hướng dẫn cài đặt & Chạy ứng dụng

Bạn có thể chạy ứng dụng trực tiếp từ mã nguồn mà không cần cài đặt các gói phụ thuộc một cách thủ công.

1.  **Clone (tải) dự án**:
    Mở `cmd` hoặc `PowerShell` và chạy lệnh sau để tải dự án về máy của bạn:

    ```bash
    git clone https://github.com/LINHTRAN9x/YouTube-Highlight-Maker--Dark-.git
    cd YouTube-Highlight-Maker--Dark-
    ```

2.  **Chạy ứng dụng**:
    Chạy file `ai.py` bằng lệnh:

    ```bash
    python ai.py
    ```

    Khi bạn chạy lần đầu, ứng dụng sẽ tự động kiểm tra và cài đặt các thư viện Python cần thiết. Sau khi cài đặt xong, giao diện của ứng dụng sẽ tự động xuất hiện.

## Giao diện & Cách sử dụng

  - **YouTube URL**: Dán link video YouTube mà bạn muốn cắt.
  - **Chất lượng video**: Chọn độ phân giải cho video đầu ra (1080p hoặc 720p).
  - **Số lượng clip**: Chọn số đoạn highlight mà bạn muốn tạo.
  - **Thời lượng (giây)**: Đặt độ dài cho mỗi clip highlight.
  - **Tỷ lệ khung hình**: Tùy chỉnh tỷ lệ (Gốc, Dọc 9:16) để tạo video phù hợp cho các nền tảng như TikTok, Shorts, hoặc Reels.
  - **Thư mục đầu ra**: Chọn nơi lưu các file highlight sau khi hoàn thành.
  - Nhấn nút **"Tạo Highlight"** để bắt đầu.

Tất cả các file video highlight đã tạo sẽ được lưu trong **Thư viện**, nơi bạn có thể xem lại hoặc mở chúng một cách dễ dàng.

## Tác giả

  ylinhtran
