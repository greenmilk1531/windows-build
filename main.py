import tkinter as tk
from tkinter import messagebox, filedialog
import yt_dlp
import threading

def download_video():
    url = url_entry.get().strip()
    if not url:
        messagebox.showwarning("경고", "유튜브 URL을 입력해 주세요.")
        return
    
    # 저장할 디렉토리 선택
    save_path = filedialog.askdirectory()
    if not save_path:
        return
    
    # 다운로드 중 UI 차단을 막기 위해 스레드(Thread) 사용
    status_label.config(text="다운로드 시작 중...", fg="blue")
    download_btn.config(state=tk.DISABLED)
    
    def _download():
        ydl_opts = {
            # 가장 좋은 화질의 비디오와 오디오를 합쳐서 mp4로 저장
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            status_label.config(text="다운로드 완료!", fg="green")
            messagebox.showinfo("성공", "동영상이 성공적으로 다운로드되었습니다.")
        except Exception as e:
            status_label.config(text="오류 발생", fg="red")
            messagebox.showerror("오류", f"다운로드 중 오류가 발생했습니다:\n{e}")
        finally:
            download_btn.config(state=tk.NORMAL)

    # 스레드 시작
    threading.Thread(target=_download, daemon=True).start()

# GUI 창 설정
root = tk.Tk()
root.title("유튜브 MP4 다운로더")
root.geometry("500x200")
root.resizable(False, False)

# UI 요소 구성
title_label = tk.Label(root, text="유튜브 동영상 다운로더", font=("맑은 고딕", 16, "bold"))
title_label.pack(pady=10)

frame = tk.Frame(root)
frame.pack(pady=10, fill='x', px=20)

url_label = tk.Label(frame, text="URL:", font=("맑은 고딕", 10))
url_label.pack(side=tk.LEFT, padx=5)

url_entry = tk.Entry(frame, font=("맑은 고딕", 10))
url_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)

download_btn = tk.Button(root, text="다운로드 및 저장", font=("맑은 고딕", 11, "bold"), bg="#ff0000", fg="white", command=download_video)
download_btn.pack(pady=10)

status_label = tk.Label(root, text="", font=("맑은 고딕", 10))
status_label.pack(pady=5)

# 프로그램 실행
root.mainloop()
