import sys
import os
import json
import time
import uuid
import random
import tempfile
import threading
import shutil
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# أضف هذين السطرين هنا لضمان عدم ضبابية الأيقونات والصور
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"    

def _icon_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'icon.ico')

ICON_PATH = _icon_path()

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdt_gallery")
os.makedirs(APP_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(APP_DIR, "history.json")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QScrollArea, QFrame,
    QProgressBar, QFileDialog, QSlider, QSizePolicy, QDialog,
    QGridLayout, QLineEdit, QCheckBox, QGroupBox, QGraphicsBlurEffect,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QMimeData, QTimer, QEvent
from PySide6.QtGui import (
    QPixmap, QFont, QDrag, QIcon, QPainter, QLinearGradient, QColor,
    QGuiApplication,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

try:
    import torch
    import warnings; warnings.filterwarnings("ignore")
    from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image
    import diffusers; diffusers.utils.logging.set_verbosity_error()
    from PIL import Image as PILImage, ImageFilter, ImageEnhance
    HAS_AI = True
    try:
        CUDA_OK  = torch.cuda.is_available()
        CUDA_GPU = torch.cuda.get_device_name(0) if CUDA_OK else ""
    except Exception:
        CUDA_OK = False; CUDA_GPU = ""
except Exception:
    HAS_AI   = False; CUDA_OK  = False; CUDA_GPU = ""
    PILImage = None

try:
    from gfpgan import GFPGANer
    HAS_GFPGAN = True
except Exception:
    HAS_GFPGAN = False

# ══════════════════════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════════════════════
C_BG    = "#0D0D0D"; C_PANEL = "#151515"; C_USER_B = "#1E1E1E"; C_AI_B  = "#111827"
C_BORDER= "#2A2A2A"; C_TEXT  = "#E5E5E5"; C_MUTED  = "#737373"
C_ACC_A = "#6366F1"; C_ACC_B = "#8B5CF6"; C_DANGER = "#EF4444"
C_OK    = "#10B981"; C_WARN  = "#F59E0B"

# SD-Turbo is trained at 512px — smaller = distortion
QS    = {"Ultra Fast": 1, "Fast": 3, "Balanced": 4, "Quality": 6, "Max": 10}
SIZES = [
    "256x256", "384x384", "448x448",
    "512x512", "512x768", "576x576", "640x640", "704x704",
    "768x512", "768x768", "832x832", "896x896", "960x540",
    "1024x576", "1024x768", "768x1024", "1024x1024", "1080x720", "1080x1080",
]

ENHANCE_TAG = "masterpiece, best quality, ultra-detailed, 8k, cinematic lighting, sharp focus"

def s_combo():
    return (f"QComboBox{{background:{C_USER_B};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:4px;font-size:11px;padding:2px 6px;}}"
            f"QComboBox::drop-down{{border:none;width:16px;}}"
            f"QComboBox QAbstractItemView{{background:{C_PANEL};color:{C_TEXT};"
            f"selection-background-color:{C_ACC_A};}}")

def s_btn(bg=C_USER_B):
    return (f"QPushButton{{background:{bg};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:4px;font-size:11px;padding:0 10px;}}"
            f"QPushButton:hover{{border-color:{C_ACC_A};}}"
            f"QPushButton:disabled{{color:{C_MUTED};}}")

def s_vgradient():
    return (f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C_ACC_A},stop:1 {C_ACC_B});color:white;font-weight:bold;"
            f"border:none;border-radius:5px;font-size:12px;}}"
            f"QPushButton:hover{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C_ACC_B},stop:1 {C_ACC_A});}}")

def s_danger():
    return (f"QPushButton{{background:{C_DANGER};color:white;font-weight:bold;"
            f"border:none;border-radius:5px;font-size:12px;}}"
            f"QPushButton:hover{{background:#DC2626;}}")

def s_lbl(txt, color=C_MUTED, sz=10):
    l = QLabel(txt); l.setStyleSheet(f"color:{color};font-size:{sz}px;background:transparent;")
    return l

def _vsep():
    f = QFrame(); f.setFrameShape(QFrame.VLine); f.setFixedWidth(1)
    f.setStyleSheet(f"background:{C_BORDER};border:none;"); return f


# ══════════════════════════════════════════════════════════════════════════════
#  PREVIEW BLUR CARD REMOVED (as per freegen_app style)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  REAL IMAGE CARD
# ══════════════════════════════════════════════════════════════════════════════
from PySide6.QtWidgets import QMenu, QGraphicsDropShadowEffect
from PySide6.QtGui import QAction, QCursor, QImageReader

