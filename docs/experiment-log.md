# 实验记录索引

> 这个仓不只放结论，也放「做过什么」。本文件按实验组列出参数、产物与结论，方便后人不复跑、或只在疑点处复跑。
> 产物（图）不入仓；需要时按本文件的参数重跑。

## 一、基线建立

### E1 二次元底模基线（SDXL 谱系）

- 底模：Illustrious 谱系二次元模型
- 参数：832×1216，28 步，`dpmpp_2m` / `karras`，cfg 6.5，纯 Danbooru tag
- 耗时：12–18 s / 张
- 结论：速度是 20B 级模型的 1/10；纯 tag、无角色 LoRA、无 hires 时画风与角色都对不上。它适合当「快速底图」，不适合直接交成品。

### E2 生成尺寸与耗时标定（Krea 2 Turbo）

| 尺寸 | 像素 | 耗时 |
| --- | --- | --- |
| 1024×1024 | 1.05 MP | 20 s |
| 1024×1536 | 1.57 MP | 45 s |
| 1536×1536 / 2048×1152 | 2.36 MP | 85 s |
| 2560×1440 | 3.69 MP | 143 s |

结论：耗时与像素成正比；2560 长边在 16 GB 卡上不会 OOM，只是慢。日常定 2048×1152。

## 二、画风调校

### E3 七个方向逐个试（Krea 2）

按时间顺序：普通描述 → 加光源/暗部/构图 → 换 Krea 2 → anime 风格 LoRA → `semi-realistic` → `2.5D anime` → 三渲二（`toon-shaded 3D, cel-shaded shadows, clear outline, anime facial proportions`）。

结论：三渲二最接近「游戏引擎渲染感」；负向里写 `3d render` 会把它往外推；`semi-realistic` 推向真人；`illustration / painterly` 拉满手绘感。

### E4 材质提示词对照（七组同 seed）

- 组：基线 / 加 SSS / 加材质区分 / 加硬边阴影 / 加环境反弹 / 加后期 / 全套
- 参数：同 seed、同尺寸、同步数
- 结论：单项收益有限，**材质区分 + 硬边阴影 + 环境反弹**三项同时给才有明显差；后期词（bloom/grain）只影响完成度，不改底层质感。

### E5 风格参考（style reference）

- 链路：Krea 2 Turbo int8 + `krea2_style_reference.safetensors`，1 张参考图，8 步 cfg 1.0
- 尺寸：2048×1152 / 1152×2048
- 结论：参考图选得好时最接近「要这个味」；但它只迁风格与氛围，不保身份。

## 三、角色一致性

### E6 Krea 2 Identity Edit（五次实验）

参数与结果见 [`krea2-identity-edit.md`](krea2-identity-edit.md)。一句话：只会复制源图，不会演绎新姿势；社区参数（cfg 2.5 / 12 步 / KEEP-first）也救不了。

### E7 跨模型低 denoise 重绘

- 做法：Illustrious 底图 → Krea 2 img2img（10 步 cfg 1）
- denoise 0.30 / 0.40 / 0.50：0.30 结构保得住、0.40 可用、**0.50 直接换头**
- 结论：上界低于同模型重绘；保身份必须加 `SetLatentNoiseMask`。

### E8 LoRA 训练尝试

- 数据集：35 张同角色立绘（28 张 ≥1500 宽）+ captions
- 工具链：ai-toolkit（官方示例按显存分档）
- 结果：**卡在内存而不是显存** —— 24.5 GB bf16 权重加载时可用内存跌到 1 GB 级，被 watchdog 杀
- 结论：16 GB 显存能训 2B 级或 SDXL；12.8B 级模型在 32 GB 内存上不可行

## 四、材质专项

### E9 Anima 2B 三组同 seed

| 组 | LoRA | 结果 |
| --- | --- | --- |
| A | 无 | 基线，材质平均 |
| B | SmoothBooster | 皮肤与布料平滑，细节略增 |
| C | SmoothBooster + AddMicroDetails | 材质完成度 7.5/10（参考图记 10） |

参数：832×1216，同 seed，8–10 步。结论：瓶颈是模型对材质与光的理解，不是分辨率或细节 LoRA 强度。

### E10 材质 benchmark 探针

目的：在 Blender 侧确认 normal / AO pass 与 raycast 法线是否可用（给后续材质基准做准备）。结论：Blender 5 的 pass 体系与旧版差异大，改用 raycast 法线（见 `saya-blender-ai`）。

## 五、社区参数复现

### E11 Krea 2 Identity Edit 社区参数

cfg 2.5 / 12 步 / KEEP-first 提示词 / 负向防并排图：结果与 cfg1 版无实质差异。

### E12 提示词写法对照

- 一整段「最高优先级风格约束」vs 规范的 1–2 句风格开场：画风无改善
- 负向写 `no flat colour blocks`：CFG-distilled 模型无负向分支，无效
- 大量形容词堆叠 vs 具体物理描述：后者在材质项上更稳

## 六、待复跑清单

| 项 | 为什么值得复跑 |
| --- | --- |
| nvfp4 vs fp8 同 seed A/B | 精度档的画质损失从未验证 |
| Qwen-Image-Edit 在 16 GB 上的实跑 | 只有文档，没有本机耗时 |
| Anima 2B 角色 LoRA 正式训练 | 目前只有小样本冒烟 |
| 2K 下材质判据的稳定性 | 同一提示词在不同尺寸下的差异未测 |
