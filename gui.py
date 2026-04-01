# -*- coding: utf-8 -*-
# gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import tempfile
from pathlib import Path
from watermark import insert, detect, WatermarkOptions

# --- 설정값 (고정) ---
SECRET_KEY = "grad_project_key"
TARGET_COL = "price"
REF_COLS = ("area", "floor")

class B2MarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B²Mark Watermarking System")
        self.root.geometry("560x540")

        # 탭(Tab) 만들기 (삽입 / 검출 / DOV)
        tab_control = ttk.Notebook(root)
        self.tab_embed = ttk.Frame(tab_control)
        self.tab_detect = ttk.Frame(tab_control)
        self.tab_dov = ttk.Frame(tab_control)
        
        tab_control.add(self.tab_embed, text='Watermark Embedding (판매용)')
        tab_control.add(self.tab_detect, text='Watermark Detection (추적용)')
        tab_control.add(self.tab_dov, text='Data Ownership Verification (DOV)')
        tab_control.pack(expand=1, fill="both")

        # UI 구성요소 배치
        self.create_embed_tab()
        self.create_detect_tab()
        self.create_dov_tab()

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

    def select_json_file(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
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
        ttk.Button(frame, text="찾기", command=lambda: self.select_json_file(self.ent_meta_input)).grid(row=1, column=2)

        # 3. 비트 길이
        ttk.Label(frame, text="ID 길이:").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_bit_len = ttk.Entry(frame, width=30)
        self.ent_bit_len.insert(0, "5")
        self.ent_bit_len.grid(row=2, column=1, padx=5)

        # 4. 실행 버튼
        ttk.Button(frame, text="🔍 범인 색출 시작", command=self.run_detect).grid(row=3, column=0, columnspan=3, pady=20, sticky="ew")

    def create_dov_tab(self):
        frame = ttk.LabelFrame(self.tab_dov, text=" 데이터 소유권 검증(DOV) 설정 ")
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # 1. 의심 파일 선택
        ttk.Label(frame, text="유출된 CSV 파일:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_dov_input = ttk.Entry(frame, width=35)
        self.ent_dov_input.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="찾기", command=lambda: self.select_file(self.ent_dov_input)).grid(row=0, column=2)

        # 2. 메타데이터 파일 선택
        ttk.Label(frame, text="메타데이터 (JSON):").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_dov_meta = ttk.Entry(frame, width=35)
        self.ent_dov_meta.grid(row=1, column=1, padx=5)
        ttk.Button(frame, text="찾기", command=lambda: self.select_json_file(self.ent_dov_meta)).grid(row=1, column=2)

        # 3. 주장 구매자 ID
        ttk.Label(frame, text="주장 구매자 ID:").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_dov_claimed_id = ttk.Entry(frame, width=35)
        self.ent_dov_claimed_id.insert(0, "10110")
        self.ent_dov_claimed_id.grid(row=2, column=1, padx=5)

        # 4. 비트 길이
        ttk.Label(frame, text="ID 길이:").grid(row=3, column=0, sticky="w", pady=5)
        self.ent_dov_bit_len = ttk.Entry(frame, width=35)
        self.ent_dov_bit_len.insert(0, "5")
        self.ent_dov_bit_len.grid(row=3, column=1, padx=5)

        # 5. Z-threshold
        ttk.Label(frame, text="Z 임계값 (bit=1):").grid(row=4, column=0, sticky="w", pady=5)
        self.ent_dov_z = ttk.Entry(frame, width=35)
        self.ent_dov_z.insert(0, "1.645")
        self.ent_dov_z.grid(row=4, column=1, padx=5)

        # 6. 최소 일치율
        ttk.Label(frame, text="최소 일치율 (0~1):").grid(row=5, column=0, sticky="w", pady=5)
        self.ent_dov_ratio = ttk.Entry(frame, width=35)
        self.ent_dov_ratio.insert(0, "0.8")
        self.ent_dov_ratio.grid(row=5, column=1, padx=5)

        # 7. 실행 버튼
        ttk.Button(frame, text="✅ DOV 검증 시작", command=self.run_dov).grid(
            row=6, column=0, columnspan=3, pady=20, sticky="ew"
        )

    def run_embed(self):
        input_path = self.ent_embed_input.get()
        output_path = self.ent_embed_output.get()
        buyer_id = self.ent_buyer_id.get()

        if not input_path or not output_path or not buyer_id:
            messagebox.showerror("오류", "모든 필드를 입력해주세요.")
            return

        self.log(f"[*] 워터마킹 시작... (Buyer: {buyer_id})")
        
        try:
            options = WatermarkOptions(
                secret_key=SECRET_KEY,
                buyer_bitstring=buyer_id,
                target_col=TARGET_COL,
                ref_cols=REF_COLS,
                k=20,
                g=5,
            )
            
            embed_result = insert(input_path, output_path, options)
            meta_data = embed_result.metadata
            
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
            
            options = WatermarkOptions(
                secret_key=SECRET_KEY,
                buyer_bitstring="1" * int(bit_len),
                target_col=TARGET_COL,
                ref_cols=REF_COLS,
                k=20,
                g=5,
            )
            
            detection_result = detect(input_path, options, embed_metadata=meta_data)
            detected_id = detection_result.detected_bitstring
            score = detection_result.score
            
            self.log(f"\n[!!!] 검출 결과: 범인의 ID는 [{detected_id}] 입니다.")
            self.log(f"[!!!] 신뢰도 점수: {score:.4f}")
            messagebox.showinfo("검출 완료", f"검출된 ID: {detected_id}\n신뢰도: {score:.4f}")

        except Exception as e:
            self.log(f"[-] 오류 발생: {str(e)}")
            messagebox.showerror("오류", str(e))

    def run_dov(self):
        input_path = self.ent_dov_input.get()
        meta_path = self.ent_dov_meta.get()
        claimed_id = self.ent_dov_claimed_id.get()
        bit_len = self.ent_dov_bit_len.get()
        z_threshold = self.ent_dov_z.get()
        min_ratio = self.ent_dov_ratio.get()

        if not input_path or not meta_path or not claimed_id:
            messagebox.showerror("오류", "파일과 주장 ID를 모두 입력해주세요.")
            return

        self.log(f"[*] DOV 시작... (File: {os.path.basename(input_path)}, Claimed: {claimed_id})")

        try:
            with open(meta_path, "r") as f:
                meta_data = json.load(f)

            options = WatermarkOptions(
                secret_key=SECRET_KEY,
                buyer_bitstring=claimed_id,
                target_col=TARGET_COL,
                ref_cols=REF_COLS,
                k=20,
                g=5,
            )
            
            detection_result = detect(input_path, options, embed_metadata=meta_data)
            detected_id = detection_result.detected_bitstring
            score = detection_result.score
            
            # DOV 검증: 검출된 ID와 주장 ID 비교
            matched_bits = sum(1 for i in range(len(claimed_id)) if claimed_id[i] == detected_id[i] if detected_id[i] != "?")
            known_bits = sum(1 for bit in detected_id if bit != "?")
            match_ratio = matched_bits / known_bits if known_bits > 0 else 0.0
            
            ownership_verified = match_ratio >= float(min_ratio)
            decision_text = "소유권 검증 성공" if ownership_verified else "소유권 불충분"
            
            self.log("--- [DOV Report] ---")
            self.log(f"Claimed ID : {claimed_id}")
            self.log(f"Detected ID: {detected_id}")
            self.log(f"Matched    : {matched_bits}/{known_bits}")
            self.log(f"Match Ratio: {match_ratio:.2%}")
            self.log(f"Score      : {score:.4f}")
            self.log(f"Decision   : {decision_text}\n")

            messagebox.showinfo(
                "DOV 결과",
                f"{decision_text}\n"
                f"Detected ID: {detected_id}\n"
                f"Match Ratio: {match_ratio:.2%}",
            )
        except Exception as e:
            self.log(f"[-] 오류 발생: {str(e)}")
            messagebox.showerror("오류", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = B2MarkApp(root)
    root.mainloop()