class ImageCard(QFrame):
    edit_req  = Signal(str)
    regen_req = Signal(str)
    request_preview = Signal(object, bool)
    request_delete = Signal(object)
    
    def __init__(self, path, prompt=""):
        super().__init__()
        self.path = path
        self.prompt = prompt
        self.is_hidden = False
        self.setObjectName("ImageCard")
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)
        
        self.press_timer = QTimer(self)
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.long_press_action)
        
        self.target_width = 180
        self.ratio = 1.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.lbl = QLabel("")
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setScaledContents(True)
        self.lbl.setObjectName("ImageLabel")
        layout.addWidget(self.lbl)
        
        self.blur_effect = QGraphicsBlurEffect(self)
        self.blur_effect.setBlurRadius(0)
        self.lbl.setGraphicsEffect(self.blur_effect)

        if os.path.exists(self.path):
            reader = QImageReader(self.path)
            size = reader.size()
            if size.isValid() and size.height() > 0:
                self.ratio = size.width() / size.height()
        
        self.apply_ratio_size()
        
        self.pixmap = QPixmap(self.path)
        if not self.pixmap.isNull():
            self.lbl.setPixmap(self.pixmap)

    def trigger_glow(self):
        if self.is_hidden: return
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self.glow_anim = QPropertyAnimation(self.blur_effect, b"blurRadius", self)
        self.glow_anim.setDuration(1000)
        self.glow_anim.setStartValue(10)
        self.glow_anim.setEndValue(0)
        self.glow_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.glow_anim.start()

    def update_width(self, new_width):
        self.target_width = new_width
        self.setFixedWidth(self.target_width)
        self.apply_ratio_size()

    def apply_ratio_size(self):
        target_h = int(self.target_width / self.ratio)
        self.setFixedHeight(target_h)

    def enterEvent(self, event):
        if not self.is_hidden:
            self.lbl.setStyleSheet(f"border: 1px solid {C_ACC_A}; background-color: {C_USER_B};")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.lbl.setStyleSheet("border: none; background-color: transparent;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_hidden:
            self.press_timer.start(400)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.press_timer.stop()
        self.request_preview.emit(None, False)
        super().mouseReleaseEvent(event)

    def long_press_action(self):
        if self.pixmap:
            self.request_preview.emit(self.pixmap, True)

    def show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {C_PANEL}; color: {C_TEXT}; border: 1px solid {C_BORDER}; padding: 5px; border-radius: 4px; }}"
                           f"QMenu::item:selected {{ background-color: {C_USER_B}; }}")
        down_act = QAction("Save As...", self)
        down_act.triggered.connect(self._save)
        
        regen_act = QAction("Generate Again", self)
        regen_act.triggered.connect(lambda: self.regen_req.emit(self.path))
        
        gen_img_act = QAction("Use as Reference", self)
        gen_img_act.triggered.connect(lambda: self.edit_req.emit(self.path))
        
        del_act = QAction("Delete", self)
        del_act.triggered.connect(lambda: self.request_delete.emit(self))
        
        menu.addAction(down_act)
        menu.addAction(regen_act)
        menu.addAction(gen_img_act)
        menu.addSeparator()
        menu.addAction(del_act)
        menu.exec(QCursor.pos())

    def _save(self):
        dst, _ = QFileDialog.getSaveFileName(None, "Save", f"img_{int(time.time())}.png", "PNG (*.png);;JPEG (*.jpg)")
        if dst: self.pixmap.save(dst)

# ══════════════════════════════════════════════════════════════════════════════
#  WORKER THREAD
# ══════════════════════════════════════════════════════════════════════════════
#  FACE RESTORE
# ══════════════════════════════════════════════════════════════════════════════
def face_restore_basic(img_path: str) -> str:
    """
    Enhance face/details using PIL sharpening.
    If GFPGANv1.4.pth exists in app folder and gfpgan is installed, uses real restoration.
    """
    if PILImage is None:
        return img_path
    try:
        img = PILImage.open(img_path).convert("RGB")
        if HAS_GFPGAN:
            import cv2, numpy as np
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GFPGANv1.4.pth")
            if os.path.exists(model_path):
                restorer = GFPGANer(model_path=model_path, upscale=1,
                                    arch='clean', channel_multiplier=2)
                img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                _, _, restored = restorer.enhance(img_np, has_aligned=False,
                                                   only_center_face=False, paste_back=True)
                img = PILImage.fromarray(cv2.cvtColor(restored, cv2.COLOR_BGR2RGB))
            else:
                # Basic PIL fallback
                img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))
                img = ImageEnhance.Contrast(img).enhance(1.08)
                img = ImageEnhance.Sharpness(img).enhance(1.4)
        else:
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))
            img = ImageEnhance.Contrast(img).enhance(1.08)
            img = ImageEnhance.Sharpness(img).enhance(1.4)
        out = os.path.join(tempfile.gettempdir(), f"fr_{uuid.uuid4().hex[:8]}.png")
        img.save(out); return out
    except Exception:
        return img_path


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORY
# ══════════════════════════════════════════════════════════════════════════════
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid = []
            for e in data:
                if isinstance(e, dict) and "imgs" in e:
                    e["imgs"] = [p for p in e["imgs"] if os.path.exists(p)]
                    if e["imgs"]: valid.append(e)
            return valid
    except Exception: pass
    return []

def save_history(sessions):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False)
    except Exception: pass

