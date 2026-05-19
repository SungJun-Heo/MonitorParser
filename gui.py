import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
PROMPTS_DIR = BASE_DIR / "prompts"
GT_FILE = BASE_DIR / "ground_truth.json"

PART_NAMES = ["Flange Nut", "Gear Ring", "Spacer Ring", "Hex Nut", "Dome Nut"]


def load_gt():
    return json.loads(GT_FILE.read_text()) if GT_FILE.exists() else {}


def save_gt(data):
    GT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


class AddTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.src_path = None
        self._img_pil = None
        self._img_tk = None

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # 좌: 컨트롤
        left = ttk.Frame(body, padding=(0, 0, 12, 0))
        left.pack(side="left", fill="y")

        ttk.Label(left, text="이미지 추가", font=("", 10, "bold")).pack(anchor="w")

        row = ttk.Frame(left)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, text="이미지:").pack(side="left")
        self.path_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.path_var, width=32).pack(side="left", padx=4)
        ttk.Button(row, text="찾기", command=self._browse).pack(side="left")

        row2 = ttk.Frame(left)
        row2.pack(fill="x", pady=(4, 0))
        ttk.Label(row2, text="저장 파일명:").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.name_var, width=24).pack(side="left", padx=4)

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="정답 입력", font=("", 10, "bold")).pack(anchor="w")

        tbl = ttk.Frame(left)
        tbl.pack(fill="x", pady=4)
        ttk.Label(tbl, text="Part Name", width=20, anchor="w").grid(row=0, column=0, padx=4)
        ttk.Label(tbl, text="Quantity", width=10, anchor="w").grid(row=0, column=1, padx=4)
        ttk.Separator(tbl, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        self.qty_vars = {}
        for i, name in enumerate(PART_NAMES):
            ttk.Label(tbl, text=name, width=20, anchor="w").grid(row=i + 2, column=0, padx=4, pady=3)
            var = tk.StringVar(value="0")
            ttk.Entry(tbl, textvariable=var, width=8).grid(row=i + 2, column=1, padx=4)
            self.qty_vars[name] = var

        total_row = ttk.Frame(left)
        total_row.pack(fill="x", pady=(8, 0))
        ttk.Label(total_row, text="total_count:").pack(side="left")
        self.total_var = tk.StringVar(value="0")
        ttk.Entry(total_row, textvariable=self.total_var, width=8).pack(side="left", padx=4)
        ttk.Button(total_row, text="자동계산", command=self._auto_total).pack(side="left")

        ttk.Button(left, text="저장", command=self._save).pack(pady=(8, 0))

        ttk.Separator(left).pack(fill="x", pady=12)

        ttk.Label(left, text="이미지 삭제", font=("", 10, "bold")).pack(anchor="w")
        del_row = ttk.Frame(left)
        del_row.pack(fill="x", pady=(4, 0))
        self.del_var = tk.StringVar()
        self.del_cb = ttk.Combobox(del_row, textvariable=self.del_var, width=28, state="readonly")
        self.del_cb.pack(side="left")
        ttk.Button(del_row, text="삭제", command=self._delete).pack(side="left", padx=6)

        # 우: 이미지 프리뷰
        right = ttk.LabelFrame(body, text="미리보기", padding=4)
        right.pack(side="left", fill="both", expand=True)
        self.preview_canvas = tk.Canvas(right, bg="#1e1e1e")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._resize_preview)

        self._refresh_del_list()

    def _browse(self):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.src_path = path
            self.path_var.set(path)
            self.name_var.set(Path(path).name)
            self._img_pil = Image.open(path)
            self._resize_preview()

    def _resize_preview(self, _=None):
        if self._img_pil is None:
            return
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.after(50, self._resize_preview)
            return
        img = self._img_pil.copy()
        img.thumbnail((w, h), Image.LANCZOS)
        self._img_tk = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(w // 2, h // 2, anchor="center", image=self._img_tk)

    def _auto_total(self):
        try:
            self.total_var.set(str(sum(int(v.get() or 0) for v in self.qty_vars.values())))
        except ValueError:
            pass

    def _save(self):
        if not self.src_path:
            messagebox.showerror("오류", "이미지를 선택하세요")
            return
        fname = self.name_var.get().strip()
        if not fname:
            messagebox.showerror("오류", "저장 파일명을 입력하세요")
            return

        parts = []
        for name, var in self.qty_vars.items():
            try:
                qty = int(var.get())
            except ValueError:
                messagebox.showerror("오류", f"수량 오류: {name}")
                return
            if qty > 0:
                parts.append({"name": name, "quantity": qty})
        try:
            total = int(self.total_var.get())
        except ValueError:
            messagebox.showerror("오류", "total_count 오류")
            return

        IMAGES_DIR.mkdir(exist_ok=True)
        shutil.copy2(self.src_path, IMAGES_DIR / fname)

        data = load_gt()
        data[fname] = {"target_parts": parts, "total_count": total}
        save_gt(data)

        self._refresh_del_list()
        messagebox.showinfo("완료", f"{fname} 저장 완료")

    def _delete(self):
        fname = self.del_var.get()
        if not fname:
            return
        if not messagebox.askyesno("확인", f"{fname} 을 삭제하시겠습니까?"):
            return

        img_path = IMAGES_DIR / fname
        if img_path.exists():
            img_path.unlink()

        data = load_gt()
        data.pop(fname, None)
        save_gt(data)

        self._refresh_del_list()

    def _refresh_del_list(self):
        images = sorted(load_gt().keys())
        self.del_cb["values"] = images
        self.del_var.set(images[0] if images else "")


class EvalTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._img_tk = None
        self._img_pil = None

        # --- 실행 인자 ---
        args = ttk.LabelFrame(self, text="실행 인자", padding=6)
        args.pack(fill="x")

        ttk.Label(args, text="--prompt").grid(row=0, column=0, sticky="w")
        self.prompt_var = tk.StringVar()
        self.prompt_cb = ttk.Combobox(args, textvariable=self.prompt_var, width=32)
        self.prompt_cb.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(args, text="--image").grid(row=1, column=0, sticky="w")
        self.image_var = tk.StringVar()
        self.image_cb = ttk.Combobox(args, textvariable=self.image_var, width=32)
        self.image_cb.grid(row=1, column=1, padx=4, pady=2)
        self.image_cb.bind("<<ComboboxSelected>>", self._on_image_select)

        ttk.Button(args, text="실행", command=self._run).grid(row=0, column=2, rowspan=2, padx=12)

        # --- 메인 패널 ---
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, pady=(8, 0))

        # 좌: 이미지
        img_frame = ttk.LabelFrame(pane, text="이미지", padding=4)
        self.img_canvas = tk.Canvas(img_frame, bg="#1e1e1e")
        self.img_canvas.pack(fill="both", expand=True)
        self.img_canvas.bind("<Configure>", self._resize_image)
        pane.add(img_frame, weight=1)

        # 우: 정답 + 출력
        right_pane = ttk.PanedWindow(pane, orient="vertical")

        gt_frame = ttk.LabelFrame(right_pane, text="정답", padding=4)
        self.gt_text = tk.Text(gt_frame, font=("Courier", 9), state="disabled", wrap="none", height=8)
        self.gt_text.pack(fill="both", expand=True)
        right_pane.add(gt_frame, weight=1)

        out_frame = ttk.LabelFrame(right_pane, text="LLM 출력", padding=4)
        self.out_text = tk.Text(out_frame, font=("Courier", 9), wrap="none")
        self.out_text.pack(fill="both", expand=True)
        right_pane.add(out_frame, weight=1)

        pane.add(right_pane, weight=1)

        # --- 비교 결과 ---
        cmp_frame = ttk.LabelFrame(self, text="비교 결과", padding=4)
        cmp_frame.pack(fill="x", pady=(8, 0))
        self.cmp_text = tk.Text(cmp_frame, font=("Courier", 9), height=7, state="disabled", wrap="none")
        self.cmp_text.tag_config("pass", foreground="#2ecc71")
        self.cmp_text.tag_config("fail", foreground="#e74c3c")
        self.cmp_text.tag_config("ok",   foreground="#2ecc71")
        self.cmp_text.tag_config("ng",   foreground="#e74c3c")
        self.cmp_text.pack(fill="x")

        self.refresh()

    def refresh(self):
        prompts = sorted(p.name for p in PROMPTS_DIR.glob("*.txt"))
        self.prompt_cb["values"] = prompts
        if prompts and not self.prompt_var.get():
            self.prompt_var.set(prompts[0])

        images = sorted(load_gt().keys())
        self.image_cb["values"] = images
        if images:
            if not self.image_var.get() or self.image_var.get() not in images:
                self.image_var.set(images[0])
            self._load_image(self.image_var.get())
            self._show_gt()

    def _on_image_select(self, _=None):
        self._load_image(self.image_var.get())
        self._show_gt()

    def _load_image(self, fname):
        path = IMAGES_DIR / fname
        if not path.exists():
            self._img_pil = None
            self.img_canvas.delete("all")
            return
        self._img_pil = Image.open(path)
        self._resize_image()

    def _resize_image(self, _=None):
        if self._img_pil is None:
            return
        w = self.img_canvas.winfo_width()
        h = self.img_canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.after(50, self._resize_image)
            return
        img = self._img_pil.copy()
        img.thumbnail((w, h), Image.LANCZOS)
        self._img_tk = ImageTk.PhotoImage(img)
        self.img_canvas.delete("all")
        self.img_canvas.create_image(w // 2, h // 2, anchor="center", image=self._img_tk)

    def _show_gt(self):
        gt = load_gt().get(self.image_var.get(), {})
        self.gt_text.config(state="normal")
        self.gt_text.delete("1.0", "end")
        self.gt_text.insert("end", json.dumps(gt, ensure_ascii=False, indent=2))
        self.gt_text.config(state="disabled")

    def _run(self):
        prompt, image = self.prompt_var.get(), self.image_var.get()
        if not prompt or not image:
            messagebox.showerror("오류", "prompt와 image를 선택하세요")
            return

        cmd = ["python", "run_task_A.py", "--prompt", prompt, "--image", image]
        self.out_text.delete("1.0", "end")
        self.out_text.insert("end", f"$ {' '.join(cmd)}\n\n")
        self._clear_cmp()
        self.update()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
            output = result.stdout or result.stderr
            self.out_text.insert("end", output)
        except Exception as e:
            self.out_text.insert("end", str(e))
            return

        gt = load_gt().get(image, {})
        self._compare(gt, output)

    def _clear_cmp(self):
        self.cmp_text.config(state="normal")
        self.cmp_text.delete("1.0", "end")
        self.cmp_text.config(state="disabled")

    def _compare(self, gt, output):
        try:
            # stdout 앞의 커맨드 헤더를 건너뛰고 JSON 파싱
            json_str = output[output.index("{"):]
            pred = json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            self.cmp_text.config(state="normal")
            self.cmp_text.insert("end", "JSON 파싱 실패 — LLM 출력을 확인하세요\n", "fail")
            self.cmp_text.config(state="disabled")
            return

        gt_parts   = {p["name"]: p["quantity"] for p in gt.get("target_parts", [])}
        pred_parts = {p["name"]: p["quantity"] for p in pred.get("target_parts", [])}
        all_names  = sorted(set(gt_parts) | set(pred_parts))

        rows = []   # (text, tag)
        passed = True
        for name in all_names:
            gt_q, pr_q = gt_parts.get(name, 0), pred_parts.get(name, 0)
            if gt_q == pr_q:
                rows.append((f"  ✓  {name:<18} {pr_q}\n", "ok"))
            else:
                rows.append((f"  ✗  {name:<18} 정답={gt_q}  출력={pr_q}\n", "ng"))
                passed = False

        gt_total   = gt.get("total_count", 0)
        pred_total = pred.get("total_count", 0)
        if gt_total == pred_total:
            rows.append((f"  ✓  total_count       {pred_total}\n", "ok"))
        else:
            rows.append((f"  ✗  total_count       정답={gt_total}  출력={pred_total}\n", "ng"))
            passed = False

        self.cmp_text.config(state="normal")
        verdict = "PASS" if passed else "FAIL"
        tag     = "pass" if passed else "fail"
        self.cmp_text.insert("end", f"[{verdict}]\n", tag)
        for text, t in rows:
            self.cmp_text.insert("end", text, t)
        self.cmp_text.config(state="disabled")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MonitorParser GUI")
        self.geometry("960x640")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.add_tab = AddTab(nb)
        self.eval_tab = EvalTab(nb)
        nb.add(self.add_tab, text="이미지 추가 / 삭제")
        nb.add(self.eval_tab, text="검증")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.eval_tab.refresh())


if __name__ == "__main__":
    App().mainloop()