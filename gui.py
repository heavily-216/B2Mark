# -*- coding: utf-8 -*-
"""
B2Mark Watermarking System - GUI
tkinter 기반 데이터 워터마킹 시스템
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import threading
from pathlib import Path
from watermark import B2MarkEmbedder, B2MarkDetector, load_config_by_datatype

SECRET_KEY = "grad_project_key"


class B2MarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("B2Mark - Data Watermarking System")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # 스타일 설정
        style = ttk.Style()
        style.theme_use("clam")

        # 탭 생성
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # 각 탭 생성
        self.embed_frame = ttk.Frame(self.notebook)
        self.detect_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.embed_frame, text="🔐 워터마크 삽입 (Embed)")
        self.notebook.add(self.detect_frame, text="🔍 워터마크 검출 (Detect)")

        # 각 탭 UI 구성
        self.create_embed_tab()
        self.create_detect_tab()

        # 로그 창
        self.create_log_area()

    # ==================== Embed Tab ====================
    def create_embed_tab(self):
        frame = ttk.Frame(self.embed_frame, padding="10")
        frame.pack(fill="both", expand=True)

        # 제목
        ttk.Label(frame, text="워터마크 삽입", font=("Arial", 14, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        # 입력 파일
        ttk.Label(frame, text="원본 CSV 파일:").pack(anchor="w", pady=(5, 0))
        self.embed_input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.embed_input_var, width=50).pack(
            anchor="w", pady=(0, 5)
        )
        ttk.Button(
            frame,
            text="파일 선택",
            command=lambda: self.select_file(self.embed_input_var),
        ).pack(anchor="w", pady=(0, 10))

        # 출력 파일
        ttk.Label(frame, text="출력 CSV 파일:").pack(anchor="w", pady=(5, 0))
        self.embed_output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.embed_output_var, width=50).pack(
            anchor="w", pady=(0, 5)
        )
        ttk.Button(
            frame,
            text="저장 위치",
            command=lambda: self.select_save_file(self.embed_output_var),
        ).pack(anchor="w", pady=(0, 10))

        # 구매자 ID
        ttk.Label(frame, text="구매자 ID (비트스트링):").pack(anchor="w", pady=(5, 0))
        self.embed_buyer_id_var = tk.StringVar(value="10110")
        ttk.Entry(frame, textvariable=self.embed_buyer_id_var, width=50).pack(
            anchor="w", pady=(0, 10)
        )

        # 데이터 타입
        ttk.Label(frame, text="데이터 타입:").pack(anchor="w", pady=(5, 0))
        self.embed_datatype_var = tk.StringVar(value="real_estate")
        datatype_combo = ttk.Combobox(
            frame,
            textvariable=self.embed_datatype_var,
            values=["real_estate", "insurance", "credit_card"],
            state="readonly",
            width=47,
        )
        datatype_combo.pack(anchor="w", pady=(0, 10))

        # Verbose 옵션
        self.embed_verbose_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, text="상세 로그 출력", variable=self.embed_verbose_var
        ).pack(anchor="w", pady=(0, 10))

        # 실행 버튼
        ttk.Button(frame, text="워터마크 삽입 실행", command=self.run_embed).pack(
            anchor="w", pady=(10, 0)
        )

    def run_embed(self):
        """워터마크 삽입 실행"""
        input_file = self.embed_input_var.get()
        output_file = self.embed_output_var.get()
        buyer_id = self.embed_buyer_id_var.get()
        data_type = self.embed_datatype_var.get()
        verbose = self.embed_verbose_var.get()

        if not input_file or not output_file or not buyer_id:
            messagebox.showerror("오류", "모든 필드를 입력해주세요")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {input_file}")
            return

        # 스레드에서 실행
        thread = threading.Thread(
            target=self._embed_worker,
            args=(input_file, output_file, buyer_id, data_type, verbose),
        )
        thread.daemon = True
        thread.start()

    def _embed_worker(self, input_file, output_file, buyer_id, data_type, verbose):
        try:
            self.log(f"[*] 워터마크 삽입 시작... (데이터타입: {data_type})")

            # config 로드
            config = load_config_by_datatype(data_type)
            k = config["k"]
            g = config["g"]
            embed_seed = config["embed_seed"]

            self.log(f"    설정: k={k}, g={g}, embed_seed={embed_seed}")
            self.log(f"    열 이름 자동 탐지 중...")

            # 워터마킹 실행 (자동 열 탐지)
            embedder = B2MarkEmbedder(secret_key=SECRET_KEY)
            meta_data = embedder.embed(
                source_path=input_file,
                output_path=output_file,
                buyer_bitstring=buyer_id,
                target_col=None,  # 자동 탐지
                ref_cols=None,  # 자동 탐지
                k=k,
                g=g,
                embed_seed=embed_seed,
                verbose=verbose,
                data_type=data_type,  # 자동 탐지에 필요
            )

            # 메타데이터 저장
            meta_path = output_file + ".meta.json"
            with open(meta_path, "w") as f:
                json.dump(meta_data, f)

            self.log(f"[+] 워터마크 삽입 완료!")
            self.log(f"    출력 파일: {output_file}")
            self.log(f"    메타데이터: {meta_path}")
            messagebox.showinfo(
                "성공",
                f"워터마크 삽입이 완료되었습니다!\n\n출력: {output_file}\n메타데이터: {meta_path}",
            )

        except Exception as e:
            self.log(f"[!] 오류: {str(e)}")
            messagebox.showerror("오류", f"워터마크 삽입 중 오류 발생:\n{str(e)}")

    # ==================== Detect Tab ====================
    def create_detect_tab(self):
        frame = ttk.Frame(self.detect_frame, padding="10")
        frame.pack(fill="both", expand=True)

        # 제목
        ttk.Label(frame, text="워터마크 검출", font=("Arial", 14, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        # 입력 파일
        ttk.Label(frame, text="검사 대상 CSV 파일:").pack(anchor="w", pady=(5, 0))
        self.detect_input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.detect_input_var, width=50).pack(
            anchor="w", pady=(0, 5)
        )
        ttk.Button(
            frame,
            text="파일 선택",
            command=lambda: self.select_file(self.detect_input_var),
        ).pack(anchor="w", pady=(0, 10))

        # 메타데이터 파일
        ttk.Label(frame, text="메타데이터 JSON 파일:").pack(anchor="w", pady=(5, 0))
        self.detect_meta_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.detect_meta_var, width=50).pack(
            anchor="w", pady=(0, 5)
        )
        ttk.Button(
            frame,
            text="파일 선택",
            command=lambda: self.select_file(self.detect_meta_var),
        ).pack(anchor="w", pady=(0, 10))

        # 구매자 ID 길이
        ttk.Label(frame, text="구매자 ID 길이 (비트 수):").pack(anchor="w", pady=(5, 0))
        self.detect_bitlen_var = tk.StringVar(value="5")
        ttk.Entry(frame, textvariable=self.detect_bitlen_var, width=50).pack(
            anchor="w", pady=(0, 10)
        )

        # 데이터 타입
        ttk.Label(frame, text="데이터 타입:").pack(anchor="w", pady=(5, 0))
        self.detect_datatype_var = tk.StringVar(value="real_estate")
        datatype_combo = ttk.Combobox(
            frame,
            textvariable=self.detect_datatype_var,
            values=["real_estate", "insurance", "credit_card"],
            state="readonly",
            width=47,
        )
        datatype_combo.pack(anchor="w", pady=(0, 10))

        # Verbose 옵션
        self.detect_verbose_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, text="상세 로그 출력", variable=self.detect_verbose_var
        ).pack(anchor="w", pady=(0, 10))

        # 실행 버튼
        ttk.Button(frame, text="워터마크 검출 실행", command=self.run_detect).pack(
            anchor="w", pady=(10, 0)
        )

    def run_detect(self):
        """워터마크 검출 실행"""
        input_file = self.detect_input_var.get()
        meta_file = self.detect_meta_var.get()
        bit_len = self.detect_bitlen_var.get()
        data_type = self.detect_datatype_var.get()
        verbose = self.detect_verbose_var.get()

        if not input_file or not meta_file or not bit_len:
            messagebox.showerror("오류", "모든 필드를 입력해주세요")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {input_file}")
            return

        if not os.path.exists(meta_file):
            messagebox.showerror(
                "오류", f"메타데이터 파일을 찾을 수 없습니다: {meta_file}"
            )
            return

        try:
            bit_len = int(bit_len)
        except ValueError:
            messagebox.showerror("오류", "비트 수는 정수여야 합니다")
            return

        # 스레드에서 실행
        thread = threading.Thread(
            target=self._detect_worker,
            args=(input_file, meta_file, bit_len, data_type, verbose),
        )
        thread.daemon = True
        thread.start()

    def _detect_worker(self, input_file, meta_file, bit_len, data_type, verbose):
        try:
            self.log(f"[*] 워터마크 검출 시작... (데이터타입: {data_type})")

            # config 로드
            config = load_config_by_datatype(data_type)

            self.log(f"    열 이름 자동 탐지 중...")

            # 메타데이터 로드
            with open(meta_file, "r") as f:
                meta_data = json.load(f)

            # 검출 실행 (자동 열 탐지)
            detector = B2MarkDetector(secret_key=SECRET_KEY)
            detected_id = detector.detect(
                suspect_path=input_file,
                meta_data=meta_data,
                bit_length=bit_len,
                target_col=None,  # 자동 탐지
                ref_cols=None,  # 자동 탐지
                verbose=verbose,
                data_type=data_type,  # 자동 탐지에 필요
            )

            self.log(f"[+] 검출 완료!")
            self.log(f"    검출된 구매자 ID: [{detected_id}]")
            messagebox.showinfo(
                "성공", f"워터마크 검출 완료!\n\n검출된 ID: [{detected_id}]"
            )

        except Exception as e:
            self.log(f"[!] 오류: {str(e)}")
            messagebox.showerror("오류", f"워터마크 검출 중 오류 발생:\n{str(e)}")

    # ==================== Log Area ====================
    def create_log_area(self):
        """로그 창 생성"""
        log_frame = ttk.LabelFrame(self.root, text="📝 로그", padding="5")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = tk.Text(
            log_frame, height=10, state="disabled", bg="#f0f0f0", font=("Courier", 9)
        )
        self.log_text.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        """로그에 메시지 추가"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    # ==================== File Dialog ====================
    def select_file(self, var):
        """파일 선택 대화"""
        filename = filedialog.askopenfilename(
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ]
        )
        if filename:
            var.set(filename)

    def select_save_file(self, var):
        """파일 저장 대화"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filename:
            var.set(filename)


def main():
    root = tk.Tk()
    app = B2MarkGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