def copy_to_gallery(src):
    try:
        ext = os.path.splitext(src)[1] or ".png"
        dst = os.path.join(APP_DIR, f"img_{uuid.uuid4().hex[:12]}{ext}")
        shutil.copy2(src, dst); return dst
    except Exception: return src


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class SettingsDialog(QDialog):
    def __init__(self, cfg, images_list, parent=None):
        super().__init__(parent); self._cfg = cfg; self._imgs = images_list
        self.setWindowTitle("Settings"); self.setFixedSize(420, 360)
        self.setStyleSheet(
            f"QDialog{{background:{C_BG};}}"
            f"QGroupBox{{color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;"
            f"margin-top:10px;font-size:11px;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:8px;padding:0 3px;color:{C_MUTED};}}"
            f"QCheckBox{{color:{C_TEXT};font-size:11px;spacing:6px;}}"
        )
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16)

        # Device
        g1 = QGroupBox("Device & Performance"); l1 = QVBoxLayout(g1)
        self.c_dev = QComboBox(); self.c_dev.setStyleSheet(s_combo()); self.c_dev.setFixedHeight(26)
        self.c_dev.addItem("CPU  (always works, slower)")
        if CUDA_OK:
            self.c_dev.addItem(f"CUDA  -  {CUDA_GPU}")
        else:
            gpu_info = "Not available"
            try:
                import subprocess
                r = subprocess.run(["wmic","path","win32_VideoController","get","name"],
                                   capture_output=True, text=True, timeout=3)
                names = [x.strip() for x in r.stdout.splitlines()
                         if x.strip() and x.strip() != "Name"]
                if names: gpu_info = names[0]
            except Exception: pass
            self.c_dev.addItem(f"CUDA  -  {gpu_info}  (install CUDA PyTorch)")
            self.c_dev.model().item(1).setEnabled(False)
        self.c_dev.setCurrentIndex(1 if cfg.get("dev") == "cuda" and CUDA_OK else 0)
        l1.addWidget(self.c_dev)
        self.chk_attn = QCheckBox("Attention Slicing  (Low VRAM)")
        self.chk_attn.setChecked(cfg.get("attn", True)); l1.addWidget(self.chk_attn)
        self.chk_vae = QCheckBox("VAE Tiling  (Large images, less VRAM)")
        self.chk_vae.setChecked(cfg.get("vae_tile", False)); l1.addWidget(self.chk_vae)

        # NSFW Toggle
        self.chk_nsfw = QCheckBox("Enable NSFW ")
        self.chk_nsfw.setChecked(cfg.get("nsfw", True))
        l1.addWidget(self.chk_nsfw)
        root.addWidget(g1)

        # Generation
        g2 = QGroupBox("Generation Options"); l2 = QVBoxLayout(g2)
        fr_label = "GFPGAN detected - real face restore" if HAS_GFPGAN else "PIL sharpening (basic)"
        self.chk_fr = QCheckBox(f"Face Restore after generation  ({fr_label})")
        self.chk_fr.setChecked(cfg.get("face_restore", False)); l2.addWidget(self.chk_fr)
        warn = QLabel("Important: sizes below 512x512 cause distortion — model trained at 512px")
        warn.setWordWrap(True)
        warn.setStyleSheet(f"color:{C_WARN};font-size:10px;background:transparent;padding-top:4px;")
        l2.addWidget(warn)
        root.addWidget(g2)

        # Export
        g3 = QGroupBox("Export"); l3 = QVBoxLayout(g3)
        btn_dl = QPushButton("Download All Images"); btn_dl.setFixedHeight(28)
        btn_dl.setStyleSheet(s_btn()); btn_dl.clicked.connect(self._dl_all); l3.addWidget(btn_dl)
        root.addWidget(g3)

        root.addStretch()
        bb = QHBoxLayout(); bb.addStretch()
        bc = QPushButton("Cancel"); bc.setFixedSize(70,28); bc.setStyleSheet(s_btn()); bc.clicked.connect(self.reject)
        bs = QPushButton("Save");   bs.setFixedSize(70,28); bs.setStyleSheet(s_vgradient()); bs.clicked.connect(self.accept)
        bb.addWidget(bc); bb.addWidget(bs); root.addLayout(bb)

    def _dl_all(self):
        if not self._imgs: return
        dst = QFileDialog.getExistingDirectory(self, "Select Folder")
        if dst:
            for i, p in enumerate(self._imgs):
                QPixmap(p).save(os.path.join(dst, f"sdt_{int(time.time())}_{i}.png"))

    def get_cfg(self):
        return {
            "dev":          "cuda" if self.c_dev.currentIndex() == 1 and CUDA_OK else "cpu",
            "attn":         self.chk_attn.isChecked(),
            "vae_tile":     self.chk_vae.isChecked(),
            "face_restore": self.chk_fr.isChecked(),
            "nsfw":         self.chk_nsfw.isChecked(),
        }


