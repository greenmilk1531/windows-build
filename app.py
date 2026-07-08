import os
import sys
import json
import base64
import threading
import subprocess
import requests
from urllib.parse import unquote
import minecraft_launcher_lib
import minecraft_launcher_lib.forge  # 패브릭 대신 포지 모듈 사용
import minecraft_launcher_lib.utils
import customtkinter as ctk
from tkinter import messagebox

# ==========================================
# 런처 전역 설정 경로
# ==========================================
if sys.platform == "win32":
    APP_DATA = os.environ.get("APPDATA")
    MINECRAFT_DIR = os.path.join(APP_DATA, ".minecraft_custom")
elif sys.platform == "darwin":
    MINECRAFT_DIR = os.path.expanduser("~/Library/Application Support/minecraft_custom")
else:
    MINECRAFT_DIR = os.path.expanduser("~/.minecraft_custom")

CONFIG_FILE = os.path.join(MINECRAFT_DIR, "launcher_settings.json")

# ==========================================
# 유틸리티: 비밀번호 단순 인코딩/디코딩
# ==========================================
def encode_pw(pw: str) -> str:
    return base64.b64encode(pw.encode('utf-8')).decode('utf-8')

def decode_pw(pw_encoded: str) -> str:
    try:
        return base64.b64decode(pw_encoded.encode('utf-8')).decode('utf-8')
    except:
        return ""

