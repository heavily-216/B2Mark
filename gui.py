# gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import threading
from watermark import B2MarkEmbedder, B2MarkDetector

# --- 설정값 (고정) ---
SECRET_KEY = "grad_project_key"
TARGET_COL = "price"
REF_COLS = ["area", "floor"]

class B2MarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B²Mark Watermarking System")
        self.root.geometry("500x450")

        # 탭(Tab) 만들기 (삽입 / 검출)
        tab_control = ttk.Notebook(root)
        self.tab_embed = ttk.Frame(tab_control)
        self.tab_detect = ttk.Frame(tab_control)
        
        tab_control.add(self.tab_embed, text='Watermark Embedding (판매용)')
        tab_control.add(self.tab_detect, text='Watermark Detection (추적용)')
        tab_control.pack(expand=1, fill="both")

        # UI 구성요소 배치
        self.create_embed_tab()
        self.create_detect_tab()

        # 로그 창 (하단)
        self.log_area = tk.Text(root, height=8, state='disabled', bg="#f0f0f0")
        self.log_area.pack(fill="x", padx=5, pady=5)

    def log(self, message):
        """로그 창에 메시지 출력"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def select_file(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def create_embed_tab(self):
        frame = ttk.LabelFrame(self.tab_embed, text=" 워터마크 삽입 설정 ")
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # 1. 원본 파일 선택
        ttk.Label(frame, text="원본 CSV 파일:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_embed_input = ttk.Entry(frame, width=30)
        self.ent_embed_input.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="찾기", command=lambda: self.select_file(self.ent_embed_input)).grid(row=0, column=2)

        # 2. 구매자 ID
        ttk.Label(frame, text="구매자 ID (비트열):").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_buyer_id = ttk.Entry(frame, width=30)
        self.ent_buyer_id.insert(0, "10110") # 기본값
        self.ent_buyer_id.grid(row=1, column=1, padx=5)

        # 3. 저장할 파일명
        ttk.Label(frame, text="저장할 파일명:").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_embed_output = ttk.Entry(frame, width=30)
        self.ent_embed_output.insert(0, "sold_data.csv")
        self.ent_embed_output.grid(row=2, column=1, padx=5)

        # 4. 실행 버튼
        ttk.Button(frame, text="🚀 워터마킹 실행", command=self.run_embed).grid(row=3, column=0, columnspan=3, pady=20, sticky="ew")

    def create_detect_tab(self):
        frame = ttk.LabelFrame(self.tab_detect, text=" 범인 추적 설정 ")
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # 1. 의심 파일 선택
        ttk.Label(frame, text="유출된 CSV 파일:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_detect_input = ttk.Entry(frame, width=30)
        self.ent_detect_input.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="찾기", command=lambda: self.select_file(self.ent_detect_input)).grid(row=0, column=2)

        # 2. 메타데이터 파일 선택
        ttk.Label(frame, text="메타데이터 (JSON):").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_meta_input = ttk.Entry(frame, width=30)
        self.ent_meta_input.grid(row=1, column=1, padx=5)
        ttk.Button(frame, text="찾기", command=lambda: self.select_file(self.ent_meta_input)).grid(row=1, column=2)

        # 3. 비트 길이
        ttk.Label(frame, text="ID 길이:").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_bit_len = ttk.Entry(frame, width=30)
        self.ent_bit_len.insert(0, "5")
        self.ent_bit_len.grid(row=2, column=1, padx=5)

        # 4. 실행 버튼
        ttk.Button(frame, text="🔍 범인 색출 시작", command=self.run_detect).grid(row=3, column=0, columnspan=3, pady=20, sticky="ew")

    def run_embed(self):
        input_path = self.ent_embed_input.get()
        output_path = self.ent_embed_output.get()
        buyer_id = self.ent_buyer_id.get()

        if not input_path or not output_path or not buyer_id:
            messagebox.showerror("오류", "모든 필드를 입력해주세요.")
            return

        self.log(f"[*] 워터마킹 시작... (Buyer: {buyer_id})")
        
        try:
            embedder = B2MarkEmbedder(secret_key=SECRET_KEY)
            meta_data = embedder.embed(input_path, output_path, buyer_id, TARGET_COL, REF_COLS)
            
            # 메타데이터 저장
            meta_path = output_path + ".meta.json"
            with open(meta_path, "w") as f:
                json.dump(meta_data, f)
            
            self.log(f"[+] 성공! 파일 저장됨: {output_path}")
            self.log(f"[+] 메타데이터 저장됨: {meta_path}")
            messagebox.showinfo("성공", "워터마킹이 완료되었습니다!")
            
        except Exception as e:
            self.log(f"[-] 오류 발생: {str(e)}")
            messagebox.showerror("오류", str(e))

    def run_detect(self):
        input_path = self.ent_detect_input.get()
        meta_path = self.ent_meta_input.get()
        bit_len = self.ent_bit_len.get()

        if not input_path or not meta_path:
            messagebox.showerror("오류", "파일을 모두 선택해주세요.")
            return

        self.log(f"[*] 추적 시작... (File: {os.path.basename(input_path)})")

        try:
            with open(meta_path, "r") as f:
                meta_data = json.load(f)
            
            detector = B2MarkDetector(secret_key=SECRET_KEY)
            detected_id = detector.detect(input_path, meta_data, int(bit_len), TARGET_COL, REF_COLS)
            
            self.log(f"\n[!!!] 검출 결과: 범인의 ID는 [{detected_id}] 입니다.")
            messagebox.showinfo("검출 완료", f"검출된 ID: {detected_id}")

        except Exception as e:
            self.log(f"[-] 오류 발생: {str(e)}")
            messagebox.showerror("오류", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = B2MarkApp(root)
    root.mainloop()