class PromptArea(QTextEdit):
    submitted = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Describe what you want...  (Enter = Generate | Ctrl+V = paste image)")
        self.setFixedHeight(85)
        self.setObjectName("PromptInput")
        self.setStyleSheet(f"background:{C_USER_B};color:{C_TEXT};border:1px solid {C_BORDER};"
                               f"border-radius:8px;padding:10px;font-size:13px;")
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.submitted.emit()
        else:
            super().keyPressEvent(event)
    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class SDWorker(QThread):
    progs       = Signal(int, str)
    card_prog   = Signal(int, int, str)
    image_ready = Signal(int, str)        # card_index, tmp_path
    done        = Signal(str, str, float)

    def __init__(self, prompt, neg_prompt, w, h, steps, ref_path,
                 strength, batch, seed, dev, att, vae_tile, face_restore, nsfw):
        super().__init__()
        self.prompt=prompt; self.neg_prompt=neg_prompt
        self.w=w; self.h=h; self.steps=steps
        self.ref_path=ref_path; self.strength=strength; self.batch=batch
        self.seed=seed if seed >= 0 else random.randint(0, 2**31-1)
        self.dev=dev; self.att=att; self.vae_tile=vae_tile; self.face_restore=face_restore
        self.nsfw = nsfw
        self._stop_evt=threading.Event(); self._pipe=None

    def stop(self):
        self._stop_evt.set()
        if self._pipe:
            try: self._pipe._interrupt = True
            except Exception: pass

    def run(self):
        t0 = time.time()
        try:
            if not HAS_AI:
                return self.done.emit("", "diffusers / torch not installed.", 0)
            mdir = "./sd_turbo_original"
            if not os.path.exists(mdir):
                return self.done.emit("", f"Missing model folder: {mdir}", 0)

            dt = torch.float16 if self.dev == "cuda" else torch.float32
            if self.dev == "cuda": torch.backends.cudnn.benchmark = True

            has_neg   = bool(self.neg_prompt and self.neg_prompt.strip())
            cfg_scale = 7.5 if has_neg else 0.0
            stps      = max(self.steps, 3 if has_neg else 2)

            self.progs.emit(5, "Loading model...")

            def step_cb(pipeline, i, t, kw):
                if self._stop_evt.is_set():
                    try: pipeline._interrupt = True
                    except Exception: pass
                return kw

            # NSFW Support
            pipe_kwargs = {"torch_dtype": dt}
            if self.nsfw:
                pipe_kwargs["safety_checker"] = None
                pipe_kwargs["requires_safety_checker"] = False

            if self.ref_path:
                pipe = AutoPipelineForImage2Image.from_pretrained(mdir, **pipe_kwargs)
            else:
                pipe = AutoPipelineForText2Image.from_pretrained(mdir, **pipe_kwargs)

            self._pipe = pipe; pipe.to(self.dev)
            if self.nsfw and hasattr(pipe, "safety_checker") and pipe.safety_checker is not None:
                pipe.safety_checker = None
            if self.att: pipe.enable_attention_slicing(1)
            if self.vae_tile:
                try: pipe.enable_vae_tiling()
                except Exception: pass

            gen = torch.Generator(device=self.dev).manual_seed(self.seed)
            self.progs.emit(15, "Model ready")

            out_paths = []

            for idx in range(self.batch):
                if self._stop_evt.is_set(): break
                self.progs.emit(15 + int(idx * 80 / self.batch), f"Generating {idx+1}/{self.batch}...")
                self.card_prog.emit(idx, 5, "Starting...")

                try:
                    if self.ref_path:
                        ref_img = PILImage.open(self.ref_path).convert("RGB").resize((self.w, self.h))
                        result = pipe(
                            prompt=self.prompt, negative_prompt=self.neg_prompt or None,
                            image=ref_img, num_inference_steps=max(stps, 2),
                            strength=self.strength, guidance_scale=cfg_scale,
                            generator=gen, callback_on_step_end=step_cb,
                            callback_on_step_end_tensor_inputs=[],
                        )
                    else:
                        result = pipe(
                            prompt=self.prompt, negative_prompt=self.neg_prompt or None,
                            num_inference_steps=stps, guidance_scale=cfg_scale,
                            width=self.w, height=self.h,
                            generator=gen, callback_on_step_end=step_cb,
                            callback_on_step_end_tensor_inputs=[],
                        )

                    if self._stop_evt.is_set():
                        self.card_prog.emit(idx, 0, "Stopped"); break

                    tmp = os.path.join(tempfile.gettempdir(), f"s_{uuid.uuid4().hex[:8]}.png")
                    result.images[0].save(tmp)

                    if self.face_restore:
                        self.card_prog.emit(idx, 90, "Face restore...")
                        tmp = face_restore_basic(tmp)

                    out_paths.append(tmp)
                    self.card_prog.emit(idx, 100, "Done")
                    self.image_ready.emit(idx, tmp)

                except Exception as ex:
                    self.card_prog.emit(idx, 0, "Stopped" if self._stop_evt.is_set() else "Error")
                    print(f"Card {idx} error: {ex}")

            if self._stop_evt.is_set():
                self.done.emit("", "Cancelled", 0)
            else:
                self.progs.emit(100, "Done")
                self.done.emit(",".join(out_paths), "", time.time() - t0)

        except Exception as exc:
            self.done.emit("", str(exc), 0)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(960, 700)
        self.resize(960, 700)
        if os.path.exists(ICON_PATH): self.setWindowIcon(QIcon(ICON_PATH))

        self._cfg = {"dev": "cuda" if CUDA_OK else "cpu", "attn": True,
                     "vae_tile": False, "face_restore": False, "nsfw": True}
        self._ref = None
        self._sessions = load_history()
        self._wk = None; self._owk = []
        self._gen = False; self._last_sd = -1; self._elap = 0
        self._batch_container = None
        self._batch_gallery_paths = {}  # idx -> gallery path

        self.all_items = []

        self._imgs = []
        for s in self._sessions: self._imgs.extend(s.get("imgs", []))

        self._last_prompt=""; self._last_neg=""
        self._last_size="512x512"; self._last_quality="Balanced"
        self._last_batch=1; self._last_seed=-1
        self._last_strength=0.75; self._last_ref=None

        self._t = QTimer(); self._t.setInterval(1000); self._t.timeout.connect(self._tick)

        self._player = None
        if HAS_AUDIO:
            try:
                self._player = QMediaPlayer(); self._audio_out = QAudioOutput()
                self._player.setAudioOutput(self._audio_out)
                snd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notification.mp3")
                if os.path.exists(snd): self._player.setSource(QUrl.fromLocalFile(snd))
            except Exception: self._player = None

        self._build()
        if self._sessions:
            # Reverse sessions to show newest at the top
            for s in reversed(self._sessions):
                self._restore_session(s)
            
    # ── Masonry Helpers ───────────────────────────────────────────────────────
    def update_column_count(self, num_cols):
        if not hasattr(self, 'cols') or len(self.cols) == num_cols:
            return
        while self.masonry_layout.count():
            item = self.masonry_layout.takeAt(0)
            layout = item.layout()
            if layout:
                while layout.count():
                    layout.takeAt(0)
                layout.deleteLater()
                
        self.cols = []
        self.col_heights = [0] * num_cols
        for _ in range(num_cols):
            col = QVBoxLayout()
            col.setSpacing(0)
            col.setContentsMargins(0, 0, 0, 0)
            col.setAlignment(Qt.AlignTop)
            self.masonry_layout.addLayout(col)
            self.cols.append(col)
            
        for card in self.all_items:
            self.add_to_masonry(card, at_top=False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'scroll') and hasattr(self, 'overlay') and self.overlay:
            if self.overlay.parent(): self.overlay.setGeometry(self.scroll.geometry())
            
        if hasattr(self, 'scroll'):
            # Dynamic Columns like freegen_app
            num_cols = 10 if self.isMaximized() or self.width() > 1400 else 5
            if self.width() < 1000: num_cols = 4
            if self.width() < 700: num_cols = 2
            
            self.update_column_count(num_cols)
            
            if hasattr(self, 'cols') and self.cols:
                # 20px margins + 15px scrollbar + safety
                available_w = self.width() - 40
                new_w = max(50, available_w // num_cols)
                for card in self.all_items:
                    card.update_width(new_w)

    def add_to_masonry(self, item, at_top=True):
        if not hasattr(self, 'col_heights') or len(self.col_heights) != len(self.cols):
            self.col_heights = [0] * len(self.cols)

        min_idx = 0
        min_height = self.col_heights[0]
        for i in range(1, len(self.cols)):
            if self.col_heights[i] < min_height:
                min_height = self.col_heights[i]
                min_idx = i
                
        shortest_col = self.cols[min_idx]
        if at_top: shortest_col.insertWidget(0, item)
        else: shortest_col.addWidget(item)
        
        h = item.height() if item.height() > 0 else 180
        self.col_heights[min_idx] += h

    def toggle_max_normal(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def toggle_preview(self, pixmap, show):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        from PySide6.QtCore import QPoint
        if not show:
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.hide()
                self.overlay.deleteLater()
                self.overlay = None
            return

        if show and pixmap:
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.hide()
                self.overlay.deleteLater()
            
            screen = QApplication.primaryScreen()
            screen_geo = screen.geometry()
            screenshot = screen.grabWindow(0)
            
            self.overlay = QFrame()
            self.overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.overlay.setAttribute(Qt.WA_TranslucentBackground)
            self.overlay.setStyleSheet("background: transparent;")
            self.overlay.setGeometry(screen_geo)
            
            self.overlay_bg = QLabel(self.overlay)
            self.overlay_bg.setScaledContents(True)
            self.overlay_bg.setGeometry(0, 0, screen_geo.width(), screen_geo.height())
            self.overlay_bg.setPixmap(screenshot)
            
            self.overlay_blur = QGraphicsBlurEffect()
            self.overlay_blur.setBlurRadius(40)
            self.overlay_bg.setGraphicsEffect(self.overlay_blur)
            
            layout = QVBoxLayout(self.overlay)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            
            self.preview_lbl = QLabel()
            self.preview_lbl.setAlignment(Qt.AlignCenter)
            target_w = screen_geo.width() - 100
            target_h = screen_geo.height() - 100
            self.preview_lbl.setPixmap(pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            self.preview_shadow = QGraphicsDropShadowEffect(blurRadius=60, color=QColor(0,0,0,80), offset=QPoint(0,10))
            self.preview_lbl.setGraphicsEffect(self.preview_shadow)
            
            layout.addWidget(self.preview_lbl)
            self.overlay_bg.show()
            self.overlay_bg.lower()
            
            self.overlay.show()
            self.overlay.activateWindow()
            QApplication.processEvents()

    def delete_card(self, card):
        if card in self.all_items:
            self.all_items.remove(card)
        for i, col in enumerate(self.cols):
            if col.indexOf(card) != -1:
                col.removeWidget(card)
                if hasattr(self, 'col_heights') and i < len(self.col_heights):
                    self.col_heights[i] -= card.height()
                card.deleteLater()
                break
        if os.path.exists(card.path):
            try: os.remove(card.path)
            except: pass

    # ── Restore ───────────────────────────────────────────────────────────────
    def _restore_session(self, sess):
        pr=sess.get("p",""); ng=sess.get("n",""); imgs=sess.get("imgs",[])
        # Reverse images within session to match the 'at_top=True' logic during generation
        for gp in reversed(imgs):
            c = ImageCard(gp, pr)
            c.edit_req.connect(lambda x: (self._set_ref(x), self.inp.setFocus()))
            c.regen_req.connect(self._on_regen)
            c.request_preview.connect(self.toggle_preview)
            c.request_delete.connect(self.delete_card)
            self.all_items.append(c)
            self.add_to_masonry(c, at_top=False)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build(self):
        wdg=QWidget(); wdg.setObjectName("M")
        wdg.setStyleSheet(f"QWidget#M{{background:{C_BG};border:1px solid {C_BORDER};border-radius:10px;}}")
        self.setCentralWidget(wdg)
        vl=QVBoxLayout(wdg); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # ── Title Bar ──────────────────────────────────────────────────────
        tb=QFrame(); tb.setFixedHeight(44)
        tb.setStyleSheet(f"background:{C_PANEL};border-bottom:1px solid {C_BORDER};"
                         f"border-top-left-radius:10px;border-top-right-radius:10px;")
        tl=QHBoxLayout(tb); tl.setContentsMargins(14,0,10,0); tl.setSpacing(6)
        if os.path.exists(ICON_PATH):
            icL=QLabel(); icL.setPixmap(QPixmap(ICON_PATH).scaled(20,20,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            tl.addWidget(icL); tl.addSpacing(4)
        tl.addWidget(s_lbl("SD-Turbo Studio", C_TEXT, 12)); tl.addStretch()

        # Removed tb_seed, tb_rand, tb_reuse
        tl.addWidget(_vsep())

        st=QPushButton("Settings"); st.setFixedHeight(28); st.setStyleSheet(s_btn())
        st.clicked.connect(self._settings); tl.addWidget(st); tl.addSpacing(4)
        for t,f in [("-",self.showMinimized), ("□", self.toggle_max_normal), ("x",self.close)]:
            b=QPushButton(t); b.setFixedSize(30,30)
            b.setStyleSheet(f"QPushButton{{background:transparent;color:{C_MUTED};border:none;font-size:16px;}}"
                            f"QPushButton:hover{{background:{C_DANGER if t=='x' else C_BORDER};color:white;border-radius:15px;}}")
            b.clicked.connect(f); tl.addWidget(b)
        self._dp=None
        tb.mousePressEvent   = lambda e: setattr(self,'_dp',e.globalPosition().toPoint()) if e.button()==Qt.LeftButton else None
        tb.mouseMoveEvent    = lambda e: (self.move(self.pos()+e.globalPosition().toPoint()-self._dp), setattr(self,'_dp',e.globalPosition().toPoint())) if self._dp and e.buttons()&Qt.LeftButton else None
        tb.mouseReleaseEvent = lambda e: setattr(self,'_dp',None)
        vl.addWidget(tb)

        # ── Masonry Grid ──────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.StyledPanel)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea{{background:{C_BG};border:none;}}"
                              f"QScrollBar:vertical{{background:transparent;width:5px;}}"
                              f"QScrollBar::handle:vertical{{background:{C_BORDER};border-radius:2px;}}")
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("GridWidget")
        self.grid_widget.setStyleSheet(f"background:{C_BG};")
        self.grid_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        self.masonry_layout = QHBoxLayout(self.grid_widget)
        self.masonry_layout.setSpacing(0)
        self.masonry_layout.setContentsMargins(0, 0, 0, 0)
        self.masonry_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        
        self.cols = []
        # Initial columns based on window width
        num_cols = 5
        if self.width() < 1000: num_cols = 4
        if self.width() < 700: num_cols = 2
        
        self.col_heights = [0] * num_cols
        for _ in range(num_cols):
            col = QVBoxLayout()
            col.setSpacing(0)
            col.setContentsMargins(0, 0, 0, 0)
            col.setAlignment(Qt.AlignTop)
            self.masonry_layout.addLayout(col)
            self.cols.append(col)
        
        self.scroll.setWidget(self.grid_widget)
        vl.addWidget(self.scroll, 1)

        # Progress bar removed to match freegen_app

        # ── Bottom Bar ────────────────────────────────────────────────────
        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("BottomBar")
        self.bottom_bar.setStyleSheet(f"background:{C_PANEL};border-top:1px solid {C_BORDER};"
                          f"border-bottom-left-radius:10px;border-bottom-right-radius:10px;")
        bar_layout = QHBoxLayout(self.bottom_bar)
        bar_layout.setContentsMargins(14, 12, 14, 12)
        bar_layout.setSpacing(12)

        self.image_frame = QPushButton()
        self.image_frame.setFixedSize(75, 75)
        self.image_frame.setObjectName("ImageFrame")
        self.image_frame.setStyleSheet(f"QPushButton#ImageFrame{{background:{C_USER_B};border:2px dashed {C_MUTED};border-radius:8px;}}"
                                       f"QPushButton#ImageFrame:hover{{border-color:{C_ACC_A};}}")
        self.image_frame.clicked.connect(self._load_ref)
        
        self.image_frame_layout = QVBoxLayout(self.image_frame)
        self.image_frame_layout.setContentsMargins(5, 5, 5, 5)
        
        self.img_preview = QLabel()
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.image_frame_layout.addWidget(self.img_preview)

        self.clear_img_btn = QPushButton("×", self.image_frame)
        self.clear_img_btn.setFixedSize(20, 20)
        self.clear_img_btn.move(55, 0)
        self.clear_img_btn.setObjectName("ClearImgBtn")
        self.clear_img_btn.setStyleSheet(f"QPushButton{{background:rgba(0,0,0,180);color:white;border:none;border-radius:10px;font-weight:bold;}}"
                                         f"QPushButton:hover{{background:{C_DANGER};}}")
        self.clear_img_btn.clicked.connect(self._clr_ref)
        self.clear_img_btn.hide()
        
        bar_layout.addWidget(self.image_frame)

        self.inp = PromptArea()
        self.inp.submitted.connect(self._tog)
        self.inp.installEventFilter(self)
        bar_layout.addWidget(self.inp, 1)

        right_controls = QVBoxLayout()
        right_controls.setSpacing(5)

        self.bg = QPushButton("Generate")
        self.bg.setFixedWidth(120)
        self.bg.setFixedHeight(45)
        self.bg.setStyleSheet(s_vgradient())
        self.bg.clicked.connect(self._tog)

        btn_clr=QPushButton("Clear Chat"); btn_clr.setFixedHeight(45)
        btn_clr.setStyleSheet(f"QPushButton{{background:transparent;color:{C_MUTED};"
                              f"border:1px solid {C_BORDER};border-radius:5px;font-size:11px;padding:0 12px;}}"
                              f"QPushButton:hover{{border-color:{C_DANGER};color:{C_DANGER};}}")
        btn_clr.clicked.connect(self._clear_chat)

        gen_row = QHBoxLayout()
        gen_row.setSpacing(5)
        gen_row.addWidget(self.bg)
        gen_row.addWidget(btn_clr)
        right_controls.addLayout(gen_row)

        # Settings below generate
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(5)
        self.c_q=QComboBox(); self.c_q.addItems(list(QS.keys())); self.c_q.setCurrentIndex(2)
        self.c_q.setStyleSheet(s_combo()); self.c_q.setFixedHeight(26)
        self.c_b=QComboBox(); self.c_b.addItems([str(i) for i in range(1,11)])
        self.c_b.setStyleSheet(s_combo()); self.c_b.setFixedWidth(46); self.c_b.setFixedHeight(26)
        self.c_s=QComboBox(); self.c_s.addItems(SIZES); self.c_s.setCurrentIndex(0)
        self.c_s.setStyleSheet(s_combo()); self.c_s.setFixedHeight(26)
        
        opts_layout.addWidget(self.c_q)
        opts_layout.addWidget(self.c_b)
        opts_layout.addWidget(self.c_s)
        right_controls.addLayout(opts_layout)

        # Strength slider
        str_layout = QHBoxLayout()
        str_layout.addWidget(s_lbl("Str:", C_MUTED, 9))
        self.s_st=QSlider(Qt.Horizontal); self.s_st.setRange(10,95); self.s_st.setValue(75)
        self.s_st.setStyleSheet(f"QSlider::groove:horizontal{{background:{C_BORDER};height:3px;border-radius:1px;}}"
                                f"QSlider::handle:horizontal{{background:{C_ACC_A};width:10px;height:10px;margin:-4px 0;border-radius:5px;}}")
        self.l_st=s_lbl("0.75",C_TEXT,10)
        self.s_st.valueChanged.connect(lambda v: self.l_st.setText(f"{v/100:.2f}"))
        str_layout.addWidget(self.s_st); str_layout.addWidget(self.l_st)
        right_controls.addLayout(str_layout)

        bar_layout.addLayout(right_controls)
        vl.addWidget(self.bottom_bar)
        
        from PySide6.QtWidgets import QSizeGrip
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.setStyleSheet(f"background: transparent;")
        vl.addWidget(self.grip, 0, Qt.AlignRight | Qt.AlignBottom)

    # ── Core ──────────────────────────────────────────────────────────────────
    def eventFilter(self, o, e):
        if o is self.inp and e.type() == QEvent.KeyPress:
            if e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_V:
                if QApplication.clipboard().mimeData().hasImage():
                    img = QApplication.clipboard().image()
                    tmp = os.path.join(tempfile.gettempdir(), f"c_{uuid.uuid4().hex[:5]}.png")
                    img.save(tmp); self._set_ref(tmp); return True
            if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not e.modifiers() & Qt.ShiftModifier:
                self._tog(); return True
        return super().eventFilter(o, e)

    def _enh(self):
        t = self.inp.toPlainText().strip()
        if t and ENHANCE_TAG not in t: self.inp.setPlainText(f"{t}, {ENHANCE_TAG}")

    def _settings(self):
        d = SettingsDialog(self._cfg, self._imgs, self)
        if d.exec(): self._cfg = d.get_cfg()

    def _load_ref(self):
        p, _ = QFileDialog.getOpenFileName(self,"Load Reference","","Images (*.png *.jpg *.jpeg *.webp)")
        if p: self._set_ref(p)

    def _set_ref(self, p):
        self._ref=p
        self.img_preview.setPixmap(QPixmap(p).scaled(65,65,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        self.clear_img_btn.show()
        self.image_frame.setStyleSheet(f"QPushButton#ImageFrame{{background:{C_USER_B};border:1px solid {C_ACC_A};border-style:solid;border-radius:8px;}}")
        self.c_b.setCurrentText("4")

    def _clr_ref(self):
        self._ref=None; self.img_preview.clear()
        self.clear_img_btn.hide(); self.c_b.setCurrentText("1")
        self.image_frame.setStyleSheet(f"QPushButton#ImageFrame{{background:{C_USER_B};border:2px dashed {C_MUTED};border-radius:8px;}}"
                                       f"QPushButton#ImageFrame:hover{{border-color:{C_ACC_A};}}")

    def _scroll_bottom(self):
        QTimer.singleShot(80, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def _clear_chat(self):
        ans=QMessageBox.question(self,"Clear All",
            "Delete all images permanently?",
            QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes: return
        for c in self.all_items:
            try:
                c.deleteLater()
            except Exception: pass
        self.all_items.clear()
        
        while self.masonry_layout.count():
            item = self.masonry_layout.takeAt(0)
            layout = item.layout()
            if layout:
                while layout.count():
                    w = layout.takeAt(0).widget()
                    if w: w.deleteLater()
                    
        for s in self._sessions:
            for p in s.get("imgs",[]):
                try:
                    if os.path.exists(p): os.remove(p)
                except Exception: pass
        self._sessions.clear(); self._imgs.clear()
        save_history([])
        try:
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        except Exception: pass

    def _tog(self):
        if self._gen: self._force_stop()
        else: self._start()

    def _force_stop(self):
        if self._wk:
            self._wk.stop()
            for sig in [self._wk.progs, self._wk.card_prog,
                        self._wk.image_ready, self._wk.done]:
                try: sig.disconnect()
                except Exception: pass
        self._gen=False; self._t.stop()
        self.bg.setText("Generate"); self.bg.setStyleSheet(s_vgradient())
        
        if hasattr(self, '_blur_cards'):
            for bc in self._blur_cards:
                if bc in self.all_items:
                    self.all_items.remove(bc)
                for col in self.cols:
                    if col.indexOf(bc) != -1:
                        col.removeWidget(bc)
                bc.deleteLater()
            self._blur_cards = []

    def _start(self, regen_from=None):
        if regen_from:
            pr=self._last_prompt; ng=self._last_neg; size=self._last_size
            quality=self._last_quality; btc=1; sd=self._last_seed
            strg=self._last_strength; ref=self._last_ref
        else:
            pr=self.inp.toPlainText().strip(); ng="" # Removed negative prompt field
            size=self.c_s.currentText(); quality=self.c_q.currentText()
            btc=int(self.c_b.currentText())
            sd=-1 # Removed seed field
            strg=self.s_st.value()/100.0; ref=self._ref

        if not pr: return

        self._last_prompt=pr; self._last_neg=ng; self._last_size=size
        self._last_quality=quality; self._last_batch=btc; self._last_seed=sd
        self._last_strength=strg; self._last_ref=ref
        self._batch_gallery_paths={}

        w,h=map(int, size.split("x")); stps=QS[quality]

        if not regen_from: self.inp.clear()

        self._gen=True; self._elap=0
        self.bg.setText("Stop"); self.bg.setStyleSheet(s_danger())

        self._blur_cards = []
        for i in range(btc):
            from PySide6.QtWidgets import QFrame # Temporary dummy frame just to hold space if needed, or we just skip this since we're removing PreviewBlurCard
            pass
            
        self._scroll_bottom()

        self._owk=[x for x in self._owk if x.isRunning()]
        self._wk=SDWorker(pr, ng, w, h, stps, ref, strg, btc, sd,
                          self._cfg["dev"], self._cfg["attn"],
                          self._cfg.get("vae_tile",False),
                          self._cfg.get("face_restore",False),
                          self._cfg.get("nsfw", True))
        self._wk.progs.connect(self._prog)
        self._wk.card_prog.connect(self._card_prog)
        self._wk.image_ready.connect(self._on_image_ready)
        self._wk.done.connect(self._done)
        self._wk.start(); self._t.start()

    def _tick(self):
        self._elap+=1

    def _prog(self, p, m):
        pass

    def _card_prog(self, idx, pct, status):
        pass

    def _on_image_ready(self, idx, tmp_path):
        gp=copy_to_gallery(tmp_path)
        self._imgs.append(gp)
        self._batch_gallery_paths[idx]=gp
        
        card = ImageCard(gp, self._last_prompt)
        card.edit_req.connect(lambda x: (self._set_ref(x), self.inp.setFocus()))
        card.regen_req.connect(self._on_regen)
        card.request_preview.connect(self.toggle_preview)
        card.request_delete.connect(self.delete_card)
        
        self.all_items.insert(0, card)
        self.add_to_masonry(card, at_top=True)
        
        # Calculate width dynamically based on current columns
        num_cols = len(self.cols) if self.cols else 5
        available_w = self.width() - 40
        col_width = max(50, available_w // num_cols)
        card.update_width(col_width)
        
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(0))
        QTimer.singleShot(300, card.trigger_glow)

    def _done(self, ps, e, el):
        self._t.stop(); self._gen=False
        self.bg.setText("Generate"); self.bg.setStyleSheet(s_vgradient())
        if self._wk: self._owk.append(self._wk); self._wk=None
        QTimer.singleShot(3000, lambda: setattr(self,'_owk',[w for w in self._owk if w.isRunning()]))

        if hasattr(self, '_blur_cards'):
            for bc in self._blur_cards:
                if bc in self.all_items:
                    self.all_items.remove(bc)
                for col in self.cols:
                    if col.indexOf(bc) != -1:
                        col.removeWidget(bc)
                try: bc.deleteLater()
                except Exception: pass
            self._blur_cards = []

        if self._player:
            try: self._player.setPosition(0); self._player.play()
            except Exception: pass

        if e:
            if e != "Cancelled": print(f"Error: {e}")
            return

        gal_paths=[self._batch_gallery_paths[i]
                   for i in sorted(self._batch_gallery_paths.keys())]
        if gal_paths:
            new_sess={"p":self._last_prompt,"n":self._last_neg,"imgs":gal_paths}
            self._sessions.append(new_sess); save_history(self._sessions)

    def _on_regen(self, img_path):
        if self._gen: return
        self._start(regen_from=img_path)

    def closeEvent(self, e):
        if self._wk and self._wk.isRunning():
            self._wk.stop(); self._wk.wait(3000)
        save_history(self._sessions)
        e.accept(); QApplication.quit()


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"YASSER27.SDTurboStudio.1.0")
    except Exception: pass

    app=QApplication(sys.argv)
    app.setFont(QFont("Segoe UI",9)); app.setStyle("Fusion")
    if os.path.exists(ICON_PATH): app.setWindowIcon(QIcon(ICON_PATH))
    w=MainApp(); w.show()
    sys.exit(app.exec())