<p align="center">
  <img src="img/logo.png" width="150" alt="Edit Img Tool Logo">
  <h1 align="center">SD Turbo Generator</h1>
</p>
<p align="center">

<a href="#النسخة-العربية">النسخة العربية</a>
</p>


> This project is a simple, professional user interface designed for generating images using the SD Turbo model.



![overview](img/40b95a727708fbf9.gif)


## Features

*   **Local Operation:** The application runs entirely offline, requiring no internet connection for operation.
*   **Model Integration:** It integrates with the SD Turbo model by loading the necessary weights from the `sd_turbo_original` directory.
*   **Workflow:** Place the `image_generate` program near the `sd_turbo_original` folder to make the application function correctly.
*   **Generation Limits:** Capable of generating up to 10 images sequentially.
*   **Resolution Range:** Supports image sizes ranging from 256 to 1024 pixels.
*   **Quality Presets:** Offers various quality modes: `turbo`, `fast`, `medium`, `quality`, and `max`.
    *   **Image-to-Image:** Includes an Image-to-Image feature for advanced image manipulation.


| Image | Image |
|---|---|
| ![img_1776555124](img/img_1776555124.png) | ![img_1776624757](img/img_1776624757.png) |



| Image | Image |
|---|---|
| ![img_1777056452](img/img_1777056452.png) | ![img_1777129333](img/img_1777129333.png) |




## Setup

1.  **Download Model:** Download the SD Turbo weights from the official Hugging Face repository: https://huggingface.co/stabilityai/sd-turbo
2.  **Setup Directory:** Place the downloaded `sd_turbo_original` folder in the project directory.
3.  **Run Application:** Place the `image generate` program next to the `sd_turbo_original` folder to run the application.

> [image Generate](https://github.com/YASSER-27/sd-turbo-original/releases)

### ROOT 


![root](img/YA_20260425_161023.png)

```

ROOT:
├── image Generate.exe
└── sd_turbo_original
    ├── ggml.txt
    ├── model_index.json
    ├── scheduler
    │   └── scheduler_config.json
    ├── sd_turbo.safetensors
    ├── text_encoder
    │   ├── config.json
    │   ├── model.fp16.safetensors
    │   └── model.safetensors
    ├── tokenizer
    │   ├── merges.txt
    │   ├── special_tokens_map.json
    │   ├── tokenizer_config.json
    │   └── vocab.json
    ├── unet
    │   ├── config.json
    │   ├── diffusion_pytorch_model.fp16.safetensors
    │   └── diffusion_pytorch_model.safetensors
    └── vae
        ├── config.json
        ├── diffusion_pytorch_model.fp16.safetensors
        └── diffusion_pytorch_model.safetensors

```
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)



> YASSER-27



<h2 id="النسخة-العربية">النسخة العربية</h2>

## نظرة عامة

هذا المشروع هو واجهة بسيطة واحترافية مصممة لتوليد الصور باستخدام نموذج SD Turbo.

## الميزات

*   **العمل دون اتصال:** يعمل التطبيق بالكامل دون اتصال بالإنترنت، ولا يتطلب اتصالاً بالإنترنت للعمل.
*   **تكامل النموذج:** يتكامل مع نموذج SD Turbo عن طريق تحميل الأوزان اللازمة من مجلد `sd_turbo_original`.
*   **سير العمل:** ضع برنامج `image_generate` بالقرب من مجلد `sd_turbo_original` ليعمل التطبيق بشكل صحيح.
*   **حدود التوليد:** قادر على توليد ما يصل إلى 10 صور بالتتابع.
*   **نطاق الدقة:** يدعم أحجام صور تتراوح من 256 إلى 1024 بكسل.
*   **إعدادات الجودة:** يوفر أوضاع جودة مختلفة: `turbo`, `fast`, `medium`, `quality`, و `max`.
    *   **صورة إلى صورة:** يتضمن ميزة صورة إلى صورة لمعالجة الصور المتقدمة.

## الإعداد

1.  **تحميل النموذج:** قم بتحميل أوزان SD Turbo من مستودع Hugging Face الرسمي: https://huggingface.co/stabilityai/sd-turbo
2.  **إعداد المجلد:** ضع مجلد `sd_turbo_original` في مجلد المشروع.
3.  **تشغيل التطبيق:** ضع برنامج `image_generate` بجوار مجلد `sd_turbo_original` لتشغيل التطبيق.

---

![overview](img/overview.png)