# ==========================================
# 메인 런처 애플리케이션 클래스
# ==========================================
class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Greenmilk Minecraft Launcher")
        self.geometry("950x650")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # 제어 및 상태 변수 초기화
        self.status_var = ctk.StringVar(value="환영합니다! 런처가 준비되었습니다.")
        self.ram_var = ctk.StringVar(value="4 GB")  # 기본값 4GB
        self.progress_max = 100
        self.is_launching = False

        # 레이아웃 생성 및 데이터 로드
        self.build_ui()
        self.load_config()
        self.load_news()  # 원격 공지사항 불러오기

    def build_ui(self):
        # 1. 왼쪽 사이드바 (로고 및 내비게이션 탭 역할)
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#181818")
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="GREENMILK\nLAUNCHER", 
                                       font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(40, 30))

        # 사이드바 메뉴 버튼 (탭 메뉴 대체)
        self.btn_nav_home = ctk.CTkButton(self.sidebar_frame, text="홈", height=45, fg_color="#2A2A2A",
                                          anchor="w", font=ctk.CTkFont(size=14, weight="bold"),
                                          command=lambda: self.show_frame("home"))
        self.btn_nav_home.pack(fill="x", padx=15, pady=5)

        self.btn_nav_settings = ctk.CTkButton(self.sidebar_frame, text="설정", height=45, fg_color="transparent",
                                              anchor="w", font=ctk.CTkFont(size=14, weight="bold"),
                                              command=lambda: self.show_frame("settings"))
        self.btn_nav_settings.pack(fill="x", padx=15, pady=5)

        # 2. 오른쪽 메인 컨텐츠 영역 컨테이너
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(side="right", fill="both", expand=True)

        # 하단 상태 바 영역 고정 (프레임 전환과 무관하게 상시 노출)
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=25, pady=25)

        self.status_label = ctk.CTkLabel(self.bottom_frame, textvariable=self.status_var, 
                                         font=ctk.CTkFont(size=13), anchor="w")
        self.status_label.pack(side="top", fill="x", pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, height=12, progress_color="#2FA54B")
        self.progress_bar.pack(side="bottom", fill="x")
        self.progress_bar.set(0.0)

        # 홈 프레임과 설정 프레임 각각 빌드
        self.build_home_frame()
        self.build_settings_frame()
        
        # 첫 화면 세팅
        self.show_frame("home")

    def build_home_frame(self):
        self.home_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        
        # 홈 왼쪽: 실시간 원격 소식 확인 패널
        self.home_left = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.home_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        news_title = ctk.CTkLabel(self.home_left, text="최신 소식", font=ctk.CTkFont(size=20, weight="bold"))
        news_title.pack(anchor="nw", pady=(10, 20))

        self.news_label = ctk.CTkLabel(self.home_left, text="공지사항을 불러오는 중...", justify="left", 
                                       font=ctk.CTkFont(size=14), text_color="#CCCCCC", wraplength=420)
        self.news_label.pack(anchor="nw")

        # 홈 오른쪽: 로그인 카드 패널
        self.login_card = ctk.CTkFrame(self.home_frame, width=300, corner_radius=15, fg_color="#242424")
        self.login_card.pack(side="right", fill="y", padx=10, pady=10)
        self.login_card.pack_propagate(False)

        login_title = ctk.CTkLabel(self.login_card, text="계정 로그인", font=ctk.CTkFont(size=18, weight="bold"))
        login_title.pack(pady=(40, 20))

        self.entry_email = ctk.CTkEntry(self.login_card, width=250, height=40, placeholder_text="이메일")
        self.entry_email.pack(pady=10)

        self.entry_pw = ctk.CTkEntry(self.login_card, width=250, height=40, placeholder_text="비밀번호", show="*")
        self.entry_pw.pack(pady=10)

        self.remember_var = ctk.BooleanVar(value=False)
        self.check_remember = ctk.CTkCheckBox(self.login_card, text="로그인 정보 저장", 
                                              variable=self.remember_var, font=ctk.CTkFont(size=13))
        self.check_remember.pack(anchor="w", padx=25, pady=10)

        self.btn_launch = ctk.CTkButton(self.login_card, text="게임 실행", height=50, width=250,
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        fg_color="#2FA54B", hover_color="#248A3C",
                                        command=self.start_launch_thread)
        self.btn_launch.pack(side="bottom", pady=30)

    def build_settings_frame(self):
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        
        settings_title = ctk.CTkLabel(self.settings_frame, text="런처 설정", font=ctk.CTkFont(size=20, weight="bold"))
        settings_title.pack(anchor="nw", pady=(10, 20))
        
        ram_group = ctk.CTkFrame(self.settings_frame, fg_color="#242424", corner_radius=10)
        ram_group.pack(fill="x", pady=10, padx=5)
        
        ram_label = ctk.CTkLabel(ram_group, text="최대 RAM 할당량 (-Xmx)", font=ctk.CTkFont(size=14, weight="bold"))
        ram_label.pack(side="left", padx=20, pady=20)
        
        self.ram_option = ctk.CTkOptionMenu(ram_group, values=["2 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB"],
                                            variable=self.ram_var, command=lambda _: self.save_config())
        self.ram_option.pack(side="right", padx=20, pady=20)

    def show_frame(self, frame_name):
        if frame_name == "home":
            self.settings_frame.pack_forget()
            self.home_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)
            self.btn_nav_home.configure(fg_color="#2A2A2A")
            self.btn_nav_settings.configure(fg_color="transparent")
        elif frame_name == "settings":
            self.home_frame.pack_forget()
            self.settings_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)
            self.btn_nav_home.configure(fg_color="transparent")
            self.btn_nav_settings.configure(fg_color="#2A2A2A")

    def load_news(self):
        def fetch():
            try:
                res = requests.get("https://file.gmilk.kr/1/minecraft/modserver/update.txt", timeout=5)
                if res.status_code == 200:
                    self.news_label.configure(text=res.text.strip())
                else:
                    self.news_label.configure(text="공지사항 로드 실패")
            except Exception as e:
                self.news_label.configure(text=f"공지사항을 동기화할 수 없습니다.\n오류내용: {e}")
        
        threading.Thread(target=fetch, daemon=True).start()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if "ram" in data:
                    self.ram_var.set(data["ram"])
                
                if data.get("remember_me"):
                    self.remember_var.set(True)
                    self.entry_email.insert(0, data.get("email", ""))
                    self.entry_pw.insert(0, decode_pw(data.get("password", "")))
            except Exception as e:
                print(f"런처 구성 데이터 로드 실패: {e}")

    def save_config(self):
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        
        data = {
            "ram": self.ram_var.get(),
            "remember_me": self.remember_var.get(),
            "email": self.entry_email.get() if self.remember_var.get() else "",
            "password": encode_pw(self.entry_pw.get()) if self.remember_var.get() else ""
        }
            
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"런처 구성 데이터 저장 오류: {e}")

    def update_status(self, text: str):
        self.status_var.set(text)
        self.update_idletasks()

    def update_progress(self, value: int):
        if self.progress_max > 0:
            self.progress_bar.set(value / self.progress_max)
        self.update_idletasks()

    def set_max_progress(self, value: int):
        self.progress_max = value
        self.update_idletasks()

    def start_launch_thread(self):
        if self.is_launching: return
        
        email = self.entry_email.get()
        pw = self.entry_pw.get()

        if not email or not pw:
            messagebox.showwarning("입력 오류", "이메일과 비밀번호를 정확히 기입하십시오.")
            return

        self.is_launching = True
        self.btn_launch.configure(state="disabled", text="실행 준비 중...", fg_color="#555555")
        
        self.save_config()

        threading.Thread(target=self.launch_game, args=(email, pw), daemon=True).start()

    def download_mods(self, mc_dir: str):
        mods_dir = os.path.join(mc_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        
        self.update_status("원격 서버 모드 파일 동기화 체크 중...")
        try:
            txt_url = "https://file.gmilk.kr/1/minecraft/modserver/mods.txt"
            res = requests.get(txt_url, timeout=10)
            if res.status_code != 200:
                raise Exception("원격 모드 체크 파일 응답 실패")
            mod_urls = [line.strip() for line in res.text.splitlines() if line.strip()]
        except Exception as e:
            print(f"모드 리스트 동기화 실패 무시 처리: {e}")
            return
        
        for url in mod_urls:
            filename = unquote(url.split("/")[-1])
            target_path = os.path.join(mods_dir, filename)
            
            if not os.path.exists(target_path):
                self.update_status(f"신규 필수 모드 다운로드 중: {filename}")
                try:
                    response = requests.get(url, stream=True, timeout=15)
                    if response.status_code == 200:
                        with open(target_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk: f.write(chunk)
                except Exception as e:
                    print(f"지정 모드 ({filename}) 다운로드 예외 발생: {e}")

    def launch_game(self, username, password):
        try:
            # 1. 외부 호환용 의존성 라이브러리 다운로드 및 검증
            injector_path = os.path.abspath("authlib-injector.jar")
            if not os.path.exists(injector_path):
                self.update_status("Authlib Injector 구성 요소 다운로드 중...")
                url = "https://file.gmilk.kr/1/daisy/authlib-injector.jar"
                response = requests.get(url, stream=True)
                with open(injector_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)

            # 2. 지정 API 통합 Yggdrasil 커스텀 인증 연동
            self.update_status("인증서버와 통신중...")
            auth_url = 'https://min.gmilk.kr/index.php/api/yggdrasil/authserver/authenticate'
            payload = {"username": username, "password": password, "agent": {"name": "Minecraft", "version": 1}}
            
            response = requests.post(auth_url, json=payload, headers={'Content-Type': 'application/json'})
            auth_data = response.json()

            if response.status_code != 200 or "accessToken" not in auth_data:
                raise Exception(auth_data.get("errorMessage", "보안 서버 인증에 실패했습니다. 계정 정보를 다시 확인해 주세요."))

            access_token = auth_data["accessToken"]
            uuid = auth_data["selectedProfile"]["id"]
            profile_name = auth_data["selectedProfile"]["name"]

            # 3. 환경 구성을 위한 타겟 에셋 설치 자동화 (Forge 버전으로 변경)
            version_number = "1.20.1" 
            callback_dict = {
                "setStatus": self.update_status,
                "setProgress": self.update_progress,
                "setMax": self.set_max_progress
            }

            self.update_status("최신 버전 정보 확인 중...")
            # 1.20.1에 해당하는 최신 포지 버전을 자동으로 검색 (예: 1.20.1-47.2.18)
            forge_version = minecraft_launcher_lib.forge.find_forge_version(version_number)
            if not forge_version:
                raise Exception(f"{version_number}에 해당하는 Forge 버전을 찾을 수 없습니다.")

            installed_versions = minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR)
            installed_version = next((v["id"] for v in installed_versions if "forge" in v["id"].lower() and version_number in v["id"]), None)

            if not (installed_version and os.path.exists(os.path.join(MINECRAFT_DIR, "versions", installed_version))):
                self.update_status("클라이언트 런타임 및 Forge 원격 다운로드 중... (시간이 소요될 수 있습니다)")
                
                # 포지 설치 진행
                minecraft_launcher_lib.forge.install_forge_version(forge_version, MINECRAFT_DIR, callback=callback_dict)
                
                # 설치 완료 후 버전 디렉토리 이름을 다시 갱신
                installed_versions = minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR)
                installed_version = next((v["id"] for v in installed_versions if "forge" in v["id"].lower() and version_number in v["id"]), None)

            if not installed_version:
                raise Exception("Forge 설치 로직이 완료되었으나, 해당 버전을 찾을 수 없습니다.")

            # (이전 패브릭 전용 4번 JSON 보정 패치 단계는 포지에서 불필요하므로 제거됨)

            # 4. 최신 추가 및 제거 빌드 모드 백그라운드 체크
            self.download_mods(MINECRAFT_DIR)

            # 5. 최종 서브 프로세스 실행 파라미터 빌드
            self.update_status("JVM 최적화 파라미터 바인딩 및 런타임 조율 중...")
            yggdrasil_api_url = "https://min.gmilk.kr/index.php/api/yggdrasil"
            
            try:
                ram_gb = self.ram_var.get().split()[0]
            except:
                ram_gb = "4"
                
            options = {
                "username": profile_name,
                "uuid": uuid,
                "token": access_token,
                "jvmArguments": [
                    f"-Xmx{ram_gb}G", "-Xms2G",
                    f"-javaagent:{injector_path}={yggdrasil_api_url}"
                ]
            }
            if sys.platform == "darwin": options["jvmArguments"].append("-XstartOnFirstThread")

            # 구동 커맨드 생성
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(installed_version, MINECRAFT_DIR, options)

            self.update_status(f"반갑습니다, {profile_name}님!")
            self.progress_bar.set(1.0)
            
            subprocess.Popen(minecraft_command)

        except Exception as e:
            self.update_status(f"클라이언트 구동 중 치명적 오류: {str(e)}")
            messagebox.showerror("구동 프로세스 에러", str(e))
        finally:
            self.is_launching = False
            self.btn_launch.configure(state="normal", text="게임 실행", fg_color="#2FA54B")

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()